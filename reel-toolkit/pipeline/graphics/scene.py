"""Scene builder: HTML markup + GSAP timeline ops + SFX events for one card scene.

A scene is rendered as a HyperFrames sub-composition (see compose.py). All times are
seconds relative to the scene start. Every animated op also records an SFX event.
"""
from __future__ import annotations

import html
import json
import re

from .icons import CURSOR, icon

STAGE_SPLIT_CY = 478     # card centre while the face occupies the bottom half
STAGE_GRAPHIC_CY = 740   # card centre in full-graphic layout
OVERLAP = 0.0           # seconds a scene host stays alive into the next scene (exit choreography)
CARD_ZOOM = 1.32        # cards are laid out at 948/zoom css px and zoomed (bigger type)
CARD_W = 948
FIT_MAX_H = 700          # max on-screen card height in the split layout
GRAPHIC_SCALE = 1.08     # card scale in the full-graphic layout
STAGE_H = 960            # .rk-stage box height (card centre = stage top + STAGE_H / 2)


def stage_geometry(layout: dict | None = None) -> dict:
    """Card-stage geometry; style["layout"] may override any key (all optional).

    stage_cy / stage_graphic_cy: card centre (px) in split / full-graphic layouts,
    graphic_scale: card scale in full-graphic layouts, fit_max_h: max card height,
    kicker_top: top (px) of the full-graphic kicker headline.
    """
    lay = layout or {}
    return {"split_cy": int(lay.get("stage_cy", STAGE_SPLIT_CY)),
            "graphic_cy": int(lay.get("stage_graphic_cy", STAGE_GRAPHIC_CY)),
            "graphic_scale": float(lay.get("graphic_scale", GRAPHIC_SCALE)),
            "fit_max_h": int(lay.get("fit_max_h", FIT_MAX_H)),
            "kicker_top": int(lay.get("kicker_top", 1040))}


def esc(s: str) -> str:
    return html.escape(str(s), quote=True)


