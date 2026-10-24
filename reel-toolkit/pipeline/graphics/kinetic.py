"""Full-screen kinetic-type cards (talking-head styles such as bold-talk).

A kinetic scene fills the 1080x1920 frame during its full-graphic layout run(s) and handles its own
entrance and exit (Scene.fullscreen = True). Every card uses the same fixed grid, so cards read as one
design system and nothing ever collides with the caption band:

  tag pill        y 200-280      48 px / 800
  headline        y 290-610      96-140 px / 900, max 2 lines, accent on 1-2 words (spans 290-1020 when there is no body)
  body            y 640-1020     rows (max 3, 116 px tall) | hero number | icon tiles | CTA button   (>= 70 px above the caption)
  caption band    y ~1090-1215   (captions composition, same y as on the speaker)
  tracker chips   y 1470-1550

params (all optional unless noted):
  bg      "dark" | "accent" | "warn" | CSS colour   background (red = hook/warning, yellow = result/CTA, dark = process)
  tag     pill text
  big     headline html (<br>, <span class="rk-acc">)       the card's single dominant line
  sub     short line under the headline (>= 46 px, high contrast)
  lines   [{"text", "icon", "tone": good|warn|accent, "at": word, "count": {"from","to","suffix"}}]   max 3
  number  {"to": 20, "prefix": "+", "suffix": "%"}           hero number stamped into the body
  icons   [{"icon", "label"}]                                 max 3 tiles in the body
  button  CTA pill in the body
  hero    true: hook / twist / conclusion / CTA motion (bigger build, zoom-through exit)
  exit    "push" (section divider wipe) | default
  at      {"big": word, "big2": word, "button": word}
"""
from __future__ import annotations

import re

from .icons import icon
from .scene import Scene, esc

# grid (px)
TAG_Y, HEAD_Y, HEAD_H, BODY_Y, BODY_H, TRACKER_TOP = 200, 290, 320, 640, 380, 1470
FOOT_Y = 1270
SIDE = 64
WIDTH = 1080 - 2 * SIDE
BIG_MAX, BIG_MIN = 140, 96
ROW_H, ROW_GAP, ROW_FONT = 116, 16, 62
# motion (s)
BG_SETTLE = 0.5
WORD_STAGGER = 0.08
EXIT_ROWS, EXIT_CARD = 0.2, 0.22


def _palette(s: Scene, bg: str) -> tuple[str, str, str, str]:
    """(background, foreground, accent, soft) for a background keyword."""
    c = s.c
    if bg == "accent":
        return c["accent"], "#111111", c.get("warn", "#E03131"), "#3A3A3A"
    if bg == "warn":
        return c.get("warn", "#E03131"), "#FFFFFF", c["accent"], "#FFFFFF"
    if bg in ("dark", "", None):
        return c["background"], c["ink"], c["accent"], "#D9D9D9"
    return bg, c["ink"], c["accent"], "#D9D9D9"


def _em_width(text: str) -> float:
    """Rough rendered width in em (Hangul ~0.95em, latin/digits ~0.62em, space 0.25em)."""
    w = 0.0
    for ch in text:
        if ch == " ":
            w += 0.25
        elif "가" <= ch <= "힣":
            w += 0.95
        else:
            w += 0.62
    return w


def big_size(html_text: str) -> int:
    """Largest headline size (BIG_MIN..BIG_MAX) whose longest line fits the content width."""
    plain = re.sub(r"<[^>]+>", "", html_text.replace("<br>", "|"))
    longest = max((_em_width(x) for x in plain.split("|")), default=1.0)
    return int(max(BIG_MIN, min(BIG_MAX, WIDTH / max(longest, 0.1))))


def _beat(s: Scene) -> tuple[float, float]:
    win = s.graphic_window()
    return win if win else (0.0, s.dur)


