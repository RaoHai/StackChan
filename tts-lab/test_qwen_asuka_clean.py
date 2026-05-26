from __future__ import annotations

from pathlib import Path

import soundfile as sf
import torch
from qwen_tts import Qwen3TTSModel


ROOT = Path(r"Y:\StackChan")
BASE = ROOT / "tts-lab" / "qwen_asuka_output_clean_5ep"
OUT = BASE / "tests"
EPOCHS = [2, 3, 4]
CASES = [
    ("antabaka", "あんたバカ? 何やってんのよ。"),
    ("command", "いいから私の言う通りに動きなさい。"),
    ("angry_low", "バカね。次はちゃんとしなさいよ。"),
    ("native_alt", "ねえ、起きてる?"),
    ("chinese_ja", "なにしてるのよ、ほんとバカね。"),
]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for epoch in EPOCHS:
        tts = Qwen3TTSModel.from_pretrained(
            str(BASE / f"checkpoint-epoch-{epoch}"),
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
                max_new_tokens=120,
            )
            path = OUT / f"epoch{epoch}_{name}.wav"
            sf.write(path, wavs[0], sr)
            print(path)
        del tts
        torch.cuda.empty_cache()


if __name__ == "__main__":
    main()
