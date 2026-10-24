"""Doodle (whiteboard) templates: each takes (DoodleScene, params) and draws on the paper board.

params["at"] maps beat names to transcript anchor words (as in templates.py). Layouts are
fixed grids on the 1080 x board_h board so every scene shares the same margins and scale:
title row y 30-130, content y 160-860, side margins 60 px.
"""
from __future__ import annotations

import re

from .doodle_kit import (DoodleScene, arrow_paths, check_path, cross_paths, rough_ellipse, rough_line,
                         rough_rect, wave_line)
from .scene import esc

TITLE_Y = 34
HAND_W = 0.80        # approx. advance of one hand-font glyph, in font-size units


def _a(p: dict, key: str):
    return (p.get("at") or {}).get(key)


def _tw(text: str, size: int) -> float:
    plain = re.sub(r"<[^>]+>", "", text)
    return sum(size * (0.42 if ch == " " else 0.55 if ch.isascii() else HAND_W) for ch in plain)


def _title(s: DoodleScene, text: str | None, t: float, color: str | None = None) -> float:
    """Title in hand writing with a yellow marker swipe behind it."""
    if not text:
        return t
    size = 78
    w = min(960, _tw(text, size) + 30)
    s.svg("tmk", [rough_line(540 - w / 2, TITLE_Y + 72, 540 + w / 2, TITLE_Y + 70, s.rng("tmk"), 0.004)],
          color="marker", width=30, opacity=.85)
    s.text("ttl", 540, TITLE_Y, text, size=size, color=color)
    if s.first and t <= 0.01:
        s.show("tmk")
        s.show("ttl")
        return 0.0
    te = s.write("ttl", t, len(text))
    s.draw("tmk", t + 0.12, 0.3, sfx=None)
    return te


def _seq(s: DoodleScene, p: dict, keys: list[str], start: float, end_frac: float = 0.75) -> list[float]:
    """Anchor each beat; un-anchored beats are spread evenly between start and end_frac*dur."""
    n = len(keys)
    span = max(0.3, s.dur * end_frac - start)
    return [s.at(_a(p, k), start + span * i / max(1, n - 1) if n > 1 else start) for i, k in enumerate(keys)]


# --------------------------------------------------------------------------- stop (hook / twist)
def dd_stop(s: DoodleScene, p: dict) -> None:
    """A drawn result sheet -> arrow -> send button, then a red X and a circled warning."""
    items = p.get("items") or ["할 일", "답장", "매출"]
    pre = s.first
    t = _title(s, p.get("title"), 0.0)
    s.svg("doc", [rough_rect(70, 175, 430, 560, s.rng("doc"))])
    for i, it in enumerate(items[:3]):
        y = 225 + i * 165
        s.svg(f"cb{i}", [rough_rect(112, y + 20, 60, 60, s.rng("cb", i), 2)], width=5)
        s.svg(f"ck{i}", [check_path(118, y + 8, 64, s.rng("ck", i))], color="accent2", width=8)
        s.text(f"it{i}", 190, y + 8, esc(it), size=60, align="left", w=310)
    s.svg("ar", arrow_paths(515, 455, 660, 455, s.rng("ar"), bend=-0.18))
    s.svg("btn", [rough_rect(672, 380, 370, 150, s.rng("btn"))])
    s.text("bt", 857, 420, esc(p.get("button", "그대로 보내기")), size=56, w=360, font="body")
    s.svg("x", cross_paths(590, 455, 190, s.rng("x")), color="accent", width=13)
    stamp = p.get("stamp", "잠깐! 검토 먼저")
    sw = min(900, _tw(stamp, 86) + 120)
    s.text("st", 540, 760, esc(stamp), size=86, color="accent", rot=-2)
    s.svg("stc", [rough_ellipse(540, 812, sw / 2, 78, s.rng("stc"))], color="accent", width=7)
    names = ["doc"] + [f"cb{i}" for i in range(len(items[:3]))] + [f"ck{i}" for i in range(len(items[:3]))] + ["ar", "btn"]
    texts = [f"it{i}" for i in range(len(items[:3]))] + ["bt"]
    if pre:
        for n in names + texts:
            s.show(n)
    else:
        s.draw("doc", t * 0.3, 0.35)
        for i in range(len(items[:3])):
            s.draw(f"cb{i}", 0.2 + 0.1 * i, 0.2, sfx=None)
            s.write(f"it{i}", 0.25 + 0.1 * i, 3, sfx=None)
            s.draw(f"ck{i}", 0.4 + 0.1 * i, 0.2, sfx="tick" if i == 0 else None)
        s.draw("ar", 0.45, 0.25, sfx=None)
        s.draw("btn", 0.5, 0.25, sfx=None)
        s.write("bt", 0.55, 6, sfx=None)
    tb = 0.15 if pre else s.at(_a(p, "block"), s.dur * 0.55)
    s.draw("x", tb, 0.3, stagger=0.12, sfx="stamp", ease="power2.out")
    if not pre:
        s.nudge("card", tb + 0.3, (540, 450), 1.06)
        s.wiggle("card", tb + 0.32, 1.5, origin=(540, 450))
    s.wiggle("btn", tb + 0.3, 3, origin=(857, 455))
    s.write("st", tb + 0.2, len(stamp))
    s.draw("stc", tb + 0.45, 0.4, sfx=None)


