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

class DoggyStaticFeature : public Feature {
public:
    explicit DoggyStaticFeature(lv_obj_t* parent);
    ~DoggyStaticFeature();

    void setPosition(const uitk::Vector2i& position) override;
    void setWeight(int weight) override;
    void setRotation(int rotation) override;
    void setEmotion(const Emotion& emotion) override;
    void setVisible(bool visible) override;
    void setSize(int size) override;

private:
    std::unique_ptr<uitk::lvgl_cpp::Container> _anchor;
};

class DoggyAvatar : public Avatar {
public:
    lv_color_t primaryColor   = lv_color_hex(0x26313C);
    lv_color_t secondaryColor = lv_color_hex(0xBFEAD2);

    void init(lv_obj_t* parent, const lv_font_t* font = &lv_font_montserrat_16);
    uitk::lvgl_cpp::Container* getPanel() const;

private:
    std::unique_ptr<uitk::lvgl_cpp::Container> _panel;
    std::unique_ptr<uitk::lvgl_cpp::Image> _sprite;
};

}  // namespace stackchan::avatar
