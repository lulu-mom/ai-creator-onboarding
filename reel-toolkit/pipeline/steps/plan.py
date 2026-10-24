"""Step 4-6 planning: caption chunks, layout segments (cut rhythm) and graphic scenes.

All times here are EDITED-timeline seconds.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .cut import EditMap, Sentence, _norm

STRIP_PUNCT = re.compile(r"[.,!…~\"'“”]+")
NEG_WORDS = ("안됩", "안 ", "않", "말라", "못", "마세요", "금지")


@dataclass
class EWord:
    text: str
    start: float
    end: float
    sent: int


@dataclass
class Chunk:
    words: list[EWord]
    start: float = 0.0
    end: float = 0.0
    emph: bool = False
    emph_words: list = field(default_factory=list)
    y: float = 0.45
    layout: str = ""
    hidden: bool = False      # a full-screen card already shows this text (scene param hide_caption)

    @property
    def text(self) -> str:
        t = " ".join(STRIP_PUNCT.sub("", w.text) for w in self.words)
        return re.sub(r"\s+", " ", t).strip()

    @property
    def sent(self) -> int:
        return self.words[0].sent


@dataclass
class Segment:
    chunks: list[Chunk]
    layout: str = "split"
    scene: int = 0
    start: float = 0.0
    end: float = 0.0
    punch: float = 1.0

    @property
    def dur(self) -> float:
        return self.end - self.start


@dataclass
class ScenePlan:
    idx: int
    template: str
    params: dict
    start: float = 0.0
    end: float = 0.0
    first_chunk: int = 0
    layout_events: list = field(default_factory=list)


# ------------------------------------------------------------------ words
def edited_words(sents: list[Sentence], em: EditMap) -> list[EWord]:
    """Kept words in EDITED order. A word inside several kept intervals (e.g. a cold-open teaser
    that repeats a later line) appears once per interval."""
    items = []
    for s in sents:
        for w in s.words:
            if not w.keep:
                continue
            mid = (w.start + w.end) / 2
            hits = [(k, iv) for k, iv in enumerate(em.keeps) if iv[0] - 0.02 <= mid <= iv[1] + 0.02]
            if not hits:
                # ASR timing drift: snap to the nearest kept interval (and to every copy of it,
                # e.g. the cold-open teaser) instead of dropping or misplacing the word
                def dist(iv):
                    return 0.0 if iv[0] <= mid <= iv[1] else min(abs(mid - iv[0]), abs(mid - iv[1]))
                best = min(em.keeps, key=dist)
                if dist(best) <= 0.6:
                    hits = [(k, iv) for k, iv in enumerate(em.keeps) if dist(iv) <= dist(best) + 1e-6]
            if hits:
                for k, (ks, ke) in hits:
                    off = em.offsets[k]
                    a = (off + min(max(w.start, ks), ke) - ks) / em.speed
                    b = (off + max(min(w.end, ke), min(max(w.start, ks), ke)) - ks) / em.speed
                    items.append((a, b, w.text, s.idx))
            else:
                later = [(iv[0], k) for k, iv in enumerate(em.keeps) if iv[1] > w.start]
                k = min(later)[1] if later else len(em.keeps) - 1
                a = em.offsets[k] / em.speed
                items.append((a - 0.001, a + 0.05, w.text, s.idx))
    items.sort(key=lambda x: x[0])
    out: list[EWord] = []
    for a, b, text, sid in items:
        if out and re.fullmatch(r"[%.,?!]+", text.strip()) and out[-1].sent == sid:
            out[-1].text += text.strip()
            out[-1].end = round(max(out[-1].end, b), 3)
            continue
        if out and a < out[-1].start:
            a = out[-1].start
        out.append(EWord(text, round(a, 3), round(max(b, a + 0.06), 3), sid))
    return out


# words that must not start a caption chunk (Korean bound nouns / counters) and
# words that must not end one (numerals / determiners that modify the next word)
BOUND_NEXT = {"수", "명", "것", "거", "줄", "개", "번", "번째", "건", "중", "가지", "때", "뿐", "적", "데", "만큼"}
# bound noun / negative auxiliary that completes the previous word ("두 명 | 몫까지", "바뀌지 | 않을");
# opt-in per style with captions.bind_prefixes
BOUND_PREFIX = ("몫", "않", "못하")
BIND_PREV = {"한", "두", "세", "네", "첫", "이", "그", "저", "할", "될", "몇", "모든", "이번", "다음", "제", "AI", "내", "더", "잘", "안", "못"}


def _no_break(prev: EWord, nxt: EWord, prefixes: tuple = ()) -> bool:
    p, n = _norm(prev.text), _norm(nxt.text)
    return (n in BOUND_NEXT or any(n.startswith(b) and len(n) <= len(b) + 2 for b in ("번째", "가지"))
            or (bool(prefixes) and n.startswith(prefixes)) or p in BIND_PREV)


# ------------------------------------------------------------------ chunks
def keep_spans(words: list[EWord], phrases: list[str] | None) -> list[int | None]:
    """Per word: id of the plan "caption_keep" phrase it belongs to (None = free).
    Every occurrence of each phrase is marked."""
    span: list[int | None] = [None] * len(words)
    sid = 0
    for ph in phrases or []:
        target = _norm(ph)
        wi = _match_anchor(words, ph)
        while wi is not None:
            acc, j = "", wi
            while j < len(words) and len(acc) < len(target):
                acc += _norm(words[j].text)
                j += 1
            if all(x is None for x in span[wi:j]):
                span[wi:j] = [sid] * (j - wi)
                sid += 1
            wi = _match_anchor(words, ph, wi + 1)
    return span


def make_chunks(words: list[EWord], cfg: dict, duration: float, keep: list[str] | None = None) -> list[Chunk]:
    max_w, max_c, max_d = cfg["max_words"], cfg["max_chars"], cfg["max_dur"]
    chunks: list[Chunk] = []
    cur: list[EWord] = []

    def flush():
        if cur:
            chunks.append(Chunk(list(cur)))
            cur.clear()

    solo = bool(cfg.get("solo_numbers"))
    pre = BOUND_PREFIX if cfg.get("bind_prefixes") else ()
    span = keep_spans(words, keep)
    for i, w in enumerate(words):
        if cur and keep and (span[i] is not None or span[i - 1] is not None):
            # plan-defined phrase: never split inside it, always break at its edges
            if span[i] != span[i - 1] or w.sent != cur[-1].sent:
                flush()
            cur.append(w)
            continue
        if cur and solo and (is_number_word(w) or is_number_word(cur[-1])):
            # numbers / money get a caption of their own (shown bigger by the karaoke renderer)
            flush()
        if cur:
            chars = sum(len(_norm(x.text)) for x in cur) + len(_norm(w.text))
            ends_prev = bool(re.search(r"[.?!,]$", cur[-1].text))
            topic_end = len(cur) >= 1 and re.search(r"(에게는|에서는|는|은)$", _norm(cur[-1].text)) is not None                 and len(_norm(cur[-1].text)) >= 3
            topic_end = topic_end and not _no_break(cur[-1], w)
            hard = ends_prev or w.sent != cur[-1].sent or topic_end
            soft = len(cur) >= max_w or chars > max_c or w.end - cur[0].start > max_d
            limit = max_w + (1 if pre and _norm(w.text).startswith(pre) else 0)
            if hard or (soft and not (_no_break(cur[-1], w, pre) and len(cur) <= limit)):
                flush()
        cur.append(w)
    flush()
    # merge a dangling 1-word chunk with ≤3 chars into the previous chunk of the same sentence
    merged: list[Chunk] = []
    word_idx = {id(w): k for k, w in enumerate(words)}

    def kept(c: Chunk) -> bool:
        return any(span[word_idx[id(w)]] is not None for w in c.words)

    for c in chunks:
        if kept(c) or (merged and kept(merged[-1])):
            merged.append(c)
        elif solo and (is_number_word(c.words[0]) or (merged and is_number_word(merged[-1].words[-1]))):
            merged.append(c)
        elif (merged and len(c.words) == 1 and len(_norm(c.words[0].text)) <= 3 and merged[-1].sent == c.sent
                and len(merged[-1].words) < max_w + 1
                and sum(len(_norm(x.text)) for x in merged[-1].words) + len(_norm(c.words[0].text)) <= max_c + 2):
            merged[-1].words.extend(c.words)
        else:
            merged.append(c)
    for k, c in enumerate(merged):
        c.start = 0.0 if k == 0 else c.words[0].start
        nxt = merged[k + 1].words[0].start if k + 1 < len(merged) else None
        last_end = c.words[-1].end + 0.25
        c.end = nxt if (nxt is not None and nxt - c.words[-1].end < 0.7) else min(last_end, duration)
        if nxt is not None:
            c.end = min(c.end, nxt)
    merged[-1].end = duration
    return merged


NUMBER_WORD = re.compile(r"\d")


def is_number_word(w: EWord) -> bool:
    """A word that carries a number or an amount (3가지, 20%, 150만)."""
    return bool(NUMBER_WORD.search(w.text))


def _match_anchor(words: list[EWord], anchor: str, from_idx: int = 0) -> int | None:
    """Index of the first word where the normalised anchor text begins."""
    target = _norm(anchor)
    if not target:
        return None
    norms = [_norm(w.text) for w in words]
    for i in range(from_idx, len(words)):
        acc = ""
        for j in range(i, min(len(words), i + 8)):
            acc += norms[j]
            if acc.startswith(target) or (target.startswith(acc) and len(acc) >= len(target)):
                return i
            if not target.startswith(acc):
                break
    return None


def mark_emphasis(chunks: list[Chunk], plan: dict | None) -> None:
    """Word-level emphasis: only the words covered by an emphasis anchor turn orange."""
    anchors = [_norm(a) for a in (plan or {}).get("emphasis", []) if _norm(a)]
    for c in chunks:
        norms = [_norm(STRIP_PUNCT.sub("", w.text)) for w in c.words]
        marks = [False] * len(norms)
        if anchors:
            joined = "".join(norms)
            spans, pos = [], 0
            for n in norms:
                spans.append((pos, pos + len(n)))
                pos += len(n)
            for a in anchors:
                k = joined.find(a)
                while k >= 0:
                    for wi, (lo, hi) in enumerate(spans):
                        if lo < k + len(a) and hi > k:
                            marks[wi] = True
                    k = joined.find(a, k + 1)
        else:
            marks = [bool(re.search(r"\d|%|AI", w.text)) or any(nw in w.text for nw in NEG_WORDS) for w in c.words]
        c.emph_words = marks
        c.emph = any(marks)


# ------------------------------------------------------------------ scenes + segments
def resolve_scenes(words: list[EWord], chunks: list[Chunk], plan: dict | None) -> list[ScenePlan]:
    word_chunk = {}
    k = 0
    for ci, c in enumerate(chunks):
        for _ in c.words:
            word_chunk[k] = ci
            k += 1
    scenes: list[ScenePlan] = []
    if plan and plan.get("scenes"):
        pos = 0
        for si, sc in enumerate(plan["scenes"]):
            wi = _match_anchor(words, sc["anchor"], pos)
            if wi is None:
                print(f"[plan] anchor not found, scene skipped: {sc['anchor']}")
                continue
            pos = wi + 1
            scenes.append(ScenePlan(len(scenes), sc["template"], sc.get("params", {}),
                                    first_chunk=word_chunk[wi]))
    else:
        seen = set()
        for ci, c in enumerate(chunks):
            if c.sent not in seen:
                seen.add(c.sent)
                scenes.append(ScenePlan(len(scenes), "keyword", auto_keyword(chunks, c.sent),
                                        first_chunk=ci))
    if not scenes or scenes[0].first_chunk != 0:
        scenes.insert(0, ScenePlan(0, "keyword", auto_keyword(chunks, chunks[0].sent), first_chunk=0))
    # drop scenes that start on the same chunk (keep the later definition)
    uniq: list[ScenePlan] = []
    for sc in scenes:
        if uniq and uniq[-1].first_chunk == sc.first_chunk:
            uniq[-1] = sc
        else:
            uniq.append(sc)
    for i, sc in enumerate(uniq):
        sc.idx = i
    return uniq


def auto_keyword(chunks: list[Chunk], sent: int) -> dict:
    words = [w.text for c in chunks if c.sent == sent for w in c.words]
    cands = sorted((STRIP_PUNCT.sub("", w) for w in words), key=lambda w: -len(_norm(w)))
    kw = cands[0] if cands else ""
    num = next((w for w in words if re.search(r"\d", w)), None)
    return {"keyword": STRIP_PUNCT.sub("", num or kw), "sub": " ".join(words[:4]), "icon": "spark"}


def make_segments(chunks: list[Chunk], scenes: list[ScenePlan], cfg: dict) -> list[Segment]:
    mn, tgt, mx = cfg["segment_min"], cfg["segment_target"], cfg["segment_max"]
    forced = {sc.first_chunk for sc in scenes}
    segs: list[Segment] = []
    cur: list[Chunk] = []
    for ci, c in enumerate(chunks):
        if cur:
            dur = cur[-1].end - cur[0].start
            new_dur = c.end - cur[0].start
            if (ci in forced or dur >= tgt or (dur >= mn and c.sent != cur[-1].sent)
                    or (new_dur > mx and dur >= mn * 0.6)):
                segs.append(Segment(cur))
                cur = []
        cur.append(c)
    if cur:
        segs.append(Segment(cur))
    # merge a too-short tail segment into its predecessor when it does not start a scene
    out: list[Segment] = []
    for s in segs:
        s.start, s.end = s.chunks[0].start, s.chunks[-1].end
        if out and s.dur < 0.7 and chunks.index(s.chunks[0]) not in forced:
            out[-1].chunks.extend(s.chunks)
            out[-1].end = s.end
        else:
            out.append(s)
    for s in out:
        s.start, s.end = s.chunks[0].start, s.chunks[-1].end
    return out


def assign_layouts(segs: list[Segment], scenes: list[ScenePlan], chunks: list[Chunk],
                   words: list[EWord], plan: dict | None, rcfg: dict, lcfg: dict) -> None:
    chunk_seg = {}
    for si, s in enumerate(segs):
        for c in s.chunks:
            chunk_seg[id(c)] = si
    word_chunk = []
    for c in chunks:
        word_chunk += [c] * len(c.words)
    # scene of each segment
    starts = [sc.first_chunk for sc in scenes]
    for s in segs:
        ci = chunks.index(s.chunks[0])
        s.scene = max(i for i, st in enumerate(starts) if st <= ci)
    hints: dict[int, str] = {}
    for kind in ("face", "graphic"):
        for a in (plan or {}).get(kind, []):
            # "text" hints every occurrence (a cold-open teaser repeats a line);
            # {"anchor": "text", "occurrence": n} only the n-th (1-based)
            text, only = (a["anchor"], int(a.get("occurrence", 0))) if isinstance(a, dict) else (a, 0)
            wi, n = _match_anchor(words, text), 0
            while wi is not None:
                n += 1
                if not only or n == only:
                    hints[chunk_seg[id(word_chunk[wi])]] = kind
                wi = _match_anchor(words, text, wi + 1)
    scene_first = {}
    for si, s in enumerate(segs):
        scene_first.setdefault(s.scene, si)
    since_change = 0
    alt_count = 0
    base = rcfg.get("default_layout", "split")
    for si, s in enumerate(segs):
        first_of_scene = scene_first[s.scene] == si
        prev = segs[si - 1].layout if si else base
        if base != "split":
            # talking-head styles: every segment uses the base layout unless the plan hints otherwise;
            # a scene may set its own default layout (params.layout, e.g. "split" for a floating panel)
            s.layout = hints.get(si, scenes[s.scene].params.get("layout", base))
            continue
        if si == 0:
            s.layout = "split"
        elif si in hints and not (hints[si] == "face" and (first_of_scene or prev == "face")):
            s.layout = hints[si]
        else:
            last_of_sentence = si + 1 < len(segs) and segs[si + 1].chunks[0].sent != s.chunks[-1].sent
            auto_gap = int((plan or {}).get("auto_gap", 2))
            if (not first_of_scene and prev == "split" and
                    ((not hints and last_of_sentence) or since_change >= auto_gap)):
                # alternate the two full-screen layouts so long split runs are broken up
                s.layout = "graphic" if (alt_count % 3 == 2) else "face"
                alt_count += 1
            else:
                s.layout = "split"
        since_change = since_change + 1 if s.layout == "split" else 0
    # punch-in / punch-out: consecutive segments with the same layout alternate framing so
    # every segment boundary is a visible cut (reference: scale changes happen at cuts)
    big = lcfg.get("emphasis_punch", 1.15)
    for si, s in enumerate(segs):
        prev = segs[si - 1] if si else None
        if prev is not None and prev.layout == s.layout:
            s.punch = 1.0 if prev.punch != 1.0 else big
        else:
            s.punch = big if s.layout == "face" else 1.0
        sp = lcfg.get("split_punch")
        if s.layout == "split" and sp is False:
            s.punch = 1.0   # the speaker stays still under a floating panel (no reframe while it is up)
        elif s.layout == "split" and isinstance(sp, (int, float)) and not isinstance(sp, bool):
            # reframe only when the panel changes scene (the cut lands on the panel swap)
            s.punch = float(sp) if s.scene % 2 else 1.0
    for sc in scenes:
        mine = [s for s in segs if s.scene == sc.idx]
        sc.start = mine[0].start
        sc.end = mine[-1].end
        sc.layout_events = [(round(s.start - sc.start, 3), s.layout) for s in mine]


def hide_card_captions(segs: list[Segment], scenes: list[ScenePlan]) -> None:
    for sg in segs:
        if sg.layout == "graphic" and scenes[sg.scene].params.get("hide_caption"):
            for c in sg.chunks:
                c.hidden = True


def caption_positions(segs: list[Segment], ccfg: dict) -> None:
    for s in segs:
        y = {"split": ccfg["y_split"], "face": ccfg["y_full_face"],
             "graphic": ccfg["y_full_graphic"]}[s.layout]
        for c in s.chunks:
            c.y = y
            c.layout = s.layout


def anchor_resolver(words: list[EWord], scene: ScenePlan):
    """Return f(anchor, default) -> seconds relative to scene start."""
    first_word = 0
    for i, w in enumerate(words):
        if w.start >= scene.start - 1e-3:
            first_word = i
            break

    def resolve(anchor: str, default: float) -> float:
        wi = _match_anchor(words, anchor, first_word)
        if wi is None or words[wi].start > scene.end + 0.05:
            return default
        return max(0.0, words[wi].start - scene.start)

    return resolve


def fix_caption_words(chunks: list[Chunk], fixes: dict | None) -> None:
    """Plan "caption_fixes": {"ASR word": "correct word"} applied to on-screen caption words only."""
    if not fixes:
        return
    for c in chunks:
        for w in c.words:
            core = STRIP_PUNCT.sub("", w.text)
            if core in fixes:
                w.text = w.text.replace(core, fixes[core])


def build_plan(sents, em: EditMap, style: dict, plan: dict | None):
    words = edited_words(sents, em)
    chunks = make_chunks(words, style["captions"], em.duration, (plan or {}).get("caption_keep"))
    fix_caption_words(chunks, (plan or {}).get("caption_fixes"))
    mark_emphasis(chunks, plan)
    scenes = resolve_scenes(words, chunks, plan)
    segs = make_segments(chunks, scenes, style["rhythm"])
    assign_layouts(segs, scenes, chunks, words, plan, style["rhythm"], style["layout"])
    caption_positions(segs, style["captions"])
    hide_card_captions(segs, scenes)
    return words, chunks, segs, scenes
