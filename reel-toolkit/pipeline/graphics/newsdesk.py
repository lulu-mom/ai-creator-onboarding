"""News-desk overlays: fixed headline bar with section titles, section sweep cards,
bottom ticker and broadcast lower-third captions.

Everything here is opt-in from the style JSON:
  style["overlays"]["newsdesk"]  -> overlay_html()   (headline bar / sweeps / ticker)
  style["captions"]["style"] == "lower_third" -> lower_third_captions()
Content (section titles, ticker items, brand, date) comes from the content plan:
  plan["sections"] = [{"anchor": "...", "chip": "1/3", "title": "...", "sweep": true}]
  plan["ticker_items"] = ["...", ...]; plan["newsdesk"] = {"brand": ..., "date": ..., "source": ...}
"""
from __future__ import annotations

import html
import re

W, H = 1080, 1920
STRIP = re.compile(r"[.,!…~\"'“”]+")

DEFAULT_DESK = {
    "top_h": 330,                 # headline bar height (px)
    "meta_top": 104,              # LIVE / brand / source row
    "head_top": 176,              # chip + section title row (120 px tall)
    "brand": "BRIEFING",
    "live": "LIVE",
    "date": "",
    "source": "",
    "title_size": 64,
    "title_max_chars": 13,        # titles longer than this shrink to fit
    "sweep": {"top": 330, "bottom": 1075, "lead": 0.42, "in": 0.2, "out": 0.24},
    "ticker": {"y": 1834, "h": 66, "label": "BRIEF", "speed": 110, "font_size": 34},
}


def esc(s) -> str:
    return html.escape(str(s), quote=True)


def _merge(base: dict, over: dict | None) -> dict:
    out = dict(base)
    for k, v in (over or {}).items():
        out[k] = _merge(base[k], v) if isinstance(v, dict) and isinstance(base.get(k), dict) else v
    return out


def desk_config(style: dict, plan: dict | None) -> dict:
    """Style defaults < style overlays.newsdesk < plan newsdesk (content-specific text)."""
    cfg = _merge(DEFAULT_DESK, (style.get("overlays") or {}).get("newsdesk") or {})
    return _merge(cfg, (plan or {}).get("newsdesk") or {})


def section_times(sections: list[dict], words) -> list[tuple[float, dict]]:
    """Resolve section anchors to edited-timeline seconds (in order; missing anchors skipped).
    The first section always starts at 0 so the bar is never empty."""
    from steps.plan import _match_anchor
    out, pos = [], 0
    for sec in sections:
        wi = _match_anchor(words, sec.get("anchor", ""), pos) if sec.get("anchor") else None
        if wi is None and out:
            print(f"[newsdesk] section anchor not found: {sec.get('anchor')}")
            continue
        t = 0.0 if wi is None else words[wi].start
        if wi is not None:
            pos = wi + 1
        out.append((t, sec))
    if out:
        out[0] = (0.0, out[0][1])
    return out


def _title_size(text: str, cfg: dict) -> int:
    n = len(re.sub(r"<[^>]+>", "", text))
    base, mx = int(cfg["title_size"]), int(cfg["title_max_chars"])
    return base if n <= mx else max(40, int(base * mx / n))


def _ticker_strip(items: list[str], min_px: float, font_size: int) -> str:
    """Repeat the items until the strip is wider than the distance it scrolls."""
    if not items:
        return ""
    sep = '<i class="nd-sep">◆</i>'
    unit = sep.join(f"<span>{esc(x)}</span>" for x in items) + sep

    def est(text: str) -> float:
        return sum(font_size * (1.0 if ord(ch) > 0x1100 else 0.55) for ch in text) + font_size * 2.2

    unit_px = sum(est(x) for x in items) or 1.0
    reps = int(min_px / unit_px) + 2
    return unit * reps


