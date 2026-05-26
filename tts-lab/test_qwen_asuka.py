from __future__ import annotations

from pathlib import Path

import soundfile as sf
import torch
from qwen_tts import Qwen3TTSModel


ROOT = Path(r"Y:\StackChan")
CHECKPOINT = ROOT / "tts-lab" / "qwen_asuka_output" / "checkpoint-epoch-0"
OUT = ROOT / "tts-lab" / "qwen_asuka_output" / "asuka_test_epoch0.wav"


def main() -> None:
    tts = Qwen3TTSModel.from_pretrained(
        str(CHECKPOINT),
        device_map="cuda:0",
        dtype=torch.bfloat16,
        attn_implementation="sdpa",
    )
    wavs, sr = tts.generate_custom_voice(
        text="あんたバカ? 何やってんのよ。",
        speaker="asuka",
    )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    sf.write(OUT, wavs[0], sr)
    print(OUT)


if __name__ == "__main__":
    main()
