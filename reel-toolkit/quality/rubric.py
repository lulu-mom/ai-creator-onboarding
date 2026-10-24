"""Reel quality rubric: criteria, thresholds and scoring (pure functions, no I/O).

Groups and weights (normalised over the groups that could be measured):
  (e) content & craft 55   (b) editing 20   (a) technical 10   (c) vs reference 10
  (d) quick visual style match 5.  The content group (content.py) is scored by an
  independent judge sub-agent from a judge pack (judge_pack.py).
  'standalone total' = technical + editing + content only (same rubric for
  output and reference; used for the output > reference stopping rule).
Each criterion scores 0..1; PASS >= 0.8, WARN >= 0.5, else FAIL.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

PASS_AT, WARN_AT = 0.8, 0.5

# Instagram Reels safe zone (Meta guidance): keep text out of top 14 %,
# bottom 35 % and 6 % on each side.
IG_SAFE_ZONE = (0.06, 0.14, 0.94, 0.65)
# Face "good framing": centre x in 0.30-0.70 and the whole face inside the frame
# (top >= 5 %, bottom <= 95 %). Vertical placement is style-dependent (split
# screen puts the face low), so it is judged against the reference instead.
FACE_X, FACE_TOP_MIN, FACE_BOTTOM_MAX = (0.30, 0.70), 0.05, 0.95
FACE_MIN_PRESENCE = 0.30          # below this the reel is not talking-head -> N/A

VISUAL_KEYS = {
    "caption_style": "자막 스타일 (폰트·색·강조·애니메이션)",
    "motion_graphics": "모션그래픽 (아이콘·카드·전환)",
    "zoom_reframe": "줌/리프레임 (얼굴 크기·펀치인)",
    "pacing": "페이싱 (컷 리듬·정보 밀도)",
    "hook": "훅 (첫 1-3초 장악력)",
}
OVERALL_PASS = 80.0
# Must-not-FAIL criteria: a reel with wrong format, bad loudness, black/frozen
# frames or missing captions fails regardless of the overall score.
GATE_IDS = ("T1", "T4", "T5", "E5")
GROUP_WEIGHTS = {"content": 55, "editing": 20, "technical": 10, "reference": 10, "visual": 5}
STANDALONE_GROUPS = ("content", "editing", "technical")


# ------------------------------------------------------------------ helpers
def ramp_low(v: float, good: float, bad: float) -> float:
    """1 when v <= good, 0 when v >= bad, linear between."""
    if v <= good:
        return 1.0
    if v >= bad:
        return 0.0
    return (bad - v) / (bad - good)


def ramp_high(v: float, good: float, bad: float) -> float:
    """1 when v >= good, 0 when v <= bad, linear between."""
    if v >= good:
        return 1.0
    if v <= bad:
        return 0.0
    return (v - bad) / (good - bad)


def band(v: float, lo: float, hi: float, tol: float) -> float:
    """1 inside [lo, hi], fading to 0 at `tol` outside."""
    if lo <= v <= hi:
        return 1.0
    dist = lo - v if v < lo else v - hi
    return max(0.0, 1.0 - dist / tol)


def match(v: float, ref: float, tol: float, relative: bool) -> float:
    """1 within tol of the reference, linear to 0 at 3x tol."""
    diff = abs(v - ref)
    allowed = tol * abs(ref) if relative else tol
    if allowed <= 0:
        return 1.0 if diff == 0 else 0.0
    return 1.0 if diff <= allowed else max(0.0, 1.0 - (diff - allowed) / (2 * allowed))


def status(score: float | None) -> str:
    if score is None:
        return "N/A"
    return "PASS" if score >= PASS_AT else "WARN" if score >= WARN_AT else "FAIL"


def _f(v, fmt="{:.2f}", unit=""):
    return "-" if v is None else fmt.format(v) + unit


@dataclass
class Criterion:
    cid: str
    group: str
    name: str
    weight: float
    target: str
    fn: Callable[[dict], tuple[float | None, str]]


# ------------------------------------------------------------- (a) technical
def _resolution(m):
    w, h = m["width"], m["height"]
    if (w, h) == (1080, 1920):
        s = 1.0
    elif h and abs(w / h - 9 / 16) < 0.01 and w >= 1080:
        s = 1.0          # larger 9:16 masters are fine (IG downsizes)
    elif h and abs(w / h - 9 / 16) < 0.01 and w >= 720:
        s = 0.6
    else:
        s = 0.0
    return s, f"{w}x{h}"


def _fps(m):
    f = m["fps"]
    s = 1.0 if 29.0 <= f <= 60.5 else 0.7 if 23.9 <= f < 29.0 else 0.0
    return s, f"{f:.2f}"


def _bitrate(m):
    b = m["video_bitrate_mbps"]
    return ramp_high(b, 6.0, 2.0), f"{b:.1f} Mbps"


def _loudness(m):
    i, tp = m.get("loudness_i"), m.get("true_peak")
    if i is None:
        return None, "no audio"
    s = band(i, -15.0, -13.0, 4.0)
    if tp is not None and tp > -1.0:
        s *= 0.8
    return s, f"{i:.1f} LUFS / TP {_f(tp, '{:.1f}')}"


def _black_freeze(m):
    black, freeze = m["black_total_s"], m["freeze_longest_s"]
    s = min(ramp_low(black, 0.2, 1.5), ramp_low(freeze, 1.5, 4.0))
    return s, f"black {black:.2f}s / freeze max {freeze:.2f}s"


def _sharpness(m):
    v = m.get("sharpness_median")
    return (None, "-") if v is None else (ramp_high(v, 120.0, 30.0), f"LapVar {v:.0f}")


# --------------------------------------------------------------- (b) editing
def _dead_air(m):
    v = m.get("dead_air_ratio")
    if v is None:
        return None, "no speech data"
    s = min(ramp_low(v, 0.03, 0.15), ramp_low(m.get("longest_gap_s") or 0, 0.8, 2.5))
    return s, f"{v * 100:.1f}% (max gap {_f(m.get('longest_gap_s'), '{:.2f}', 's')})"


def _cut_rhythm(m):
    avg, longest = m["avg_shot_s"], m["longest_shot_s"]
    s = 0.6 * band(avg, 1.5, 4.0, 3.0) + 0.4 * ramp_low(longest, 7.0, 15.0)
    return s, f"{m['cuts_per_min']:.1f}/min, avg {avg:.1f}s, max {longest:.1f}s"


def _hook(m):
    checks = []
    def at(key, default=99.0):
        v = m.get(key)
        return default if v is None else v

    if m.get("speech_start_s") is not None:
        checks.append(m["speech_start_s"] <= 0.5)
    if m.get("ocr_enabled"):
        checks.append(at("first_caption_s") <= 1.0)
    checks.append(at("first_cut_s") <= 3.0 or at("hook_motion_ratio", 0.0) >= 1.0)
    return sum(checks) / len(checks), f"{sum(checks)}/{len(checks)} (speech≤0.5s, caption≤1s, change≤3s)"


def _face(m):
    pres = m.get("face_presence")
    if pres is None or pres < FACE_MIN_PRESENCE:
        return None, f"face {_f(pres, '{:.0%}')} (not talking-head)"
    v = m["face_safe_ratio"]
    return ramp_high(v, 0.85, 0.5), f"{v:.0%} framed (face in {pres:.0%})"


def _coverage(m):
    v = m.get("caption_coverage")
    return (None, "-") if v is None else (ramp_high(v, 0.9, 0.5), f"{v:.0%}")


def _sync(m):
    v = m.get("sync_median_abs_ms")
    if v is None:
        return None, "no matched captions"
    return ramp_low(v, 120.0, 500.0), (f"median |err| {v:.0f} ms, mean {m['sync_mean_signed_ms']:+.0f} ms"
                                       f" (n={m['sync_n']})")


def _caption_safe(m):
    v = m.get("caption_safe_ratio")
    return (None, "-") if v is None else (ramp_high(v, 0.95, 0.6), f"{v:.0%} boxes inside")


def _legibility(m):
    h, conf = m.get("caption_text_height"), m.get("ocr_confidence")
    if h is None:
        return None, "-"
    s = min(ramp_high(h, 0.030, 0.015), ramp_high(conf or 0, 0.85, 0.6))
    return s, f"text h {h * 100:.1f}% of H, OCR conf {_f(conf)}"


CRITERIA = [
    Criterion("T1", "technical", "해상도·비율 9:16", 4, "1080x1920", _resolution),
    Criterion("T2", "technical", "프레임레이트", 3, "29.97-60 fps", _fps),
    Criterion("T3", "technical", "비디오 비트레이트", 3, ">= 6 Mbps", _bitrate),
    Criterion("T4", "technical", "라우드니스", 5, "-14±1 LUFS, TP <= -1 dBTP", _loudness),
    Criterion("T5", "technical", "검은/정지 화면", 5, "black <= 0.2s, freeze <= 1.5s", _black_freeze),
    Criterion("T6", "technical", "선명도", 5, "Laplacian var >= 120 @540w", _sharpness),
    Criterion("E1", "editing", "무음(데드에어) 비율", 6, "<= 3%, gap <= 0.8s", _dead_air),
    Criterion("E2", "editing", "컷 리듬", 5, "avg shot 1.5-4s, max <= 7s", _cut_rhythm),
    Criterion("E3", "editing", "훅 (첫 3초)", 4, "all 3 checks", _hook),
    Criterion("E4", "editing", "얼굴 중앙·안전영역", 4, ">= 85% frames", _face),
    Criterion("E5", "editing", "자막 커버리지", 5, ">= 90% of speech", _coverage),
    Criterion("E6", "editing", "자막 싱크 오차", 5, "median <= 120 ms", _sync),
    Criterion("E7", "editing", "자막 IG 안전영역", 3, ">= 95% boxes", _caption_safe),
    Criterion("E8", "editing", "자막 가독성", 3, "h >= 3% H, conf >= 0.85", _legibility),
]

# (metric, label, tolerance, relative?)
REFERENCE_METRICS = [
    ("cuts_per_min", "컷 빈도 (/분)", 0.25, True),
    ("dead_air_ratio", "무음 비율", 0.03, False),
    ("words_per_sec", "말 속도 (단어/초)", 0.20, True),
    ("caption_coverage", "자막 커버리지", 0.10, False),
    ("caption_events_per_min", "자막 전환 빈도 (/분)", 0.30, True),
    ("chars_per_caption", "자막 1개당 글자 수", 0.30, True),
    ("caption_y_center", "자막 세로 위치", 0.05, False),
    ("caption_text_height", "자막 글자 크기", 0.20, True),
    ("face_height", "얼굴 크기 (줌 정도)", 0.20, True),
    ("face_center_x", "얼굴 가로 위치", 0.05, False),
    ("face_center_y", "얼굴 세로 위치 (레이아웃)", 0.06, False),
    ("graphic_text_ratio", "모션그래픽 텍스트 노출 비율", 0.15, False),
    ("motion_mean", "화면 움직임 양", 0.30, True),
    ("sharpness_median", "선명도", 0.30, True),
    ("brightness", "밝기", 0.12, True),
    ("saturation", "채도", 0.20, True),
    ("loudness_i", "라우드니스", 1.5, False),
]


def score_report(out: dict, ref: dict | None = None, visual: dict | None = None,
                 content: dict | None = None) -> dict:
    rows = []
    for c in CRITERIA:
        s, val = c.fn(out)
        ref_val = c.fn(ref)[1] if ref else None
        rows.append({"id": c.cid, "group": c.group, "name": c.name, "weight": c.weight,
                     "target": c.target, "value": val, "reference": ref_val,
                     "score": s, "status": status(s)})
    if ref:
        rows += _reference_rows(out, ref)
    if visual:
        rows += _visual_rows(visual)
    if content:
        from content import content_rows
        rows += content_rows(content, GROUP_WEIGHTS["content"])
    overall = _overall(rows)
    gate_fails = [r["id"] for r in rows if r["id"] in GATE_IDS and r["status"] == "FAIL"]
    verdict = "PASS" if overall >= OVERALL_PASS and not gate_fails else "FAIL"
    return {"rows": rows, "overall": overall, "groups": _group_scores(rows),
            "standalone": _overall(rows, STANDALONE_GROUPS),
            "verdict": verdict, "gate_fails": gate_fails}


def _reference_rows(out: dict, ref: dict) -> list[dict]:
    w = GROUP_WEIGHTS["reference"] / len(REFERENCE_METRICS)
    rows = []
    for i, (key, label, tol, rel) in enumerate(REFERENCE_METRICS, 1):
        o, r = out.get(key), ref.get(key)
        s = None if o is None or r is None else match(o, r, tol, rel)
        target = f"±{tol:.0%}" if rel else f"±{tol:g}"
        rows.append({"id": f"R{i}", "group": "reference", "name": label, "weight": w,
                     "target": target, "value": _f(o, "{:.3g}"), "reference": _f(r, "{:.3g}"),
                     "score": s, "status": status(s)})
    return rows


def _visual_rows(visual: dict) -> list[dict]:
    w = GROUP_WEIGHTS["visual"] / len(VISUAL_KEYS)
    rows = []
    for i, (key, label) in enumerate(VISUAL_KEYS.items(), 1):
        v = visual.get(key)
        s = None if v is None else max(0.0, min(1.0, float(v) / 5))   # 4/5 -> 0.8 = PASS
        rows.append({"id": f"V{i}", "group": "visual", "name": label, "weight": w,
                     "target": ">= 4/5", "value": "-" if v is None else f"{v}/5",
                     "reference": "5/5", "score": s, "status": status(s)})
    return rows


def _group_scores(rows: list[dict]) -> dict:
    out = {}
    for g in GROUP_WEIGHTS:
        rs = [r for r in rows if r["group"] == g and r["score"] is not None]
        if rs:
            out[g] = 100 * sum(r["score"] * r["weight"] for r in rs) / sum(r["weight"] for r in rs)
    return out


def _overall(rows: list[dict], only: tuple[str, ...] | None = None) -> float:
    groups = {g: v for g, v in _group_scores(rows).items() if only is None or g in only}
    if not groups:
        return 0.0
    total_w = sum(GROUP_WEIGHTS[g] for g in groups)
    return sum(groups[g] * GROUP_WEIGHTS[g] for g in groups) / total_w