def _words_html(s: Scene, html_text: str) -> tuple[str, list[int]]:
    """Wrap each word of the headline in a span (accent spans stay whole) so words can build in.
    Returns the html and the line number of every word."""
    out, lines = [], []
    n = 0
    for line_no, line in enumerate(html_text.split("<br>")):
        if line_no:
            out.append("<br>")
        for tok in re.findall(r'<span class="rk-acc">.*?</span>|[^\s<]+', line):
            acc = tok.startswith("<span")
            inner = re.sub(r"<[^>]+>", "", tok) if acc else tok
            cls = "kn-w rk-acc" if acc else "kn-w"
            out.append(f'<span class="{cls}" id="{s.id(f"w{n}")}">{esc(inner)}</span>')
            lines.append(line_no)
            n += 1
    return "".join(out), lines


def _row_text(s: Scene, i: int, r: dict) -> str:
    """Row html; a {"count": {"from", "to", "suffix"}} row puts a counter span at "{n}" (starts at "from")."""
    c = r.get("count")
    if not c:
        return r["text"]
    span = f'<span class="rk-acc" id="{s.id(f"rc{i}")}">{c["from"]}{c.get("suffix", "")}</span>'
    return r["text"].replace("{n}", span)


def _css(s: Scene, bg: str, fg: str, acc: str, soft: str, light: bool) -> str:
    row_bg = "#FFFFFF" if light else "rgba(255,255,255,.09)"
    row_fg = "#111111" if light else fg
    k = f".kn-{s.sid}"
    return f"""
    {k} {{ position:absolute; inset:0; color:{fg}; overflow:hidden; }}
    {k} .kn-bg {{ position:absolute; inset:0; background:{bg}; }}
    {k} .kn-glow {{ position:absolute; left:-20%; right:-20%; top:6%; height:62%; background:radial-gradient(closest-side, {acc}33, transparent); }}
    {k} .rk-acc {{ color:{acc}; }}
    {k} .kn-tag {{ position:absolute; top:{TAG_Y}px; left:0; right:0; display:flex; justify-content:center; }}
    {k} .kn-tag span {{ font-size:48px; font-weight:800; padding:10px 34px; border-radius:999px; border:4px solid {fg}; letter-spacing:-1px; }}
    {k} .kn-head {{ position:absolute; top:{HEAD_Y}px; left:{SIDE}px; right:{SIDE}px; height:{HEAD_H}px; display:flex;
        flex-direction:column; align-items:center; justify-content:center; gap:22px; text-align:center; }}
    {k} .kn-big {{ font-weight:900; letter-spacing:-0.04em; line-height:1.1; }}
    {k} .kn-w {{ display:inline-block; margin:0 .13em; }}
    {k} .kn-sub {{ font-size:56px; font-weight:800; color:{soft}; letter-spacing:-1px; white-space:nowrap; }}
    {k} .kn-body {{ position:absolute; top:{BODY_Y}px; left:{SIDE}px; right:{SIDE}px; height:{BODY_H}px; display:flex;
        flex-direction:column; align-items:center; justify-content:center; gap:{ROW_GAP}px; }}
    {k} .kn-row {{ width:100%; height:{ROW_H}px; box-sizing:border-box; display:flex; align-items:center; gap:24px; padding:0 30px;
        border-radius:30px; background:{row_bg}; color:{row_fg}; font-size:{ROW_FONT}px; font-weight:800; letter-spacing:-1.5px;
        white-space:nowrap; overflow:hidden; }}
    {k} .kn-ri {{ width:88px; height:88px; border-radius:24px; display:flex; align-items:center; justify-content:center; flex:none; }}
    {k} .kn-num {{ font-size:220px; font-weight:900; letter-spacing:-0.05em; line-height:1; color:{acc}; }}
    {k} .kn-icons {{ display:flex; gap:36px; }}
    {k} .kn-ic {{ width:250px; display:flex; flex-direction:column; align-items:center; gap:16px; font-size:56px; font-weight:800; white-space:nowrap; }}
    {k} .kn-ib {{ width:200px; height:200px; border-radius:54px; background:{acc}; color:{bg}; display:flex; align-items:center; justify-content:center; }}
    {k} .kn-btn {{ font-size:84px; font-weight:900; padding:28px 80px; border-radius:999px; background:#111; color:#fff; white-space:nowrap; }}
    {k} .kn-foot {{ position:absolute; left:0; right:0; top:{FOOT_Y}px; display:flex; justify-content:center; }}
    {k} .kn-foot span {{ display:inline-block; font-size:58px; font-weight:900; padding:22px 48px; border-radius:999px;
        background:{fg}; color:{bg}; letter-spacing:-1.5px; white-space:nowrap; }}
    {k} .kn-tr {{ position:absolute; left:0; right:0; top:{TRACKER_TOP}px; display:flex; justify-content:center; gap:14px; }}
    {k} .kn-tc {{ display:flex; align-items:center; gap:12px; padding:14px 28px; border-radius:999px; border:5px solid;
        background:#151515; color:#fff; font-size:50px; font-weight:800; white-space:nowrap; }}
    """