def overlay_html(style: dict, plan: dict, words, duration: float) -> tuple[str, list]:
    """HyperFrames sub-composition with the headline bar, section sweeps and ticker."""
    cfg = desk_config(style, plan)
    col = style["colors"]
    fam = style["font"]["family"]
    navy, red = col.get("desk", col["ink"]), col.get("breaking", col["accent"])
    yellow, grey = col.get("flash", "#FFD43B"), col.get("ink_soft", "#ADB5BD")
    secs = section_times(plan.get("sections") or [], words)
    events: list[tuple[float, str]] = []
    js: list[str] = []
    top_h = int(cfg["top_h"])

    sw = cfg["sweep"]

    def head_time(k: int) -> float:
        """Headline swap time: with a chapter sweep the header changes as the sweep starts."""
        t, sec = secs[k]
        return max(0.0, t - float(sw["lead"]) + 0.08) if sec.get("sweep") and t >= 0.5 else t

    # ---------------------------------------------------------------- headline bar
    heads = []
    for k, (t, sec) in enumerate(secs):
        chip_bg = red if sec.get("chip_style") == "alert" else yellow
        chip_fg = "#fff" if sec.get("chip_style") == "alert" else navy
        chip = (f'<span class="nd-chip" id="nd-c{k}" style="background:{chip_bg};color:{chip_fg}">{esc(sec["chip"])}</span>'
                if sec.get("chip") else "")
        vis = "" if k == 0 else "transform:translateY(130px);"
        heads.append(f'<div class="nd-head" id="nd-h{k}" style="{vis}">{chip}'
                     f'<span class="nd-title" id="nd-t{k}" style="font-size:{_title_size(sec.get("title", ""), cfg)}px">'
                     f'{sec.get("title", "")}</span></div>')
        nxt = head_time(k + 1) if k + 1 < len(secs) else None
        if k > 0:
            t = head_time(k)
            # opaque push inside a clipped row: the new headline pushes the old one up (no empty or ghost frame)
            js.append(f'tl.fromTo("#nd-h{k}",{{y:130}},{{y:0,duration:.24,ease:"power3.out"}},{t - .02:.3f});')
            if sec.get("chip"):
                js.append(f'tl.fromTo("#nd-c{k}",{{scale:.7}},{{scale:1,duration:.3,ease:"back.out(2.6)"}},{t + .1:.3f});')
            js.append(f'tl.fromTo("#nd-line",{{scaleX:0}},{{scaleX:1,duration:.45,ease:"power3.inOut",immediateRender:false}},{t:.3f});')
            events.append((t, "tick"))
        if nxt is not None:
            js.append(f'tl.to("#nd-h{k}",{{y:-130,duration:.14,ease:"power2.in"}},{max(0.0, nxt - .16):.3f});')
    if secs:
        js.append('tl.fromTo("#nd-line",{scaleX:0},{scaleX:1,duration:.6,ease:"power3.out"},0);')
    meta_r = " · ".join(x for x in (cfg.get("source"), cfg.get("date")) if x)
    top = (f'<div class="nd-top" style="height:{top_h}px">'
           f'<div class="nd-meta"><span class="nd-live"><i id="nd-dot"></i>{esc(cfg["live"])}</span>'
           f'<span class="nd-brand">{esc(cfg["brand"])}</span><span class="nd-src">{esc(meta_r)}</span></div>'
           f'<div class="nd-headbox">{"".join(heads)}</div><div class="nd-line" id="nd-line"></div></div>')
    blinks = max(1, int(duration / 0.6))
    js.append(f'tl.to("#nd-dot",{{opacity:.25,duration:.6,repeat:{blinks},yoyo:true,ease:"sine.inOut"}},0);')

    # ---------------------------------------------------------------- section sweeps
    sweeps = []
    # alternate the wipe direction so chapter cards do not all move the same way
    wipes = [("inset(0% 100% 0% 0%)", "inset(0% 0% 0% 100%)"), ("inset(0% 0% 0% 100%)", "inset(0% 100% 0% 0%)"),
             ("inset(0% 0% 100% 0%)", "inset(100% 0% 0% 0%)")]
    for k, (t, sec) in enumerate(secs):
        if not sec.get("sweep") or t < 0.5:
            continue
        t_in = max(0.0, t - float(sw["lead"]))
        sweeps.append(f'<div class="nd-sw" id="nd-sw{k}"><div class="nd-sw-num">{esc(sec.get("chip", ""))}</div>'
                      f'<div class="nd-sw-t">{sec.get("sweep_title", sec.get("title", ""))}</div></div>')
        # in-place clip wipe (left -> right in, then off to the right): no sliced text sliding past the edge
        w_in, w_out = wipes[(len(sweeps) - 1) % len(wipes)]
        js.append(f'tl.fromTo("#nd-sw{k}",{{clipPath:"{w_in}"}},{{clipPath:"inset(0% 0% 0% 0%)",duration:{sw["in"]},ease:"power3.out"}},{t_in:.3f});')
        js.append(f'tl.fromTo("#nd-sw{k} .nd-sw-num",{{scale:.6}},{{scale:1,duration:.3,ease:"back.out(2.4)"}},{t_in + .08:.3f});')
        js.append(f'tl.to("#nd-sw{k}",{{clipPath:"{w_out}",duration:{sw["out"]},ease:"power3.in",immediateRender:false}},{t + .02:.3f});')
        events.append((t_in, "whoosh"))
    sw_box = (f'<div class="nd-swbox" style="top:{sw["top"]}px;height:{int(sw["bottom"]) - int(sw["top"])}px">'
              f'{"".join(sweeps)}</div>') if sweeps else ""

    # ---------------------------------------------------------------- ticker
    tk = cfg["ticker"]
    items = plan.get("ticker_items") or tk.get("items") or []
    ticker = ""
    if items:
        dist = float(tk["speed"]) * duration
        strip = _ticker_strip(items, dist + W, int(tk["font_size"]))
        ticker = (f'<div class="nd-tk" style="top:{tk["y"]}px;height:{tk["h"]}px">'
                  f'<div class="nd-tk-l">{esc(tk["label"])}</div>'
                  f'<div class="nd-tk-win"><div class="nd-tk-s" id="nd-tks">{strip}</div></div></div>')
        js.append(f'tl.fromTo("#nd-tks",{{x:0}},{{x:{-dist:.0f},duration:{duration:.3f},ease:"none"}},0);')

    body = top + sw_box + ticker
    jsb = "\n    ".join(js)
    css = f"""
    @font-face {{ font-family: '{fam}'; src: url('assets/fonts/PretendardVariable.ttf') format('truetype'); font-weight: 100 900; }}
    #root {{ position: absolute; inset: 0; font-family: '{fam}', sans-serif; }}
    .nd-top {{ position: absolute; left: 0; top: 0; width: 1080px; background: {navy}; overflow: hidden; }}
    .nd-meta {{ position: absolute; left: 54px; right: 54px; top: {cfg['meta_top']}px; display: flex; align-items: center; gap: 18px; }}
    .nd-live {{ display: inline-flex; align-items: center; gap: 10px; background: {red}; color: #fff; font-size: 28px; font-weight: 800;
               padding: 6px 16px 6px 14px; border-radius: 4px; letter-spacing: 1px; }}
    .nd-live i {{ width: 14px; height: 14px; border-radius: 50%; background: #fff; display: block; }}
    .nd-brand {{ color: #fff; font-size: 32px; font-weight: 800; letter-spacing: -0.5px; }}
    .nd-src {{ margin-left: auto; color: {grey}; font-size: 27px; font-weight: 600; }}
    .nd-headbox {{ position: absolute; left: 54px; right: 40px; top: {cfg['head_top']}px; height: 124px; overflow: hidden; }}
    .nd-head {{ position: absolute; inset: 0; display: flex; align-items: center; gap: 22px; }}
    .nd-chip {{ flex: none; font-size: 44px; font-weight: 900; padding: 6px 18px; border-radius: 4px; letter-spacing: -1px; }}
    .nd-title {{ color: #fff; font-weight: 800; letter-spacing: -2px; white-space: nowrap; line-height: 1.1; }}
    .nd-title .acc {{ color: {yellow}; }}
    .nd-line {{ position: absolute; left: 0; bottom: 0; width: 1080px; height: 8px; background: {red}; transform-origin: 0 50%; }}
    .nd-swbox {{ position: absolute; left: 0; width: 1080px; overflow: hidden; }}
    .nd-sw {{ position: absolute; inset: 0; background: {navy}; border-left: 22px solid {red}; display: flex; flex-direction: column;
             align-items: center; justify-content: flex-start; padding-top: {sw.get("content_top", 150)}px; gap: 18px; clip-path: inset(0% 100% 0% 0%); }}
    .nd-sw-num {{ font-size: 190px; font-weight: 900; color: {yellow}; letter-spacing: -6px; line-height: 1; }}
    .nd-sw-t {{ font-size: 64px; font-weight: 800; color: #fff; letter-spacing: -2px; }}
    .nd-tk {{ position: absolute; left: 0; width: 1080px; background: {navy}; border-top: 5px solid {yellow}; display: flex; align-items: center; overflow: hidden; }}
    .nd-tk-l {{ flex: none; height: 100%; display: flex; align-items: center; padding: 0 26px; background: {red}; color: #fff;
               font-size: {tk["font_size"]}px; font-weight: 900; letter-spacing: 1px; z-index: 2; }}
    .nd-tk-win {{ flex: 1; height: 100%; overflow: hidden; position: relative; }}
    .nd-tk-s {{ position: absolute; left: 24px; top: 0; height: 100%; display: flex; align-items: center; white-space: nowrap;
               color: #fff; font-size: {tk["font_size"]}px; font-weight: 700; }}
    .nd-sep {{ font-style: normal; color: {yellow}; margin: 0 26px; font-size: {int(tk["font_size"]) * 0.6:.0f}px; }}
"""
    src = f"""<template>
  <style>{css}
  </style>
  <div id="root" data-composition-id="newsdesk" data-width="1080" data-height="1920">
    {body}
  </div>
  <script>
    const tl = gsap.timeline({{ paused: true }});
    {jsb}
    tl.set({{}},{{}},{duration:.3f});
    window.__timelines["newsdesk"] = tl;
  </script>
</template>
"""
    return src, events


