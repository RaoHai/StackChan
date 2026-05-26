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
CLEAN = ROOT / "tts-lab" / "qwen_asuka_dataset_clean"
OUT = ROOT / "tts-lab" / "qwen_asuka_dataset_bright"
TARGET_SR = 24000
SPEAKER = "asuka"

REPEATED = re.compile(r"([あいうえおアーぁぃぅぇぉ!！])\1{3,}")
LATIN = re.compile(r"[A-Za-z]")
BAD_WORDS = [
    "いやー",
    "あああ",
    "わああ",
    "ママ",
    "死",
    "殺",
    "エンジェル",
    "サードインパクト",
    "グラコード",
]
PREFERRED = ["あんた", "バカ", "なに", "何", "どうして", "ほんと", "信じ", "シンジ", "ねえ", "ほら"]


def rows_from_metadata() -> list[tuple[Path, str]]:
    rows = []
    for line in (SOURCE / "metadata.list").read_text(encoding="utf-8").splitlines():
        parts = line.split("|", 3)
        if len(parts) != 4:
            continue
        rel, _speaker, _lang, text = parts
        text = text.strip()
        if text:
            rows.append((SOURCE / rel, text))
    return rows


def load_audio(path: Path) -> tuple[np.ndarray, int]:
    y, sr = librosa.load(path, sr=TARGET_SR, mono=True)
    y, _ = librosa.effects.trim(y, top_db=35)
    return y.astype(np.float32), sr


def stats(path: Path) -> dict[str, float]:
    y, sr = load_audio(path)
    if len(y) == 0:
        return {"duration": 0, "rms": 0, "peak": 0, "centroid": 0, "f0_med": 0, "f0_std": 999}
    rms = float(np.sqrt(np.mean(y * y)))
    peak = float(np.max(np.abs(y)))
    centroid = float(np.mean(librosa.feature.spectral_centroid(y=y, sr=sr)))
    f0 = librosa.yin(y, fmin=160, fmax=900, sr=sr)
    f0 = f0[np.isfinite(f0)]
    f0 = f0[(f0 > 160) & (f0 < 900)]
    if len(f0) < 5:
        f0_med = 0.0
        f0_std = 999.0
    else:
        f0_med = float(np.median(f0))
        f0_std = float(np.std(f0))
    return {
        "duration": len(y) / sr,
        "rms": rms,
        "peak": peak,
        "centroid": centroid,
        "f0_med": f0_med,
        "f0_std": f0_std,
    }


def reject_reason(text: str, s: dict[str, float]) -> str | None:
    if s["duration"] < 1.0 or s["duration"] > 4.8:
        return "duration"
    if len(text) < 4 or len(text) > 42:
        return "text_len"
    if REPEATED.search(text):
        return "repeated"
    if LATIN.search(text):
        return "latin"
    if any(word in text for word in BAD_WORDS):
        return "bad_word"
    if text.count("?") + text.count("!") + text.count("？") + text.count("！") > 2:
        return "punct"
    if s["peak"] > 0.985:
        return "clipped"
    if s["rms"] < 0.018 or s["rms"] > 0.20:
        return "rms"
    if s["f0_med"] < 360 or s["f0_med"] > 720:
        return "f0_med"
    if s["f0_std"] > 230:
        return "f0_std"
    if s["centroid"] < 1700 or s["centroid"] > 5000:
        return "centroid"
    return None


def score(text: str, s: dict[str, float]) -> float:
    preferred_bonus = sum(1 for word in PREFERRED if word in text) * 0.35
    return (
        preferred_bonus
        - abs(s["duration"] - 2.4) * 0.15
        - abs(s["f0_med"] - 520) / 400
        - abs(s["centroid"] - 2500) / 3000
        - s["f0_std"] / 800
    )


def convert(src: Path, dst: Path) -> None:
    y, _ = librosa.load(src, sr=TARGET_SR, mono=True)
    sf.write(dst, y, TARGET_SR, subtype="PCM_16")


def main() -> None:
    wav_out = OUT / "wavs"
    wav_out.mkdir(parents=True, exist_ok=True)
    candidates: list[tuple[float, Path, str, dict[str, float]]] = []
    rejected = ["file,reason,text"]

    for src, text in rows_from_metadata():
        s = stats(src)
        reason = reject_reason(text, s)
        if reason:
            rejected.append(f"{src.name},{reason},{text}")
            continue
        candidates.append((score(text, s), src, text, s))

    candidates.sort(reverse=True, key=lambda item: item[0])
    selected = candidates[:90]

    # Mix back a small amount of stable clean data to keep the decoder grounded.
    clean_rows = []
    clean_jsonl = CLEAN / "train_raw.jsonl"
    if clean_jsonl.exists():
        for line in clean_jsonl.read_text(encoding="utf-8").splitlines():
            item = json.loads(line)
            clean_rows.append((Path(item["audio"]), item["text"]))
    clean_rows = clean_rows[:30]

    # Reference: exact target-like phrase if available.
    ref_src = SOURCE / "wavs" / "asuka_00015.wav"
    if not ref_src.exists():
        ref_src = selected[0][1]
    ref = OUT / "ref_bright.wav"
    convert(ref_src, ref)

    rows = []
    for _score, src, text, _s in selected:
        dst = wav_out / src.name
        convert(src, dst)
        rows.append((dst, text, "bright"))

    for src, text in clean_rows:
        dst = wav_out / f"clean_{src.name}"
        convert(src, dst)
        rows.append((dst, text, "clean"))

    with (OUT / "train_raw.jsonl").open("w", encoding="utf-8") as f:
        for dst, text, kind in rows:
            f.write(
                json.dumps(
                    {
                        "audio": str(dst),
                        "text": text,
                        "ref_audio": str(ref),
                        "speaker": SPEAKER,
                        "kind": kind,
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )

    (OUT / "selected.csv").write_text(
        "file,score,duration,rms,f0_med,f0_std,centroid,text\n"
        + "\n".join(
            f"{src.name},{sc:.4f},{s['duration']:.3f},{s['rms']:.5f},{s['f0_med']:.1f},"
            f"{s['f0_std']:.1f},{s['centroid']:.0f},{text}"
            for sc, src, text, s in selected
        )
        + "\n",
        encoding="utf-8",
    )
    (OUT / "rejected.csv").write_text("\n".join(rejected) + "\n", encoding="utf-8")
    shutil.copyfile(ref, OUT / "ref.wav")

    print(f"bright_candidates={len(candidates)}")
    print(f"selected_bright={len(selected)}")
    print(f"mixed_clean={len(clean_rows)}")
    print(f"total={len(rows)}")
    print(f"ref={ref_src.name}")
    print(f"out={OUT}")


if __name__ == "__main__":
    main()
