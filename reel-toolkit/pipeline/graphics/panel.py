"""Floating panel cards over a continuous speaker (bold-talk round 2).

The scene's segments use the "split" layout: the speaker video sits in the lower box
(layout.seam_y, head at ~y 1480) and this template draws an opaque rounded panel in the upper
frame plus a dark backdrop behind it. Captions stay at one y (between panel and head) and are never
crossed by any panel motion. Consecutive panel scenes swap content in place (rotateX flip, max 70 deg);
otherwise the panel leaves by role over the full-frame speaker (collapse to its tag / fold up).

Grid (px, 1080x1920): panel x 60, y 220, 960 x 780, radius 44, inner padding 48
  accent bar  top 10 px (setup = yellow, result = green, warn = red)
  tag row     +44, 64 px tall (tag pill left, story dots right)
  headline    +140..+330, 84 px / 900, max 2 lines
  body        +370..+732: up to 3 rows (104 px) | hero number (200 px) + source line | 3 tiles

params:
  role    "setup" | "result" | "warn"
  tag, big (html, <br>, <span class="rk-acc">), lines [{text, icon, tone, at, count}], number {to, prefix,
  suffix, source}, icons [{icon, label}], at {big, hero, number}
"""
from __future__ import annotations

import re

from .icons import icon
from .kinetic import _em_width, _row_text, _words_html
from .scene import Scene, esc

PX, PY, PW, PH, RADIUS, PAD = 60, 220, 960, 780, 44, 48
BACK_H = 1000
TAG_DY, HEAD_DY, HEAD_H, BODY_DY, BODY_H = 44, 136, 190, 362, 372
ROW_H, ROW_GAP, ROW_FONT = 112, 16, 62
HEAD_MAX, HEAD_MIN = 84, 64
ROLE_COLOR = {"setup": "accent", "result": "good", "warn": "warn"}


def head_size(html_text: str) -> int:
    plain = re.sub(r"<[^>]+>", "", html_text.replace("<br>", "|"))
    longest = max((_em_width(x) for x in plain.split("|")), default=1.0)
    return int(max(HEAD_MIN, min(HEAD_MAX, (PW - 2 * PAD) / max(longest * 1.04, 0.1))))


def _runs(s: Scene) -> list[tuple[float, float]]:
    """(start, end) of every split-layout run inside the scene, scene-relative."""
    out, ev = [], s.layout_events
    for k, (t, lay) in enumerate(ev):
        if lay != "split":
            continue
        end = ev[k + 1][0] if k + 1 < len(ev) else s.dur
        if out and abs(out[-1][1] - t) < 1e-3:
            out[-1] = (out[-1][0], end)
        else:
            out.append((t, end))
    return out