class Scene:
    def __init__(self, sid: str, duration: float, colors: dict, resolve, layout_events,
                 first: bool = False, geo: dict | None = None):
        self.sid = sid
        self.dur = duration
        self.c = colors
        self._resolve = resolve          # (anchor:str|None, default:float) -> float
        self.layout_events = layout_events
        self.first = first
        self.body: list[str] = []
        self.css: list[str] = []
        self.js: list[str] = []
        self.events: list[tuple[float, str]] = []
        self.enter_style = "push"
        self.last = False
        self.kicker: dict | None = None
        self.tracker: list | None = None
        self.geo = geo or stage_geometry()
        self.exit_override: dict | None = None   # style graphics.exit: {role or "*": GSAP tween vars}
        # full-screen templates (graphics/kinetic.py) place their own markup on the 1080x1920
        # root and handle their own entrance/exit: no card stage, no stage moves
        self.fullscreen = False
        self.pre_js: list[str] = []      # layout code that runs before the timeline is built (e.g. fit-to-box)
        self.swap_in = False             # previous panel scene hands over in place (graphics/panel.py)
        self.swap_out = False
        self.prev_params: dict = {}      # neighbouring scenes' params (panel swaps pick their style from the roles)
        self.next_params: dict = {}
        self.tail = 0.0                  # seconds the host outlives the scene (exit over the next shot)

    # ------------------------------------------------------------ helpers
    def id(self, name: str) -> str:
        return f"{self.sid}-{name}"

    def sel(self, name: str) -> str:
        return f"#{self.id(name)}"

    def at(self, anchor, default: float) -> float:
        t = self._resolve(anchor, default) if anchor else default
        return max(0.0, min(self.dur - 0.12, t))

    def add(self, markup: str) -> None:
        self.body.append(markup)

    def ev(self, t: float, kind: str) -> None:
        if 0 <= t < self.dur:
            self.events.append((round(t, 3), kind))

    def _js(self, line: str) -> None:
        self.js.append(line)

    # ------------------------------------------------------------ animation ops
    ENTER = {
        # opaque, on-screen motion; each card role has a clearly different entrance AND exit
        "push": ('{x:70}', '{x:0,duration:.42,ease:"expo.out"}'),
        "zoom": ('{scale:.5}', '{scale:1,duration:.45,ease:"back.out(2.2)"}'),
        "drop": ('{y:-150}', '{y:0,duration:.55,ease:"bounce.out"}'),
        "rise": ('{y:120}', '{y:0,duration:.42,ease:"expo.out"}'),
        "wipe": ('{clipPath:"inset(0% 55% 0% 0% round 38px)"}', '{clipPath:"inset(0% 0% 0% 0% round 38px)",duration:.45,ease:"power3.out"}'),
        "flip": ('{rotationX:-85,transformPerspective:1400,transformOrigin:"50% 0%"}', '{rotationX:0,duration:.55,ease:"back.out(1.6)"}'),
        # hero beats: slam down from above-scale, followed by a short settle shake
        "slam": ('{scale:1.3}', '{scale:1,duration:.3,ease:"power4.in"}'),
    }
    EXIT = {
        "push": '{x:-100,opacity:0,duration:.28,ease:"power2.in"}',
        "zoom": '{scale:.6,opacity:0,duration:.28,ease:"power2.in"}',
        "drop": '{y:-90,opacity:0,duration:.28,ease:"power2.in"}',
        "rise": '{y:90,opacity:0,duration:.28,ease:"power2.in"}',
        "wipe": '{x:-120,opacity:0,duration:.28,ease:"power2.in"}',
        "flip": '{rotationX:80,transformPerspective:1400,transformOrigin:"50% 100%",duration:.3,ease:"power2.in"}',
        "slam": '{scale:.82,opacity:0,duration:.28,ease:"power2.in"}',
    }

    def enter_card(self, name: str = "card", t: float = 0.0) -> None:
        if self.first and t == 0.0:
            # hook card is readable on frame 0 but still settles in (scale .9 -> 1)
            self._js(f'tl.fromTo("{self.sel(name)}",{{scale:.9}},{{scale:1,duration:.5,ease:"back.out(2)"}},0);')
            return
        frm, to = self.ENTER.get(self.enter_style, self.ENTER["push"])
        self._js(f'tl.fromTo("{self.sel(name)}",{frm},{to},{t:.3f});')
        self.ev(t, "stamp" if self.enter_style == "slam" else "whoosh")
        if self.enter_style == "slam":
            self.shake(name, t + 0.32, 10)

    def _ghost_js(self, name: str, t: float, ghost: float, ease: str) -> None:
        ghost = max(ghost, 0.5)
        self._js(f'tl.fromTo("{self.sel(name)}",{{opacity:{ghost},scale:.96,filter:"grayscale(1)"}},'
                 f'{{opacity:1,scale:1,filter:"grayscale(0)",duration:.3,ease:"{ease}"}},{t:.3f});')

    def pop(self, name: str, t: float, sfx: str = "pop", from_scale: float = .6, ghost: float = 0) -> None:
        if ghost:
            self._ghost_js(name, t, ghost, "back.out(2.2)")
        else:
            self._js(f'tl.fromTo("{self.sel(name)}",{{opacity:0,scale:{from_scale}}},'
                     f'{{opacity:1,scale:1,duration:.32,ease:"back.out(2.2)"}},{t:.3f});')
        self.ev(t, sfx)

    def rise(self, name: str, t: float, sfx: str | None = "tick", dy: int = 26, ghost: float = 0) -> None:
        if ghost:
            self._ghost_js(name, t, ghost, "expo.out")
        else:
            self._js(f'tl.fromTo("{self.sel(name)}",{{opacity:0,y:{dy}}},'
                     f'{{opacity:1,y:0,duration:.34,ease:"expo.out"}},{t:.3f});')
        if sfx:
            self.ev(t, sfx)

    def show_from_start(self, name: str) -> None:
        self._js(f'tl.set("{self.sel(name)}",{{opacity:1}},0);')

    def hide_at(self, name: str, t: float, dur: float = .2) -> None:
        self._js(f'tl.to("{self.sel(name)}",{{opacity:0,duration:{dur},ease:"power2.in"}},{t:.3f});')

    def fade_to(self, name: str, t: float, opacity: float, dur: float = .25) -> None:
        self._js(f'tl.to("{self.sel(name)}",{{opacity:{opacity},duration:{dur},ease:"power2.out"}},{t:.3f});')

    def grow(self, name: str, t: float, dur: float, to: float = 1.0, ease: str = "power2.inOut",
             frm: float = 0.0) -> None:
        self._js(f'tl.fromTo("{self.sel(name)}",{{scaleX:{frm}}},{{scaleX:{to},duration:{dur:.3f},'
                 f'ease:"{ease}"}},{t:.3f});')

    def grow_y(self, name: str, t: float, dur: float, to: float = 1.0) -> None:
        self._js(f'tl.fromTo("{self.sel(name)}",{{scaleY:0}},{{scaleY:{to},duration:{dur:.3f},'
                 f'ease:"expo.out"}},{t:.3f});')
        self.ev(t, "rise")

    def count(self, name: str, t: float, frm: float, to: float, dur: float, decimals: int = 0,
              prefix: str = "", suffix: str = "", comma: bool = True) -> None:
        self._js(
            f'(function(){{const o={{v:{frm}}};const el=document.querySelector("{self.sel(name)}");'
            f'tl.to(o,{{v:{to},duration:{dur:.3f},ease:"power3.out",onUpdate:function(){{'
            f'el.textContent={json.dumps(prefix)}+fmt(o.v,{decimals},{str(comma).lower()})+{json.dumps(suffix)};}}}},{t:.3f});}})();')
        self.ev(t, "count")

    def type_text(self, name: str, t: float, text: str, cps: float = 16.0, caret: bool = True) -> float:
        dur = max(0.25, len(text) / cps)
        self._js(
            f'(function(){{const s={json.dumps(text)};const o={{n:0}};const el=document.querySelector("{self.sel(name)}");'
            f'tl.to(o,{{n:s.length,duration:{dur:.3f},ease:"none",onUpdate:function(){{'
            f'el.textContent=s.slice(0,Math.round(o.n));}}}},{t:.3f});}})();')
        self.ev(t, "type")
        return dur

    def stamp(self, name: str, t: float, rot: float = -8) -> None:
        self._js(f'tl.fromTo("{self.sel(name)}",{{opacity:0,scale:2.1,rotation:{rot - 10}}},'
                 f'{{opacity:1,scale:1,rotation:{rot},duration:.34,ease:"back.out(1.6)"}},{t:.3f});')
        self.ev(t, "stamp")

    def check(self, name: str, t: float) -> None:
        self._js(f'tl.fromTo("{self.sel(name)}",{{opacity:0,scale:0,rotation:-30}},'
                 f'{{opacity:1,scale:1,rotation:0,duration:.3,ease:"back.out(2.6)"}},{t:.3f});')
        self.ev(t, "ding")

    def tint(self, name: str, t: float, bg: str, color: str | None = None, dur: float = .25) -> None:
        extra = f',color:"{color}"' if color else ""
        self._js(f'tl.to("{self.sel(name)}",{{backgroundColor:"{bg}"{extra},duration:{dur},'
                 f'ease:"power2.out"}},{t:.3f});')

    def cursor(self, name: str, path: list[tuple[float, float, float]], clicks: list[float]) -> None:
        """path: [(t, x, y)] in stage px. First point sets the start position."""
        k = CARD_W / CARD_ZOOM / CARD_W
        path = [(t, x * k, y * k) for t, x, y in path]
        t0, x0, y0 = path[0]
        self._js(f'tl.fromTo("{self.sel(name)}",{{opacity:0,x:{x0 + 60},y:{y0 + 80}}},'
                 f'{{opacity:1,x:{x0},y:{y0},duration:.35,ease:"power3.out"}},{t0:.3f});')
        prev = t0 + .35
        for t, x, y in path[1:]:
            st = max(prev, t - .45)
            self._js(f'tl.to("{self.sel(name)}",{{x:{x},y:{y},duration:{max(.2, t - st):.3f},'
                     f'ease:"power3.inOut"}},{st:.3f});')
            prev = t
        for t in clicks:
            self._js(f'tl.to("{self.sel(name)}",{{scale:.82,duration:.08,ease:"power2.in"}},{t:.3f});')
            self._js(f'tl.to("{self.sel(name)}",{{scale:1,duration:.16,ease:"back.out(3)"}},{t + .08:.3f});')
            self.ev(t, "click")

    def press(self, name: str, t: float) -> None:
        self._js(f'tl.to("{self.sel(name)}",{{scale:.93,duration:.08,ease:"power2.in"}},{t:.3f});')
        self._js(f'tl.to("{self.sel(name)}",{{scale:1,duration:.22,ease:"back.out(3)"}},{t + .08:.3f});')

    def shake(self, name: str, t: float, amp: float = 14) -> None:
        for k, dx in enumerate((amp, -amp, amp * .6, -amp * .4, 0)):
            self._js(f'tl.to("{self.sel(name)}",{{x:{dx},duration:.05,ease:"sine.inOut"}},{t + .05 * k:.3f});')

    def pulse(self, name: str, t: float, scale: float = 1.08) -> None:
        self._js(f'tl.to("{self.sel(name)}",{{scale:{scale},duration:.14,ease:"power2.out"}},{t:.3f});')
        self._js(f'tl.to("{self.sel(name)}",{{scale:1,duration:.3,ease:"power2.inOut"}},{t + .14:.3f});')

    # ------------------------------------------------------------ markup helpers
    def card_header(self, ico: str, title: str, tag: str | None = None, tag_id: str = "tag") -> str:
        tag_html = (f'<span class="rk-pill" id="{self.id(tag_id)}">{esc(tag)}</span>' if tag else "")
        return (f'<div class="rk-hd"><span class="rk-dots"><i></i><i></i><i></i></span>'
                f'<span class="rk-hd-ico">{icon(ico, 28, 2.2)}</span>'
                f'<span class="rk-hd-t">{esc(title)}</span>{tag_html}</div>')

    def avatar(self, size: int = 64, ring: bool = True) -> str:
        ring_css = f"box-shadow:0 0 0 4px #fff,0 0 0 7px {self.c['accent']};" if ring else ""
        return (f'<img src="assets/avatar.jpg" alt="" style="width:{size}px;height:{size}px;border-radius:50%;'
                f'object-fit:cover;flex:none;{ring_css}">')

    def cursor_markup(self, name: str = "cur") -> str:
        return f'<div class="rk-cursor" id="{self.id(name)}">{CURSOR}</div>'

    # ------------------------------------------------------------ assembly
    def stage_js(self) -> list[str]:
        """Move the card stage between split (top half) and full-graphic (centred) layouts."""
        if self.fullscreen:
            return []
        out = []
        dy = self.geo["graphic_cy"] - self.geo["split_cy"]
        g_scale = self.geo["graphic_scale"]
        state = "split"
        prev_lay = None
        card = self.sel("card")
        kick = self.sel("kick")
        for t, lay in self.layout_events:
            if prev_lay == "face" and lay != "face" and t > 0.01:
                # the card comes back after a full-face beat: re-enter instead of popping in
                out.append(f'tl.fromTo("{card}",{{y:60}},{{y:0,duration:.4,ease:"expo.out"}},{t:.3f});')
                self.ev(t, "whoosh")
            if self.kicker:
                if lay == "graphic" and prev_lay != "graphic":
                    t = t + float(self.kicker.get("delay", 0))
                    if self.kicker.get("at"):
                        t = max(t, self.at(self.kicker["at"], t))
                    out.append(f'tl.fromTo("{kick}-t",{{opacity:0,scale:.6}},{{opacity:1,scale:1,duration:.42,ease:"back.out(2)"}},{t:.3f});')
                    out.append(f'tl.fromTo("{kick}-s",{{opacity:0,y:24}},{{opacity:1,y:0,duration:.3,ease:"expo.out"}},{t + .14:.3f});')
                    if self.tracker:
                        out.append(f'tl.fromTo("{kick}-tr .rk-tc",{{opacity:0,y:30}},{{opacity:1,y:0,duration:.35,ease:"back.out(2)",stagger:.07}},{t + .2:.3f});')
                    self.ev(t, "pop")
                elif lay != "graphic" and prev_lay == "graphic":
                    out.append(f'tl.to("{kick}-t, {kick}-s",{{opacity:0,duration:.01}},{t:.3f});')
                prev_lay = lay
                continue
            prev_lay = lay
            want = "graphic" if lay == "graphic" else "split"
            if lay == "face" or want == state or (dy == 0 and g_scale == 1.0):
                continue
            y, sc = (dy, g_scale) if want == "graphic" else (0, 1.0)
            if t <= 0.01:
                out.append(f'tl.set("{self.sel("stage")}",{{y:{y},scale:{sc}}},0);')
            else:
                out.append(f'tl.to("{self.sel("stage")}",{{y:{y},scale:{sc},duration:.5,'
                           f'ease:"power3.inOut"}},{t:.3f});')
            state = want
        if self.layout_events and self.layout_events[-1][1] != "face" and not self.last:
            # exit choreography: the host outlives the scene by OVERLAP seconds, so the old card
            # is pushed out while the next card enters (no empty frame between cards)
            # quick opaque settle-out that ends exactly on the cut to the next card
            ex = self.exit_override or {}
            exit_tw = ex.get(self.enter_style) or ex.get("*") or self.EXIT.get(self.enter_style, self.EXIT["push"])
            out.append(f'tl.to("{card}",{exit_tw},{self.dur - 0.28:.3f});')
        if self.kicker and self.layout_events and self.layout_events[-1][1] == "graphic" and not self.last:
            out.append(f'tl.to("{kick}-t, {kick}-s, {kick}-tr",{{opacity:0,y:40,duration:.24,ease:"power2.in"}},{self.dur - 0.26:.3f});')
        return out

    def kicker_markup(self) -> str:
        if not self.kicker:
            return ""
        plain = re.sub(r"<[^>]+>", "", self.kicker.get("text", "").replace("<br>", "|"))
        longest = max(len(x) for x in plain.split("|"))
        size = 112 if longest <= 9 else max(72, int(112 * 9 / longest))
        tr = ""
        if self.tracker:
            chips = []
            for k, (label, ico, st) in enumerate(self.tracker):
                col = {"done": self.c["good"], "active": self.c["accent"], "warn": "#D99A2B"}.get(st, self.c["ink_soft"])
                mark = {"done": icon("check", 38, 3.2, col), "active": icon("spark", 38, 2.6, col),
                        "warn": icon("alert", 38, 2.6, col)}.get(st, icon(ico, 38, 2.2, col))
                chips.append(f'<div class="rk-tc" style="border-color:{col}">{mark}<span>{esc(label)}</span></div>')
            tr = f'<div class="rk-tr" id="{self.id("kick")}-tr">{"".join(chips)}</div>'
        return (f'<div class="rk-kick">{tr}<div class="rk-kick-t" id="{self.id("kick")}-t" style="font-size:{size}px">{self.kicker.get("text", "")}</div>'
                f'<div class="rk-kick-s" id="{self.id("kick")}-s">{esc(self.kicker.get("sub", ""))}</div></div>')

    @staticmethod
    def _baseline(lines: list[str]) -> list[str]:
        """Only the earliest fromTo per element may immediateRender (GSAP seek safety)."""
        pat = re.compile(r'tl\.fromTo\("([^"]+)".*,(-?[\d.]+)\);$')
        first: dict[str, float] = {}
        for ln in lines:
            m = pat.search(ln)
            if m:
                first[m.group(1)] = min(first.get(m.group(1), 1e9), float(m.group(2)))
        out, used = [], set()
        for ln in lines:
            m = pat.search(ln)
            if m and (m.group(1) in used or float(m.group(2)) > first[m.group(1)]):
                i = ln.index("},{") + 3
                ln = ln[:i] + "immediateRender:false," + ln[i:]
            elif m:
                used.add(m.group(1))
            out.append(ln)
        return out

    def _root_markup(self) -> str:
        if self.fullscreen:
            return "".join(self.body)
        return (f'<div class="rk-stage" id="{self.id("stage")}">'
                f'<div class="rk-fit" id="{self.id("fit")}">{"".join(self.body)}</div></div>'
                f'{self.kicker_markup()}')

    def graphic_window(self) -> tuple[float, float] | None:
        """(start of the first, end of the last) full-graphic layout run inside this scene, scene-relative.
        A talking-head beat in between simply covers the card (face layers sit above scene hosts)."""
        start = end = None
        for k, (t, lay) in enumerate(self.layout_events):
            if lay == "graphic":
                start = t if start is None else start
                end = self.layout_events[k + 1][0] if k + 1 < len(self.layout_events) else self.dur
        return (start, end) if start is not None else None

    def build(self, shared_css: str) -> str:
        sid = self.sid
        js = "\n    ".join(self._baseline(self.stage_js() + self.js))
        return f"""<template>
  <style>
{shared_css}
{''.join(self.css)}
  </style>
  <div id="root" data-composition-id="{sid}" data-width="1080" data-height="1920">
    {self._root_markup()}
  </div>
  <script>
    (function(){{
    function fmt(v,d,c){{const s=Number(v).toFixed(d);if(!c)return s;const p=s.split(".");p[0]=p[0].replace(/\\B(?=(\\d{{3}})+(?!\\d))/g,",");return p.join(".");}}
    const fitEl = document.querySelector("#{sid}-fit");
    if (fitEl) {{ const r = fitEl.getBoundingClientRect(); const k = Math.min(1, {self.geo["fit_max_h"]} / Math.max(1, r.height)); if (k < 1) gsap.set(fitEl, {{ scale: k }}); }}
    {''.join(self.pre_js)}
    const tl = gsap.timeline({{ paused: true }});
    {js}
    tl.set({{}},{{}},{self.dur + (0 if self.last else max(OVERLAP, self.tail)):.3f});
    window.__timelines["{sid}"] = tl;
    }})();
  </script>
</template>
"""


