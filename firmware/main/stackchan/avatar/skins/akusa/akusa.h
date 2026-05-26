/*
 * SPDX-FileCopyrightText: 2026 M5Stack Technology CO LTD
 *
 * SPDX-License-Identifier: MIT
 */
#pragma once
#include "../../avatar/avatar.h"
#include "../../avatar/elements/feature.h"
#include "../default/default.h"
#include <lvgl.h>
#include <smooth_lvgl.hpp>
#include <memory>

namespace stackchan::avatar {

class AkusaAvatar;

class AkusaImageFeature : public Feature {
public:
    enum class Role {
        LeftEye,
        RightEye,
        Mouth,
    };

    AkusaImageFeature(AkusaAvatar& avatar, Role role);
    ~AkusaImageFeature() override = default;

    void setPosition(const uitk::Vector2i& position) override;
    void setWeight(int weight) override;
    void setRotation(int rotation) override;
    void setEmotion(const Emotion& emotion) override;
    Emotion getEmotion() const override;
    void setVisible(bool visible) override;
    void setSize(int size) override;

private:
    AkusaAvatar& _avatar;
    Role _role = Role::Mouth;
};

class AkusaAvatar : public Avatar {
public:
    lv_color_t primaryColor   = lv_color_hex(0x26313C);
    lv_color_t secondaryColor = lv_color_hex(0xBFEAD2);

    void init(lv_obj_t* parent, const lv_font_t* font = &lv_font_montserrat_16);
    void setEmotion(const Emotion& emotion) override;
    void setMouthWeight(int weight);
    Emotion getFrameEmotion() const;
    uitk::lvgl_cpp::Container* getPanel() const;

private:
    void updateFrame();

    std::unique_ptr<uitk::lvgl_cpp::Container> _panel;
    std::unique_ptr<uitk::lvgl_cpp::Image> _sprite;
    int _mouth_weight = 0;
};

}  // namespace stackchan::avatar
