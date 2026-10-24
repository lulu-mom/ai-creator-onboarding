"""Step 2a: speech regions with Silero VAD."""
from __future__ import annotations

import json
import sys
import wave
from pathlib import Path

import numpy as np


def _read_wav16k(path: Path) -> np.ndarray:
    with wave.open(str(path), "rb") as wf:
        if wf.getframerate() != 16000 or wf.getnchannels() != 1:
            raise ValueError("expected 16 kHz mono wav")
        data = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16)
    return data.astype(np.float32) / 32768.0


def speech_regions(wav16k: Path, out_json: Path, threshold: float = 0.45,
                   min_silence_ms: int = 120) -> list[list[float]]:
    if out_json.exists():
        return json.loads(out_json.read_text(encoding="utf-8"))
    import torch
    from silero_vad import get_speech_timestamps, load_silero_vad

    audio = torch.from_numpy(_read_wav16k(wav16k))
    model = load_silero_vad()
    ts = get_speech_timestamps(audio, model, threshold=threshold, sampling_rate=16000,
                               min_speech_duration_ms=120, min_silence_duration_ms=min_silence_ms,
                               speech_pad_ms=0, return_seconds=True)
    regions = [[round(float(r["start"]), 3), round(float(r["end"]), 3)] for r in ts]
    out_json.write_text(json.dumps(regions), encoding="utf-8")
    return regions


if __name__ == "__main__":
    regs = speech_regions(Path(sys.argv[1]), Path(sys.argv[2]))
    total = sum(e - s for s, e in regs)
    print(f"{len(regs)} regions, speech {total:.1f}s")
    for s, e in regs:
        print(f"{s:7.2f} {e:7.2f}")