def lower_third_captions(chunks, style: dict, duration: float) -> str:
    """Broadcast lower third: fixed-width navy bar, left accent notch, left-aligned text,
    key words turn into red blocks on their own spoken word. A bar wipes in when speech
    resumes after a pause; inside a run only the text rolls up."""
    cc, col = style["captions"], style["colors"]
    fam = style["font"]["family"]
    bar = _merge({"x": 54, "w": 972, "pad_x": 34, "pad_y": 16, "radius": 4, "notch": 16}, cc.get("bar"))
    fs = int(cc["font_size"])
    bar_h = fs * 1.25 + 2 * int(bar["pad_y"])
    emph_bg = col.get("caption_emph_bg", col.get("breaking", col["accent"]))
    groups, js = [], []
    prev_end = -1.0
    for i, c in enumerate(chunks):
        if not c.text:
            continue
        dur = max(0.1, c.end - c.start)
        top = c.y * H - bar_h / 2
        marks = c.emph_words or [c.emph] * len(c.words)
        parts = []
        for k, (w, m) in enumerate(zip(c.words, marks)):
            wt = esc(STRIP.sub("", w.text))
            if not wt:
                continue
            if m:
                parts.append(f'<span class="lt-em"><i id="ce{i}_{k}"></i>{wt}</span>')
                t_w = max(c.start, w.start)
                if t_w > 0.05:
                    js.append(f'tl.fromTo("#ce{i}_{k}",{{scaleX:0}},{{scaleX:1,duration:.18,ease:"power3.out"}},{t_w:.3f});')
            else:
                parts.append(wt)
        groups.append(
            f'<div id="cg{i}" class="clip lt" data-start="{c.start:.3f}" data-duration="{dur:.3f}" data-track-index="0" '
            f'style="top:{top:.0f}px"><div class="lt-bar" id="cb{i}"><div class="lt-tx" id="ct{i}">{" ".join(parts)}</div></div></div>')
        if c.start >= 0.05:
            if c.start - prev_end > 0.05:
                js.append(f'tl.fromTo("#cb{i}",{{clipPath:"inset(0% 100% 0% 0%)"}},'
                          f'{{clipPath:"inset(0% 0% 0% 0%)",duration:.26,ease:"power3.out"}},{c.start:.3f});')
                js.append(f'tl.fromTo("#ct{i}",{{opacity:0,x:-24}},{{opacity:1,x:0,duration:.22,ease:"power2.out"}},{c.start + .08:.3f});')
            else:
                js.append(f'tl.fromTo("#ct{i}",{{opacity:0}},{{opacity:1,duration:.1,ease:"power1.out"}},{c.start:.3f});')
        prev_end = c.end
    body = "\n    ".join(groups)
    jsb = "\n    ".join(js)
    return f"""<template>
  <style>
    @font-face {{ font-family: '{fam}'; src: url('assets/fonts/PretendardVariable.ttf') format('truetype'); font-weight: 100 900; }}
    #root {{ position: absolute; inset: 0; }}
    .lt {{ position: absolute; left: {bar['x']}px; width: {bar['w']}px; }}
    .lt-bar {{ position: relative; overflow: hidden; background: {col['caption_bg']}; border-radius: {bar['radius']}px;
              padding: {bar['pad_y']}px {bar['pad_x']}px {bar['pad_y']}px {int(bar['pad_x']) + int(bar['notch'])}px;
              box-shadow: 0 10px 28px rgba(0,0,0,.28); clip-path: inset(0% 0% 0% 0%); }}
    .lt-bar::before {{ content: ""; position: absolute; left: 0; top: 0; bottom: 0; width: {bar['notch']}px; background: {emph_bg}; }}
    .lt-tx {{ font-family: '{fam}', sans-serif; font-size: {fs}px; font-weight: {cc['font_weight']}; line-height: 1.25;
             letter-spacing: {cc.get('letter_spacing', -1)}px; color: {col['caption_text']}; white-space: nowrap; }}
    .lt-em {{ position: relative; z-index: 0; color: #fff; }}
    .lt-em i {{ position: absolute; left: -8px; right: -8px; top: 6px; bottom: 4px; background: {emph_bg}; border-radius: 4px;
               z-index: -1; transform-origin: 0 50%; }}
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
