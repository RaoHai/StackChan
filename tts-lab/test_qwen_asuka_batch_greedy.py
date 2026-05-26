from __future__ import annotations

from pathlib import Path

import soundfile as sf
import torch
from qwen_tts import Qwen3TTSModel


ROOT = Path(r"Y:\StackChan")
BASE = ROOT / "tts-lab" / "qwen_asuka_output_filtered_10ep"
CHECKPOINT = BASE / "checkpoint-epoch-5"
OUT = BASE / "batch_greedy"


TEXTS = [
    ("01_antabaka", "あんたバカ? 何やってんのよ。"),
    ("02_hayaku", "ほら、早くしなさいよ。待ってる暇なんてないんだから。"),
    ("03_tsun", "べ、別にあんたのためじゃないわよ。勘違いしないで。"),
    ("04_pride", "私は負けない。絶対に、誰にも負けたりしない。"),
    ("05_short", "信じらんない。"),
    ("06_command", "いいから私の言う通りに動きなさい。"),
    ("07_soft", "少しだけなら、話を聞いてあげてもいいけど。"),
    ("08_angry", "もう、ほんっとにムカつく! どうしてそうなるのよ!"),
    ("09_stackchan", "スタックチャン、今日もちゃんと起きてる?"),
    ("10_chinese", "你在干什么呀，真是笨蛋。"),
]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    tts = Qwen3TTSModel.from_pretrained(
        str(CHECKPOINT),
        device_map="cuda:0",
        dtype=torch.bfloat16,
        attn_implementation="sdpa",
    )
    for name, text in TEXTS:
        wavs, sr = tts.generate_custom_voice(
            text=text,
            speaker="asuka",
            language="Japanese" if name != "10_chinese" else "Chinese",
            do_sample=False,
            repetition_penalty=1.12,
            max_new_tokens=160,
        )
        path = OUT / f"{name}.wav"
        sf.write(path, wavs[0], sr)
        print(path)


if __name__ == "__main__":
    main()
