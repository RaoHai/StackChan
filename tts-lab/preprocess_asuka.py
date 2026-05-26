from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import numpy as np
import soundfile as sf
from faster_whisper import WhisperModel
from faster_whisper.audio import decode_audio


def rms_db(audio: np.ndarray, sample_rate: int, frame_ms: int = 20) -> tuple[np.ndarray, int]:
    frame = max(1, int(sample_rate * frame_ms / 1000))
    count = int(math.ceil(len(audio) / frame))
    padded = np.pad(audio, (0, count * frame - len(audio)))
    frames = padded.reshape(count, frame)
    rms = np.sqrt(np.mean(frames * frames, axis=1) + 1e-12)
    return 20 * np.log10(rms + 1e-12), frame


def smooth_mask(mask: np.ndarray, min_speech_frames: int, max_gap_frames: int) -> np.ndarray:
    mask = mask.copy()
    i = 0
    while i < len(mask):
        if mask[i]:
            i += 1
            continue
        start = i
        while i < len(mask) and not mask[i]:
            i += 1
        end = i
        if start > 0 and end < len(mask) and end - start <= max_gap_frames:
            mask[start:end] = True

    i = 0
    while i < len(mask):
        if not mask[i]:
            i += 1
            continue
        start = i
        while i < len(mask) and mask[i]:
            i += 1
        end = i
        if end - start < min_speech_frames:
            mask[start:end] = False
    return mask


def find_split(db: np.ndarray, start: int, end: int, target: int, search: int) -> int:
    left = max(start + 1, target - search)
    right = min(end - 1, target + search)
    if right <= left:
        return target
    return left + int(np.argmin(db[left:right]))


def collect_segments(
    audio: np.ndarray,
    sample_rate: int,
    min_sec: float,
    max_sec: float,
    silence_gap_sec: float,
    pad_sec: float,
) -> list[tuple[int, int]]:
    db, frame = rms_db(audio, sample_rate)
    threshold = max(float(np.percentile(db, 20) + 10.0), -45.0)
    mask = db > threshold
    min_speech_frames = max(1, int(0.20 * sample_rate / frame))
    max_gap_frames = max(1, int(silence_gap_sec * sample_rate / frame))
    mask = smooth_mask(mask, min_speech_frames, max_gap_frames)

    frame_segments: list[tuple[int, int]] = []
    i = 0
    while i < len(mask):
        if not mask[i]:
            i += 1
            continue
        start = i
        while i < len(mask) and mask[i]:
            i += 1
        end = i
        if (end - start) * frame / sample_rate >= min_sec:
            frame_segments.append((start, end))

    max_frames = int(max_sec * sample_rate / frame)
    search_frames = int(1.25 * sample_rate / frame)
    split_segments: list[tuple[int, int]] = []
    for start, end in frame_segments:
        cursor = start
        while end - cursor > max_frames:
            split = find_split(db, cursor, end, cursor + max_frames, search_frames)
            split_segments.append((cursor, split))
            cursor = split
        if end - cursor > 0:
            split_segments.append((cursor, end))

    pad = int(pad_sec * sample_rate)
    sample_segments: list[tuple[int, int]] = []
    for start, end in split_segments:
        sample_start = max(0, start * frame - pad)
        sample_end = min(len(audio), end * frame + pad)
        if (sample_end - sample_start) / sample_rate >= min_sec:
            sample_segments.append((sample_start, sample_end))
    return sample_segments


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default=r"Y:\StackChan\firmware\main\assets\sfx\asuka.mp4")
    parser.add_argument("--out", default=r"Y:\StackChan\tts-lab\asuka_dataset")
    parser.add_argument("--speaker", default="Asuka")
    parser.add_argument("--language", default="ja")
    parser.add_argument("--sample-rate", type=int, default=32000)
    parser.add_argument("--min-sec", type=float, default=2.0)
    parser.add_argument("--max-sec", type=float, default=10.0)
    parser.add_argument("--silence-gap-sec", type=float, default=0.45)
    parser.add_argument("--pad-sec", type=float, default=0.12)
    parser.add_argument("--model", default="small")
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--compute-type", default="int8")
    parser.add_argument("--transcribe-only", action="store_true")
    args = parser.parse_args()

    input_path = Path(args.input)
    out_dir = Path(args.out)
    wav_dir = out_dir / "wavs"
    wav_dir.mkdir(parents=True, exist_ok=True)

    if args.transcribe_only:
        wav_paths = sorted(wav_dir.glob("*.wav"))
    else:
        audio = decode_audio(str(input_path), sampling_rate=args.sample_rate)
        audio = np.asarray(audio, dtype=np.float32)
        sf.write(out_dir / "asuka_full.wav", audio, args.sample_rate, subtype="PCM_16")

        segments = collect_segments(
            audio,
            args.sample_rate,
            min_sec=args.min_sec,
            max_sec=args.max_sec,
            silence_gap_sec=args.silence_gap_sec,
            pad_sec=args.pad_sec,
        )
        wav_paths = []
        for idx, (start, end) in enumerate(segments, start=1):
            wav_path = wav_dir / f"asuka_{idx:05d}.wav"
            sf.write(wav_path, audio[start:end], args.sample_rate, subtype="PCM_16")
            wav_paths.append(wav_path)

    model = WhisperModel(args.model, device=args.device, compute_type=args.compute_type)
    metadata_path = out_dir / "metadata.list"
    segment_report_path = out_dir / "segments.csv"
    metadata_path.write_text("", encoding="utf-8")
    segment_report_path.write_text("file,start_sec,end_sec,duration_sec,text\n", encoding="utf-8")

    for idx, wav_path in enumerate(wav_paths, start=1):
        name = wav_path.name
        whisper_segments, _info = model.transcribe(
            str(wav_path),
            language=args.language,
            beam_size=5,
            vad_filter=False,
            condition_on_previous_text=False,
        )
        text = "".join(seg.text.strip() for seg in whisper_segments).strip()
        with metadata_path.open("a", encoding="utf-8") as f:
            f.write(f"wavs/{name}|{args.speaker}|{args.language}|{text}\n")
        with segment_report_path.open("a", encoding="utf-8") as f:
            duration = sf.info(str(wav_path)).duration
            f.write(f"{name},,,{duration:.3f},{text}\n")
        print(
            f"[{idx:04d}/{len(wav_paths):04d}] {name} {text}",
            flush=True,
        )

    print(f"done: {len(wav_paths)} clips -> {out_dir}")


if __name__ == "__main__":
    main()
