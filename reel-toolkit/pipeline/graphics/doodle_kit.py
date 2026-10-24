"""Hand-drawn ("doodle") scene kit: rough SVG primitives with stroke draw-on, handwritten
text write-on and an eraser exit. Used when a style sets motion.language = "doodle".

Board coordinates are CSS px of the 1080-wide frame; the board covers y 0..board_h
(the paper area above the face photo). All times are seconds relative to the scene.
Draw-on uses pathLength=1 + stroke-dashoffset (a free alternative to GSAP DrawSVG).
"""
from __future__ import annotations

import hashlib
import math
import re

import numpy as np

from .icons import _P as ICON_PATHS
from .scene import Scene, esc

PEN_W = 6.0
DRAW_OFF = 1.05          # dash offset that hides a stroke completely (no round-cap dot)


def _rng(*key) -> np.random.Generator:
    h = hashlib.sha1("|".join(map(str, key)).encode()).hexdigest()[:8]
    return np.random.default_rng(int(h, 16))


def _f(v: float) -> str:
    return f"{v:.1f}"


# ------------------------------------------------------------------ rough geometry
def rough_line(x1, y1, x2, y2, rng, wob: float = 0.012) -> str:
    """Slightly bowed line (quadratic), as a single path command string."""
    dx, dy = x2 - x1, y2 - y1
    ln = math.hypot(dx, dy) or 1.0
    off = rng.uniform(-1, 1) * ln * wob + rng.uniform(-1.2, 1.2)
    cx, cy = (x1 + x2) / 2 - dy / ln * off, (y1 + y2) / 2 + dx / ln * off
    return f"M{_f(x1)} {_f(y1)} Q{_f(cx)} {_f(cy)} {_f(x2)} {_f(y2)}"


def rough_rect(x, y, w, h, rng, j: float = 3.0) -> str:
    """One continuous stroke around a box, overshooting the start corner like a pen."""
    pts = [(x + rng.uniform(-j, j), y + rng.uniform(-j, j)), (x + w + rng.uniform(-j, j), y + rng.uniform(-j, j)),
           (x + w + rng.uniform(-j, j), y + h + rng.uniform(-j, j)), (x + rng.uniform(-j, j), y + h + rng.uniform(-j, j))]
    pts.append((pts[0][0] + min(26, w * 0.12), pts[0][1] + rng.uniform(-j, j) - 2))
    d = f"M{_f(pts[0][0])} {_f(pts[0][1])}"
    for (ax, ay), (bx, by) in zip(pts, pts[1:]):
        ln = math.hypot(bx - ax, by - ay) or 1
        off = rng.uniform(-1, 1) * ln * 0.01
        cx, cy = (ax + bx) / 2 - (by - ay) / ln * off, (ay + by) / 2 + (bx - ax) / ln * off
        d += f" Q{_f(cx)} {_f(cy)} {_f(bx)} {_f(by)}"
    return d


def rough_ellipse(cx, cy, rx, ry, rng, turns: float = 1.12, start_deg: float = -110) -> str:
    """Hand-drawn loop around something: a bit more than one turn, wobbly radius."""
    n = 46
    a0 = math.radians(start_deg + rng.uniform(-15, 15))
    ph1, ph2 = rng.uniform(0, 6.28, 2)
    pts = []
    for k in range(n + 1):
        a = a0 + 2 * math.pi * turns * k / n
        r = 1 + 0.035 * math.sin(2 * a + ph1) + 0.02 * math.sin(3 * a + ph2) + 0.05 * k / n
        pts.append((cx + rx * r * math.cos(a), cy + ry * r * math.sin(a)))
    return "M" + " L".join(f"{_f(px)} {_f(py)}" for px, py in pts)


def arrow_paths(x1, y1, x2, y2, rng, bend: float = 0.15, head: float = 30) -> list[str]:
    """Shaft (curved) + two head strokes."""
    dx, dy = x2 - x1, y2 - y1
    ln = math.hypot(dx, dy) or 1.0
    off = ln * bend
    cx, cy = (x1 + x2) / 2 - dy / ln * off, (y1 + y2) / 2 + dx / ln * off
    shaft = f"M{_f(x1)} {_f(y1)} Q{_f(cx)} {_f(cy)} {_f(x2)} {_f(y2)}"
    ang = math.atan2(y2 - cy, x2 - cx)
    heads = []
    for s in (-1, 1):
        a = ang + math.pi + s * math.radians(28 + rng.uniform(-4, 4))
        heads.append(f"M{_f(x2)} {_f(y2)} L{_f(x2 + head * math.cos(a))} {_f(y2 + head * math.sin(a))}")
    return [shaft] + heads


def wave_line(x, y, w, rng, amp: float = 5.0) -> str:
    n = max(8, int(w / 24))
    ph = rng.uniform(0, 6.28)
    return "M" + " L".join(f"{_f(x + w * k / n)} {_f(y + amp * math.sin(k * 1.3 + ph) + rng.uniform(-1, 1))}"
                           for k in range(n + 1))


