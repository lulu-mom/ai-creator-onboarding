"""FX overlay above the speaker (below captions): word-anchored stickers and cut flashes.

Only written when the content plan has `stickers` or the style asks for flashes
(style transitions.flash_on_layout_change), so styles without them are unchanged.

Sticker (plan "stickers" entry):
  {"anchor": "메모를", "text": "메모 → 할 일", "icon": "doc", "tone": "accent|warn|good|light",
   "side": "left|center|right", "dur": 1.8}
"""
from __future__ import annotations

import html

from graphics.icons import icon

from .plan import EWord, Segment, _match_anchor

STICKER_TOP = 290        # px default (style motion.sticker_top overrides, e.g. under the caption band)
STICKER_MIN_DUR = 0.6
FLASH_DUR = 0.12


def resolve_stickers(stickers: list[dict], words: list[EWord], duration: float,
                     blocked: list[tuple[float, float]] | None = None) -> list[dict]:
    """Anchor each sticker to its word; drop stickers whose anchor is missing; no overlaps.
    `blocked` windows (full-screen graphic beats) end a sticker before they start."""
    out, pos = [], 0
    for st in stickers:
        wi = _match_anchor(words, st["anchor"], pos)
        if wi is None:
            print(f"[overlay] sticker anchor not found: {st['anchor']}")
            continue
        pos = wi + 1
        t0 = max(0.0, words[wi].start)
        t1 = min(duration, t0 + float(st.get("dur", 1.8)))
        if out and out[-1]["t1"] > t0:
            out[-1]["t1"] = t0               # the previous sticker leaves when the next one lands
        out.append({**st, "t0": round(t0, 3), "t1": round(t1, 3)})
    for st in out:
        for a, b in blocked or []:
            if a <= st["t0"] < b:
                st["t1"] = st["t0"]                      # lands inside a full-screen beat: drop
            elif st["t0"] < a < st["t1"]:
                st["t1"] = a
    return [s for s in out if s["t1"] - s["t0"] >= STICKER_MIN_DUR]


def graphic_windows(segs: list[Segment]) -> list[tuple[float, float]]:
    # stickers only live on the plain speaker: never over full-screen cards or floating panels
    return [(s.start, s.end) for s in segs if s.layout in ("graphic", "split")]


def flash_times(segs: list[Segment]) -> list[float]:
    """Cuts into or out of a full-graphic beat."""
    out = []
    for a, b in zip(segs, segs[1:]):
        if a.layout != b.layout and "graphic" in (a.layout, b.layout):
            out.append(round(b.start, 3))
    return out


def _tone(colors: dict, tone: str) -> tuple[str, str]:
    """(badge colour, icon colour)."""
    return {"warn": (colors.get("warn", "#E03131"), "#FFFFFF"),
            "good": (colors.get("good", "#2FA36B"), "#FFFFFF"),
            "light": ("#FFFFFF", "#111111")}.get(tone, (colors["accent"], "#111111"))


def fx_html(stickers: list[dict], flashes: list[float], style: dict, duration: float) -> tuple[str, list]:
    col, fam = style["colors"], style["font"]["family"]
    top = int((style.get("motion") or {}).get("sticker_top", STICKER_TOP))
    body, js, events = [], [], []
    for i, st in enumerate(stickers):
        badge, ink = _tone(col, st.get("tone", "accent"))
        side = st.get("side", "center")
        just = {"left": "flex-start", "right": "flex-end"}.get(side, "center")
        rot = {"left": -4, "right": 4}.get(side, -2)
        dur = st["t1"] - st["t0"]
        body.append(
            f'<div class="clip st-row" data-start="{st["t0"]:.3f}" data-duration="{dur:.3f}" data-track-index="0" '
            f'style="justify-content:{just}"><div class="st" id="st{i}">'
            f'<span class="st-ic" style="background:{badge};color:{ink}">{icon(st.get("icon", "spark"), 58, 2.4)}</span>'
            f'<span class="st-t">{html.escape(st["text"])}</span></div></div>')
        dx = {"left": -160, "right": 160}.get(side, 0)
        js.append(f'tl.fromTo("#st{i}",{{x:{dx},scale:{0.5 if dx else 0.8},rotation:{rot - 12}}},{{x:0,scale:1,rotation:{rot},'
                  f'duration:.26,ease:"back.out(2.2)"}},{st["t0"]:.3f});')
        js.append(f'tl.fromTo("#st{i} .st-ic",{{rotation:-25}},{{rotation:0,duration:.5,ease:"elastic.out(1,.45)",'
                  f'immediateRender:false}},{st["t0"] + 0.12:.3f});')
        if st.get("tone") == "warn":          # warnings land with a short shake
            for k, x in enumerate((14, -12, 8, -4, 0)):
                js.append(f'tl.to("#st{i}",{{x:{x},duration:.05,ease:"sine.inOut"}},{st["t0"] + 0.42 + 0.05 * k:.3f});')
        elif st.get("tone") == "good":        # done items get a check pop
            js.append(f'tl.fromTo("#st{i} .st-ic",{{scale:.4}},{{scale:1,duration:.4,ease:"back.out(3)",immediateRender:false}},'
                      f'{st["t0"] + 0.2:.3f});')
        if dur > 0.9:
            js.append(f'tl.to("#st{i}",{{opacity:0,scale:.92,duration:.14,ease:"power1.in"}},'
                      f'{st["t1"] - 0.14:.3f});')
        events.append((st["t0"], "pop"))
    for k, t in enumerate(flashes):
        js.append(f'tl.fromTo("#flash",{{opacity:.85}},{{opacity:0,duration:{FLASH_DUR},ease:"power1.out",'
                  f'immediateRender:false}},{t:.3f});')
    doc = f"""<template>
  <style>
    @font-face {{ font-family: '{fam}'; src: url('assets/fonts/PretendardVariable.ttf') format('truetype'); font-weight: 100 900; }}
    #root {{ position: absolute; inset: 0; }}
    #flash {{ position: absolute; inset: 0; background: #fff; opacity: 0; }}
    .st-row {{ position: absolute; left: 64px; right: 64px; top: {top}px; display: flex; }}
    .st {{ display: inline-flex; align-items: center; gap: 18px; padding: 14px 34px 14px 14px; border-radius: 999px;
          background: #fff; border: 6px solid #111; box-shadow: 0 10px 0 #111; font-family: '{fam}', sans-serif;
          font-size: 66px; font-weight: 900; color: #111; letter-spacing: -1.5px; white-space: nowrap; }}
    .st-ic {{ width: 96px; height: 96px; border-radius: 50%; display: flex; align-items: center; justify-content: center; }}
  </style>
  <div id="root" data-composition-id="fx" data-width="1080" data-height="1920">
    {chr(10).join('    ' + b for b in body)}
    <div id="flash"></div>
  </div>
  <script>
    const tl = gsap.timeline({{ paused: true }});
    {chr(10).join('    ' + j for j in js)}
    tl.set({{}},{{}},{duration:.3f});
    window.__timelines["fx"] = tl;
  </script>
</template>
"""
    return doc, events