def _css(s: Scene, acc: str) -> str:
    c = s.c
    k = f".pn-{s.sid}"
    return f"""
    {k} {{ position:absolute; inset:0; opacity:0; }}
    {k} .pn-back {{ position:absolute; left:0; top:0; width:1080px; height:{BACK_H}px; background:{c['background']}; }}
    {k} .pn-back i {{ position:absolute; left:-160px; top:-100px; width:1400px; height:1400px;
        background:radial-gradient(closest-side, rgba(255,225,77,.10), transparent); }}
    {k} .pn-panel {{ position:absolute; left:{PX}px; top:{PY}px; width:{PW}px; height:{PH}px; border-radius:{RADIUS}px;
        background:#161616; border:2px solid rgba(255,255,255,.08); box-shadow:0 24px 64px rgba(0,0,0,.65);
        overflow:hidden; color:{c['ink']}; transform-origin:50% 50%; }}
    {k} .pn-in {{ position:absolute; inset:0; }}
    {k} .pn-bar {{ position:absolute; left:0; right:0; top:0; height:10px; background:{acc}; }}
    {k} .pn-tagrow {{ position:absolute; left:{PAD}px; right:{PAD}px; top:{TAG_DY}px; height:72px; display:flex;
        align-items:center; justify-content:space-between; }}
    {k} .pn-tag {{ height:72px; display:flex; align-items:center; padding:0 30px; border-radius:999px; background:{acc};
        color:#0E0E0E; font-size:46px; font-weight:800; letter-spacing:-1px; white-space:nowrap; }}
    {k} .pn-dots {{ display:flex; gap:14px; }}
    {k} .pn-dot {{ width:52px; height:52px; border-radius:50%; border:5px solid #555; box-sizing:border-box; display:flex;
        align-items:center; justify-content:center; }}
    {k} .pn-head {{ position:absolute; left:{PAD}px; right:{PAD}px; top:{HEAD_DY}px; height:{HEAD_H}px; display:flex;
        align-items:center; justify-content:center; text-align:center; }}
    {k} .pn-big {{ font-weight:900; letter-spacing:-0.035em; line-height:1.1; }}
    {k} .kn-w {{ display:inline-block; margin:0 .12em; }}
    {k} .rk-acc {{ color:{c['accent']}; display:inline-block; }}
    {k} .pn-body {{ position:absolute; left:{PAD}px; right:{PAD}px; top:{BODY_DY}px; height:{BODY_H}px; display:flex;
        flex-direction:column; align-items:center; justify-content:center; gap:{ROW_GAP}px; }}
    {k} .pn-row {{ width:100%; height:{ROW_H}px; box-sizing:border-box; border-radius:22px; background:#262626; display:flex;
        align-items:center; padding:0 22px; overflow:hidden; }}
    {k} .pn-rc {{ display:flex; align-items:center; gap:22px; font-size:{ROW_FONT}px; font-weight:800; letter-spacing:-1.5px;
        white-space:nowrap; opacity:0; }}
    {k} .pn-ri {{ width:64px; height:64px; border-radius:18px; display:flex; align-items:center; justify-content:center; flex:none; }}
    {k} .pn-src {{ font-size:52px; font-weight:800; color:#D9D9D9; letter-spacing:-1px; white-space:nowrap; }}
    {k} .pn-num {{ font-size:200px; font-weight:900; letter-spacing:-0.05em; line-height:1; color:{c['accent']}; opacity:0; }}
    {k} .pn-tiles {{ display:flex; gap:24px; }}
    {k} .pn-tile {{ width:272px; height:300px; border-radius:30px; background:#262626; display:flex; flex-direction:column;
        align-items:center; justify-content:center; gap:22px; font-size:46px; font-weight:800; white-space:nowrap; }}
    {k} .pn-tc {{ display:flex; flex-direction:column; align-items:center; gap:22px; opacity:0; }}
    {k} .pn-ib {{ width:150px; height:150px; border-radius:40px; background:{acc}; color:#0E0E0E; display:flex;
        align-items:center; justify-content:center; }}
    """


def _dots(s: Scene) -> str:
    if not s.tracker:
        return ""
    c = s.c
    out = []
    for _label, _ico, st in s.tracker:
        if st == "done":
            out.append(f'<span class="pn-dot" style="background:{c["good"]};border-color:{c["good"]};color:#fff">{icon("check", 30, 3.4)}</span>')
        elif st == "active":
            out.append(f'<span class="pn-dot" style="border-color:{c["accent"]};color:{c["accent"]}">{icon("spark", 26, 3)}</span>')
        elif st == "warn":
            out.append(f'<span class="pn-dot" style="background:{c["warn"]};border-color:{c["warn"]};color:#fff">{icon("alert", 28, 3)}</span>')
        else:
            out.append('<span class="pn-dot"></span>')
    return f'<div class="pn-dots">{"".join(out)}</div>'