def check_path(x, y, s, rng) -> str:
    return (f"M{_f(x)} {_f(y + s * 0.52)} Q{_f(x + s * 0.2)} {_f(y + s * 0.7)} {_f(x + s * 0.36)} {_f(y + s * 0.95)}"
            f" Q{_f(x + s * 0.6)} {_f(y + s * 0.35 + rng.uniform(-3, 3))} {_f(x + s * 1.05)} {_f(y)}")


def cross_paths(cx, cy, s, rng) -> list[str]:
    h = s / 2
    return [rough_line(cx - h, cy - h, cx + h, cy + h, rng, 0.04), rough_line(cx + h, cy - h, cx - h, cy + h, rng, 0.04)]


def stroke_icon(ico: str) -> str:
    """Icon paths (24-unit) tagged for draw-on."""
    return re.sub(r"<(path|rect|circle)", lambda m: f'<{m.group(1)} class="dd-s" pathLength="1"',
                  ICON_PATHS.get(ico, ICON_PATHS["spark"]))


# ------------------------------------------------------------------ scene
class DoodleScene(Scene):
    """Scene variant: a transparent paper 'board' with drawn elements instead of UI cards."""

    def __init__(self, *a, board_h: int = 900, cfg: dict | None = None, **kw):
        super().__init__(*a, **kw)
        self.board_h = board_h
        self.cfg = cfg or {}
        self.exit_style = "lift"
        self._n = 0
        self.kick_h: str | None = None
        self._texts: set[str] = set()

    # ---------------------------------------------------------- colours
    def col(self, name: str | None) -> str:
        if not name:
            return self.c["ink"]
        return self.c.get(name, name)

    def rng(self, *key):
        return _rng(self.sid, *key)

    # ---------------------------------------------------------- markup
    def svg(self, name: str, paths: list[str], color: str | None = None, width: float = PEN_W,
            extra: str = "", opacity: float = 1.0, cap: str = "round") -> None:
        body = "".join(f'<path class="dd-s" pathLength="1" d="{d}"/>' for d in paths)
        blend = "mix-blend-mode:multiply;" if color == "marker" else ""   # highlighter sits "under" the ink
        self.add(f'<svg class="dd-svg" id="{self.id(name)}" viewBox="0 0 1080 {self.board_h}" '
                 f'style="height:{self.board_h}px;opacity:{opacity};{blend}" fill="none" stroke="{self.col(color)}" '
                 f'stroke-width="{width}" stroke-linecap="{cap}" stroke-linejoin="round">{body}{extra}</svg>')

    def icon_svg(self, name: str, ico: str, x: float, y: float, size: float, color: str | None = None) -> None:
        """Line icon (24-unit paths) drawn on like pen strokes."""
        body = stroke_icon(ico)
        k = size / 24
        self.add(f'<svg class="dd-svg" id="{self.id(name)}" viewBox="0 0 1080 {self.board_h}" style="height:{self.board_h}px" '
                 f'fill="none" stroke="{self.col(color)}" stroke-width="1.9" stroke-linecap="round" '
                 f'stroke-linejoin="round"><g transform="translate({_f(x)} {_f(y)}) scale({k:.3f})">{body}</g></svg>')

    def text(self, name: str, x: float, y: float, txt: str, size: int = 64, color: str | None = None,
             font: str = "hand", w: float | None = None, align: str = "center", weight: int | None = None,
             rot: float = 0.0) -> None:
        """Absolutely placed text; x is the centre for align=center, the left edge otherwise."""
        w = w or 940
        if font == "hand":
            size = max(size, self.cfg.get("min_hand_px", 60))
        else:
            size = max(size, self.cfg.get("min_body_px", 0))
        left = x - w / 2 if align == "center" else (x - w if align == "right" else x)
        fam = "var(--dd-hand)" if font == "hand" else "var(--dd-body)"
        wt = weight or (700 if font == "hand" else 800)
        rot_css = f"rotate:{rot}deg;" if rot else ""
        if font == "hand" and self.cfg.get("hand_tracking") is not None:
            rot_css += f"letter-spacing:{self.cfg['hand_tracking']}em;"
        self._texts.add(name)
        self.add(f'<div class="dd-t" id="{self.id(name)}" style="left:{_f(left)}px;top:{_f(y)}px;width:{_f(w)}px;'
                 f'text-align:{align};font-family:{fam};font-size:{size}px;font-weight:{wt};color:{self.col(color)};{rot_css}">'
                 f'<span class="dd-w">{txt}</span></div>')

    def avatar_at(self, name: str, cx: float, cy: float, size: int) -> None:
        self.add(f'<img class="dd-av" id="{self.id(name)}" src="assets/avatar.jpg" alt="" '
                 f'style="left:{_f(cx - size / 2)}px;top:{_f(cy - size / 2)}px;width:{size}px;height:{size}px">')

    def hatch_bar(self, name: str, x: float, y_bottom: float, w: float, h: float, color: str | None = None) -> None:
        col = self.col(color)
        self.add(f'<div class="dd-bar" id="{self.id(name)}" style="left:{_f(x)}px;top:{_f(y_bottom - h)}px;width:{_f(w)}px;'
                 f'height:{_f(h)}px;background:repeating-linear-gradient(-45deg,{col} 0 7px,transparent 7px 19px);"></div>')

    # ---------------------------------------------------------- motion
    def clamp(self, t: float) -> float:
        return max(0.0, min(self.dur - 0.15, t))

    def draw(self, name: str, t: float, dur: float = 0.45, stagger: float = 0.0, sfx: str | None = "scribble",
             ease: str = "power1.inOut") -> float:
        t = self.clamp(t)
        if t < self.OPEN_WINDOW and not self.first:
            stagger = 0.0            # skeleton strokes appear together on the cut (no orphan parts)
        if t < self.OPEN_WINDOW and not self.first:
            # skeleton is on the board on the very first frame of the scene (no blank flash)
            self._js(f'tl.set("{self.sel(name)} .dd-s",{{strokeDashoffset:0}},0);')
            self._skeleton_rise(name)
            if sfx:
                self.ev(0.0, sfx)
            return 0.0
        t, dur = self._fit_end(*self._opening(t, dur))
        st = f",stagger:{stagger}" if stagger else ""
        self._js(f'tl.fromTo("{self.sel(name)} .dd-s",{{strokeDashoffset:{DRAW_OFF}}},'
                 f'{{strokeDashoffset:0,duration:{dur:.3f},ease:"{ease}"{st}}},{t:.3f});')
        if sfx:
            self.ev(t, sfx)
        return t + dur

    def show(self, name: str) -> None:
        """Element fully visible from frame 0 (hook thumbnail)."""
        self._js(f'tl.set("{self.sel(name)} .dd-s",{{strokeDashoffset:0}},0);')
        self._js(f'tl.set("{self.sel(name)}",{{opacity:1}},0);')
        self._js(f'tl.set("{self.sel(name)} > .dd-w",{{clipPath:"inset(0% 0% 0% 0%)"}},0);')

    def write(self, name: str, t: float, chars: int = 6, sfx: str | None = "marker", dur: float | None = None) -> float:
        """Handwriting reveal: clip opens left -> right at roughly pen speed."""
        t = self.clamp(t)
        dur = dur or min(0.6, max(0.25, 0.05 * chars))
        if t < self.OPEN_WINDOW and not self.first:
            self._js(f'tl.set("{self.sel(name)}",{{opacity:1}},0);')
            self._js(f'tl.set("{self.sel(name)} > .dd-w",{{clipPath:"inset(0% 0% 0% 0%)"}},0);')
            self._skeleton_rise(name)
            return 0.0
        t, dur = self._fit_end(*self._opening(t, dur))
        if self.cfg.get("text_reveal", "rise") == "clip":
            # pen-speed clip reveal (can show half-formed Hangul syllables mid-way)
            self._js(f'tl.set("{self.sel(name)}",{{opacity:1}},{t:.3f});')
            self._js(f'tl.fromTo("{self.sel(name)} > .dd-w",{{clipPath:"inset(0% 100% 0% 0%)"}},'
                     f'{{clipPath:"inset(0% 0% 0% 0%)",duration:{dur:.3f},ease:"power1.inOut"}},{t:.3f});')
        else:
            # whole line appears with a short rise: syllables are never shown half-written
            self._js(f'tl.set("{self.sel(name)} > .dd-w",{{clipPath:"inset(0% 0% 0% 0%)"}},{t:.3f});')
            if self.cfg.get("solid_text"):
                # secondary motion: opaque on its first frame (no ghost), only position/scale settle
                dur = 0.32
                self._js(f'tl.fromTo("{self.sel(name)}",{{opacity:0}},{{opacity:1,duration:.1,ease:"none",immediateRender:false}},{t:.3f});')
                self._js(f'tl.fromTo("{self.sel(name)}",{{y:46,scale:.9}},{{y:0,scale:1,duration:{dur:.3f},'
                         f'ease:"back.out(1.7)",immediateRender:false}},{t:.3f});')
            else:
                dur = min(dur, 0.3)
                self._js(f'tl.fromTo("{self.sel(name)}",{{opacity:0,y:14}},{{opacity:1,y:0,duration:{dur:.3f},ease:"power2.out"}},{t:.3f});')
        if sfx:
            self.ev(t, sfx)
        return t + dur

    def _skeleton_rise(self, name: str) -> None:
        """Skeleton parts are opaque from frame 0 but settle in a staggered rise (entrance choreography)."""
        if not self.cfg.get("solid_text"):
            return
        k = getattr(self, "_sk", 0)
        self._sk = k + 1
        t = min(0.05 * k, 0.3)
        self._js(f'tl.fromTo("{self.sel(name)}",{{y:44}},{{y:0,duration:.34,ease:"back.out(1.6)"}},{t:.3f});')

    OPEN_WINDOW = 0.3     # elements due this early are the scene's skeleton: drawn right on the cut
    OPEN_DUR = 0.04

    EXIT_GUARD = 0.32     # every draw/write must be finished this long before the scene ends

    def _fit_end(self, t: float, dur: float) -> tuple[float, float]:
        """Never cut (or exit) on a half-drawn element: squeeze/shift it to end before the exit."""
        limit = self.dur - (0.0 if self.last else self.EXIT_GUARD)
        if t + dur <= limit:
            return t, dur
        dur = max(0.12, limit - t)
        return max(0.0, min(t, limit - dur)), dur

    def _opening(self, t: float, dur: float) -> tuple[float, float]:
        """No blank page after a cut: everything due in the first OPEN_WINDOW s is drawn in OPEN_DUR."""
        if self.first or t >= self.OPEN_WINDOW:
            return t, dur
        return t * 0.3, min(dur, self.OPEN_DUR)

    def hero(self, name: str, t: float, sfx: str | None = "stamp") -> float:
        """Hero entrance: small -> overshoot -> settle (motion hierarchy above the write-ons)."""
        t = self.clamp(t)
        if name in self._texts:
            self._js(f'tl.set("{self.sel(name)} > .dd-w",{{clipPath:"inset(0% 0% 0% 0%)"}},{t:.3f});')
        if self.cfg.get("solid_text"):
            # hero: opaque from its first frame, 0.45 -> 1.14 -> .97 -> 1 with a slight counter-rotation
            self._js(f'tl.set("{self.sel(name)}",{{opacity:1}},{t:.3f});')
            self._js(f'tl.fromTo("{self.sel(name)}",{{scale:.45,rotation:-6}},{{keyframes:[{{scale:1.14,rotation:1,duration:.167,ease:"power3.out"}},'
                     f'{{scale:.97,rotation:0,duration:.133,ease:"sine.inOut"}},{{scale:1,duration:.133,ease:"sine.inOut"}}],'
                     f'immediateRender:false}},{t:.3f});')
            if sfx:
                self.ev(t, sfx)
            return t + 0.43
        self._js(f'tl.fromTo("{self.sel(name)}",{{opacity:0,scale:.3}},{{opacity:1,keyframes:[{{scale:1.14,duration:.22,ease:"power3.out"}},'
                 f'{{scale:1,duration:.3,ease:"back.out(2)"}}]}},{t:.3f});')
        if sfx:
            self.ev(t, sfx)
        return t + 0.52

    def pop_in(self, name: str, t: float, sfx: str | None = "pop", frm: float = 0.4) -> float:
        t = self.clamp(t)
        if name in self._texts:
            self._js(f'tl.set("{self.sel(name)} > .dd-w",{{clipPath:"inset(0% 0% 0% 0%)"}},{t:.3f});')
        if self.cfg.get("solid_text"):
            self._js(f'tl.set("{self.sel(name)}",{{opacity:1}},{t:.3f});')
            self._js(f'tl.fromTo("{self.sel(name)}",{{scale:{max(frm, .6)}}},{{scale:1,duration:.3,ease:"back.out(2)",'
                     f'immediateRender:false}},{t:.3f});')
        else:
            self._js(f'tl.fromTo("{self.sel(name)}",{{opacity:0,scale:{frm}}},{{opacity:1,scale:1,duration:.38,'
                     f'ease:"back.out(2.4)"}},{t:.3f});')
        if sfx:
            self.ev(t, sfx)
        return t + 0.38

    def wiggle(self, name: str, t: float, deg: float = 4, origin: tuple[float, float] | None = None) -> None:
        """Short rotate shake; `origin` (board px) is needed for full-board SVG layers."""
        t = self.clamp(t)
        org = f',transformOrigin:"{origin[0]:.0f}px {origin[1]:.0f}px"' if origin else ""
        for k, r in enumerate((deg, -deg, deg * .5, 0)):
            self._js(f'tl.to("{self.sel(name)}",{{rotation:{r}{org},duration:.07,ease:"sine.inOut"}},{t + .07 * k:.3f});')

    def nudge(self, name: str, t: float, origin: tuple[float, float], scale: float = 1.06) -> None:
        """Scale pulse around a board point (pulse() would scale around the layer centre)."""
        t = self.clamp(t)
        org = f'transformOrigin:"{origin[0]:.0f}px {origin[1]:.0f}px"'
        self._js(f'tl.to("{self.sel(name)}",{{scale:{scale},{org},duration:.14,ease:"power2.out"}},{t:.3f});')
        self._js(f'tl.to("{self.sel(name)}",{{scale:1,{org},duration:.3,ease:"power2.inOut"}},{t + .14:.3f});')

    # ---------------------------------------------------------- layout / kicker / exit
    def kicker_markup(self) -> str:
        if not self.kicker:
            return ""
        k = self.kicker
        plain = re.sub(r"<[^>]+>", "", k.get("text", "").replace("<br>", "|"))
        longest = max(len(x) for x in plain.split("|"))
        size = 150 if longest <= 8 else max(96, int(150 * 8 / longest))
        lines = k.get("text", "").split("<br>")
        y0 = 1150
        out = [f'<div class="dd-kick" id="{self.id("kick")}">']
        for i, ln in enumerate(lines):
            out.append(f'<div class="dd-kt" id="{self.id("kick")}-t{i}" style="top:{y0 + i * size * 1.08:.0f}px;font-size:{size}px"><span class="dd-w">{ln}</span></div>')
        y_ul = y0 + len(lines) * size * 1.08 + 6
        ul = wave_line(300, 10, 480, self.rng("kul"), 4)
        out.append(f'<svg class="dd-kul" id="{self.id("kick")}-u" viewBox="0 0 1080 30" style="top:{y_ul:.0f}px" fill="none" '
                   f'stroke="{self.col("marker")}" stroke-width="16" stroke-linecap="round"><path class="dd-s" pathLength="1" d="{ul}"/></svg>')
        if k.get("sub"):
            out.append(f'<div class="dd-ks" id="{self.id("kick")}-s" style="top:{y_ul + 50:.0f}px">{esc(k["sub"])}</div>')
        icons = k.get("icons") or ([k["icon"]] if k.get("icon") else [])
        if k.get("cards"):
            out.append(self._cards_markup(k["cards"], y_ul + (130 if k.get("sub") else 80)))
        elif icons:
            ico_y = y_ul + (110 if k.get("sub") else 70)
            sc = 14 if len(icons) == 1 else 9
            step = 24 * sc + 60
            x0 = 540 - (len(icons) * 24 * sc + (len(icons) - 1) * 60) / 2
            groups = "".join(f'<g transform="translate({x0 + i * step:.0f} 20) scale({sc})" stroke-width="{1.6 if sc == 14 else 2.0}">'
                             f'{stroke_icon(ic)}</g>' for i, ic in enumerate(icons))
            out.append(f'<svg class="dd-kico" id="{self.id("kick")}-i" viewBox="0 0 1080 380" style="top:{ico_y:.0f}px" fill="none" '
                       f'stroke="{self.col(k.get("icon_color", "accent2"))}" stroke-linecap="round" stroke-linejoin="round">{groups}</svg>')
        out.append(self._tracker_markup(y_ul + 200))
        out.append("</div>")
        self._kick_lines = len(lines)
        return "".join(out)

    def _cards_markup(self, cards: list, y: float) -> str:
        """Row of small paper cards (the real outputs) under the kicker: title line + content line."""
        n = len(cards)
        gap = 24
        w = min(440 if n > 1 else 620, (1080 - 2 * 64 - (n - 1) * gap) / n)
        x0 = (1080 - n * w - (n - 1) * gap) / 2
        h = 250
        out = [f'<div class="dd-cards" id="{self.id("kick")}-c" style="top:{y:.0f}px">']
        for i, c in enumerate(cards):
            x = x0 + i * (w + gap)
            rot = (-1.6, 1.2, -0.8, 1.5)[i % 4]
            col = self.col(c.get("color", "accent2"))
            box = rough_rect(6, 6, w - 12, h - 12, _rng(self.sid, "card", i), 2.5)
            mark = ""
            if c.get("mark") == "check":
                mark = f'<path class="dd-m" d="{check_path(w - 78, 14, 58, _rng(self.sid, "cm", i))}" stroke="{self.col("accent2")}" stroke-width="8"/>'
            elif c.get("mark") == "q":
                mark = ""
            lines = "".join(f'<div class="dd-cl">{ln}</div>' for ln in c.get("lines", []))
            out.append(f'<div class="dd-card" id="{self.id("kick")}-c{i}" style="left:{x:.0f}px;width:{w:.0f}px;height:{h}px;rotate:{rot}deg">'
                       f'<svg viewBox="0 0 {w:.0f} {h}" fill="{self.c.get("card", "#fff")}" stroke="{self.col("ink")}" stroke-width="4.5" '
                       f'stroke-linecap="round" stroke-linejoin="round"><path d="{box}"/>{mark}</svg>'
                       f'<div class="dd-ct" style="color:{col}">{c.get("title", "")}</div>{lines}</div>')
        out.append("</div>")
        return "".join(out)

    TRACK_MARK = {"done": ("accent2", "check"), "active": ("accent", "spark"), "warn": ("accent", "alert")}

    def _tracker_markup(self, y: float) -> str:
        """Hand-drawn status chips (one per tracked task) under the kicker."""
        if not self.tracker:
            return ""
        n = len(self.tracker)
        w, gap = 330, 12
        x0 = (1080 - n * w - (n - 1) * gap) / 2
        out = []
        for k, (label, ico, st) in enumerate(self.tracker):
            x = x0 + k * (w + gap)
            colname, mark = self.TRACK_MARK.get(st, ("ink_soft", ico))
            col = self.col(colname)
            box = rough_rect(x, 8, w, 112, _rng(self.sid, "trk", k))
            ib = stroke_icon(mark)
            out.append(f'<div class="dd-trk" id="{self.id("kick")}-k{k}" style="top:{y:.0f}px">'
                       f'<svg viewBox="0 0 1080 130" fill="none" stroke-linecap="round" stroke-linejoin="round">'
                       f'<path class="dd-s" pathLength="1" d="{box}" stroke="{self.col("ink")}" stroke-width="5"/>'
                       f'<g transform="translate({x + 24:.0f} 34) scale(2.6)" stroke="{col}" stroke-width="2.2">{ib}</g></svg>'
                       f'<span style="left:{x + 92:.0f}px;width:{w - 100}px;color:{col}">{esc(label)}</span></div>')
        return "".join(out)

    def _kicker_in(self, t: float) -> list[str]:
        kick = self.sel("kick")
        out = [f'tl.set("{kick}",{{opacity:1}},{t:.3f});']
        n = getattr(self, "_kick_lines", 1)
        for i in range(n):
            # hero motion: the kicker pops in whole (scale overshoot + settle), never half-written
            ti = t + .1 * i
            out.append(f'tl.set("{kick}-t{i} > .dd-w",{{clipPath:"inset(0% 0% 0% 0%)"}},{ti:.3f});')
            if self.cfg.get("solid_text"):
                out.append(f'tl.fromTo("{kick}-t{i}",{{opacity:1,scale:.45,rotation:-4}},{{opacity:1,keyframes:[{{scale:1.12,rotation:1,duration:.167,ease:"power3.out"}},'
                           f'{{scale:.97,rotation:0,duration:.133,ease:"sine.inOut"}},{{scale:1,duration:.133,ease:"sine.inOut"}}]}},{ti:.3f});')
            else:
                out.append(f'tl.fromTo("{kick}-t{i}",{{opacity:1,scale:.7}},{{opacity:1,keyframes:[{{scale:1.07,duration:.2,ease:"power2.out"}},'
                           f'{{scale:1,duration:.25,ease:"power1.inOut"}}]}},{ti:.3f});')
        tu = t + .1 * n + .2
        out.append(f'tl.fromTo("{kick}-u .dd-s",{{strokeDashoffset:{DRAW_OFF}}},{{strokeDashoffset:0,duration:.35,ease:"power1.inOut"}},{tu:.3f});')
        if self.cfg.get("solid_text"):
            out.append(f'tl.fromTo("{kick}-s",{{opacity:0,y:46,scale:.9}},{{opacity:1,y:0,scale:1,duration:.32,ease:"back.out(1.7)"}},{tu:.3f});')
        else:
            out.append(f'tl.fromTo("{kick}-s",{{opacity:0,y:20}},{{opacity:1,y:0,duration:.3,ease:"expo.out"}},{tu + .1:.3f});')
        for k in range(len(self.kicker.get("cards") or [])):
            tc = min(tu + .1 + .12 * k, max(0.0, self.dur - 0.6))
            out.append(f'tl.fromTo("{kick}-c{k}",{{opacity:0,y:60,scale:.85,rotation:-4}},{{opacity:1,y:0,scale:1,rotation:0,duration:.34,ease:"back.out(1.7)"}},{tc:.3f});')
            out.append(f'tl.fromTo("{kick}-c{k} .dd-m",{{strokeDashoffset:{DRAW_OFF}}},{{strokeDashoffset:0,duration:.2,ease:"power1.inOut"}},{tc + .2:.3f});')
        if self.kicker.get("icon") or self.kicker.get("icons"):
            t_ico = max(0.0, min(tu, self.dur - 0.62))
            d_ico = max(0.15, min(0.5, self.dur - 0.32 - t_ico - 0.1))
            out.append(f'tl.fromTo("{kick}-i .dd-s",{{strokeDashoffset:{DRAW_OFF}}},{{strokeDashoffset:0,duration:{d_ico:.2f},ease:"power1.inOut",stagger:.02}},{t_ico:.3f});')
            if self.kicker.get("ring"):
                for k in range(3):
                    tr = tu + 0.7 + 0.9 * k
                    if tr < self.dur - 0.3:
                        out.append(f'tl.fromTo("{kick}-i",{{rotation:0}},{{keyframes:[{{rotation:9,duration:.07}},{{rotation:-9,duration:.07}},'
                                   f'{{rotation:6,duration:.07}},{{rotation:0,duration:.07}}],transformOrigin:"540px 40px",immediateRender:false}},{tr:.3f});')
        for k in range(len(self.tracker or [])):
            tk = t + .02 + .06 * k
            out.append(f'tl.fromTo("{kick}-k{k} .dd-s",{{strokeDashoffset:{DRAW_OFF}}},{{strokeDashoffset:0,duration:.35,ease:"power1.inOut"}},{tk:.3f});')
            out.append(f'tl.fromTo("{kick}-k{k} span",{{opacity:0,x:-14}},{{opacity:1,x:0,duration:.3,ease:"expo.out"}},{tk + .15:.3f});')
        self.ev(t, "pop")
        return out

    def stage_js(self) -> list[str]:
        out = []
        if not self.first:
            if self.cfg.get("solid_text"):
                out.append(f'tl.fromTo("{self.sel("card")}",{{scale:.985,transformOrigin:"50% 40%"}},'
                           f'{{scale:1,duration:.14,ease:"power2.out"}},0);')
            else:
                out.append(f'tl.fromTo("{self.sel("card")}",{{opacity:.45,scale:.96,transformOrigin:"50% 40%"}},'
                           f'{{opacity:1,scale:1,duration:.26,ease:"back.out(1.7)"}},0);')
        prev = None
        self.kicker_markup()  # sets _kick_lines
        kick = self.sel("kick")
        for t, lay in self.layout_events:
            if self.kicker and lay == "graphic" and prev != "graphic":
                t = t + float(self.kicker.get("delay", 0))
                if self.kicker.get("at"):
                    t = max(t, self.at(self.kicker["at"], t))
                out += self._kicker_in(t)
            elif self.kicker and lay != "graphic" and prev == "graphic":
                out.append(f'tl.set("{kick}",{{opacity:0}},{t:.3f});')
            prev = lay
        if self.layout_events and not self.last and self.dur >= self.cfg.get("exit_min_scene_s", 2.0):
            out += self.exit_js()       # very short beats hard-cut (an exit would eat the payoff)
        return out

    def exit_js(self) -> list[str]:
        """Exit that ends exactly on the scene cut: lift (fade + rise, default), erase, flip or slide."""
        t0 = self.dur - 0.3
        targets = f'{self.sel("card")}, {self.sel("kick")}' if self.kicker else self.sel("card")
        if self.exit_style == "lift":
            # board items sweep up and out in reverse order (last drawn leaves first), kicker drops away
            t0 = self.dur - 0.3
            self.ev(t0, "paper")
            # in-frame exits, ending exactly on the cut; the move rotates per scene (up / left / shrink)
            t0 = self.dur - 0.28
            if self.cfg.get("solid_text"):
                # quick directional exit (the passing styles' push/drop/zoom), ending on the cut
                t0 = self.dur - 0.24
                k = int(re.sub(r"\D", "", self.sid) or 0) % 3
                move = ("x:-130", "y:-110", "scale:.82")[k]
                return [f'tl.to("{targets}",{{{move},transformOrigin:"50% 40%",duration:.24,ease:"power2.in"}},{t0:.3f});',
                        f'tl.to("{targets}",{{opacity:0,duration:.1,ease:"power1.in"}},{self.dur - 0.1:.3f});']
            k = int(re.sub(r"\D", "", self.sid) or 0) % 3
            move = ("y:-28", "x:-60", "scale:.92")[k]
            out = [f'tl.to("{targets}",{{opacity:0,{move},transformOrigin:"50% 40%",duration:.28,ease:"power1.in"}},{t0:.3f});']
            return out
        if self.exit_style == "sheet":
            # act break: an opaque paper sheet rises over the board (complete at every sampled frame)
            t0 = self.dur - 0.2
            self.ev(t0, "paper")
            return [f'tl.set("{self.sel("sheet")}",{{opacity:1}},{t0:.3f});',
                    f'tl.fromTo("{self.sel("sheet")}",{{y:1960}},{{y:0,duration:.2,ease:"power2.in"}},{t0:.3f});']
        if self.exit_style == "slide":
            out = [f'tl.to("{targets}",{{y:-260,rotation:-3,duration:.28,ease:"power2.in"}},{t0:.3f});',
                   f'tl.to("{targets}",{{clipPath:"inset(0% 0% 100% 0%)",duration:.28,ease:"power2.in"}},{t0:.3f});']
            self.ev(t0, "paper")
            return out
        if self.exit_style == "flip":
            out = [f'tl.to("{targets}",{{scaleY:0,rotation:-2,transformOrigin:"50% 0%",duration:.28,ease:"power2.in"}},{t0:.3f});']
            self.ev(t0, "paper")
            return out
        out = [f'tl.fromTo("{targets}",{{clipPath:"inset(0% 0% 0% 0%)"}},{{clipPath:"inset(0% 0% 0% 100%)",duration:.3,ease:"power1.in"}},{t0:.3f});',
               f'tl.set("{self.sel("eraser")}",{{opacity:1,x:-60,rotation:-14}},{t0:.3f});',
               f'tl.to("{self.sel("eraser")}",{{x:1100,rotation:-6,duration:.3,ease:"power1.in"}},{t0:.3f});',
               f'tl.set("{self.sel("eraser")}",{{opacity:0}},{self.dur - 0.001:.3f});']
        self.ev(t0, "erase")
        return out

    def build(self, shared_css: str) -> str:
        sid = self.sid
        kick = self.kicker_markup()
        js = "\n    ".join(self._baseline(self.stage_js() + self.js))
        eraser = (f'<div class="dd-eraser" id="{self.id("eraser")}"><i></i></div>' if not self.last else "")
        if self.exit_style == "sheet" and not self.last:
            eraser += f'<div class="dd-sheet" id="{self.id("sheet")}"><i></i></div>'
        return f"""<template>
  <style>
{shared_css}
{''.join(self.css)}
  </style>
  <div id="root" data-composition-id="{sid}" data-width="1080" data-height="1920">
    <div class="dd-board" id="{self.id('card')}" style="height:{self.board_h}px">{''.join(self.body)}</div>
    {kick}
    {eraser}
  </div>
  <script>
    (function(){{
    const tl = gsap.timeline({{ paused: true }});
    {js}
    tl.set({{}},{{}},{self.dur:.3f});
    window.__timelines["{sid}"] = tl;
    }})();
  </script>
</template>
"""


