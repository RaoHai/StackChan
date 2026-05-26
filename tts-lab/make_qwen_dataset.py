from __future__ import annotations

import json
import shutil
from pathlib import Path

import librosa
import soundfile as sf


ROOT = Path(r"Y:\StackChan")
SOURCE = ROOT / "tts-lab" / "asuka_dataset"
OUT = ROOT / "tts-lab" / "qwen_asuka_dataset"
SPEAKER = "asuka"
TARGET_SR = 24000


def read_metadata(path: Path) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        parts = line.split("|", 3)
        if len(parts) != 4:
            continue
        rel, _speaker, _lang, text = parts
        text = text.strip()
        if text:
            rows.append((rel, text))
    return rows


def convert_wav(src: Path, dst: Path) -> float:
    audio, _sr = librosa.load(src, sr=TARGET_SR, mono=True)
    sf.write(dst, audio, TARGET_SR, subtype="PCM_16")
    return len(audio) / TARGET_SR


def main() -> None:
    wav_out = OUT / "wavs"
    wav_out.mkdir(parents=True, exist_ok=True)

    rows = read_metadata(SOURCE / "metadata.list")
    converted: list[dict[str, str]] = []
    best_ref: tuple[float, Path] | None = None

    for rel, text in rows:
        src = SOURCE / rel
        dst = wav_out / src.name
        duration = convert_wav(src, dst)
        converted.append({"audio": str(dst), "text": text})
        if 4.0 <= duration <= 8.0:
            score = abs(duration - 6.0)
            if best_ref is None or score < best_ref[0]:
                best_ref = (score, dst)

    if best_ref is None:
        best_ref = (0.0, wav_out / Path(rows[0][0]).name)

    ref = OUT / "ref.wav"
    shutil.copyfile(best_ref[1], ref)

    raw_jsonl = OUT / "train_raw.jsonl"
    with raw_jsonl.open("w", encoding="utf-8") as f:
        for item in converted:
            item["ref_audio"] = str(ref)
            item["speaker"] = SPEAKER
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    print(f"rows={len(converted)}")
    print(f"ref={ref}")
    print(f"raw_jsonl={raw_jsonl}")


if __name__ == "__main__":
    main()
