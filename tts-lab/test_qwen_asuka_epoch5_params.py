from __future__ import annotations

from pathlib import Path

import soundfile as sf
import torch
from qwen_tts import Qwen3TTSModel


ROOT = Path(r"Y:\StackChan")
BASE = ROOT / "tts-lab" / "qwen_asuka_output_filtered_10ep"
CHECKPOINT = BASE / "checkpoint-epoch-5"
TEXT = "あんたバカ? 何やってんのよ。"


SETTINGS = [
    ("steady_t075", dict(temperature=0.75, top_p=0.85, top_k=20, repetition_penalty=1.12, max_new_tokens=80)),
    ("steady_t060", dict(temperature=0.60, top_p=0.80, top_k=15, repetition_penalty=1.15, max_new_tokens=80)),
    ("greedyish", dict(do_sample=False, repetition_penalty=1.12, max_new_tokens=80)),
    (
        "instruct_steady",
        dict(
            temperature=0.70,
            top_p=0.85,
            top_k=20,
            repetition_penalty=1.12,
            max_new_tokens=80,
            instruct="自然で澄んだ少女の声。語尾を伸ばさず、短くはっきり話す。",
        ),
    ),
]


def main() -> None:
    tts = Qwen3TTSModel.from_pretrained(
        str(CHECKPOINT),
        device_map="cuda:0",
        dtype=torch.bfloat16,
        attn_implementation="sdpa",
    )
    for name, kwargs in SETTINGS:
        wavs, sr = tts.generate_custom_voice(text=TEXT, speaker="asuka", language="Japanese", **kwargs)
        out = BASE / f"asuka_test_epoch5_{name}.wav"
        sf.write(out, wavs[0], sr)
        print(out)


if __name__ == "__main__":
    main()