# --------------------------------------------------------------------------- branch (one -> many)
def dd_branch(s: DoodleScene, p: dict) -> None:
    """Me in a circle at the top, arrows fanning out to N task boxes."""
    items = p.get("items", [])
    n = max(1, len(items))
    w, gap = 300, 25
    x0 = (1080 - n * w - (n - 1) * gap) / 2
    s.avatar_at("av", 540, 170, 180)
    s.svg("avc", [rough_ellipse(540, 170, 104, 104, s.rng("avc"))], width=6)
    s.text("me", 700, 120, esc(p.get("center", "나")), size=72, align="left", w=300)
    tops = []
    for i, it in enumerate(items):
        x = x0 + i * (w + gap)
        tops.append(x + w / 2)
        s.svg(f"b{i}", [rough_rect(x, 455, w, 285, s.rng("b", i))])
        s.icon_svg(f"i{i}", it.get("icon", "doc"), x + w / 2 - 48, 480, 96, color="accent2")
        s.text(f"l{i}", x + w / 2, 585, esc(it.get("label", "")), size=72, w=w)
        s.text(f"s{i}", x + w / 2, 660, esc(it.get("sub", "")), size=56, color="ink_soft", w=w, font="body")
    for i, cx in enumerate(tops):
        s.svg(f"a{i}", arrow_paths(540 + (cx - 540) * 0.12, 290, cx, 440, s.rng("a", i), bend=0.08 * (1 if cx < 540 else -1)))
    if p.get("headline"):
        s.svg("hmk", [rough_line(150, 838, 930, 834, s.rng("hmk"), 0.003)], color="marker", width=34, opacity=.85)
        s.text("hl", 540, 768, p["headline"], size=76)
    s.pop_in("av", 0.0, "pop")
    s.draw("avc", 0.1, 0.4, sfx=None)
    s.write("me", 0.2, 2, sfx=None)
    tb = [0.1] * n                    # the three task boxes are the scene skeleton (on the cut)
    if _a(p, "items"):
        t_items = s.at(_a(p, "items"), 0.45)
        tb = [t_items + 0.12 * i for i in range(n)]
    for i, tt in enumerate(tb):
        s.draw(f"b{i}", tt, 0.3, sfx="scribble" if i == 0 else None)
        s.draw(f"i{i}", tt + 0.1, 0.35, sfx=None)
        s.write(f"l{i}", tt + 0.15, 3, sfx=None)
        s.write(f"s{i}", tt + 0.25, 4, sfx=None)
    tr = s.at(_a(p, "run"), max(tb) + 0.4)
    for i in range(n):
        s.draw(f"a{i}", tr, 0.3, stagger=0.1, sfx="whoosh" if i == 0 else None)
    if p.get("headline"):
        s.draw("hmk", tr + 0.2, 0.35, sfx=None)
        s.write("hl", tr + 0.1, 8)


# --------------------------------------------------------------------------- versus / question
def dd_versus(s: DoodleScene, p: dict) -> None:
    """Left thing = right person ? (big red question mark, underlined question line)."""
    s.svg("lb", [rough_rect(95, 215, 330, 330, s.rng("lb"))])
    s.icon_svg("li", p.get("left_icon", "bot"), 190, 250, 140, color="accent2")
    s.text("lt", 260, 425, esc(p.get("left", "")), size=66, w=330)
    s.svg("eq", [rough_line(470, 355, 570, 352, s.rng("e1")), rough_line(470, 400, 570, 398, s.rng("e2"))], width=8)
    s.avatar_at("av", 790, 360, 230)
    s.svg("avc", [rough_ellipse(790, 360, 132, 132, s.rng("avc"))], width=6)
    s.text("rt", 790, 488, esc(p.get("right", "")), size=66, w=360)
    s.text("q", 985, 140, "?", size=250, color="accent", w=200, rot=10)
    line = p.get("line", "")
    lw = min(940, _tw(line, 74) + 40)
    s.text("ln", 540, 600, esc(line), size=74)
    s.svg("lu", [wave_line(540 - lw / 2, 700, lw, s.rng("lu"), 6)], color="accent", width=6)
    tl_ = s.at(_a(p, "left"), 0.0)
    tr_ = s.at(_a(p, "right"), max(0.5, tl_ + 0.5))
    s.draw("lb", tl_, 0.3)
    s.draw("li", tl_ + 0.1, 0.4, sfx=None)
    s.write("lt", tl_ + 0.2, 4, sfx=None)
    s.draw("eq", (tl_ + tr_) / 2, 0.2, stagger=0.08, sfx=None)
    s.pop_in("av", tr_, "pop")
    s.draw("avc", tr_ + 0.1, 0.4, sfx=None)
    s.write("rt", tr_ + 0.2, 4, sfx=None)
    tline = s.at(_a(p, "line"), tr_ + 0.5)
    s.write("ln", tline, len(line))
    s.draw("lu", tline + 0.35, 0.35, sfx=None)
    tq = s.at(_a(p, "q"), s.dur * 0.65)
    if p.get("meter"):
        # "how much of one person?" meter: outline, then hatched fill creeping to the question mark
        s.svg("mo", [rough_rect(170, 790, 740, 70, s.rng("mo"), 2.5)], width=5)
        s.add(f'<div class="dd-bar" id="{s.id("mf")}" style="left:176px;top:796px;width:728px;height:58px;transform-origin:0 50%;'
              f'transform:scaleX(0);background:repeating-linear-gradient(-45deg,{s.col("accent")} 0 7px,transparent 7px 19px)"></div>')
        s.text("ml", 930, 790, "?", size=76, color="accent", align="left", w=100)
        tm = tline + 0.5
        s.draw("mo", tm, 0.3, sfx=None)
        s._js(f'tl.fromTo("{s.sel("mf")}",{{scaleX:0}},{{scaleX:{float(p["meter"]):.2f},duration:{max(0.2, min(tq - tm - 0.2, s.dur - s.EXIT_GUARD - s.clamp(tm + 0.2))):.3f},'
              f'ease:"power1.inOut"}},{s.clamp(tm + 0.2):.3f});')
        s.ev(tm + 0.2, "rise")
        s.pop_in("ml", tq, None, frm=0.4)
    s.pop_in("q", tq, "stamp", frm=0.4)
    s.wiggle("q", tq + 0.4, 6)


