from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

import soundfile as sf


ROOT = Path(r"Y:\StackChan")
DATA = ROOT / "tts-lab" / "qwen_asuka_dataset"
REF_NAME = "asuka_00017.wav"


REPEATED_VOWEL = re.compile(r"([あいうえおアーぁぃぅぇぉ])\1{3,}")


def keep(item: dict) -> bool:
    text = item["text"].strip()
    if len(text) < 3 or len(text) > 95:
        return False
    if REPEATED_VOWEL.search(text):
        return False
    duration = sf.info(item["audio"]).duration
    if duration < 2.0 or duration > 8.5:
        return False
    return True


def filter_file(src: Path, dst: Path, ref: Path) -> int:
    count = 0
    with src.open("r", encoding="utf-8") as fin, dst.open("w", encoding="utf-8") as fout:
        for line in fin:
            if not line.strip():
                continue
            item = json.loads(line)
            if not keep(item):
                continue
            item["ref_audio"] = str(ref)
            fout.write(json.dumps(item, ensure_ascii=False) + "\n")
            count += 1
    return count


def main() -> None:
    ref = DATA / "ref_clean.wav"
    shutil.copyfile(DATA / "wavs" / REF_NAME, ref)

    raw_count = filter_file(DATA / "train_raw.jsonl", DATA / "train_raw_filtered.jsonl", ref)
    code_count = filter_file(DATA / "train_with_codes.jsonl", DATA / "train_with_codes_filtered.jsonl", ref)
    print(f"raw={raw_count}")
    print(f"with_codes={code_count}")
    print(f"ref={ref}")


if __name__ == "__main__":
    main()