def _markup(s: Scene, p: dict, acc: str) -> tuple[str, list[int], list, list, dict | None]:
    parts = [f'<div class="pn-{s.sid}" id="{s.id("wrap")}"><div class="pn-back" id="{s.id("back")}"><i></i></div>',
             f'<div class="pn-panel" id="{s.id("card")}"><div class="pn-bar"></div><div class="pn-in" id="{s.id("in")}">',
             f'<div class="pn-tagrow"><span class="pn-tag">{esc(p.get("tag", ""))}</span>{_dots(s)}</div>']
    word_lines: list[int] = []
    if p.get("big"):
        words, word_lines = _words_html(s, p["big"])
        parts.append(f'<div class="pn-head"><div class="pn-big" id="{s.id("big")}" style="font-size:{head_size(p["big"])}px">'
                     f'{words}</div></div>')
    rows = (p.get("lines") or [])[:3]
    tiles = (p.get("icons") or [])[:3]
    num = p.get("number")
    parts.append(f'<div class="pn-body" id="{s.id("body")}">')
    if num:
        if num.get("source"):
            parts.append(f'<div class="pn-src">{esc(num["source"])}</div>')
        parts.append(f'<div class="pn-num" id="{s.id("num")}">{esc(num.get("prefix", ""))}{esc(num.get("to", 0))}'
                     f'{esc(num.get("suffix", ""))}</div>')
    elif rows:
        for i, r in enumerate(rows):
            tone = {"good": (s.c["good"], "#fff"), "warn": (s.c["warn"], "#fff")}.get(r.get("tone"), (acc, "#0E0E0E"))
            parts.append(f'<div class="pn-row" id="{s.id(f"r{i}")}"><div class="pn-rc" id="{s.id(f"rc_{i}")}">'
                         f'<span class="pn-ri" id="{s.id(f"ri{i}")}" style="background:{tone[0]};color:{tone[1]}">'
                         f'{icon(r.get("icon", "check"), 42, 2.6)}</span><span>{_row_text(s, i, r)}</span></div></div>')
    elif tiles:
        parts.append('<div class="pn-tiles">')
        for i, it in enumerate(tiles):
            parts.append(f'<div class="pn-tile"><div class="pn-tc" id="{s.id(f"t{i}")}"><div class="pn-ib">'
                         f'{icon(it.get("icon", "spark"), 96, 2.2)}</div>{esc(it.get("label", ""))}</div></div>')
        parts.append('</div>')
    parts.append('</div></div></div></div>')
    s.add("".join(parts))
    return "", word_lines, rows, tiles, num


def panel(s: Scene, p: dict) -> None:
    s.fullscreen = True
    role = p.get("role", "setup")
    acc = s.c[ROLE_COLOR.get(role, "accent")]
    s.css.append(_css(s, acc))
    _, word_lines, rows, tiles, num = _markup(s, p, acc)
    runs = _runs(s) or [(0.0, s.dur)]
    for k, (t0, t1) in enumerate(runs):
        _enter(s, p, k, t0, word_lines)
        _exit(s, p, k == len(runs) - 1, t0, t1, rows)
    g0, g1 = runs[0][0], runs[-1][1]
    _content(s, p, g0, runs[0][1], rows, tiles, num, role)
    if len(runs) > 1:
        for t0, _ in runs[1:]:          # re-entry after a talking-head beat: restore revealed rows
            s._js(f'tl.set("{s.sel("body")} .pn-rc",{{x:0,opacity:1}},{t0:.3f});')
            s._js(f'tl.set("{s.sel("body")} .pn-row",{{x:0,opacity:1}},{t0:.3f});')