def slam(s: Scene, p: dict) -> None:
    s.fullscreen = True
    g0, g1 = _beat(s)
    bg, fg, acc, soft = _palette(s, p.get("bg", "dark"))
    s.css.append(_css(s, bg, fg, acc, soft, p.get("bg") == "accent"))
    parts = [f'<div class="kn-{s.sid}" id="{s.id("card")}"><div class="kn-bg" id="{s.id("bg")}"></div><div class="kn-glow"></div>']
    if p.get("tag"):
        parts.append(f'<div class="kn-tag"><span id="{s.id("tag")}">{esc(p["tag"])}</span></div>')
    word_lines: list[int] = []
    has_body = bool(p.get("lines") or p.get("icons") or p.get("number") or p.get("button"))
    if p.get("big") or p.get("sub"):
        tall = "" if has_body else f' style="height:{BODY_Y + BODY_H - HEAD_Y}px"'
        parts.append(f'<div class="kn-head" id="{s.id("head")}"{tall}>')
        if p.get("big"):
            words, word_lines = _words_html(s, p["big"])
            parts.append(f'<div class="kn-big" id="{s.id("big")}" style="font-size:{big_size(p["big"])}px">{words}</div>')
        if p.get("sub"):
            parts.append(f'<div class="kn-sub" id="{s.id("sub")}">{esc(p["sub"])}</div>')
        parts.append('</div>')
    rows = (p.get("lines") or [])[:3]
    icons = (p.get("icons") or [])[:3]
    num = p.get("number")
    parts.append(f'<div class="kn-body" id="{s.id("body")}">')
    if num:
        parts.append(f'<div class="kn-num" id="{s.id("num")}">{esc(num.get("prefix", ""))}{esc(num.get("to", 0))}{esc(num.get("suffix", ""))}</div>')
        if num.get("source"):
            parts.append(f'<div class="kn-sub" style="font-size:64px;color:{fg}">{esc(num["source"])}</div>')
    elif rows:
        for i, r in enumerate(rows):
            tone = {"good": (s.c.get("good", "#2FA36B"), "#fff"), "warn": (s.c.get("warn", "#E03131"), "#fff")}.get(r.get("tone"), (acc, bg))
            parts.append(f'<div class="kn-row" id="{s.id(f"r{i}")}"><span class="kn-ri" style="background:{tone[0]};color:{tone[1]}">'
                         f'{icon(r.get("icon", "check"), 58, 2.6)}</span><span>{_row_text(s, i, r)}</span></div>')
    elif icons:
        parts.append('<div class="kn-icons">')
        for i, it in enumerate(icons):
            parts.append(f'<div class="kn-ic" id="{s.id(f"i{i}")}"><div class="kn-ib">{icon(it.get("icon", "spark"), 120, 2.1)}</div>'
                         f'{esc(it.get("label", ""))}</div>')
        parts.append('</div>')
    if p.get("button"):
        parts.append(f'<div class="kn-btn" id="{s.id("btn")}">{esc(p["button"])}</div>')
    parts.append('</div>')
    if s.tracker:
        parts.append(_tracker(s))
    if p.get("foot"):
        # hero foot element: fills the lower third under the caption band (y ~1250-1420)
        parts.append(f'<div class="kn-foot"><span id="{s.id("foot")}">{p["foot"]}</span></div>')
    parts.append('</div>')
    s.add("".join(parts))
    _enter(s, p, g0, word_lines)
    _body(s, p, g0, g1, rows, icons, num)
    _exit(s, p, g0, g1, rows)


