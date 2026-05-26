from __future__ import annotations

from pathlib import Path

import soundfile as sf
import torch
from qwen_tts import Qwen3TTSModel


ROOT = Path(r"Y:\StackChan")
BASE = ROOT / "tts-lab" / "qwen_asuka_output_filtered_10ep"
CHECKPOINT = BASE / "checkpoint-epoch-5"
OUT = BASE / "stability_variants"


CASES = [
    ("angry_low_01", "もう、何やってんのよ。ほんとに信じらんない。", "Japanese", ""),
    ("angry_low_02", "バカね。次はちゃんとしなさいよ。", "Japanese", ""),
    ("stackchan_kana_01", "スタックチャン、起きてる?", "Japanese", ""),
    ("stackchan_kana_02", "スタックチャン、今日もよろしくね。", "Japanese", ""),
    ("chinese_cn_01", "你在干什么呀，真是笨蛋。", "Chinese", ""),
    ("chinese_ja_01", "なにしてるのよ、ほんとバカね。", "Japanese", ""),
    (
        "instruct_female_01",
        "スタックチャン、今日もよろしくね。",
        "Japanese",
        "若い女性の声。短く、自然に、語尾を変に伸ばさずに話す。",
    ),
]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    tts = Qwen3TTSModel.from_pretrained(
        str(CHECKPOINT),
        device_map="cuda:0",
        dtype=torch.bfloat16,
        attn_implementation="sdpa",
    )
    for name, text, language, instruct in CASES:
        kwargs = {
            "text": text,
            "speaker": "asuka",
            "language": language,
            "do_sample": False,
            "repetition_penalty": 1.12,
            "max_new_tokens": 120,
        }
        if instruct:
            kwargs["instruct"] = instruct
        wavs, sr = tts.generate_custom_voice(**kwargs)
        path = OUT / f"{name}.wav"
        sf.write(path, wavs[0], sr)
        print(path)


if __name__ == "__main__":
    main()