# --------------------------------------------------------------------------- note -> extracted fields
def dd_note(s: DoodleScene, p: dict) -> None:
    """Notebook page on the left; key lines get highlighted and arrows pull out fields."""
    lines = p.get("lines", [])
    fields = p.get("fields", [])
    s.svg("pg", [rough_rect(40, 150, 590, 690, s.rng("pg"))])
    s.svg("rings", [rough_line(40, 190 + 70 * k, 72, 190 + 70 * k, s.rng("r", k), 0.02) for k in range(9)], width=5)
    s.text("doc", 335, 165, esc(p.get("doc", "메모")), size=60, color="accent2", w=540)
    for i, ln in enumerate(lines):
        y = 265 + i * 120
        s.svg(f"hl{i}", [rough_line(90, y + 56, 90 + min(520, _tw(ln, 74) + 10), y + 55, s.rng("hl", i), 0.003)],
              color="marker", width=46, opacity=.85)
        s.text(f"ln{i}", 88, y + 2, esc(ln), size=58, align="left", w=540, font="body", weight=800)
    for i, f in enumerate(fields):
        y = 190 + i * 215
        s.text(f"fl{i}", 712, y - 6, esc(f.get("label", "")), size=50, font="body", color="ink_soft", align="left", w=340)
        s.text(f"fv{i}", 712, y + 50, esc(f.get("value", "")), size=90, color="accent", align="left", w=360)
        src_y = 265 + f.get("line", i) * 120 + 34
        s.svg(f"fa{i}", arrow_paths(615, src_y, 700, y + 95, s.rng("fa", i), bend=0.12, head=24), width=5)
    if p.get("result"):
        s.text("res", 540, 790, esc(p["result"]), size=64, color="accent", w=1000)
    s.draw("pg", 0.0, 0.35)
    s.draw("rings", 0.1, 0.3, stagger=0.02, sfx=None)
    s.write("doc", 0.15, 5, sfx=None)
    for i in range(len(lines)):
        s.write(f"ln{i}", 0.12 + 0.06 * i, 9, sfx=None, dur=0.35)   # page content is part of the skeleton
    tf = _seq(s, p, [f"f{i}" for i in range(len(fields))], 0.9, 0.65)
    for i, tt in enumerate(tf):
        li = fields[i].get("line", i)
        s.draw(f"hl{li}", tt - 0.1, 0.25, sfx="marker")
        s.draw(f"fa{i}", tt, 0.25, sfx=None)
        s.write(f"fl{i}", tt + 0.1, 2, sfx=None, dur=0.2)
        s.write(f"fv{i}", tt + 0.18, 3, sfx=None)
    if p.get("result"):
        s.write("res", s.at(_a(p, "result"), s.dur * 0.75), len(p["result"]))


# --------------------------------------------------------------------------- handoff (thing -> worker)
def dd_handoff(s: DoodleScene, p: dict) -> None:
    """Big drawn object on the left, arrow, worker box on the right."""
    s.icon_svg("obj", p.get("icon", "mail"), 95, 200, 330, color="accent2")
    s.text("ol", 260, 545, esc(p.get("label", "")), size=78, w=480)
    s.svg("ar", arrow_paths(470, 360, 640, 360, s.rng("ar"), bend=-0.2))
    s.svg("wb", [rough_rect(660, 220, 340, 290, s.rng("wb"))])
    s.icon_svg("wi", p.get("worker_icon", "bot"), 760, 245, 140, color="ink")
    s.text("wl", 830, 395, esc(p.get("worker", "")), size=68, w=340)
    if p.get("note"):
        s.text("nt", 540, 690, esc(p["note"]), size=60, color="ink", font="body")
    t_obj = 0.0
    s.draw("obj", t_obj, 0.5, stagger=0.06)
    s.write("ol", t_obj + 0.25, len(p.get("label", "")), sfx=None)
    tw = 0.1
    s.draw("wb", tw, 0.3, sfx=None)
    s.draw("wi", tw + 0.1, 0.35, sfx=None)
    s.write("wl", tw + 0.2, 4, sfx=None)
    ta = s.at(_a(p, "give"), max(t_obj, tw) + 0.5)
    s.draw("ar", ta, 0.3, sfx="whoosh")
    s.nudge("obj", ta, (260, 365), 1.06)
    if p.get("note"):
        s.write("nt", ta + 0.3, len(p["note"]), sfx=None)