def _torn_polygon() -> str:
    """clip-path polygon of a page with a torn top edge (deterministic)."""
    rng = _rng("sheet-edge")
    n = 40
    top = [f"{100 * k / n:.2f}% {rng.uniform(0, 26) + 6 * math.sin(k * 1.7):.1f}px" for k in range(n + 1)]
    return ", ".join(top + ["100% 100%", "0% 100%"])


def doodle_css(c: dict, fonts: dict, board_h: int) -> str:
    """Scene CSS for the doodle language. `fonts` = style["fonts"] (body + hand)."""
    body, hand = fonts.get("body", {}), fonts.get("hand", {})
    faces = "".join(
        f"@font-face {{ font-family: '{f['family']}'; src: url('assets/fonts/{f['file']}') format('truetype'); "
        f"font-weight: {f.get('css_weight', '100 900')}; }}\n" for f in (body, hand) if f.get("file"))
    return f"""
    {faces}
    #root {{ position: absolute; inset: 0; --dd-hand: '{hand.get('family', 'cursive')}', '{body.get('family', 'sans-serif')}', cursive;
            --dd-body: '{body.get('family', 'sans-serif')}', sans-serif; color: {c['ink']}; }}
    .dd-board {{ position: absolute; left: 0; top: 0; width: 1080px; }}
    .dd-svg {{ position: absolute; left: 0; top: 0; width: 1080px; overflow: visible; }}
    .dd-s {{ stroke-dasharray: 1 2; stroke-dashoffset: {DRAW_OFF}; }}
    .dd-t {{ position: absolute; line-height: 1.12; letter-spacing: -0.04em; -webkit-text-stroke: 1.8px currentColor; padding: 6px 4px; opacity: 0; word-break: keep-all; }}
    .dd-av {{ position: absolute; border-radius: 50%; object-fit: cover; opacity: 0; filter: saturate(.85) contrast(1.05); }}
    .dd-hand {{ position: absolute; }}
    .dd-bar {{ position: absolute; transform-origin: 50% 100%; transform: scaleY(0); }}
    .dd-kick {{ position: absolute; left: 0; top: 0; width: 1080px; height: 1920px; }}
    .dd-kt {{ position: absolute; left: 50px; width: 980px; text-align: center; font-family: var(--dd-hand); font-weight: 700;
             line-height: 1.05; letter-spacing: -0.09em; -webkit-text-stroke: 2px currentColor; opacity: 0; padding: 0 10px; }}
    .dd-kul {{ position: absolute; left: 0; width: 1080px; height: 30px; overflow: visible; }}
    .dd-ks {{ position: absolute; left: 60px; width: 960px; text-align: center; font-family: var(--dd-body); font-size: 68px;
             font-weight: 800; color: {c['ink']}; opacity: 0; }}
    .dd-cards {{ position: absolute; left: 0; width: 1080px; height: 240px; }}
    .dd-card {{ position: absolute; top: 0; opacity: 0; filter: drop-shadow(0 6px 8px rgba(70,50,20,.16));
               display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center; }}
    .dd-card svg {{ position: absolute; inset: 0; width: 100%; height: 100%; overflow: visible; }}
    .dd-card .dd-m {{ fill: none; stroke-dasharray: 1 2; stroke-dashoffset: {DRAW_OFF}; }}
    .dd-ct {{ position: relative; margin: 0 14px 4px; font-family: var(--dd-hand); font-size: 84px; font-weight: 700; line-height: 1.05;
             letter-spacing: -0.08em; -webkit-text-stroke: 1.4px currentColor; white-space: nowrap; }}
    .dd-cl {{ position: relative; margin: 2px 14px 0; font-family: var(--dd-body); font-size: 58px; font-weight: 800; line-height: 1.2;
             letter-spacing: -0.03em; color: {c['ink']}; white-space: nowrap; }}
    .dd-sheet {{ position: absolute; left: -20px; top: 0; width: 1120px; height: 1990px; opacity: 0; z-index: 40;
                filter: drop-shadow(0 -12px 14px rgba(60,40,20,.35)); }}
    .dd-sheet i {{ position: absolute; inset: 0; background: {c['background']} url('assets/paper.png') 20px 30px / 1080px 1920px no-repeat;
                  clip-path: polygon({_torn_polygon()}); }}
    .dd-kico {{ position: absolute; left: 0; width: 1080px; height: 380px; overflow: visible; }}
    .dd-trk {{ position: absolute; left: 0; width: 1080px; height: 130px; }}
    .dd-trk svg {{ position: absolute; left: 0; top: 0; width: 1080px; height: 130px; overflow: visible; }}
    .dd-trk span {{ position: absolute; top: 26px; font-family: var(--dd-hand); font-size: 58px; font-weight: 700; letter-spacing: -0.04em; -webkit-text-stroke: 1px currentColor; white-space: nowrap; opacity: 0; }}
    .dd-w {{ display: inline-block; padding: 0 8px; margin: 0 -8px; clip-path: inset(0% 100% 0% 0%); }}
    .dd-acc {{ color: {c['accent']}; }}
    .dd-blue {{ color: {c.get('accent2', c['accent'])}; }}
    .dd-mk {{ background: linear-gradient(transparent 52%, {c.get('marker', '#FFE066')} 52%, {c.get('marker', '#FFE066')} 92%, transparent 92%); }}
    .dd-eraser {{ position: absolute; left: 0; top: {board_h * 0.42:.0f}px; width: 150px; height: 74px; opacity: 0; z-index: 30; }}
    .dd-eraser i {{ display: block; width: 100%; height: 100%; border-radius: 14px; background: linear-gradient(90deg, #F2A7A0 0 38%, #3D6FB6 38% 46%, #FBFBF8 46%);
                   box-shadow: 0 8px 18px rgba(60,40,20,.25); }}
"""
