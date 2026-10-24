"""Speech timing: faster-whisper word timestamps and silero-VAD dead air.

faster-whisper ships the silero VAD model, so no extra install is needed.
"""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass

CACHE_DIR = os.path.join(os.path.dirname(__file__), ".cache")
DEAD_AIR_GAP_S = 0.5           # non-speech longer than this counts as dead air


@dataclass
class Word:
    start: float
    end: float
    text: str


def transcribe(path: str, model_size: str = "small", lang: str | None = "ko") -> list[Word]:
    st = os.stat(path)
    key = hashlib.sha1(f"{os.path.abspath(path)}|{st.st_size}|{st.st_mtime}|{model_size}|{lang}"
                       .encode()).hexdigest()[:16]
    cache = os.path.join(CACHE_DIR, f"asr_{key}.json")
    if os.path.exists(cache):
        with open(cache, encoding="utf-8") as fh:
            return [Word(**w) for w in json.load(fh)]
    from faster_whisper import WhisperModel
    model = WhisperModel(model_size, device="cpu", compute_type="int8")
    segments, _ = model.transcribe(path, language=lang, word_timestamps=True,
                                   vad_filter=False, beam_size=1)
    words = [Word(float(w.start), float(w.end), w.word.strip())
             for seg in segments for w in (seg.words or []) if w.word.strip()]
    os.makedirs(CACHE_DIR, exist_ok=True)
    with open(cache, "w", encoding="utf-8") as fh:
        json.dump([w.__dict__ for w in words], fh, ensure_ascii=False)
    return words


def load_words(path: str) -> list[Word]:
    """Load pipeline word timestamps: [{"start":s,"end":e,"text"|"word":...}, ...]."""
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    if isinstance(data, dict):
        data = data.get("words") or [w for s in data.get("segments", []) for w in s.get("words", [])]
    return [Word(float(w["start"]), float(w["end"]), str(w.get("text", w.get("word", ""))).strip())
            for w in data]


def speech_metrics(words: list[Word], duration: float, gap_s: float = DEAD_AIR_GAP_S) -> dict:
    """Dead air = lead-in + tail + inter-word gaps longer than gap_s."""
    if not words or duration <= 0:
        return {"dead_air_ratio": None, "longest_gap_s": None, "speech_start_s": None,
                "words_per_sec": None}
    gaps = [words[0].start] + [b.start - a.end for a, b in zip(words, words[1:])]
    gaps.append(max(duration - words[-1].end, 0.0))
    dead = sum(g for g in gaps if g > gap_s)
    return {"dead_air_ratio": dead / duration,
            "longest_gap_s": max(gaps),
            "speech_start_s": words[0].start,
            "words_per_sec": len(words) / max(words[-1].end - words[0].start, 1e-6)}


def vad_dead_air(path: str, duration: float, gap_s: float = DEAD_AIR_GAP_S) -> dict:
    """Dead air from silero VAD speech segments (same model family the pipeline cuts with)."""
    from faster_whisper import decode_audio
    from faster_whisper.vad import VadOptions, get_speech_timestamps
    sr = 16000
    audio = decode_audio(path, sampling_rate=sr)
    segs = get_speech_timestamps(audio, VadOptions(min_silence_duration_ms=200, speech_pad_ms=30))
    spans = [(s["start"] / sr, s["end"] / sr) for s in segs]
    if not spans or duration <= 0:
        return {"dead_air_ratio": 1.0 if duration else None, "longest_gap_s": duration,
                "vad_speech_ratio": 0.0}
    gaps = [spans[0][0]] + [b[0] - a[1] for a, b in zip(spans, spans[1:])]
    gaps.append(max(duration - spans[-1][1], 0.0))
    return {"dead_air_ratio": sum(g for g in gaps if g > gap_s) / duration,
            "longest_gap_s": max(gaps),
            "vad_speech_ratio": sum(b - a for a, b in spans) / duration}