# --------------------------------------------------------------------------- chat (question -> reply draft)
def dd_chat(s: DoodleScene, p: dict) -> None:
    """Customer speech bubble writes in; a blue-pen reply draft is written below."""
    q = p.get("question", "")
    s.icon_svg("cu", "user", 60, 170, 110, color="ink")
    s.text("cl", 115, 282, esc(p.get("from", "고객")), size=56, w=200)
    bub = rough_rect(210, 160, 800, 230, s.rng("bub"))
    tail = rough_line(210, 300, 175, 345, s.rng("tl"), 0.02) + " " + rough_line(175, 345, 214, 355, s.rng("t2"), 0.02)
    s.svg("bub", [bub, tail])
    qlines = q.split("|")
    for i, ql in enumerate(qlines):
        s.text(f"q{i}", 610, 185 + i * 86, esc(ql), size=72, w=780)
    reply = p.get("reply_lines", [])
    s.svg("rb", [rough_rect(150, 470, 860, 330, s.rng("rb"))], color="accent2", width=5)
    s.text("rh", 170, 398, esc(p.get("reply", "답장 초안")), size=56, color="accent2", align="left", w=700)
    for i, rl in enumerate(reply):
        s.text(f"r{i}", 190, 528 + i * 86, esc(rl), size=56, align="left", w=810, color="ink", font="body", weight=700)
    tq = 0.0
    s.draw("cu", tq, 0.35)
    s.write("cl", tq + 0.15, 2, sfx=None)
    s.draw("bub", tq + 0.1, 0.4, stagger=0.2, sfx=None)
    tt = tq + 0.05
    for i, ql in enumerate(qlines):
        tt = s.write(f"q{i}", tt, len(ql), sfx="marker" if i == 0 else None, dur=0.35)
    if p.get("q_mark"):
        mw = _tw(p["q_mark"], 72) + 20
        s.svg("qmk", [rough_line(610 - _tw(qlines[0], 72) / 2, 262, 610 - _tw(qlines[0], 72) / 2 + mw, 260, s.rng("qmk"), 0.003)],
              color="marker", width=26, opacity=.85)
        s.draw("qmk", s.at(_a(p, "q_mark"), tt + 0.3), 0.35, sfx="marker")
    tr = s.at(_a(p, "reply"), max(tt + 0.2, s.dur * 0.6))
    tbox = min(tr, tt + 0.6)
    s.draw("rb", tbox, 0.35, sfx="scribble")
    s.write("rh", tbox + 0.1, 5, sfx=None)
    t2 = tbox + 0.45
    for i, rl in enumerate(reply):
        t2 = s.write(f"r{i}", t2, len(rl), sfx=None) + 0.05


# --------------------------------------------------------------------------- rule (if -> forbidden)
def dd_rule(s: DoodleScene, p: dict) -> None:
    """IF box -> arrow -> THEN box crossed out in red, with a circled rule."""
    s.svg("ib", [rough_rect(70, 230, 400, 270, s.rng("ib"))])
    s.icon_svg("ii", p.get("if_icon", "calendar"), 210, 255, 120, color="accent2")
    s.text("it", 270, 390, esc(p.get("if", "")), size=74, w=400)
    s.svg("ar", arrow_paths(490, 365, 600, 365, s.rng("ar"), bend=0.2))
    s.svg("tb", [rough_rect(615, 230, 400, 270, s.rng("tb"))])
    s.text("tt", 815, 290, esc(p.get("then", "")), size=100, w=400)
    s.svg("x", cross_paths(815, 365, 210, s.rng("x")), color="accent", width=12)
    rule = p.get("stamp", "")
    rw = min(940, _tw(rule, 84) + 120)
    s.text("st", 540, 620, esc(rule), size=84, color="accent", rot=-2)
    s.svg("stc", [rough_ellipse(540, 672, rw / 2, 80, s.rng("stc"))], color="accent", width=7)
    t_if = s.at(_a(p, "if"), 0.0)
    s.draw("ib", t_if, 0.3)
    s.draw("ii", t_if + 0.1, 0.35, sfx=None)
    s.write("it", t_if + 0.2, len(p.get("if", "")), sfx=None)
    tt = s.at(_a(p, "then"), s.dur * 0.35)
    s.draw("ar", tt - 0.2, 0.2, sfx=None)
    s.draw("tb", tt, 0.3, sfx=None)
    s.write("tt", tt + 0.1, 2)
    tx = s.at(_a(p, "stamp"), s.dur * 0.6)
    s.draw("x", tx, 0.28, stagger=0.1, sfx="stamp", ease="power2.out")
    s.write("st", tx + 0.15, len(rule), sfx=None)
    s.draw("stc", tx + 0.35, 0.35, sfx=None)