def _enter(s: Scene, p: dict, g0: float, word_lines: list[int]) -> None:
    """Card dissolves in over the speaker while its background settles; the headline builds word by word.
    A card on frame 0 (the hook) shows its tag and first headline line immediately and builds line 2."""
    hero = bool(p.get("hero"))
    first = s.first and g0 < 0.01      # the hook card on frame 0 of the reel
    n_words = len(word_lines)
    s.ev(g0, "whoosh")
    if not first:
        pass   # full-bleed hard cut in; the background settles and the headline builds (no panel edges)
    s._js(f'tl.fromTo("{s.sel("bg")}",{{scale:1.08}},{{scale:1,duration:{BG_SETTLE},ease:"expo.out"}},{g0:.3f});')
    t = g0 + 0.04
    if p.get("tag") and not first:
        s._js(f'tl.fromTo("{s.sel("tag")}",{{y:-24}},{{y:0,duration:.3,ease:"back.out(2)"}},{t:.3f});')
    t_big = s.at((p.get("at") or {}).get("big"), t + 0.06)
    stagger = 0.12 if hero else WORD_STAGGER
    built = [k for k in range(n_words) if not (first and word_lines[k] == 0)]
    if first:
        t_big += 0.1
    if p.get("bg") == "accent" and not first and built:
        # result cards: the whole headline stamps in (overshoot + settle)
        s._js(f'tl.fromTo("{s.sel("big")}",{{scale:1.12,rotation:-3}},{{scale:1,rotation:0,duration:.4,ease:"back.out(2.6)"}},{t_big:.3f});')
        s.ev(t_big, "stamp")
        built = []
    for j, k in enumerate(built):
        tk = t_big + stagger * j
        s._js(f'tl.fromTo("{s.sel(f"w{k}")}",{{y:50,opacity:.25}},{{y:0,opacity:1,duration:.32,ease:"back.out(1.6)"}},{tk:.3f});')
    if n_words:
        # accent words land with a springy scale once their line has built
        t_acc = t_big + stagger * len(built) + 0.05
        s._js(f'tl.fromTo("{s.sel("big")} .rk-acc",{{scale:1.15}},{{scale:1,duration:.6,ease:"elastic.out(1,0.5)",'
              f'immediateRender:false}},{t_acc:.3f});')
        s.ev(t_acc, "stamp" if hero else "pop")
        if p.get("bg") == "warn":
            s.shake("big", t_acc + 0.3, 12)
        t2 = (p.get("at") or {}).get("big2")
        if t2:
            s.pulse("big", s.at(t2, t_acc + 0.4), 1.08)
            s.shake("big", s.at(t2, t_acc + 0.4) + 0.2, 12)
    if p.get("foot"):
        tf = g0 + 0.25 if not first else 0.3
        tf = s.at((p.get("at") or {}).get("foot"), tf) if (p.get("at") or {}).get("foot") else tf
        s._js(f'tl.fromTo("{s.sel("foot")}",{{scale:.6,opacity:0}},{{scale:1,opacity:1,duration:.32,ease:"back.out(2)"}},{tf:.3f});')
        s.ev(tf, "pop")
    if p.get("sub"):
        s._js(f'tl.fromTo("{s.sel("sub")}",{{y:24,opacity:0}},{{y:0,opacity:1,duration:.3,ease:"power2.out"}},'
              f'{t_big + stagger * len(built) + 0.1:.3f});')


