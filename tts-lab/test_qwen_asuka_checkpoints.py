from __future__ import annotations

from pathlib import Path

import soundfile as sf
import torch
from qwen_tts import Qwen3TTSModel


ROOT = Path(r"Y:\StackChan")
BASE = ROOT / "tts-lab" / "qwen_asuka_output_filtered_10ep"
TEXT = "あんたバカ? 何やってんのよ。"
EPOCHS = [3, 5, 7, 9]


def main() -> None:
    for epoch in EPOCHS:
        checkpoint = BASE / f"checkpoint-epoch-{epoch}"
        tts = Qwen3TTSModel.from_pretrained(
            str(checkpoint),
            device_map="cuda:0",
            dtype=torch.bfloat16,
            attn_implementation="sdpa",
        )
        wavs, sr = tts.generate_custom_voice(text=TEXT, speaker="asuka")
        out = BASE / f"asuka_test_epoch{epoch}.wav"
        sf.write(out, wavs[0], sr)
        print(out)
        del tts
        torch.cuda.empty_cache()


if __name__ == "__main__":
    main()
