"""Word-karaoke captions (style captions.mode = "word_karaoke").

Big outlined words without a box; the word being spoken lights up (colour + scale),
plan keywords keep a secondary colour, warning words (안됩니다, 금지) a warning colour,
and a caption that is only a number/amount is shown larger. Each caption enters with a
short spring pop and is replaced by the next one (no exit).
"""
from __future__ import annotations

import html
import re

from .plan import BOUND_PREFIX, NEG_WORDS, Chunk, _no_break, is_number_word

W, H = 1080, 1920
STRIP = re.compile(r"[.,!…~\"'“”]+")
LINE_H = 1.2
WORD_GAP_EM = 0.36

DEFAULTS = {
    "font_size": 104, "number_size": 140, "font_weight": 900, "fill": "#FFFFFF",
    "stroke": {"color": "#000000", "width": 9},
    "shadow": {"color": "rgba(0,0,0,.55)", "blur": 10, "y": 4},
    # active_color None: the spoken word only pops (scale); keywords light up in keyword_color
    # when spoken and stay lit; warning words use warn_color
    # active_lift: the spoken word hops up (px) instead of scaling, so word spacing never changes
    "emphasis": {"active_color": None, "active_scale": 1.12, "active_lift": 0,
                 "keyword_color": "#FFE14D", "warn_color": "#FF4D4D"},
    # captions over full-graphic beats sit in a solid chip so they never compete with the card
    "graphic_box": {"bg": "rgba(14,14,14,.92)", "radius": 22, "pad_x": 30, "pad_y": 6},
    # graphic_plain: over full-screen cards the caption stays plain white (no keyword colour) so it never
    # competes with the card's own accent colours
    "graphic_plain": False,
    "animation": {"in": "spring_pop", "in_dur": 0.12},
    "safe_x": 0.10,
    "max_lines": 1,          # 2: long captions wrap instead of shrinking below min_scale
    "min_scale": 0.85,
    "safe_bottom": 0.645,
    "graphic_font_size": None,   # caption size over full-screen cards (they carry their own headline)    # 2-line captions never extend below this (IG bottom UI starts at 0.65)
}


def _rows_html(spans: list[str], lines: list[list[int]]) -> str:
    if len(lines) == 1:
        return "".join(spans)
    return "".join(f'<div class="kr">{"".join(spans[k] for k in ln)}</div>' for ln in lines)


def _cfg(style: dict) -> dict:
    cc = style["captions"]
    out = {k: cc.get(k, v) for k, v in DEFAULTS.items()}
    for k in ("stroke", "shadow", "emphasis", "animation", "graphic_box"):
        out[k] = {**DEFAULTS[k], **(cc.get(k) or {})}
    if "graphic_box" in cc and cc["graphic_box"] is None:
        out["graphic_box"] = None
    return out


def em_width(text: str) -> float:
    """Rough rendered width in em for Pretendard (Hangul ~0.95em, latin/digits ~0.62em)."""
    w = 0.0
    for ch in text:
        if ch == " ":
            w += WORD_GAP_EM
        elif "가" <= ch <= "힣":
            w += 0.95
        else:
            w += 0.62
    return w


def fit_size(words: list[str], base: int, max_width: float, active_scale: float) -> int:
    """Largest font size <= base whose line (incl. the active word's scale) fits max_width."""
    em = em_width(" ".join(words)) + 0.95 * (active_scale - 1.0) * 2
    return int(min(base, max_width / max(em, 0.1)))


def split_lines(words: list[str], base: int, max_width: float, max_lines: int, min_scale: float,
                no_break=None) -> list[list[int]]:
    """Word indices per line: one line unless it would shrink below min_scale * base, then a balanced
    2-line wrap. `no_break(k)` -> True forbids a break before word k (bound nouns, numerals)."""
    if max_lines < 2 or len(words) < 2 or fit_size(words, base, max_width, 1.0) >= base * min_scale:
        return [list(range(len(words)))]
    widths = [em_width(w) for w in words]
    cands = [k for k in range(1, len(words)) if not (no_break and no_break(k))] or list(range(1, len(words)))
    best = min(cands, key=lambda k: abs(sum(widths[:k]) - sum(widths[k:])))
    return [list(range(best)), list(range(best, len(words)))]


def word_role(text: str, keyword: bool, warn_words=None) -> str:
    if any(nw in text for nw in (NEG_WORDS if warn_words is None else warn_words)):
        return "warn"
    return "keyword" if keyword else "plain"