def _enter(s: Scene, p: dict, k: int, t0: float, word_lines: list[int]) -> None:
    card = s.sel("card")
    s._js(f'tl.set("{s.sel("wrap")}",{{opacity:1}},{t0:.3f});')
    s._js(f'tl.set("{s.sel("back")}",{{opacity:1}},{t0:.3f});')
    role = p.get("role", "setup")
    if k == 0 and s.swap_in and t0 < 0.01:
        if _swap_kind(s.prev_params, p) == "content":
            # same panel, new content: tag / headline / body rise in with a stagger (panel never moves)
            for j, part in enumerate(("pn-tagrow", "pn-head", "pn-body")):
                s._js(f'tl.fromTo("{s.sel("in")} .{part}",{{y:34,opacity:0}},{{y:0,opacity:1,duration:.26,'
                      f'ease:"expo.out"}},{t0 + 0.05 * j:.3f});')
            s.ev(t0, "tick")
        else:
            # flip: the previous panel folded to 70 deg; this one unfolds from the other side
            s._js(f'tl.fromTo("{card}",{{rotationX:70,transformOrigin:"50% 100%",scale:1,y:0,transformPerspective:1600}},'
                  f'{{rotationX:0,duration:.3,ease:"back.out(1.6)"}},{t0:.3f});')
            s.ev(t0, "whoosh")
    elif not (s.first and t0 < 0.01):
        if role == "result":
            # results drop in from above and land with an overshoot
            s._js(f'tl.fromTo("{card}",{{y:-90,scale:1,rotationX:0,transformPerspective:1600}},'
                  f'{{y:0,duration:.4,ease:"back.out(2.2)"}},{t0:.3f});')
        elif role == "warn":
            # warnings slam (1.1 -> 1) and shake once
            s._js(f'tl.fromTo("{card}",{{scale:1.1,y:0,rotationX:0,transformPerspective:1600}},'
                  f'{{scale:1,duration:.24,ease:"power4.in"}},{t0:.3f});')
            s.shake("card", t0 + 0.26, 10)
        else:
            s._js(f'tl.fromTo("{card}",{{scale:.92,y:24,rotationX:0,transformPerspective:1600}},'
                  f'{{scale:1,y:0,duration:.34,ease:"back.out(1.4)"}},{t0:.3f});')
        s.ev(t0, "whoosh")
    if k:
        return
    # secondary: headline words rise into place (always fully visible: position only)
    n = len(word_lines)
    t_big = t0 + 0.04
    for j in range(n):
        s._js(f'tl.fromTo("{s.sel(f"w{j}")}",{{y:30}},{{y:0,duration:.3,ease:"expo.out"}},{t_big + 0.06 * j:.3f});')
    if n and not p.get("number"):
        # hero: the accent word stamps (1.4 -> 1, -6 deg, back.out(3)) on its word or after the build
        t_h = t_big + 0.06 * n + 0.1
        at = (p.get("at") or {}).get("hero")
        if at:
            t_h = max(t_h, s.at(at, t_h))
        s._js(f'tl.fromTo("{s.sel("big")} .rk-acc",{{scale:1.4,rotation:-6}},{{scale:1,rotation:0,duration:.42,'
              f'ease:"back.out(3)",immediateRender:false}},{t_h:.3f});')
        s.ev(t_h, "stamp")
        if p.get("role") == "warn":
            s.shake("big", t_h + 0.4, 10)


