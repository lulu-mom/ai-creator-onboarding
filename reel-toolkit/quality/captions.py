"""Speech words (faster-whisper) and burned-in caption analysis (OCR results).

Caption sync = OCR-detected caption onset (refined frame-accurately by pixel
diff in the caption region) minus the matching spoken word's start time.
"""
from __future__ import annotations

import difflib
import re
import statistics

import numpy as np

from speech import Word
from vision import OcrObs, TextBox, caption_region_signature

STATIC_TEXT_FRACTION = 0.6     # text present in >60% of OCR frames = static overlay
MATCH_WINDOW_S = 1.5           # search window for the spoken word of a caption
TIME_ONLY_WINDOW_S = 0.6       # fallback: nearest word start when text doesn't match
TEXT_MATCH_MIN = 0.5
REFINE_STEPS = 6               # binary-search steps for frame-accurate onset


def norm_text(text: str) -> str:
    return re.sub(r"[\W_]+", "", text.lower())


# --------------------------------------------------------------------- captions
def split_static(ocr: list[OcrObs]) -> tuple[list[OcrObs], set[str]]:
    """Remove text that sits on screen most of the time (titles, watermarks)."""
    if not ocr:
        return [], set()
    counts: dict[str, int] = {}
    for obs in ocr:
        for key in {norm_text(b.text) for b in obs.boxes}:
            counts[key] = counts.get(key, 0) + 1
    static = {k for k, c in counts.items() if k and c / len(ocr) > STATIC_TEXT_FRACTION}
    cleaned = [OcrObs(o.t, [b for b in o.boxes if norm_text(b.text) not in static]) for o in ocr]
    return cleaned, static


BAND_BIN = 0.025               # caption-band histogram bin (fraction of height)
BAND_MIN_BOX_H = 0.012         # ignore tiny UI text when locating the caption band
BAND_KEEP = 0.5                # neighbour bins >= 50% of peak join the band
BAND_PAD = 0.03


def find_caption_band(ocr: list[OcrObs]) -> tuple[float, float] | None:
    """Locate the vertical band where subtitles live.

    Score per y-bin = sum over frames of the tallest box in that bin, so large,
    ever-present subtitle lines beat small motion-graphics UI text.
    """
    nbins = int(1 / BAND_BIN) + 1
    score = np.zeros(nbins)
    for obs in ocr:
        best = np.zeros(nbins)
        for b in obs.boxes:
            h = b.y1 - b.y0
            if h >= BAND_MIN_BOX_H:
                i = min(int(((b.y0 + b.y1) / 2) / BAND_BIN), nbins - 1)
                best[i] = max(best[i], h)
        score += best
    if score.max() <= 0:
        return None
    peak = int(score.argmax())
    lo = hi = peak
    while lo > 0 and score[lo - 1] >= BAND_KEEP * score[peak]:
        lo -= 1
    while hi < nbins - 1 and score[hi + 1] >= BAND_KEEP * score[peak]:
        hi += 1
    return max(lo * BAND_BIN - BAND_PAD, 0.0), min((hi + 1) * BAND_BIN + BAND_PAD, 1.0)


def split_caption_band(ocr: list[OcrObs], band: tuple[float, float] | None):
    """Return (caption_ocr, graphics_ocr): boxes centred in the band vs everything else."""
    if band is None:
        return ocr, [OcrObs(o.t, []) for o in ocr]
    lo, hi = band
    cap, gfx = [], []
    for o in ocr:
        inside = [b for b in o.boxes if lo <= (b.y0 + b.y1) / 2 <= hi]
        cap.append(OcrObs(o.t, inside))
        gfx.append(OcrObs(o.t, [b for b in o.boxes if b not in inside]))
    return cap, gfx


SPEECH_WINDOW_S = 2.0          # words within ±2 s of a frame may be on screen
SPEECH_MATCH_MIN = 0.6         # share of a box's characters found in nearby speech
SPEECH_MIN_CHARS = 2


def _char_overlap(box_text: str, speech_text: str) -> float:
    if not box_text or not speech_text:
        return 0.0
    sm = difflib.SequenceMatcher(None, box_text, speech_text, autojunk=False)
    return sum(blk.size for blk in sm.get_matching_blocks()) / len(box_text)


def split_by_speech(ocr: list[OcrObs], words: list[Word]):
    """Return (caption_ocr, graphics_ocr): a box is a subtitle when its text is
    (mostly) what is being said around that moment. Works for captions that move
    around the frame, unlike a fixed band."""
    starts = np.array([w.start for w in words])
    cap, gfx = [], []
    for o in ocr:
        lo, hi = np.searchsorted(starts, [o.t - SPEECH_WINDOW_S, o.t + SPEECH_WINDOW_S])
        spoken = norm_text("".join(w.text for w in words[lo:hi]))
        inside = [b for b in o.boxes if len(norm_text(b.text)) >= SPEECH_MIN_CHARS
                  and _char_overlap(norm_text(b.text), spoken) >= SPEECH_MATCH_MIN]
        cap.append(OcrObs(o.t, inside))
        gfx.append(OcrObs(o.t, [b for b in o.boxes if b not in inside]))
    return cap, gfx