# --------------------------------------------------------------------------- bars
def dd_bars(s: DoodleScene, p: dict) -> None:
    """Hand-drawn axes + hatched bars that grow; values written on top; optional note."""
    bars = p.get("bars", [])
    t0 = _title(s, p.get("title"), 0.0)
    s.svg("ax", [rough_line(150, 190, 152, 725, s.rng("ay"), 0.004), rough_line(150, 725, 940, 723, s.rng("ax"), 0.004)], width=6)
    hmax = 430
    vmax = max((b.get("value", 1) for b in bars), default=1)
    n = max(1, len(bars))
    bw = 210
    step = 760 / n
    for i, b in enumerate(bars):
        x = 160 + step * i + (step - bw) / 2
        h = hmax * b.get("value", 1) / vmax
        col = "accent" if i == n - 1 else "accent2"
        s.hatch_bar(f"bf{i}", x, 723, bw, h, color=col)
        s.svg(f"bo{i}", [rough_rect(x, 723 - h, bw, h, s.rng("bo", i), 2.5)], color=col, width=5)
        s.text(f"bv{i}", x + bw / 2, 723 - h - 100, esc(b.get("label_value", "")), size=74, color=col, w=320)
        s.text(f"bl{i}", x + bw / 2, 732, esc(b.get("label", "")), size=50, color="ink", w=300, font="body")
    s.draw("ax", max(0.0, t0 - 0.2), 0.35, stagger=0.1)
    tb = _seq(s, p, [f"b{i}" for i in range(len(bars))], 0.25, 0.5)
    for i, tt in enumerate(tb):
        s._js(f'tl.fromTo("{s.sel(f"bf{i}")}",{{scaleY:0}},{{scaleY:1,duration:.5,ease:"power2.out"}},{s.clamp(tt):.3f});')
        s.ev(tt, "rise")
        s.draw(f"bo{i}", 0.05, 0.3, sfx=None)          # empty outlines on the cut, filled on the word
        s.write(f"bl{i}", tt, 3, sfx=None)
        s.pop_in(f"bv{i}", tt + 0.4, "pop" if i == len(bars) - 1 else None, frm=0.5)
    if p.get("delta") and len(bars) >= 2:
        x1 = 160 + step * 0 + (step - bw) / 2 + bw / 2
        x2 = 160 + step * (n - 1) + (step - bw) / 2 + bw / 2
        h1 = hmax * bars[0].get("value", 1) / vmax
        h2 = hmax * bars[-1].get("value", 1) / vmax
        xr = min(1000, x2 + bw / 2 + 40)          # growth arrow + delta to the right of the last bar
        s.svg("da", [rough_line(x1 + bw / 2, 723 - h1, xr - 10, 723 - h1, s.rng("dl"), 0.0)]
              + arrow_paths(xr, 723 - h1, xr, 723 - h2 + 6, s.rng("da"), bend=0.0, head=22), color="accent", width=6)
        s.text("dv", xr + 95, 723 - h1 + 14, esc(p["delta"]), size=60, color="accent", w=190)
        tdl = s.at(_a(p, "delta"), s.dur * 0.6)
        s.draw("da", tdl, 0.35, sfx="scribble")
        s.hero("dv", tdl + 0.2, "pop")
    if p.get("report"):
        tr = s.at(_a(p, "report"), s.dur * 0.7)
        s.text("rp", 540, 116, esc(p["report"]), size=52, color="accent2", font="body")
        s.write("rp", tr, len(p["report"]))


# --------------------------------------------------------------------------- waiting (clock)
def dd_wait(s: DoodleScene, p: dict) -> None:
    """Clock with spinning hands next to three running tasks ('...' dots)."""
    rows = p.get("rows", [])
    cx, cy, r = 285, 420, 190
    s.svg("cl", [rough_ellipse(cx, cy, r, r, s.rng("cl"), turns=1.04)], width=7)
    s.svg("tk", [rough_line(cx + (r - 26) * c, cy + (r - 26) * sn, cx + (r - 6) * c, cy + (r - 6) * sn, s.rng("tk", k), 0.0)
                 for k, (c, sn) in enumerate(((1, 0), (0, 1), (-1, 0), (0, -1)))], width=6)
    s.add(f'<div class="dd-hand" id="{s.id("hm")}" style="left:{cx - 6}px;top:{cy - 150}px;width:12px;height:150px;'
          f'transform-origin:50% 100%;background:{s.c["ink"]};border-radius:6px;opacity:0"></div>')
    s.add(f'<div class="dd-hand" id="{s.id("hh")}" style="left:{cx - 7}px;top:{cy - 100}px;width:14px;height:100px;'
          f'transform-origin:50% 100%;background:{s.c["accent"]};border-radius:7px;opacity:0"></div>')
    for i, rw in enumerate(rows):
        y = 235 + i * 150
        s.svg(f"rb{i}", [rough_rect(560, y, 450, 115, s.rng("rb", i), 2.5)], width=5)
        s.text(f"rl{i}", 590, y + 18, esc(rw), size=60, align="left", w=280)
        s.svg(f"ro{i}", [rough_rect(800, y + 38, 180, 40, s.rng("ro", i), 2)], width=4)
        s.hatch_bar(f"rf{i}", 804, y + 74, 172, 32, color="accent")
        s.add(f'<style>#{s.id(f"rf{i}")}{{transform-origin:0 50%;transform:scaleX(0)}}</style>')
    s.text("wt", 540, 735, esc(p.get("text", "")), size=74)
    tc = s.at(_a(p, "clock"), 0.0)
    s.draw("cl", tc, 0.45)
    s.draw("tk", tc + 0.3, 0.2, sfx=None)
    s.pop_in("hm", tc + 0.05, None, frm=0.2)
    s.pop_in("hh", tc + 0.08, None, frm=0.2)
    t_spin = tc + 0.3
    span = max(0.5, s.dur - t_spin - 0.3)
    s._js(f'tl.fromTo("{s.sel("hm")}",{{rotation:0}},{{rotation:{int(720 * span / 2.5)},duration:{span:.3f},ease:"none",immediateRender:false}},{t_spin:.3f});')
    s._js(f'tl.fromTo("{s.sel("hh")}",{{rotation:0}},{{rotation:{int(90 * span / 2.5)},duration:{span:.3f},ease:"none",immediateRender:false}},{t_spin:.3f});')
    tr = _seq(s, p, [f"r{i}" for i in range(len(rows))], 0.05, 0.3)
    for i, tt in enumerate(tr):
        s.draw(f"rb{i}", tt, 0.25, sfx="scribble" if i == 0 else None)
        s.write(f"rl{i}", tt + 0.1, len(rows[i]), sfx=None)
        s.draw(f"ro{i}", tt + 0.05, 0.2, sfx=None)
        s._js(f'tl.fromTo("{s.sel(f"rf{i}")}",{{scaleX:0}},{{scaleX:{0.55 + 0.15 * i:.2f},duration:{span:.3f},ease:"power1.inOut"}},{s.clamp(tt + 0.2):.3f});')
    s.write("wt", s.at(_a(p, "wait"), s.dur * 0.55), len(p.get("text", "")))