def shared_css(c: dict, font_family: str, geo: dict | None = None, extra_css: str = "") -> str:
    """Card CSS. `geo` (stage_geometry) moves the stage / kicker; `extra_css` is appended
    so a style can restyle cards (radius, header chrome) without new templates."""
    geo = geo or stage_geometry()
    stage_top = geo["split_cy"] - STAGE_SPLIT_CY
    return _base_css(c, font_family, stage_top, geo["kicker_top"]) + (extra_css or "")


def _base_css(c: dict, font_family: str, stage_top: int, kicker_top: int) -> str:
    return f"""
    @font-face {{ font-family: '{font_family}'; src: url('assets/fonts/PretendardVariable.ttf') format('truetype'); font-weight: 100 900; }}
    #root {{ position: absolute; inset: 0; font-family: '{font_family}', sans-serif; color: {c['ink']}; }}
    .rk-stage {{ position: absolute; left: 0; top: {stage_top or 0}{"px" if stage_top else ""}; width: 1080px; height: 960px; display: flex; align-items: center; justify-content: center; flex-direction: column; gap: 26px; }}
    .rk-card {{ width: {CARD_W / CARD_ZOOM:.0f}px; zoom: {CARD_ZOOM}; background: {c['card']}; border-radius: 38px; box-shadow: 0 22px 60px rgba(70,45,35,.10), 0 3px 10px rgba(70,45,35,.06); padding: 30px 36px 32px; box-sizing: border-box; position: relative; }}
    .rk-hd {{ display: flex; align-items: center; gap: 14px; font-size: 34px; font-weight: 700; letter-spacing: -0.5px; margin: -6px -6px 20px; padding-bottom: 16px; border-bottom: 2px solid {c['card_soft']}; }}
    .rk-dots {{ display: flex; gap: 8px; margin-right: 6px; }}
    .rk-dots i {{ width: 14px; height: 14px; border-radius: 50%; background: {c['placeholder']}; display: block; }}
    .rk-hd-ico {{ width: 46px; height: 46px; border-radius: 13px; background: {c['accent']}; color: #fff; display: flex; align-items: center; justify-content: center; }}
    .rk-hd-t {{ flex: 1; white-space: nowrap; }}
    .rk-pill {{ font-size: 24px; font-weight: 700; padding: 8px 18px; border-radius: 999px; background: {c['accent_soft']}; color: {c['accent']}; white-space: nowrap; }}
    .rk-row {{ display: flex; align-items: center; gap: 18px; background: {c['card_soft']}; border-radius: 22px; padding: 16px 22px; font-size: 32px; font-weight: 600; margin-top: 12px; }}
    .rk-row .rk-lbl {{ flex: 1; white-space: nowrap; }}
    .rk-ibox {{ width: 54px; height: 54px; border-radius: 16px; background: #fff; display: flex; align-items: center; justify-content: center; color: {c['accent']}; flex: none; }}
    .rk-chk {{ width: 46px; height: 46px; border-radius: 50%; background: {c['accent']}; color: #fff; display: flex; align-items: center; justify-content: center; flex: none; opacity: 0; }}
    .rk-chk.ok {{ background: {c['good']}; }}
    .rk-bar {{ height: 18px; border-radius: 9px; background: {c['placeholder']}; overflow: hidden; }}
    .rk-fill {{ height: 100%; width: 100%; border-radius: 9px; background: {c['accent']}; transform-origin: 0 50%; }}
    .rk-ph {{ height: 18px; border-radius: 9px; background: {c['placeholder']}; margin-top: 14px; }}
    .rk-kick {{ position: absolute; left: 60px; right: 60px; top: {kicker_top}px; text-align: center; }}
    .rk-tr {{ display: flex; justify-content: center; gap: 16px; margin: 0 0 34px; }}
    .rk-tc {{ display: flex; align-items: center; gap: 12px; padding: 14px 26px; border-radius: 999px; background: #fff; border: 4px solid; font-size: 40px; font-weight: 800; opacity: 0; }}
    .rk-kick-t {{ font-size: 112px; font-weight: 800; letter-spacing: -4px; line-height: 1.08; opacity: 0; }}
    .rk-kick-s {{ font-size: 40px; font-weight: 700; color: {c['ink_soft']}; margin-top: 18px; opacity: 0; }}
    .rk-big {{ font-size: 150px; font-weight: 800; letter-spacing: -5px; line-height: 1; }}
    .rk-acc {{ color: {c['accent']}; }}
    .rk-soft {{ color: {c['ink_soft']}; }}
    .rk-hidden {{ opacity: 0; }}
    .rk-cursor {{ position: absolute; left: 0; top: 0; width: 64px; height: 64px; opacity: 0; z-index: 20; }}
    .rk-stamp {{ position: absolute; padding: 14px 30px; border: 6px solid {c['accent']}; color: {c['accent']}; border-radius: 18px; font-size: 54px; font-weight: 800; background: rgba(255,255,255,.92); white-space: nowrap; opacity: 0; z-index: 10; }}
    .rk-chip {{ display: inline-flex; align-items: center; gap: 10px; padding: 12px 22px; border-radius: 999px; background: {c['card_soft']}; font-size: 30px; font-weight: 700; white-space: nowrap; }}
    .rk-btn {{ display: inline-flex; align-items: center; justify-content: center; gap: 12px; padding: 20px 34px; border-radius: 22px; background: {c['accent']}; color: #fff; font-size: 34px; font-weight: 800; white-space: nowrap; }}
"""
