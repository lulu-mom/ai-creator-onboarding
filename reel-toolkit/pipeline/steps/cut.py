"""Step 2b: decide what to keep.

* bad-take removal: a sentence that is repeated later (similar text) or a false start
  ("진짜 한...") is dropped, together with short director cues sandwiched between a
  dropped take and its retake ("지금부터요").
* self-repair: "오늘은 어제는 오늘은" -> drop the first attempt of a repeated stem.
* fillers: isolated filler words (음, 어 ...).
* dead air: keep = union(kept words padded) ∩ (VAD speech padded), so pauses shrink to
  natural breath (~pad_before + pad_after).

Times here are SOURCE times. `EditMap` converts them to the edited timeline.
"""
from __future__ import annotations

import difflib
import re
from dataclasses import dataclass, field

SENT_END = re.compile(r"[.?!…]+$")


@dataclass
class Word:
    text: str
    start: float
    end: float
    prob: float = 1.0
    sent: int = 0           # sentence index
    keep: bool = True
    reason: str = ""


@dataclass
class Sentence:
    idx: int
    words: list[Word] = field(default_factory=list)

    @property
    def text(self) -> str:
        return " ".join(w.text for w in self.words)

    @property
    def norm(self) -> str:
        return _norm(self.text)

    @property
    def start(self) -> float:
        return self.words[0].start

    @property
    def end(self) -> float:
        return self.words[-1].end


def _norm(s: str) -> str:
    return re.sub(r"[^0-9A-Za-z가-힣%]", "", s)


def _stem(s: str) -> str:
    """Crude Korean stem: strip common trailing particles."""
    n = _norm(s)
    for suf in ("에게는", "에게", "와", "과", "는", "은", "를", "을", "이", "가", "도", "의", "로"):
        if len(n) > len(suf) + 1 and n.endswith(suf):
            return n[: -len(suf)]
    return n


def sentences_from_transcript(tr: dict) -> list[Sentence]:
    sents: list[Sentence] = []
    cur = Sentence(0)
    for seg in tr["segments"]:
        for w in seg["words"]:
            if not w["word"].strip():
                continue
            cur.words.append(Word(w["word"].strip(), float(w["start"]), float(w["end"]),
                                  float(w.get("prob", 1.0))))
            if SENT_END.search(w["word"].strip()):
                sents.append(cur)
                cur = Sentence(len(sents))
        if cur.words:  # whisper segment boundary also ends a sentence
            sents.append(cur)
            cur = Sentence(len(sents))
    for s in sents:
        for w in s.words:
            w.sent = s.idx
    return sents