# --------------------------------------------------------------------------- burst (big moment)
def dd_burst(s: DoodleScene, p: dict) -> None:
    """One big handwritten line with burst strokes around it."""
    txt = p.get("text", "")
    s.text("bt", 540, 300, txt, size=150, color=p.get("color", "accent"))
    s.svg("rays", [rough_ellipse(540, 395, min(500, _tw(txt, 150) / 2 + 80), 140, s.rng("ray"))], color="ink", width=7)
    marks = p.get("checks", 0)
    for i in range(marks):
        s.svg(f"c{i}", [check_path(330 + i * 160, 600, 110, s.rng("c", i))], color="accent2", width=11)
    s.hero("bt", 0.0)
    s.draw("rays", 0.35, 0.4, sfx="scribble")
    for i in range(marks):
        s.draw(f"c{i}", 0.25 + 0.12 * i, 0.2, sfx="tick")
    # optional crossed-out items under the headline (e.g. "don't send these yet")
    items = p.get("crossed", [])
    w, gap = 300, 30
    x0 = (1080 - len(items) * w - max(0, len(items) - 1) * gap) / 2
    tb = s.at(_a(p, "cross"), 0.5)
    for i, it in enumerate(items):
        x = x0 + i * (w + gap)
        s.svg(f"xb{i}", [rough_rect(x, 590, w, 150, s.rng("xb", i), 2.5)], width=5)
        s.text(f"xl{i}", x + w / 2, 622, esc(it), size=64, w=w)
        s.svg(f"xx{i}", [rough_line(x + 20, 700, x + w - 20, 625, s.rng("xx", i), 0.02)], color="accent", width=10)
        s.draw(f"xb{i}", 0.05 * i, 0.2, sfx=None)
        s.write(f"xl{i}", 0.1, len(it), sfx=None)
        s.draw(f"xx{i}", tb + 0.12 * i, 0.18, sfx="tick" if i == 0 else None)


# --------------------------------------------------------------------------- list with checks / warnings
def dd_list(s: DoodleScene, p: dict) -> None:
    """Rows written one by one, each ticked (blue check), flagged (red !) or circled."""
    rows = p.get("rows", [])
    t0 = _title(s, p.get("title"), 0.0)
    n = max(1, len(rows))
    gap = min(260, 690 / n)
    top = 160 + (700 - n * gap) / 2
    for i, r in enumerate(rows):
        y = top + i * gap
        s.svg(f"cb{i}", [rough_rect(70, y + 18, 84, 84, s.rng("cb", i), 2.5)], width=6)
        mark = r.get("mark", "check")
        if mark == "warn":
            s.text(f"mk{i}", 116, y - 4, "!", size=110, color="accent", w=80)
        else:
            s.svg(f"mk{i}", [check_path(76, y, 96, s.rng("mk", i))], color="accent" if mark == "pen" else "accent2", width=11)
        if p.get("ghosts"):
            # faint pencil placeholder of every row from the cut: the page reads as a full checklist
            s.add(f'<div class="dd-t" id="{s.id(f"gh{i}")}" style="left:185px;top:{y + 14:.0f}px;width:870px;font-family:var(--dd-body);font-size:68px;'
                  f'font-weight:800;opacity:.14;color:{s.col("ink")}"><span>{re.sub(r"<[^>]+>", "", r.get("label", ""))}</span></div>')
            s.add(f'<svg class="dd-svg" id="{s.id(f"gb{i}")}" viewBox="0 0 1080 {s.board_h}" style="height:{s.board_h}px;opacity:.18" fill="none" '
                  f'stroke="{s.col("ink")}" stroke-width="5"><path d="{rough_rect(70, y + 18, 84, 84, s.rng("cbg", i), 2.5)}"/></svg>')
        s.text(f"rl{i}", 185, y + 14, r.get("label", ""), size=68, align="left", w=870, font="body", weight=800)
        if r.get("note"):
            s.text(f"rn{i}", 186, y + 92, esc(r["note"]), size=66, color="accent2", align="left", w=880, font="body")
        if r.get("circle"):
            cw = _tw(r["label"], 80) + 70
            s.svg(f"rc{i}", [rough_ellipse(190 + cw / 2 - 20, y + 52, cw / 2, 62, s.rng("rc", i))], color="accent", width=6)
    tr = _seq(s, p, [f"r{i}" for i in range(len(rows))], max(0.2, t0), 0.72)
    for i, tt in enumerate(tr):
        r = rows[i]
        s.draw(f"cb{i}", max(0.0, tt - 0.08), 0.2, sfx=None)   # each checkbox arrives with its row (no empty frames)
        if p.get("ghosts"):
            tg = s.clamp(max(0.0, tt - 0.08))
            s._js(f'tl.set("{s.sel(f"gh{i}")}, {s.sel(f"gb{i}")}",{{opacity:0}},{tg:.3f});')
        s.write(f"rl{i}", tt - 0.05, len(re.sub(r"<[^>]+>", "", r.get("label", ""))))
        if r.get("note"):
            s.write(f"rn{i}", s.at(_a(p, f"n{i}"), tt + 0.25), len(r["note"]), sfx=None)
        tm = s.at(_a(p, f"m{i}"), tt + 0.45)
        if r.get("mark", "check") == "warn":
            s.pop_in(f"mk{i}", tm, "stamp", frm=1.8)
        else:
            s.draw(f"mk{i}", tm, 0.22, sfx="tick")
        if r.get("circle"):
            s.draw(f"rc{i}", tm + 0.15, 0.4, sfx=None)


