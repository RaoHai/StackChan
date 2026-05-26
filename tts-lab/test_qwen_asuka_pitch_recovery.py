from __future__ import annotations

from pathlib import Path

import librosa
import numpy as np
import soundfile as sf
import torch
from qwen_tts import Qwen3TTSModel


ROOT = Path(r"Y:\StackChan")
BASE = ROOT / "tts-lab" / "qwen_asuka_output_filtered_10ep"
CHECKPOINT = BASE / "checkpoint-epoch-5"
OUT = BASE / "pitch_recovery"
TEXT = "あんたバカ? 何やってんのよ。"


SETTINGS = [
    ("sample_k08_p065_t055", dict(do_sample=True, top_k=8, top_p=0.65, temperature=0.55, repetition_penalty=1.15, max_new_tokens=80)),
    ("sample_k10_p070_t060", dict(do_sample=True, top_k=10, top_p=0.70, temperature=0.60, repetition_penalty=1.15, max_new_tokens=80)),
    ("sample_k12_p075_t065", dict(do_sample=True, top_k=12, top_p=0.75, temperature=0.65, repetition_penalty=1.15, max_new_tokens=80)),
    ("sample_k16_p080_t070", dict(do_sample=True, top_k=16, top_p=0.80, temperature=0.70, repetition_penalty=1.12, max_new_tokens=80)),
    ("sample_k10_p070_t060_rep120", dict(do_sample=True, top_k=10, top_p=0.70, temperature=0.60, repetition_penalty=1.20, max_new_tokens=80)),
]


def metrics(path: Path) -> tuple[float, float, float]:
    y, sr = librosa.load(path, sr=24000, mono=True)
    y, _ = librosa.effects.trim(y, top_db=35)
    centroid = float(np.mean(librosa.feature.spectral_centroid(y=y, sr=sr)))
    f0, _, _ = librosa.pyin(y, fmin=librosa.note_to_hz("C3"), fmax=librosa.note_to_hz("C6"), sr=sr)
    voiced = f0[~np.isnan(f0)]
    f0_med = float(np.median(voiced)) if len(voiced) else float("nan")
    f0_p90 = float(np.percentile(voiced, 90)) if len(voiced) else float("nan")
    return f0_med, f0_p90, centroid


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    tts = Qwen3TTSModel.from_pretrained(
        str(CHECKPOINT),
        device_map="cuda:0",
        dtype=torch.bfloat16,
        attn_implementation="sdpa",
    )
    for name, kwargs in SETTINGS:
        wavs, sr = tts.generate_custom_voice(
            text=TEXT,
            speaker="asuka",
            language="Japanese",
            **kwargs,
        )
        path = OUT / f"{name}.wav"
        sf.write(path, wavs[0], sr)
        f0_med, f0_p90, centroid = metrics(path)
        print(path)
        print(f"  f0_med={f0_med:.1f}Hz f0_p90={f0_p90:.1f}Hz centroid={centroid:.0f}Hz")


if __name__ == "__main__":
    main()