def captions_html(chunks: list[Chunk], style: dict, duration: float) -> tuple[str, list[tuple[float, str]]]:
    cfg = _cfg(style)
    em, st, sh = cfg["emphasis"], cfg["stroke"], cfg["shadow"]
    fam = style["font"]["family"]
    max_w = W * (1 - 2 * cfg["safe_x"])
    lit = {"plain": cfg["fill"], "keyword": em["keyword_color"], "warn": em["warn_color"]}
    gb = cfg["graphic_box"]
    groups, js, events = [], [], []
    for i, c in enumerate(chunks):
        if not c.text or c.hidden:
            continue
        marks = c.emph_words or [c.emph] * len(c.words)
        items = [(STRIP.sub("", w.text), w, m) for w, m in zip(c.words, marks)]
        items = [x for x in items if x[0]]
        if not items:
            continue
        solo_num = len(items) == 1 and is_number_word(items[0][1])
        base = cfg["number_size"] if solo_num else cfg["font_size"]
        if c.layout == "graphic" and cfg.get("graphic_font_size"):
            base = cfg["graphic_font_size"]
        texts = [x[0] for x in items]
        ws = [x[1] for x in items]
        # over full-screen cards a caption stays on one line (a 2nd line would run into the card or below the safe zone)
        max_lines = 1 if c.layout == "graphic" else cfg["max_lines"]
        lines = split_lines(texts, base, max_w, max_lines, cfg["min_scale"],
                            lambda k: _no_break(ws[k - 1], ws[k], BOUND_PREFIX))
        fs = min(fit_size([texts[k] for k in ln], base, max_w, em["active_scale"]) for ln in lines)
        # 1 line sits on the band; 2 lines centre on it, lifted so they end above safe_bottom
        top = c.y * H - fs * LINE_H * len(lines) / 2
        if len(lines) > 1:   # keep the block's bottom inside the IG safe zone
            top = min(top, cfg["safe_bottom"] * H - fs * LINE_H * len(lines))
        dur = max(0.1, c.end - c.start)
        spans = []
        for k, (txt, w, m) in enumerate(items):
            role = "keyword" if solo_num else word_role(txt, m, em.get("warn_words"))
            if cfg["graphic_plain"] and c.layout == "graphic":
                role = "plain"
            start_col = lit[role] if (solo_num or role == "plain") else cfg["fill"]
            on_col = em["active_color"] or lit[role]
            spans.append(f'<span class="kw" id="w{i}_{k}" style="color:{start_col}">{html.escape(txt)}</span>')
            t_on = max(c.start, w.start)
            t_off = items[k + 1][1].start if k + 1 < len(items) else None
            act = f'scale:{em["active_scale"]},y:{-em["active_lift"]}'
            js.append(f'tl.fromTo("#w{i}_{k}",{{color:"{start_col}",scale:1,y:0}},{{color:"{on_col}",'
                      f'{act},duration:.08,ease:"back.out(3)",immediateRender:false}},{t_on:.3f});')
            if t_off is not None and t_off > t_on + 0.05:
                js.append(f'tl.fromTo("#w{i}_{k}",{{color:"{on_col}",{act}}},'
                          f'{{color:"{lit[role]}",scale:1,y:0,duration:.1,ease:"power1.out",immediateRender:false}},{t_off:.3f});')
            if role == "keyword" and not solo_num:
                events.append((round(t_on, 3), "pop"))
        if solo_num:
            events.append((round(c.start, 3), "ding"))
        groups.append(
            f'<div id="cg{i}" class="clip cg" data-start="{c.start:.3f}" data-duration="{dur:.3f}" data-track-index="0" '
            f'style="top:{top:.0f}px"><div class="kl{" boxed" if c.layout == "graphic" and gb else ""}" id="cc{i}" '
            f'style="font-size:{fs}px">{_rows_html(spans, lines)}</div></div>')
        if c.start >= 0.05:
            d = cfg["animation"]["in_dur"] / 2
            js.append(f'tl.fromTo("#cc{i}",{{scale:.9}},{{scale:1.08,duration:{d:.3f},ease:"power2.out"}},{c.start:.3f});')
            js.append(f'tl.fromTo("#cc{i}",{{scale:1.08}},{{scale:1,duration:{d:.3f},ease:"power1.inOut",'
                      f'immediateRender:false}},{c.start + d:.3f});')
    shadow = f"0 {sh['y']}px {sh['blur']}px {sh['color']}"
    box_css = (f".boxed {{ background: {gb['bg']}; border-radius: {gb['radius']}px; "
               f"padding: {gb['pad_y']}px {gb['pad_x']}px; }}") if gb else ""
    body = "\n    ".join(groups)
    jsb = "\n    ".join(js)
    doc = f"""<template>
  <style>
    @font-face {{ font-family: '{fam}'; src: url('assets/fonts/PretendardVariable.ttf') format('truetype'); font-weight: 100 900; }}
    #root {{ position: absolute; inset: 0; }}
    .cg {{ position: absolute; left: 0; width: 1080px; display: flex; justify-content: center; }}
    .kl {{ display: flex; gap: {WORD_GAP_EM}em; font-family: '{fam}', sans-serif; font-weight: {cfg['font_weight']};
          line-height: {LINE_H}; letter-spacing: -0.02em; white-space: nowrap; transform-origin: 50% 60%; }}
    .kl:has(.kr) {{ flex-direction: column; align-items: center; gap: 0; }}
    .kr {{ display: flex; gap: {WORD_GAP_EM}em; justify-content: center; }}
    {box_css}
    .kw {{ display: inline-block; -webkit-text-stroke: {st['width'] * 2}px {st['color']}; paint-order: stroke fill;
          text-shadow: {shadow}; transform-origin: 50% 70%; }}
  </style>
  <div id="root" data-composition-id="captions" data-width="1080" data-height="1920">
    {body}
  </div>
  <script>
    const tl = gsap.timeline({{ paused: true }});
    {jsb}
    tl.set({{}},{{}},{duration:.3f});
    window.__timelines["captions"] = tl;
  </script>
</template>
"""
    return doc, events