# --------------------------------------------------------------------------- kpi (before -> after)
def dd_kpi(s: DoodleScene, p: dict) -> None:
    """Rows 'label  before -> after' and a big circled delta."""
    rows = p.get("rows", [])
    t0 = _title(s, p.get("title"), 0.0)
    for i, r in enumerate(rows):
        y = 190 + i * 165
        s.text(f"kl{i}", 70, y + 18, esc(r.get("label", "")), size=50, color="ink", align="left", w=210, font="body")
        s.text(f"kb{i}", 290, y, esc(r.get("before", "")), size=74, color="ink_soft", align="left", w=230)
        s.svg(f"ka{i}", arrow_paths(520, y + 50, 640, y + 50, s.rng("ka", i), bend=-0.15, head=24), width=6)
        s.text(f"kv{i}", 660, y, esc(r.get("after", "")), size=80, color="accent2", align="left", w=360)
    delta = p.get("delta", "")
    s.text("dl", 540, 520, esc(delta), size=170, color="accent")
    s.svg("dlc", [rough_ellipse(540, 625, 250, 120, s.rng("dlc"))], color="accent", width=8)
    if p.get("delta_note"):
        s.text("dn", 540, 760, esc(p["delta_note"]), size=60, font="body", color="ink")
    tr = _seq(s, p, [f"k{i}" for i in range(len(rows))], max(0.2, t0), 0.45)
    for i, tt in enumerate(tr):
        s.write(f"kl{i}", 0.05, 3, sfx=None, dur=0.25)      # row labels + "before" values are the skeleton
        s.write(f"kb{i}", 0.1, 4, sfx=None)
        s.draw(f"ka{i}", tt, 0.2, sfx="scribble" if i == 0 else None)
        s.pop_in(f"kv{i}", tt + 0.15, "pop", frm=0.5)
    td = max(0.0, s.at(_a(p, "delta"), s.dur * 0.6) - 0.15)   # land the hero on the stressed word
    s.hero("dl", td)
    s.draw("dlc", td + 0.2, 0.45, sfx="scribble")
    if p.get("delta_note"):
        s.write("dn", td + 0.5, len(p["delta_note"]), sfx=None)


# --------------------------------------------------------------------------- split (A vs B)
def dd_split(s: DoodleScene, p: dict) -> None:
    """Two columns divided by a drawn line: left (AI) vs right (me), items under each."""
    L, R = p.get("left", {}), p.get("right", {})
    s.svg("dv", [rough_line(540, 175, 543, 700 if p.get("verdict") else 850, s.rng("dv"), 0.004)], width=5)
    s.icon_svg("li", L.get("icon", "bot"), 215, 175, 110, color="accent2")
    s.text("lh", 270, 290, esc(L.get("title", "")), size=76, color="accent2", w=440)
    s.avatar_at("ra", 810, 232, 120)
    s.svg("rac", [rough_ellipse(810, 232, 72, 72, s.rng("rac"))], width=5)
    s.text("rh", 810, 290, esc(R.get("title", "")), size=76, color="accent", w=440)
    for side, col, items, x in (("l", "accent2", L.get("items", []), 270), ("r", "accent", R.get("items", []), 810)):
        for i, it in enumerate(items):
            y = 430 + i * 150
            tx = x - 165                       # labels are left-aligned after the tick column
            s.add(f'<div class="dd-t" style="left:{tx:.0f}px;top:{y:.0f}px;width:420px;font-family:var(--dd-hand);font-size:78px;'
                  f'font-weight:700;opacity:.16;color:{s.col("ink")}"><span>{esc(it.get("label", ""))}</span></div>')
            s.text(f"{side}i{i}", tx, y, esc(it.get("label", "")), size=78, w=420, align="left")
            if it.get("mark") == "check":
                s.svg(f"{side}m{i}", [check_path(tx - 70, y + 18, 54, s.rng(side, i))], color=col, width=8)
            if it.get("circle"):
                cw = _tw(it["label"], 78) + 60
                s.svg(f"{side}c{i}", [rough_ellipse(tx + cw / 2 - 25, y + 46, cw / 2, 64, s.rng(side, "c", i))], color=col, width=6)
    s.draw("dv", 0.0, 0.35)
    tl_ = s.at(_a(p, "left"), 0.1)
    s.draw("li", tl_, 0.35)
    s.write("lh", tl_ + 0.15, 2, sfx=None)
    trh = 0.2                      # both column headers are on the board from the start
    s.pop_in("ra", trh, "pop")
    s.draw("rac", trh + 0.1, 0.35, sfx=None)
    s.write("rh", trh + 0.15, 2, sfx=None)
    for side, items in (("l", L.get("items", [])), ("r", R.get("items", []))):
        for i, it in enumerate(items):
            tt = s.at(_a(p, f"{side}{i}"), (tl_ if side == "l" else trh) + 0.4 + 0.4 * i)
            s.write(f"{side}i{i}", tt, len(it.get("label", "")))
            if it.get("mark") == "check":
                s.draw(f"{side}m{i}", tt + 0.35, 0.2, sfx="tick")
            if it.get("circle"):
                s.draw(f"{side}c{i}", tt + 0.4, 0.4, sfx="scribble")
    if p.get("verdict"):
        s.svg("vmk", [rough_line(120, 806, 960, 804, s.rng("vmk"), 0.003)], color="marker", width=40, opacity=.85)
        s.text("vd", 540, 742, p["verdict"], size=60, font="body")
        tv = s.at(_a(p, "verdict"), s.dur * 0.7)
        s.draw("vmk", tv, 0.35, sfx="marker")
        s.hero("vd", tv + 0.05, None)


