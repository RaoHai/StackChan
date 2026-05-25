/*
 * SPDX-FileCopyrightText: 2026 M5Stack Technology CO LTD
 *
 * SPDX-License-Identifier: MIT
 */
#include "app_track.h"
#include <hal/hal.h>
#include <hal/board/hal_bridge.h>
#include <mooncake.h>
#include <mooncake_log.h>
#include <stackchan/stackchan.h>
#include <smooth_lvgl.hpp>
#include <cstdint>
#include <cstring>
#include <cstdio>
#include <cmath>
#include <memory>

using namespace mooncake;
using namespace smooth_ui_toolkit::lvgl_cpp;
using namespace stackchan;

/* --------------------------- Tunable parameters --------------------------- */
// Downsampled detection grid. Tiny on purpose: cheap and noise-tolerant.
static constexpr int GRID_W = 32;
static constexpr int GRID_H = 24;

// Per-cell luma delta (0-255) to count a cell as "moving".
static constexpr int DIFF_THRESH = 18;
// Minimum number of moving cells before we trust there's a real subject.
static constexpr int MIN_MOTION_CELLS = 6;

// Normalized centre offset below which we consider the subject centred enough.
static constexpr float DEADZONE = 0.08f;

// Proportional gain: normalized error (max 0.5) -> servo angle delta.
static constexpr float KP_YAW   = 600.0f;
static constexpr float KP_PITCH = 350.0f;
// Cap a single correction step so the head never lurches.
static constexpr int MAX_STEP_YAW   = 300;
static constexpr int MAX_STEP_PITCH = 180;
static constexpr int MOVE_SPEED     = 400;  // 0-1000

// Direction calibration. If the head chases AWAY from the subject on an axis,
// flip that sign. Camera mounting / mirror / flip decide the correct values.
static constexpr int YAW_SIGN   = 1;
static constexpr int PITCH_SIGN = -1;

// Pacing.
static constexpr uint32_t FRAME_INTERVAL_MS = 50;   // between detections while still
static constexpr uint32_t SETTLE_MS         = 350;  // wait for head to stop after a move

// Camera pixel formats (standard V4L2 FourCC, avoids pulling in videodev2.h).
static constexpr uint32_t FMT_YUYV   = 0x56595559;  // 'YUYV'
static constexpr uint32_t FMT_RGB565 = 0x50424752;  // 'RGBP'
static constexpr uint32_t FMT_RGB24  = 0x33424752;  // 'RGB3'
static constexpr uint32_t FMT_GREY   = 0x59455247;  // 'GREY'

/* -------------------------------- State ----------------------------------- */
static std::unique_ptr<Button> _button_quit;
static std::unique_ptr<Label> _status_label;
static uint8_t _grid_prev[GRID_W * GRID_H];
static uint8_t _grid_cur[GRID_W * GRID_H];
static uint32_t _next_action_ms = 0;
static bool _need_baseline      = true;
static bool _warned_fmt         = false;

static inline int clampi(int v, int lo, int hi)
{
    return v < lo ? lo : (v > hi ? hi : v);
}

// Extract an 8-bit luma value for one source pixel.
static inline uint8_t luma_at(const uint8_t* d, int w, int x, int y, uint32_t fmt)
{
    switch (fmt) {
        case FMT_YUYV:
            return d[((y * w) + x) * 2];  // Y is the even byte of each YUYV pair
        case FMT_RGB565: {
            int i        = ((y * w) + x) * 2;
            uint16_t px  = (uint16_t)(d[i] | (d[i + 1] << 8));  // little-endian
            int r        = (px >> 11) & 0x1F;
            int g        = (px >> 5) & 0x3F;
            int b        = px & 0x1F;
            return (uint8_t)(((r * 630) + (g * 609) + (b * 240)) >> 8);
        }
        case FMT_RGB24: {
            int i = ((y * w) + x) * 3;
            return (uint8_t)(((d[i] * 77) + (d[i + 1] * 150) + (d[i + 2] * 29)) >> 8);
        }
        case FMT_GREY:
            return d[(y * w) + x];
        default:
            return 0;
    }
}

static void set_status(const char* text)
{
    if (!_status_label) {
        return;
    }
    LvglLockGuard lock;
    _status_label->setText(text);
}

AppTrack::AppTrack()
{
    setAppInfo().name = "TRACK";
    static uint32_t theme_color = 0x33CCFF;
    setAppInfo().userData       = (void*)&theme_color;
}

void AppTrack::onCreate()
{
    mclog::tagInfo(getAppInfo().name, "on create");
}