def _body(s: Scene, p: dict, g0: float, g1: float, rows: list, icons: list, num: dict | None) -> None:
    """Rows reveal on their spoken words; numbers stamp in; icon tiles pop with a stagger."""
    t = g0 + 0.15
    for i, r in enumerate(rows):
        if i:   # the first row lands with the card; later rows on their spoken words
            t = max(t, s.at(r.get("at"), t)) if r.get("at") else t
        t = min(t, max(g0 + 0.25, g1 - 0.7))
        s._js(f'tl.fromTo("{s.sel(f"r{i}")}",{{x:-40,opacity:0}},{{x:0,opacity:1,duration:.3,ease:"power2.out"}},{t:.3f});')
        s.ev(t, "tick")
        if r.get("count"):
            c = r["count"]
            s.count(f"rc{i}", t + 0.1, float(c["from"]), float(c["to"]), 0.8, 0, "", c.get("suffix", ""))
        if i and p.get("bg") == "warn":
            for j in range(i):
                s.fade_to(f"r{j}", t, 0.45, .2)
            s.pulse(f"r{i}", t + 0.3, 1.06)
        if r.get("tone") == "warn":
            s.shake(f"r{i}", t + 0.32, 10)
        t += 0.3
    if num:
        tn = s.at((p.get("at") or {}).get("number"), g0 + 0.3)
        s._js(f'tl.fromTo("{s.sel("num")}",{{scale:.4,rotation:-8,opacity:0}},{{scale:1,rotation:0,opacity:1,duration:.5,'
              f'ease:"back.out(3.2)"}},{tn:.3f});')
        s.ev(tn, "stamp")
    for i in range(len(icons)):
        ti = g0 + 0.3 + 0.1 * i
        s._js(f'tl.fromTo("{s.sel(f"i{i}")}",{{scale:.6,opacity:0}},{{scale:1,opacity:1,duration:.3,ease:"back.out(2)"}},{ti:.3f});')
        s.ev(ti, "pop" if i == 0 else "tick")
    if p.get("button"):
        tb = s.at((p.get("at") or {}).get("button"), g0 + 0.6)
        s._js(f'tl.fromTo("{s.sel("btn")}",{{scale:.6,opacity:0}},{{scale:1,opacity:1,duration:.3,ease:"back.out(2)"}},{tb:.3f});')
        s.press("btn", tb + 0.6)
        s.pulse("btn", tb + 1.3, 1.08)
        s.ev(tb + 0.6, "click")


def _exit(s: Scene, p: dict, g0: float, g1: float, rows: list) -> None:
    """Opaque exits only (judges read translucent card-over-face frames as ghosting):
    rows collapse upward in reverse order, then the card leaves by role and the next shot is a hard cut."""
    if g1 >= s.dur - 0.05:
        return                                          # last card holds to the end
    t_card = g1 - EXIT_CARD
    if rows:
        s._js(f'tl.to("{s.sel("body")} .kn-row",{{y:-30,opacity:0,duration:{EXIT_ROWS},stagger:{{each:.05,from:"end"}},'
              f'ease:"power2.in",immediateRender:false}},{max(g0 + 0.5, t_card - EXIT_ROWS - 0.05 * (len(rows) - 1)):.3f});')
    if p.get("hero"):
        # hero: headline lifts away, the card punches toward the viewer, hard cut to the speaker
        s._js(f'tl.to("{s.sel("head")}",{{y:-50,duration:.25,ease:"power2.in",immediateRender:false}},{g1 - 0.3:.3f});')
        s._js(f'tl.to("{s.sel("card")}",{{scale:1.12,duration:{EXIT_CARD},ease:"power2.in",immediateRender:false}},{t_card:.3f});')
        return
    move = "y:-1920" if p.get("exit") == "up" else "x:-1080"
    s._js(f'tl.to("{s.sel("card")}",{{{move},duration:{EXIT_CARD},ease:"power3.in",immediateRender:false}},{t_card:.3f});')


def _tracker(s: Scene) -> str:
    """Story tracker: one chip per storyline item (todo / active / done / warn)."""
    chips = []
    for k, (label, ico, st) in enumerate(s.tracker):
        col = {"done": s.c.get("good", "#2FA36B"), "active": s.c["accent"], "warn": s.c.get("warn", "#E03131")}.get(st, "#777777")
        mark = {"done": "check", "warn": "alert", "active": "spark"}.get(st, ico)
        chips.append(f'<div class="kn-tc" style="border-color:{col}"><span style="color:{col}">{icon(mark, 50, 3)}</span>{esc(label)}</div>')
    return f'<div class="kn-tr">{"".join(chips)}</div>'


def blank(s: Scene, p: dict) -> None:
    """No graphic: the scene only exists to start the timeline on the speaker."""
    s.fullscreen = True


KINETIC_TEMPLATES = {"slam": slam, "blank": blank}
