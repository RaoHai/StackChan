/*
 * SPDX-FileCopyrightText: 2026 M5Stack Technology CO LTD
 *
 * SPDX-License-Identifier: MIT
 */
#include "doggy.h"

using namespace uitk;
using namespace uitk::lvgl_cpp;
using namespace stackchan::avatar;

LV_IMAGE_DECLARE(doggy_face);

DoggyStaticFeature::DoggyStaticFeature(lv_obj_t* parent)
{
    _anchor = std::make_unique<Container>(parent);
    _anchor->setSize(1, 1);
    _anchor->setRadius(0);
    _anchor->setBorderWidth(0);
    _anchor->setBgOpa(0);
    _anchor->setAlign(LV_ALIGN_CENTER);
    _anchor->removeFlag(LV_OBJ_FLAG_SCROLLABLE);
}

DoggyStaticFeature::~DoggyStaticFeature()
{
    _anchor.reset();
}

void DoggyStaticFeature::setPosition(const Vector2i& position)
{
    Element::setPosition(position);
}

void DoggyStaticFeature::setWeight(int weight)
{
    Feature::setWeight(weight);
}

void DoggyStaticFeature::setRotation(int rotation)
{
    Element::setRotation(rotation);
}

void DoggyStaticFeature::setEmotion(const Emotion& emotion)
{
    (void)emotion;
}

void DoggyStaticFeature::setVisible(bool visible)
{
    Element::setVisible(visible);
    _anchor->setHidden(!visible);
}

void DoggyStaticFeature::setSize(int size)
{
    Feature::setSize(size);
}

void DoggyAvatar::init(lv_obj_t* parent, const lv_font_t* font)
{
    _panel = std::make_unique<Container>(parent);
    _panel->align(LV_ALIGN_CENTER, 0, 0);
    _panel->setSize(320, 240);
    _panel->setRadius(0);
    _panel->setBorderWidth(0);
    _panel->setBgColor(secondaryColor);
    _panel->removeFlag(LV_OBJ_FLAG_SCROLLABLE);

    _sprite = std::make_unique<Image>(_panel->get());
    _sprite->setSrc(&doggy_face);
    _sprite->setAlign(LV_ALIGN_CENTER);
    _sprite->setPos(0, 0);

    _key_elements.leftEye  = std::make_unique<DoggyStaticFeature>(_panel->get());
    _key_elements.rightEye = std::make_unique<DoggyStaticFeature>(_panel->get());
    _key_elements.mouth    = std::make_unique<DoggyStaticFeature>(_panel->get());
    _key_elements.speechBubble =
        std::make_unique<DefaultSpeechBubble>(_panel->get(), primaryColor, secondaryColor, font);
}

Container* DoggyAvatar::getPanel() const
{
    if (_panel) {
        return _panel.get();
    }
    return nullptr;
}