void AppTrack::onOpen()
{
    mclog::tagInfo(getAppInfo().name, "on open");

    _need_baseline  = true;
    _next_action_ms = 0;
    _warned_fmt     = false;

    {
        LvglLockGuard lock;

        _status_label = std::make_unique<Label>(lv_screen_active());
        _status_label->setAlign(LV_ALIGN_TOP_MID);
        _status_label->setPos(0, 20);
        _status_label->setText("Tracking motion...");

        _button_quit = std::make_unique<Button>(lv_screen_active());
        _button_quit->setAlign(LV_ALIGN_BOTTOM_MID);
        _button_quit->setPos(0, -20);
        _button_quit->label().setText("QUIT");
        _button_quit->onClick().connect([this]() { close(); });
    }

    // Hold position firmly while tracking; restore default on close.
    GetStackChan().motion().setAutoTorqueReleaseEnabled(false);
}

void AppTrack::onRunning()
{
    // Advance the servo spring animation (no avatar attached, so no LVGL needed).
    GetStackChan().update();

    uint32_t now = GetHAL().millis();
    if (now < _next_action_ms) {
        return;
    }

    auto camera = hal_bridge::board_get_camera();
    if (!camera) {
        _next_action_ms = now + 200;
        return;
    }
    if (!camera->StreamCaptures()) {
        _next_action_ms = now + 100;
        return;
    }

    const uint8_t* data = camera->GetFrameData();
    int w               = camera->GetFrameWidth();
    int h               = camera->GetFrameHeight();
    uint32_t fmt        = (uint32_t)camera->GetFrameFormat();
    if (!data || w <= 0 || h <= 0) {
        _next_action_ms = now + 100;
        return;
    }
    if (fmt != FMT_YUYV && fmt != FMT_RGB565 && fmt != FMT_RGB24 && fmt != FMT_GREY) {
        if (!_warned_fmt) {
            mclog::tagWarn(getAppInfo().name, "unsupported camera format: 0x{:08x}", fmt);
            _warned_fmt = true;
        }
        set_status("Unsupported camera format");
        _next_action_ms = now + 1000;
        return;
    }

    // Sample the frame into the downsampled luma grid.
    for (int gy = 0; gy < GRID_H; gy++) {
        int sy = (gy * h) / GRID_H;
        for (int gx = 0; gx < GRID_W; gx++) {
            int sx                       = (gx * w) / GRID_W;
            _grid_cur[(gy * GRID_W) + gx] = luma_at(data, w, sx, sy, fmt);
        }
    }

    // First frame after open / after a move becomes the comparison baseline.
    if (_need_baseline) {
        memcpy(_grid_prev, _grid_cur, sizeof(_grid_cur));
        _need_baseline  = false;
        _next_action_ms = now + FRAME_INTERVAL_MS;
        return;
    }

    // Frame difference -> weighted centroid of motion.
    long sum_w = 0, sum_x = 0, sum_y = 0;
    int cells  = 0;
    for (int gy = 0; gy < GRID_H; gy++) {
        for (int gx = 0; gx < GRID_W; gx++) {
            int idx = (gy * GRID_W) + gx;
            int d   = _grid_cur[idx] - _grid_prev[idx];
            if (d < 0) {
                d = -d;
            }
            if (d > DIFF_THRESH) {
                sum_w += d;
                sum_x += (long)d * gx;
                sum_y += (long)d * gy;
                cells++;
            }
        }
    }
    memcpy(_grid_prev, _grid_cur, sizeof(_grid_cur));

    if (cells < MIN_MOTION_CELLS || sum_w <= 0) {
        _next_action_ms = now + FRAME_INTERVAL_MS;
        return;
    }

    float cx = (float)sum_x / (float)sum_w;  // 0 .. GRID_W-1
    float cy = (float)sum_y / (float)sum_w;  // 0 .. GRID_H-1
    float ex = (cx / (float)(GRID_W - 1)) - 0.5f;  // -0.5 .. 0.5
    float ey = (cy / (float)(GRID_H - 1)) - 0.5f;

    int dyaw   = (fabsf(ex) > DEADZONE) ? clampi((int)(YAW_SIGN * KP_YAW * ex), -MAX_STEP_YAW, MAX_STEP_YAW) : 0;
    int dpitch = (fabsf(ey) > DEADZONE) ? clampi((int)(PITCH_SIGN * KP_PITCH * ey), -MAX_STEP_PITCH, MAX_STEP_PITCH) : 0;

    bool moved = false;
    if (dyaw != 0 || dpitch != 0) {
        auto& m = GetStackChan().motion();
        m.moveWithSpeed(m.getCurrentYawAngle() + dyaw, m.getCurrentPitchAngle() + dpitch, MOVE_SPEED);
        moved = true;
    }

    char buf[64];
    snprintf(buf, sizeof(buf), "x:%+.2f y:%+.2f%s", ex, ey, moved ? " >>" : "");
    set_status(buf);

    if (moved) {
        _need_baseline  = true;        // discard the next frame: it captures our own motion
        _next_action_ms = now + SETTLE_MS;
    } else {
        _next_action_ms = now + FRAME_INTERVAL_MS;
    }
}

void AppTrack::onClose()
{
    mclog::tagInfo(getAppInfo().name, "on close");

    GetStackChan().motion().setAutoTorqueReleaseEnabled(true);

    LvglLockGuard lock;
    _button_quit.reset();
    _status_label.reset();
}
