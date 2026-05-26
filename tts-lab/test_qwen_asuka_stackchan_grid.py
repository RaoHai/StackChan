from __future__ import annotations

from pathlib import Path

import soundfile as sf
import torch
from qwen_tts import Qwen3TTSModel


ROOT = Path(r"Y:\StackChan")
BASE = ROOT / "tts-lab" / "qwen_asuka_output_filtered_10ep"
OUT = BASE / "stackchan_grid"


CASES = [
    ("stackchan_katakana", "スタックチャン。"),
    ("stack_chan_pause", "スタック、チャン。"),
    ("stack_chan_hiragana", "すたっくちゃん。"),
    ("stackchan_with_yo", "スタックチャンよ。"),
    ("stackchan_okinasai", "スタックチャン、起きなさい。"),
    ("native_alt", "ねえ、起きてる?"),
]


def load_model(epoch: int) -> Qwen3TTSModel:
    return Qwen3TTSModel.from_pretrained(
        str(BASE / f"checkpoint-epoch-{epoch}"),
        device_map="cuda:0",
        dtype=torch.bfloat16,
        attn_implementation="sdpa",
    )


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for epoch in [3, 5, 7]:
        tts = load_model(epoch)
        for name, text in CASES:
            wavs, sr = tts.generate_custom_voice(
                text=text,
                speaker="asuka",
                language="Japanese",
                do_sample=False,
                repetition_penalty=1.12,
                max_new_tokens=80,
            )
            path = OUT / f"epoch{epoch}_{name}.wav"
            sf.write(path, wavs[0], sr)
            print(path)
        del tts
        torch.cuda.empty_cache()


if __name__ == "__main__":
    main()
