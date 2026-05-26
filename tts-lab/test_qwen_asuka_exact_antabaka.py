from __future__ import annotations

from pathlib import Path

import soundfile as sf
import torch
from qwen_tts import Qwen3TTSModel


ROOT = Path(r"Y:\StackChan")
CHECKPOINT = ROOT / "tts-lab" / "qwen_asuka_output_clean_5ep" / "checkpoint-epoch-3"
OUT = ROOT / "tts-lab" / "qwen_asuka_output_clean_5ep" / "analysis" / "generated_exact_antabaka.wav"


def main() -> None:
    tts = Qwen3TTSModel.from_pretrained(
        str(CHECKPOINT),
        device_map="cuda:0",
        dtype=torch.bfloat16,
        attn_implementation="sdpa",
    )
    wavs, sr = tts.generate_custom_voice(
        text="あんたバカ?",
        speaker="asuka",
        language="Japanese",
        do_sample=False,
        repetition_penalty=1.12,
        max_new_tokens=80,
    )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    sf.write(OUT, wavs[0], sr)
    print(OUT)


if __name__ == "__main__":
    main()