def _similar(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    return difflib.SequenceMatcher(None, a, b).ratio()


def remove_bad_takes(sents: list[Sentence], sim_thr: float, lookahead_s: float = 25.0) -> list[str]:
    log: list[str] = []
    retake_of: dict[int, int] = {}
    for i, si in enumerate(sents):
        for j in range(i + 1, min(len(sents), i + 6)):
            sj = sents[j]
            if sj.start - si.end > lookahead_s:
                break
            sim = _similar(si.norm, sj.norm)
            false_start = (si.text.rstrip().endswith("...") or len(si.words) <= 2) and \
                len(si.words) < len(sj.words) and _norm(si.words[0].text) == _norm(sj.words[0].text)
            if sim >= sim_thr or false_start:
                retake_of[i] = j
                why = f"retake (sim {sim:.2f})" if sim >= sim_thr else "false start"
                for w in si.words:
                    w.keep, w.reason = False, why
                log.append(f"drop sent {i} '{si.text}' -> {why}, kept sent {j}")
                break
    # director cues between a dropped take and its retake
    for i, j in retake_of.items():
        for k in range(i + 1, j):
            sk = sents[k]
            if k not in retake_of and sk.words[0].keep and len(sk.words) <= 2 and sk.end - sk.start < 1.6:
                for w in sk.words:
                    w.keep, w.reason = False, "cue between takes"
                log.append(f"drop sent {k} '{sk.text}' -> cue between takes")
    return log


def remove_self_repairs(sents: list[Sentence]) -> list[str]:
    log = []
    for s in sents:
        ws = [w for w in s.words if w.keep]
        for a in range(len(ws)):
            for gap in (1, 2):
                b = a + gap
                if b >= len(ws):
                    continue
                st = _stem(ws[a].text)
                if len(st) >= 2 and st == _stem(ws[b].text) and ws[a].keep:
                    ws[a].keep, ws[a].reason = False, "self-repair"
                    log.append(f"drop word '{ws[a].text}' @{ws[a].start:.2f} (repeated '{ws[b].text}')")
    return log


def remove_fillers(sents: list[Sentence], fillers: list[str]) -> list[str]:
    fset = {_norm(f) for f in fillers}
    log = []
    for s in sents:
        for w in s.words:
            if w.keep and _norm(w.text) in fset:
                w.keep, w.reason = False, "filler"
                log.append(f"drop filler '{w.text}' @{w.start:.2f}")
    return log


def _intersect(a: list[list[float]], b: list[list[float]]) -> list[list[float]]:
    out, i, j = [], 0, 0
    while i < len(a) and j < len(b):
        lo, hi = max(a[i][0], b[j][0]), min(a[i][1], b[j][1])
        if hi > lo:
            out.append([lo, hi])
        if a[i][1] < b[j][1]:
            i += 1
        else:
            j += 1
    return out


def _merge(iv: list[list[float]], gap: float) -> list[list[float]]:
    out: list[list[float]] = []
    for s, e in sorted(iv):
        if out and s - out[-1][1] <= gap:
            out[-1][1] = max(out[-1][1], e)
        else:
            out.append([s, e])
    return out


def keep_intervals(sents: list[Sentence], vad: list[list[float]], cfg: dict,
                   duration: float) -> list[list[float]]:
    pb, pa, mg = cfg["pad_before"], cfg["pad_after"], cfg["merge_gap"]
    words = [w for s in sents for w in s.words]
    iv = []
    for k, w in enumerate(words):
        if not w.keep:
            continue
        lo, hi = w.start - pb, w.end + pa
        if k > 0 and not words[k - 1].keep:
            lo = max(lo, words[k - 1].end)
        if k + 1 < len(words) and not words[k + 1].keep:
            hi = min(hi, words[k + 1].start)
        iv.append([max(0.0, lo), min(duration, hi)])
    iv = _merge(iv, mg)
    vad_p = _merge([[max(0.0, s - pb), min(duration, e + pa + 0.05)] for s, e in vad], 0.0)
    out = _merge(_intersect(iv, vad_p), mg)
    out = _absorb_fragments(out, min_len=0.3, max_gap=0.35)
    return [[round(s, 3), round(e, 3)] for s, e in out if e - s >= 0.12]


def _absorb_fragments(iv: list[list[float]], min_len: float, max_gap: float) -> list[list[float]]:
    """Join a very short kept piece to its nearest neighbour so a word is not chopped."""
    out = [list(x) for x in iv]
    k = 0
    while k < len(out):
        s, e = out[k]
        if e - s >= min_len or len(out) == 1:
            k += 1
            continue
        gap_prev = s - out[k - 1][1] if k > 0 else 1e9
        gap_next = out[k + 1][0] - e if k + 1 < len(out) else 1e9
        if min(gap_prev, gap_next) > max_gap:
            k += 1
            continue
        if gap_prev <= gap_next:
            out[k - 1][1] = e
        else:
            out[k + 1][0] = s
        del out[k]
    return out


class EditMap:
    """Maps source time -> edited time for kept source intervals, played at `speed`."""

    def __init__(self, keeps: list[list[float]], speed: float = 1.0):
        self.keeps = keeps
        self.speed = speed
        self.offsets = []
        acc = 0.0
        for s, e in keeps:
            self.offsets.append(acc)
            acc += e - s
        self.raw_duration = acc
        self.duration = acc / speed

    def to_edit(self, t: float) -> float:
        for (s, e), off in zip(self.keeps, self.offsets):
            if t < s:
                return off / self.speed
            if t <= e:
                return (off + (t - s)) / self.speed
        return self.duration

    def to_source(self, t: float) -> float:
        t = t * self.speed
        for (s, e), off in zip(self.keeps, self.offsets):
            if t <= off + (e - s):
                return s + max(0.0, t - off)
        return self.keeps[-1][1]

    def cut_points(self) -> list[float]:
        return [round(o / self.speed, 3) for o in self.offsets[1:]]


def remove_editorial(sents: list[Sentence], drop_anchors: list[str]) -> list[str]:
    """Editorial cuts from the content plan: drop kept sentences that start with an anchor
    (e.g. a paraphrase that repeats the hook)."""
    log = []
    for a in drop_anchors:
        na = _norm(a)
        for s in sents:
            kept = [w for w in s.words if w.keep]
            if kept and _norm("".join(w.text for w in kept)).startswith(na):
                for w in s.words:
                    w.keep, w.reason = False, "editorial"
                log.append(f"drop sent {s.idx} '{s.text}' -> editorial (plan)")
                break
    return log


def extend_tail(keeps: list[list[float]], tail: float, duration: float) -> list[list[float]]:
    """Hold a short natural tail after the last word so the final caption/CTA can land."""
    if keeps and tail > 0:
        keeps[-1][1] = round(min(duration, keeps[-1][1] + tail), 3)
    return keeps


def cold_open(sents: list[Sentence], keeps: list[list[float]], anchor: str, cfg: dict,
              start_at: str | None = None) -> tuple[list, list[str]]:
    """Flash-forward hook: copy the kept intervals of the sentence starting with `anchor`
    to the very front of the edit (it is also kept in its original place).
    `start_at` (optional) starts the teaser at that word, dropping a dangling opener ("그런데")."""
    na = _norm(anchor)
    for s in sents:
        kept = [w for w in s.words if w.keep]
        if kept and _norm("".join(w.text for w in kept)).startswith(na):
            first = kept[0]
            if start_at:
                first = next((w for w in kept if _norm(w.text).startswith(_norm(start_at))), first)
            lo, hi = first.start - cfg["pad_before"], kept[-1].end + cfg["pad_after"]
            teaser = [[max(a, lo), min(b, hi)] for a, b in keeps if b > lo and a < hi]
            if teaser:
                return teaser + keeps, [f"cold open: '{s.text}' ({sum(b - a for a, b in teaser):.1f}s) moved to the front"]
    return keeps, [f"cold open anchor not found: {anchor}"]


def plan_cuts(tr: dict, vad: list[list[float]], cfg: dict, duration: float,
              drop_anchors: list[str] | None = None, cold_open_anchor: str | None = None,
              cold_open_from: str | None = None):
    sents = sentences_from_transcript(tr)
    log = remove_bad_takes(sents, cfg["retake_similarity"])
    log += remove_editorial(sents, drop_anchors or [])
    log += remove_self_repairs(sents)
    log += remove_fillers(sents, cfg["fillers"])
    keeps = keep_intervals(sents, vad, cfg, duration)
    keeps = extend_tail(keeps, cfg.get("end_tail", 0.0), duration)
    if cold_open_anchor:
        keeps, msg = cold_open(sents, keeps, cold_open_anchor, cfg, cold_open_from)
        log += msg
    return sents, keeps, log
