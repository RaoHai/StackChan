from __future__ import annotations

from pathlib import Path

import soundfile as sf
import torch
from qwen_tts import Qwen3TTSModel


ROOT = Path(r"Y:\StackChan")
BASE = ROOT / "tts-lab" / "qwen_asuka_output_clean_5ep"
CHECKPOINT = BASE / "checkpoint-epoch-3"
OUT = BASE / "epoch3_batch"


CASES = [
    ("01_antabaka", "あんたバカ? 何やってんのよ。"),
    ("02_short_tsk", "信じらんない。ほんとバカね。"),
    ("03_hurry", "ほら、早くしなさいよ。待ってる暇なんてないんだから。"),
    ("04_command", "いいから私の言う通りに動きなさい。"),
    ("05_soft", "少しだけなら、話を聞いてあげてもいいけど。"),
    ("06_pride", "私は負けない。絶対に、誰にも負けたりしない。"),
    ("07_mild_angry", "もう、何やってんのよ。ちゃんとしなさい。"),
    ("08_question", "ねえ、あんた本当にわかってるの?"),
    ("09_native_alt", "ねえ、起きてる? 返事しなさいよ。"),
    ("10_misato", "ミサト、ちゃんと説明してくれるんでしょうね。"),
    ("11_shinji", "シンジ、ぼさっとしてないで手伝いなさい。"),
    ("12_stack_alt", "ほら、今日もちゃんと起きなさいよ。"),
    ("13_longer", "まったく、どうしてこう毎回毎回、私が面倒を見なきゃいけないのよ。"),
    ("14_greeting", "おはよう。今日くらいは少しまともにやりなさいよ。"),
    ("15_praise", "まあ、今のは少しだけよかったんじゃない?"),
]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    tts = Qwen3TTSModel.from_pretrained(
        str(CHECKPOINT),
        device_map="cuda:0",
        dtype=torch.bfloat16,
        attn_implementation="sdpa",
    )
    for name, text in CASES:
        wavs, sr = tts.generate_custom_voice(
            text=text,
            speaker="asuka",
            language="Japanese",
            do_sample=False,
            repetition_penalty=1.12,
            max_new_tokens=160,
        )
        path = OUT / f"{name}.wav"
        sf.write(path, wavs[0], sr)
        print(path)


if __name__ == "__main__":
    main()
