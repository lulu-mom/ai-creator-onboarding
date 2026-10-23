"""Transcribe an audio/video file to text with faster-whisper.

Usage: python transcribe.py <input> <output.txt> [model]
"""
import sys

from faster_whisper import WhisperModel


def main():
    src, out = sys.argv[1], sys.argv[2]
    model_name = sys.argv[3] if len(sys.argv) > 3 else "small"
    model = WhisperModel(model_name, device="cpu", compute_type="int8")
    segments, info = model.transcribe(src, vad_filter=True)
    with open(out, "w", encoding="utf-8") as f:
        for s in segments:
            f.write(f"[{s.start:7.1f}s] {s.text.strip()}\n")
    print(f"language={info.language} -> {out}")


if __name__ == "__main__":
    main()
