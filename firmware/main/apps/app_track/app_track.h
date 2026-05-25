/*
 * SPDX-FileCopyrightText: 2026 M5Stack Technology CO LTD
 *
 * SPDX-License-Identifier: MIT
 */
#pragma once
#include <mooncake.h>

/**
 * @brief Motion-following app.
 *
 * Detects the moving subject in the camera frame via frame differencing and
 * steers the head (yaw/pitch) to keep it centered.
 */
class AppTrack : public mooncake::AppAbility {
public:
    AppTrack();

    void onCreate() override;
    void onOpen() override;
    void onRunning() override;
    void onClose() override;
};