def signature(boxes: list[TextBox]) -> str:
    return " ".join(b.text for b in sorted(boxes, key=lambda b: (round(b.y0, 2), b.x0)))


def caption_events(ocr: list[OcrObs]) -> list[dict]:
    """Collapse consecutive OCR samples into caption events with onset bracket."""
    events, prev_sig, prev_t = [], "", None
    for obs in ocr:
        sig = signature(obs.boxes)
        changed = difflib.SequenceMatcher(None, norm_text(prev_sig), norm_text(sig)).ratio() < 0.6
        if sig and (not prev_sig or changed):
            events.append({"text": sig, "t_before": prev_t if prev_t is not None else obs.t,
                           "t_seen": obs.t, "boxes": obs.boxes})
        prev_sig, prev_t = sig, obs.t
    return events


def caption_layout(ocr: list[OcrObs]) -> dict:
    boxes = [b for o in ocr for b in o.boxes]
    if not boxes:
        return {"caption_y_center": None, "caption_text_height": None, "ocr_confidence": None}
    return {"caption_y_center": float(np.median([(b.y0 + b.y1) / 2 for b in boxes])),
            "caption_text_height": float(np.median([b.y1 - b.y0 for b in boxes])),
            "ocr_confidence": float(np.mean([b.score for b in boxes]))}


def coverage(ocr: list[OcrObs], words: list[Word]) -> float | None:
    """Share of OCR samples during speech that show caption text."""
    if not ocr:
        return None
    if words:
        speaking = [o for o in ocr if any(w.start - 0.15 <= o.t <= w.end + 0.15 for w in words)]
    else:
        speaking = ocr
    if not speaking:
        return None
    return sum(1 for o in speaking if o.boxes) / len(speaking)


def safe_zone_ratio(ocr: list[OcrObs], zone: tuple[float, float, float, float]) -> float | None:
    x0, y0, x1, y1 = zone
    boxes = [b for o in ocr for b in o.boxes]
    if not boxes:
        return None
    inside = sum(1 for b in boxes if b.x0 >= x0 and b.x1 <= x1 and b.y0 >= y0 and b.y1 <= y1)
    return inside / len(boxes)


def refine_onset(path: str, ev: dict) -> float:
    """Binary-search the first frame between t_before and t_seen that looks like t_seen."""
    lo, hi = ev["t_before"], ev["t_seen"]
    if hi - lo <= 0.04:
        return hi
    b = ev["boxes"]
    region = (max(min(x.x0 for x in b) - 0.02, 0), max(min(x.y0 for x in b) - 0.01, 0),
              min(max(x.x1 for x in b) + 0.02, 1), min(max(x.y1 for x in b) + 0.01, 1))
    ref_lo, ref_hi = caption_region_signature(path, [lo, hi], region)
    if ref_lo is None or ref_hi is None:
        return hi
    for _ in range(REFINE_STEPS):
        mid = (lo + hi) / 2
        (crop,) = caption_region_signature(path, [mid], region)
        if crop is None:
            break
        if np.abs(crop - ref_hi).mean() <= np.abs(crop - ref_lo).mean():
            hi = mid
        else:
            lo = mid
    return hi


def sync_errors(path: str, events: list[dict], words: list[Word], refine: bool = True) -> list[float]:
    """Signed ms error per caption event (positive = caption appears late)."""
    errs = []
    for ev in events:
        onset = refine_onset(path, ev) if refine else (ev["t_before"] + ev["t_seen"]) / 2
        word = _match_word(ev["text"], onset, words)
        if word is not None:
            errs.append((onset - word.start) * 1000.0)
    return errs


def _match_word(text: str, onset: float, words: list[Word]) -> Word | None:
    cap = norm_text(text)
    near = [w for w in words if abs(w.start - onset) <= MATCH_WINDOW_S]
    best, best_key = None, None
    for w in near:
        wt = norm_text(w.text)
        if not wt:
            continue
        ratio = difflib.SequenceMatcher(None, cap[:len(wt) + 2], wt).ratio()
        if ratio >= TEXT_MATCH_MIN:
            key = (abs(w.start - onset) - ratio, )
            if best_key is None or key < best_key:
                best, best_key = w, key
    if best is not None:
        return best
    timed = [w for w in words if abs(w.start - onset) <= TIME_ONLY_WINDOW_S]
    return min(timed, key=lambda w: abs(w.start - onset)) if timed else None


def summarize_errors(errs: list[float]) -> dict:
    if not errs:
        return {"sync_median_abs_ms": None, "sync_mean_signed_ms": None, "sync_n": 0}
    return {"sync_median_abs_ms": statistics.median(abs(e) for e in errs),
            "sync_mean_signed_ms": statistics.fmean(errs), "sync_n": len(errs)}
