from __future__ import annotations

from pathlib import Path

import librosa
import numpy as np
import soundfile as sf
import torch
from qwen_tts import Qwen3TTSModel


ROOT = Path(r"Y:\StackChan")
BASE = ROOT / "tts-lab" / "qwen_asuka_output_clean3_bright2"
OUT = BASE / "tests"
CHECKPOINTS = [0, 1]
CASES = [
    ("antabaka_exact", "あんたバカ?"),
    ("antabaka_long", "あんたバカ? 何やってんのよ。"),
    ("short_tsk", "信じらんない。ほんとバカね。"),
    ("hurry", "ほら、早くしなさいよ。"),
    ("question", "ねえ、あんた本当にわかってるの?"),
]


def audio_metrics(path: Path) -> tuple[float, float]:
    y, sr = librosa.load(path, sr=24000, mono=True)
    y, _ = librosa.effects.trim(y, top_db=35)
    f0 = librosa.yin(y, fmin=120, fmax=900, sr=sr)
    f0 = f0[np.isfinite(f0)]
    f0 = f0[(f0 > 120) & (f0 < 900)]
    f0_med = float(np.median(f0)) if len(f0) else float("nan")
    centroid = float(np.mean(librosa.feature.spectral_centroid(y=y, sr=sr)))
    return f0_med, centroid


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for epoch in CHECKPOINTS:
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
            f0_med, centroid = audio_metrics(path)
            print(path)
            print(f"  f0_med={f0_med:.1f}Hz centroid={centroid:.0f}Hz")
        del tts
        torch.cuda.empty_cache()


if __name__ == "__main__":
    main()
