/*
 * SPDX-FileCopyrightText: 2026 M5Stack Technology CO LTD
 *
 * SPDX-License-Identifier: MIT
 */
#include "akusa.h"

using namespace uitk;
using namespace uitk::lvgl_cpp;
using namespace stackchan::avatar;

LV_IMAGE_DECLARE(akusa_face_neutral);
LV_IMAGE_DECLARE(akusa_face_happy);
LV_IMAGE_DECLARE(akusa_face_angry);
LV_IMAGE_DECLARE(akusa_face_sad);
LV_IMAGE_DECLARE(akusa_face_doubt);
LV_IMAGE_DECLARE(akusa_face_sleepy);

AkusaImageFeature::AkusaImageFeature(AkusaAvatar& avatar, Role role) : _avatar(avatar), _role(role)
{
}

void AkusaImageFeature::setPosition(const Vector2i& position)
{
    Element::setPosition(position);
}

void AkusaImageFeature::setWeight(int weight)
{
    Feature::setWeight(weight);
    if (_role == Role::Mouth) {
        _avatar.setMouthWeight(_weight);
    }
}

void AkusaImageFeature::setRotation(int rotation)
{
    Element::setRotation(rotation);
}

void AkusaImageFeature::setEmotion(const Emotion& emotion)
{
    if (!getIgnoreEmotion()) {
        _avatar.setEmotion(emotion);
    }
}

Emotion AkusaImageFeature::getEmotion() const
{
    return _avatar.getFrameEmotion();
}

void AkusaImageFeature::setVisible(bool visible)
{
    Element::setVisible(visible);
}

void AkusaImageFeature::setSize(int size)
{
    Feature::setSize(size);
}

void AkusaAvatar::init(lv_obj_t* parent, const lv_font_t* font)
{
    _panel = std::make_unique<Container>(parent);
    _panel->align(LV_ALIGN_CENTER, 0, 0);
    _panel->setSize(320, 240);
    _panel->setRadius(0);
    _panel->setBorderWidth(0);
    _panel->setBgColor(secondaryColor);
    _panel->removeFlag(LV_OBJ_FLAG_SCROLLABLE);

    _sprite = std::make_unique<Image>(_panel->get());
    _sprite->setAlign(LV_ALIGN_CENTER);
    _sprite->setPos(0, 0);

    _key_elements.leftEye = std::make_unique<AkusaImageFeature>(*this, AkusaImageFeature::Role::LeftEye);
    _key_elements.rightEye = std::make_unique<AkusaImageFeature>(*this, AkusaImageFeature::Role::RightEye);
    _key_elements.mouth = std::make_unique<AkusaImageFeature>(*this, AkusaImageFeature::Role::Mouth);
    _key_elements.speechBubble =
        std::make_unique<DefaultSpeechBubble>(_panel->get(), primaryColor, secondaryColor, font);

    updateFrame();
}

void AkusaAvatar::setEmotion(const Emotion& emotion)
{
    _emotion = emotion;
    updateFrame();
}

void AkusaAvatar::setMouthWeight(int weight)
{
    _mouth_weight = clamp(weight, 0, 100);
    updateFrame();
}

Emotion AkusaAvatar::getFrameEmotion() const
{
    return getEmotion();
}

void AkusaAvatar::updateFrame()
{
    if (!_sprite) {
        return;
    }

    const lv_image_dsc_t* frame = &akusa_face_neutral;
    switch (getEmotion()) {
        case Emotion::Happy:
            frame = &akusa_face_happy;
            break;
        case Emotion::Angry:
            frame = &akusa_face_angry;
            break;
        case Emotion::Sad:
            frame = &akusa_face_sad;
            break;
        case Emotion::Doubt:
            frame = &akusa_face_doubt;
            break;
        case Emotion::Sleepy:
            frame = &akusa_face_sleepy;
            break;
        case Emotion::Neutral:
        default:
            frame = _mouth_weight >= 35 ? &akusa_face_happy : &akusa_face_neutral;
            break;
    }
    _sprite->setSrc(frame);
}

Container* AkusaAvatar::getPanel() const
{
    if (_panel) {
        return _panel.get();
    }
    return nullptr;
}