def _content(s: Scene, p: dict, g0: float, r_end: float, rows: list, tiles: list, num: dict | None, role: str) -> None:
    t = g0 + 0.18
    limit = max(g0 + 0.3, r_end - 0.5)
    for i, r in enumerate(rows):
        if i or r.get("at"):
            t = max(t, s.at(r.get("at"), t)) if r.get("at") else t
        t = min(t, limit)
        s._js(f'tl.fromTo("{s.sel(f"rc_{i}")}",{{x:28,opacity:0}},{{x:0,opacity:1,duration:.26,ease:"power3.out"}},{t:.3f});')
        s._js(f'tl.fromTo("{s.sel(f"ri{i}")}",{{scale:.6}},{{scale:1,duration:.25,ease:"back.out(2.2)"}},{t:.3f});')
        s._js(f'tl.to("{s.sel(f"r{i}")}",{{backgroundColor:"#3A3414",duration:.08,ease:"power1.out"}},{t:.3f});')
        s._js(f'tl.to("{s.sel(f"r{i}")}",{{backgroundColor:"#262626",duration:.2,ease:"power1.inOut"}},{t + 0.12:.3f});')
        s.ev(t, "tick")
        if r.get("count"):
            c = r["count"]
            s.count(f"rc{i}", t + 0.1, float(c["from"]), float(c["to"]), 0.8, 0, "", c.get("suffix", ""))
        if i and role == "warn":
            for j in range(i):
                s.fade_to(f"rc_{j}", t, 0.4, .2)
            s.pulse(f"r{i}", t + 0.26, 1.04)
        if r.get("tone") == "warn":
            s.shake(f"r{i}", t + 0.3, 10)
        t += 0.12
    if num:
        tn = s.at((p.get("at") or {}).get("number"), g0 + 0.3)
        s._js(f'tl.fromTo("{s.sel("num")}",{{scale:1.4,rotation:-6,opacity:0}},{{scale:1,rotation:0,opacity:1,duration:.42,'
              f'ease:"back.out(3)"}},{tn:.3f});')
        s.ev(tn, "stamp")
        tp = (p.get("at") or {}).get("pulse")
        if tp:
            s.pulse("num", max(tn + 0.5, s.at(tp, tn + 0.5)), 1.12)
            s.ev(max(tn + 0.5, s.at(tp, tn + 0.5)), "ding")
    for i in range(len(tiles)):
        ti = g0 + 0.2 + 0.1 * i
        s._js(f'tl.fromTo("{s.sel(f"t{i}")}",{{scale:.6,opacity:0}},{{scale:1,opacity:1,duration:.3,ease:"back.out(2)"}},{ti:.3f});')
        s.ev(ti, "pop" if i == 0 else "tick")


def _swap_kind(a: dict, b: dict) -> str:
    """Consecutive result panels update their content in place; any other pair flips."""
    return "content" if a.get("role") == b.get("role") == "result" else "flip"


EXIT_DUR = 0.26


def _exit(s: Scene, p: dict, last_run: bool, t0: float, t1: float, rows: list) -> None:
    """Exits finish ON the cut, over the dark backdrop (never over the full-frame speaker)."""
    card, wrap = s.sel("card"), s.sel("wrap")
    at_end = t1 >= s.dur - 0.05
    if at_end and last_run:
        if s.swap_out:
            if _swap_kind(p, s.next_params) == "content":
                s._js(f'tl.to("{s.sel("in")}",{{y:-34,opacity:0,duration:.14,ease:"power2.in",immediateRender:false}},'
                      f'{max(t0 + 0.3, s.dur - 0.14):.3f});')
            else:
                # fold to 70 deg (never past), the next panel scene unfolds
                s._js(f'tl.to("{card}",{{rotationX:-70,transformOrigin:"50% 0%",transformPerspective:1600,duration:.2,ease:"power2.in",'
                      f'immediateRender:false}},{max(t0 + 0.3, s.dur - 0.2):.3f});')
            return
        if s.last:
            return
    te = max(t0 + 0.4, t1 - EXIT_DUR)
    role = p.get("role", "setup")
    if role == "result":
        # fold up around the top edge
        s._js(f'tl.to("{card}",{{rotationX:-80,transformOrigin:"50% 0%",transformPerspective:1600,duration:{EXIT_DUR},'
              f'ease:"power2.in",immediateRender:false}},{te:.3f});')
    elif role == "warn":
        # collapse toward the tag pill
        s._js(f'tl.to("{card}",{{scale:.3,transformOrigin:"50% 10%",duration:{EXIT_DUR},ease:"power3.in",'
              f'immediateRender:false}},{te:.3f});')
    else:
        # push up and out of the top edge (away from the caption band)
        s._js(f'tl.to("{card}",{{y:-1040,duration:{EXIT_DUR},ease:"power3.in",immediateRender:false}},{te:.3f});')
    s._js(f'tl.set("{wrap}",{{opacity:0}},{t1:.3f});')
    s.ev(te, "whoosh")


PANEL_TEMPLATES = {"panel": panel}