# --------------------------------------------------------------------------- pick + CTA
def dd_pick(s: DoodleScene, p: dict) -> None:
    """Options in a row, one gets circled, arrow down to the goal and a drawn follow button."""
    opts = p.get("options", [])
    k = int(p.get("pick", 0))
    t0 = _title(s, p.get("title"), 0.0)
    n = max(1, len(opts))
    w, gap = 270, 26
    x0 = (1080 - n * w - (n - 1) * gap) / 2
    for i, o in enumerate(opts):
        x = x0 + i * (w + gap)
        s.svg(f"o{i}", [rough_rect(x, 175, w, 150, s.rng("o", i), 2.5)], width=5)
        s.text(f"ol{i}", x + w / 2, 200, esc(o), size=70, w=w)
    if k < 0:          # "one of these" without naming it: loop around the whole row
        xk, rx = 540, (n * w + (n - 1) * gap) / 2 + 14
    else:
        xk, rx = x0 + k * (w + gap) + w / 2, w / 2 + 30
    s.svg("pc", [rough_ellipse(xk, 250, rx, 110, s.rng("pc"))], color="accent", width=8)
    s.svg("pa", arrow_paths(xk, 370, 540, 470, s.rng("pa"), bend=0.15))
    goal = p.get("goal", "")
    s.svg("gmk", [rough_line(540 - _tw(goal, 84) / 2 - 10, 562, 540 + _tw(goal, 84) / 2 + 10, 560, s.rng("gmk"), 0.003)],
          color="marker", width=36, opacity=.85)
    s.text("gl", 540, 480, esc(goal), size=84, color="ink")
    if p.get("cta"):
        s.svg("cb", [rough_rect(170, 650, 740, 150, s.rng("cb"))], color="accent", width=7)
        s.text("ct", 540, 680, esc(p["cta"]), size=72, color="accent", w=720)
        s.icon_svg("hand", "hand", 760, 730, 110, color="ink")
    for i in range(len(opts)):
        s.draw(f"o{i}", max(0.0, t0 - 0.1) + 0.12 * i, 0.25, sfx="scribble" if i == 0 else None)
        s.write(f"ol{i}", max(0.0, t0) + 0.12 * i, len(opts[i]), sfx=None)
    tp = s.at(_a(p, "pick"), s.dur * 0.35)
    s.draw("pc", tp, 0.4, sfx="scribble")
    for i in range(n):
        if k >= 0 and i != k:
            s.fade_to(f"ol{i}", tp + 0.2, 0.35)
    tg = s.at(_a(p, "goal"), tp + 0.5)
    s.draw("pa", tg - 0.2, 0.25, sfx=None)
    s.write("gl", tg, len(goal))
    s.draw("gmk", tg + 0.2, 0.35, sfx=None)
    if p.get("cta"):
        tc = s.at(_a(p, "cta"), tg + 0.5)
        s.draw("cb", tc, 0.35, sfx="pop")
        s.write("ct", tc + 0.1, len(p["cta"]), sfx=None)
        s.draw("hand", tc + 0.45, 0.35, sfx=None)
        s.nudge("cb", tc + 0.9, (540, 725), 1.05)
        s.ev(tc + 0.9, "click")


# --------------------------------------------------------------------------- keyword (auto fallback)
def dd_keyword(s: DoodleScene, p: dict) -> None:
    """Auto-planner fallback: one circled handwritten keyword + a short line under it."""
    kw = p.get("keyword", "")
    size = 130 if len(kw) <= 6 else max(80, int(130 * 6 / max(1, len(kw))))
    s.text("kw", 540, 280, esc(kw), size=size, color="accent")
    s.svg("kc", [rough_ellipse(540, 280 + size * 0.62, min(480, _tw(kw, size) / 2 + 60), size * 0.75, s.rng("kc"))],
          color="ink", width=6)
    s.text("sub", 540, 600, esc(p.get("sub", "")), size=60)
    s.write("kw", 0.0, len(kw))
    s.draw("kc", 0.3, 0.4, sfx=None)
    s.write("sub", 0.6, len(p.get("sub", "")), sfx=None)


DOODLE_TEMPLATES = {
    "keyword": dd_keyword, "dd_keyword": dd_keyword,
    "dd_stop": dd_stop, "dd_branch": dd_branch, "dd_versus": dd_versus, "dd_note": dd_note,
    "dd_handoff": dd_handoff, "dd_chat": dd_chat, "dd_rule": dd_rule, "dd_bars": dd_bars,
    "dd_wait": dd_wait, "dd_burst": dd_burst, "dd_list": dd_list, "dd_kpi": dd_kpi,
    "dd_split": dd_split, "dd_pick": dd_pick,
}
