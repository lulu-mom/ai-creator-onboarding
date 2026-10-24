"""Step 1: transcribe Korean speech with faster-whisper (word timestamps)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

DEFAULT_MODEL = "large-v3-turbo"


def _load_model(model_name: str):
    from faster_whisper import WhisperModel

    try:
        return WhisperModel(model_name, device="cuda", compute_type="float16")
    except Exception as exc:  # CUDA libs missing -> CPU
        print(f"[transcribe] cuda unavailable ({exc.__class__.__name__}); using cpu", file=sys.stderr)
        return WhisperModel(model_name, device="cpu", compute_type="int8")


def transcribe(audio_path: Path, out_json: Path, model_name: str = DEFAULT_MODEL,
               initial_prompt: str | None = None) -> dict:
    if out_json.exists():
        return json.loads(out_json.read_text(encoding="utf-8"))
    model = _load_model(model_name)
    segments, info = model.transcribe(
        str(audio_path), language="ko", word_timestamps=True, beam_size=5,
        vad_filter=False, condition_on_previous_text=False,
        initial_prompt=initial_prompt,
    )
    out = {"language": info.language, "duration": info.duration, "segments": []}
    for seg in segments:
        out["segments"].append({
            "start": round(seg.start, 3), "end": round(seg.end, 3), "text": seg.text.strip(),
            "words": [{"start": round(w.start, 3), "end": round(w.end, 3),
                       "word": w.word.strip(), "prob": round(w.probability, 3)}
                      for w in (seg.words or [])],
        })
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    return out


if __name__ == "__main__":
    res = transcribe(Path(sys.argv[1]), Path(sys.argv[2]), *(sys.argv[3:4] or []))
    for s in res["segments"]:
        print(f"[{s['start']:6.2f}-{s['end']:6.2f}] {s['text']}")
