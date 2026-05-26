from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

import librosa
import numpy as np
import soundfile as sf


ROOT = Path(r"Y:\StackChan")
SOURCE = ROOT / "tts-lab" / "asuka_dataset"
OUT = ROOT / "tts-lab" / "qwen_asuka_dataset_clean"
TARGET_SR = 24000
SPEAKER = "asuka"

REPEATED = re.compile(r"([あいうえおアーぁぃぅぇぉ!！])\1{2,}")
LATIN = re.compile(r"[A-Za-z]")
BAD_WORDS = [
    "いやー",
    "あああ",
    "わああ",
    "うるさい",
    "殺",
    "死",
    "ママ",
    "エンジェル",
    "フィールド",
    "サードインパクト",
    "グラコード",
    "ドイツ",
]


def read_rows() -> list[tuple[Path, str]]:
    rows: list[tuple[Path, str]] = []
    for line in (SOURCE / "metadata.list").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        parts = line.split("|", 3)
        if len(parts) != 4:
            continue
        rel, _speaker, _lang, text = parts
        text = text.strip()
        if text:
            rows.append((SOURCE / rel, text))
    return rows


def audio_stats(path: Path) -> dict[str, float]:
    y, sr = librosa.load(path, sr=TARGET_SR, mono=True)
    y, _ = librosa.effects.trim(y, top_db=35)
    if len(y) == 0:
        return {"duration": 0, "rms": 0, "peak": 0, "f0_med": 0, "f0_std": 999, "centroid": 0}
    rms = float(np.sqrt(np.mean(y * y)))
    peak = float(np.max(np.abs(y)))
    centroid = float(np.mean(librosa.feature.spectral_centroid(y=y, sr=sr)))
    f0, _, _ = librosa.pyin(y, fmin=librosa.note_to_hz("C3"), fmax=librosa.note_to_hz("C6"), sr=sr)
    voiced = f0[~np.isnan(f0)]
    if len(voiced) < 5:
        f0_med = 0.0
        f0_std = 999.0
    else:
        f0_med = float(np.median(voiced))
        f0_std = float(np.std(voiced))
    return {
        "duration": len(y) / sr,
        "rms": rms,
        "peak": peak,
        "f0_med": f0_med,
        "f0_std": f0_std,
        "centroid": centroid,
    }


def reject_reason(text: str, stats: dict[str, float]) -> str | None:
    duration = stats["duration"]
    if duration < 2.4 or duration > 7.2:
        return "duration"
    if len(text) < 5 or len(text) > 55:
        return "text_len"
    if REPEATED.search(text):
        return "repeated"
    if LATIN.search(text):
        return "latin"
    if any(word in text for word in BAD_WORDS):
        return "bad_word"
    if text.count("?") + text.count("!") + text.count("？") + text.count("！") > 2:
        return "punct"
    if stats["peak"] > 0.985:
        return "clipped"
    if stats["rms"] < 0.012 or stats["rms"] > 0.18:
        return "rms"
    if not (230 <= stats["f0_med"] <= 520):
        return "f0_med"
    if stats["f0_std"] > 130:
        return "f0_std"
    if not (1200 <= stats["centroid"] <= 4200):
        return "centroid"
    return None


def convert_wav(src: Path, dst: Path) -> None:
    y, _ = librosa.load(src, sr=TARGET_SR, mono=True)
    sf.write(dst, y, TARGET_SR, subtype="PCM_16")


def main() -> None:
    wav_out = OUT / "wavs"
    wav_out.mkdir(parents=True, exist_ok=True)
    accepted: list[tuple[Path, str, dict[str, float]]] = []
    rejected: list[str] = ["file,reason,text"]

    for src, text in read_rows():
        stats = audio_stats(src)
        reason = reject_reason(text, stats)
        if reason:
            rejected.append(f"{src.name},{reason},{text}")
            continue
        accepted.append((src, text, stats))

    accepted.sort(key=lambda item: (abs(item[2]["duration"] - 4.5), item[0].name))

    # Keep the best-balanced subset. For this dataset, 160 clean clips is a better
    # first target than using every marginally acceptable clip.
    selected = accepted[:160]
    selected.sort(key=lambda item: item[0].name)

    if not selected:
        raise RuntimeError("no clean clips selected")

    ref_src, _ref_text, _ = min(selected, key=lambda item: abs(item[2]["duration"] - 5.0))
    ref = OUT / "ref_clean.wav"
    convert_wav(ref_src, ref)

    with (OUT / "train_raw.jsonl").open("w", encoding="utf-8") as f:
        for src, text, _stats in selected:
            dst = wav_out / src.name
            convert_wav(src, dst)
            item = {
                "audio": str(dst),
                "text": text,
                "ref_audio": str(ref),
                "speaker": SPEAKER,
            }
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    (OUT / "selected.csv").write_text(
        "file,duration,rms,f0_med,f0_std,centroid,text\n"
        + "\n".join(
            f"{src.name},{stats['duration']:.3f},{stats['rms']:.5f},{stats['f0_med']:.1f},"
            f"{stats['f0_std']:.1f},{stats['centroid']:.0f},{text}"
            for src, text, stats in selected
        )
        + "\n",
        encoding="utf-8",
    )
    (OUT / "rejected.csv").write_text("\n".join(rejected) + "\n", encoding="utf-8")

    print(f"accepted_candidates={len(accepted)}")
    print(f"selected={len(selected)}")
    print(f"ref={ref_src.name}")
    print(f"out={OUT}")


if __name__ == "__main__":
    main()
