"""Step 5-6: write the HyperFrames project (layouts, face reframe, cards, captions)."""
from __future__ import annotations

import html
import json
import os
import shutil
import stat
from pathlib import Path

import re

import numpy as np

from graphics import newsdesk
from graphics.doodle_kit import DoodleScene, doodle_css, rough_rect
from graphics.doodle_templates import DOODLE_TEMPLATES
from graphics.paper import write_paper
from graphics.scene import OVERLAP, Scene, shared_css, stage_geometry
from graphics.templates import TEMPLATES

from .cut import EditMap
from .face_track import face_path
from .plan import Chunk, ScenePlan, Segment, anchor_resolver

W, H = 1080, 1920
STRIP = re.compile(r"[.,!…~\"'“”]+")
FONT_DIR = Path(__file__).resolve().parents[1] / "assets" / "fonts"


class FaceCropper:
    def __init__(self, track: dict, em: EditMap, vid_w: int, vid_h: int):
        self.t, self.v = face_path(track)
        self.em = em
        self.vw, self.vh = vid_w, vid_h

    def at(self, t_edit: float) -> tuple[float, float, float]:
        ts = self.em.to_source(t_edit)
        return tuple(float(np.interp(ts, self.t, self.v[:, c])) for c in range(3))

    def place(self, t_edit: float, box: tuple[int, int], scale: float, anchor_y: float):
        """Return (left, top, width, height) of the video element inside the box."""
        bw, bh = box
        fx, fy, _ = self.at(t_edit)
        s = max(scale * bw / self.vw, bh / self.vh)  # cover the box
        vw, vh = self.vw * s, self.vh * s
        left = min(0.0, max(bw - vw, bw / 2 - fx * vw))
        top = min(0.0, max(bh - vh, bh * anchor_y - fy * vh))
        return left, top, vw, vh


def write_avatar(face_mp4: Path, crop: FaceCropper, out_jpg: Path, t: float = 1.0) -> None:
    """Square face crop of the speaker, used inside cards (profile chips, reviewer avatar)."""
    from .media import ffmpeg_bin, run
    fx, fy, fh = crop.at(t)
    side = min(crop.vw, crop.vh, int(fh * crop.vh * 1.7))
    x = int(min(max(0, fx * crop.vw - side / 2), crop.vw - side))
    y = int(min(max(0, fy * crop.vh - side * 0.55), crop.vh - side))
    run([ffmpeg_bin(), "-y", "-v", "error", "-ss", f"{t:.2f}", "-i", str(face_mp4), "-frames:v", "1",
         "-vf", f"crop={side}:{side}:{x}:{y},scale=240:240", "-q:v", "3", str(out_jpg)])


def _layout_box(seg: Segment, style: dict) -> tuple[int, int, int] | None:
    seam = int(round(style["layout"]["seam_y"] * H))
    if seg.layout == "split":
        return 0, seam, H - seam
    if seg.layout == "face":
        top = int(style["layout"].get("face_full_top", 0))   # e.g. below a fixed title bar
        return 0, top, H - top
    if seg.layout == "graphic" and style["layout"].get("face_under_graphic"):
        # speaker keeps playing under full-screen cards so cards can move in/out over the face
        return 0, 0, H
    return None


def _face_frame_cfg(style: dict) -> dict | None:
    """Optional layout.face_frame: the split-layout face sits inside a taped photo frame."""
    return style["layout"].get("face_frame")


def _split_photo_box(style: dict) -> tuple[int, int, int, int]:
    """(left, top, width, height) of the face photo in the split layout when framed."""
    ff = _face_frame_cfg(style) or {}
    seam = int(round(style["layout"]["seam_y"] * H))
    inset, gap = int(ff.get("inset", 0)), int(ff.get("top_gap", 0))
    return inset, seam + gap, W - 2 * inset, H - seam - gap - inset


def _split_fade(sg: Segment, style: dict) -> str:
    """Optional dark gradient over the top edge of the speaker box in the split layout
    (layout.split_fade px), so a floating panel above it blends into the backdrop."""
    fade = int(style["layout"].get("split_fade", 0) or 0)
    if sg.layout != "split" or not fade:
        return ""
    bg = style["colors"]["background"]
    return (f'<div style="position:absolute;left:0;top:0;width:1080px;height:{fade}px;'
            f'background:linear-gradient({bg},{bg}00)"></div>')


def face_clips(segs: list[Segment], crop: FaceCropper, style: dict) -> tuple[str, list[str]]:
    lay = style["layout"]
    push_to = lay.get("push_in_to", 1.035)   # slow push-in per talking-head segment (1.0 = steady framing)
    out, js = [], []
    z = 2
    for i, sg in enumerate(segs):
        box = _layout_box(sg, style)
        if box is None:
            continue
        _, top_px, bh = box
        left_px, bw = 0, W
        if sg.layout == "split" and _face_frame_cfg(style):
            left_px, top_px, bw, bh = _split_photo_box(style)
        if sg.layout == "split":
            zoom, ay = lay["split_zoom"] * sg.punch, lay["face_split_anchor_y"]
        else:
            zoom, ay = lay["full_zoom"] * sg.punch, lay["face_full_anchor_y"]
        l0, t0, vw, vh = crop.place(sg.start + 0.05, (bw, bh), zoom, ay)
        l1, t1, _, _ = crop.place(max(sg.start + 0.05, sg.end - 0.05), (bw, bh), zoom, ay)
        dur = round(sg.end - sg.start, 3)
        geo = f"left:{left_px}px;width:{bw}px;" if bw != W else ""
        fb_id = f' id="fb{i}"' if lay.get("face_slide") else ""
        out.append(
            f'<div class="facebox"{fb_id} style="{geo}top:{top_px}px;height:{bh}px;z-index:{0 if sg.layout == "graphic" else z}">'
            f'<div class="facezoom" id="fz{i}" style="transform-origin:50% {ay * 100:.0f}%">'
            f'<div class="facepan" id="pan{i}">'
            f'<video id="v{i}" class="clip" src="assets/face.mp4" data-start="{sg.start:.3f}" data-duration="{dur:.3f}" '
            f'data-media-start="{sg.start:.3f}" data-track-index="2" muted playsinline '
            f'style="position:absolute;left:{l0:.1f}px;top:{t0:.1f}px;width:{vw:.1f}px;height:{vh:.1f}px"></video>'
            f'</div></div>{_split_fade(sg, style)}</div>')
        dx, dy = l1 - l0, t1 - t0
        # face follow + a slow push-in (1.0 -> 1.035) so talking-head stretches never sit still
        kp = float(lay.get("keyword_punch", 0) or 0)
        if kp:
            for c in sg.chunks:
                for w, m in zip(c.words, c.emph_words or [c.emph] * len(c.words)):
                    if m and sg.start + 0.2 < w.start < sg.end - 0.35:
                        js.append(f'tl.to("#fz{i}",{{scale:{kp},duration:.12,ease:"power2.out",yoyo:true,repeat:1}},{w.start:.3f});')
        rp = float(lay.get("return_punch", 0) or 0)
        rp_from = lay.get("return_punch_from") or ["graphic"]
        if rp and i and segs[i - 1].layout in rp_from and sg.layout == "face":
            # back on the speaker after a full-screen card: a short punch-in settle
            js.append(f'tl.fromTo("#fz{i}",{{scale:{rp}}},{{scale:1,duration:.3,ease:"power2.out"}},{sg.start:.3f});')
        js.append(f'tl.fromTo("#pan{i}",{{x:0,y:0,scale:1}},{{x:{dx:.1f},y:{dy:.1f},scale:{push_to},duration:{dur:.3f},ease:"none"}},{sg.start:.3f});')
    return "\n      ".join(out), js


def face_frame_html(segs: list[Segment], style: dict) -> tuple[str, list[str]]:
    """Pencil border + two tape strips around the split-layout photo, shown only on split beats."""
    ff = _face_frame_cfg(style)
    if not ff:
        return "", []
    import numpy as _np
    x, y, w, h = _split_photo_box(style)
    col = style["colors"]
    tape = ff.get("tape_color", "rgba(236,222,180,.82)")
    torn = ff.get("edge") == "torn"
    if torn:
        # full-bleed panel: the board's paper edge is torn and lies over the top of the photo
        art = _torn_edge_svg(y, col.get("background", "#FAF7F0"), int(ff.get("seed", 5)))
        tape_pos = [(tx - 80, rot) for tx, rot in zip(ff.get("tape_x", [110, 970]), (-5, 5))]
        tape_top, tape_w, tape_h = y - 24, 160, 50
    else:
        ink = col.get(ff.get("border", "ink"), ff.get("border", "#2B2B2B"))
        border = rough_rect(x - 6, y - 6, w + 12, h + 12, _np.random.default_rng(11), 3.0)
        art = (f'<svg viewBox="0 0 {W} {H}" style="position:absolute;left:0;top:0;width:{W}px;height:{H}px" fill="none" '
               f'stroke="{ink}" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"><path d="{border}"/></svg>')
        tape_pos = [(x + 40, -8), (x + w - 210, 7)]
        tape_top, tape_w, tape_h = y - 26, 170, 54
    tapes = "".join(
        f'<div class="ff-tape" style="position:absolute;left:{tx}px;top:{tape_top}px;width:{tape_w}px;height:{tape_h}px;'
        f'rotate:{rot}deg"><div class="ff-tp" style="width:100%;height:100%;background:{tape};'
        f'box-shadow:0 2px 4px rgba(80,60,30,.12)"></div></div>'
        for tx, rot in tape_pos) if ff.get("tape", True) else ""
    html_ = (f'<div id="faceframe" style="position:absolute;inset:0;z-index:4;pointer-events:none;opacity:0">'
             f'{art}{tapes}</div>')
    js, state = [], None
    for sg in segs:
        want = 1 if sg.layout == "split" else 0
        if want != state:
            t = max(0.0, sg.start)
            js.append(f'tl.set("#faceframe",{{opacity:{want}}},{t:.3f});')
            if torn and ff.get("tape", True) and state is not None and t > 0.01:
                js += _tape_motion_js(want, t)
            state = want
    js += _face_slide_js(segs, style, "#faceframe")
    return html_, js


def _torn_edge_svg(y: int, paper: str, seed: int) -> str:
    """Torn paper edge (board paper over the photo top) with a soft shadow."""
    import numpy as _np
    rng = _np.random.default_rng(seed)
    xs = _np.linspace(-10, W + 10, 64)
    ys = y + 4 + rng.uniform(2, 14, len(xs)) + 3 * _np.sin(xs / 37.0)
    pts = " ".join(f"L{px:.1f} {py:.1f}" for px, py in zip(xs[::-1], ys[::-1]))
    d = f"M-10 {y - 2} L{W + 10} {y - 2} {pts} Z"
    return (f'<svg viewBox="0 0 {W} {H}" style="position:absolute;left:0;top:0;width:{W}px;height:{H}px;'
            f'filter:drop-shadow(0 5px 5px rgba(60,45,20,.28))"><path d="{d}" fill="{paper}"/></svg>')


def _tape_motion_js(want: int, t: float) -> list[str]:
    """Designed accents on the face <-> board hard cut: tape slaps down on the photo's return,
    peels up and away when the board takes over (the panel itself always switches on the cut)."""
    if want:
        return [f'tl.fromTo("#faceframe .ff-tp",{{scale:1.3,rotation:-4}},{{scale:1,rotation:0,duration:.14,'
                f'ease:"power3.out"}},{t:.3f});']
    return [f'tl.set("#faceframe",{{opacity:1}},{t:.3f});',
            f'tl.fromTo("#faceframe .ff-tp",{{y:0,rotation:0,opacity:1}},{{y:-34,rotation:12,opacity:0,duration:.1,'
            f'ease:"power2.in"}},{t:.3f});',
            f'tl.set("#faceframe svg",{{opacity:0}},{t:.3f});',
            f'tl.set("#faceframe",{{opacity:0}},{t + .11:.3f});',
            f'tl.set("#faceframe svg, #faceframe .ff-tp",{{opacity:1,y:0,rotation:0}},{t + .12:.3f});']


def _face_slide_js(segs: list[Segment], style: dict, target_fmt: str) -> list[str]:
    """layout.face_slide: after a full-graphic beat the split-layout photo comes back with a hard cut
    and a short drop-and-settle (dy px + scale), so the switch reads as designed but stays a visible cut.
    With out_s > 0 it also slides down out of frame before the next full-graphic beat.
    `target_fmt` may contain {i} for the segment index."""
    cfg = style["layout"].get("face_slide")
    if not cfg:
        return []
    dy, t_out, t_in = int(cfg.get("dy", 60)), float(cfg.get("out_s", 0.0)), float(cfg.get("in_s", 0.32))
    sc = float(cfg.get("scale", 1.0))
    out_dy = int(cfg.get("out_dy", dy))
    js = []
    for i, sg in enumerate(segs):
        if sg.layout != "split":
            continue
        tgt = target_fmt.format(i=i)
        prev_g = i > 0 and segs[i - 1].layout == "graphic"
        next_g = i + 1 < len(segs) and segs[i + 1].layout == "graphic"
        if prev_g:
            js.append(f'tl.fromTo("{tgt}",{{y:{-dy},scale:{sc}}},{{y:0,scale:1,duration:{t_in},ease:"power3.out",'
                      f'immediateRender:false}},{sg.start:.3f});')
        if next_g and t_out > 0 and sg.dur > t_out + 0.3:
            js.append(f'tl.fromTo("{tgt}",{{y:0}},{{y:{out_dy},duration:{t_out},ease:"power2.in",immediateRender:false}},{sg.end - t_out:.3f});')
    return js


def _caption_extra_css(cc: dict, col: dict) -> str:
    """CSS for the optional captions.box / captions.emphasis(marker) settings ('' when unused)."""
    out = ""
    box = cc.get("box")
    if box:
        out += ("\n    .chip { background: %s; border-radius: %spx; box-shadow: %s; border: %s; }"
                % (box.get("bg", col["caption_bg"]), box.get("radius", cc["radius"]),
                   box.get("shadow", "none"), box.get("border", "none")))
        if box.get("word_spacing"):
            out += " .chip { word-spacing: %spx; }" % box["word_spacing"]
    emph = cc.get("emphasis") or {}
    if emph.get("method") == "marker":
        mk = col.get(emph.get("color", "marker"), emph.get("color", "#FFE066"))
        txt = col.get(emph.get("text", "caption_text"), col["caption_text"])
        out += ("\n    .mk { color: %s; background-image: linear-gradient(transparent 50%%, %s 50%%, %s 94%%, transparent 94%%); "
                "background-repeat: no-repeat; background-position: 0 0; background-size: 100%% 100%%; "
                "padding: 0 4px; margin: 0 -4px; }" % (txt, mk, mk))
    return out


def captions_html(chunks: list[Chunk], style: dict, duration: float) -> str:
    cc, col = style["captions"], style["colors"]
    if cc.get("style") == "lower_third":
        return newsdesk.lower_third_captions(chunks, style, duration)
    fam = style["font"]["family"]
    groups, js = [], []
    box = cc.get("box")                                   # optional chip override (e.g. paper strip)
    marker = (cc.get("emphasis") or {}).get("method") == "marker"
    chip_h = cc["font_size"] * 1.25 + 2 * cc["pad_y"]
    for i, c in enumerate(chunks):
        if not c.text:
            continue
        dur = max(0.1, c.end - c.start)
        top = c.y * H - chip_h / 2
        marks = c.emph_words or [c.emph] * len(c.words)
        parts = []
        for w, m in zip(c.words, marks):
            wt = html.escape(STRIP.sub("", w.text))
            if not wt:
                continue
            if m and marker:
                parts.append(f'<span class="mk">{wt}</span>')
            else:
                parts.append(f'<span style="color:{col["caption_emph"]}">{wt}</span>' if m else wt)
        inner = " ".join(parts)
        tilt = ""
        if box and box.get("tilt_deg"):
            tilt = f";rotate:{box['tilt_deg'] * (1 if i % 2 else -1):.2f}deg"
        groups.append(
            f'<div id="cg{i}" class="clip cg" data-start="{c.start:.3f}" data-duration="{dur:.3f}" data-track-index="0" '
            f'style="top:{top:.0f}px"><span class="chip" id="cc{i}" style="color:{col["caption_text"]}{tilt}">{inner}</span></div>')
        if c.start < 0.05:
            continue
        js.append(f'tl.fromTo("#cc{i}",{{scale:.9,y:8}},{{scale:1,y:0,duration:.16,ease:"back.out(2.5)"}},{c.start:.3f});')
        if marker and any(marks):
            # highlighter swipe drawn behind the key word, just after the chip lands
            js.append(f'tl.fromTo("#cc{i} .mk",{{backgroundSize:"0% 100%"}},{{backgroundSize:"100% 100%",duration:.3,'
                      f'ease:"power2.out"}},{c.start + 0.1:.3f});')
    body = "\n    ".join(groups)
    jsb = "\n    ".join(js)
    return f"""<template>
  <style>
    @font-face {{ font-family: '{fam}'; src: url('assets/fonts/PretendardVariable.ttf') format('truetype'); font-weight: 100 900; }}
    #root {{ position: absolute; inset: 0; }}
    .cg {{ position: absolute; left: 0; width: 1080px; text-align: center; }}
    .chip {{ display: inline-block; font-family: '{fam}', sans-serif; font-size: {cc['font_size']}px; font-weight: {cc['font_weight']};
            line-height: 1.25; letter-spacing: -1px; background: {col['caption_bg']}; padding: {cc['pad_y']}px {cc['pad_x']}px;
            border-radius: {cc['radius']}px; white-space: nowrap; }}{_caption_extra_css(cc, col)}
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


def _subset_style_fonts(out_dir: Path, style: dict, text: str) -> None:
    """Fonts flagged "subset": true keep only the glyphs used by the scenes (+ printable ASCII),
    so large CJK hand fonts do not slow down page loads in the renderer."""
    for f in (style.get("fonts") or {}).values():
        if not f.get("subset") or not f.get("file"):
            continue
        from fontTools import subset
        path = out_dir / "assets" / "fonts" / f["file"]
        chars = set(re.sub(r"<[^>]+>", "", text)) | {chr(c) for c in range(32, 127)}
        opts = subset.Options()
        opts.layout_features = ["*"]
        font = subset.load_font(str(path), opts)
        sub = subset.Subsetter(opts)
        sub.populate(text="".join(sorted(chars)))
        sub.subset(font)
        subset.save_font(font, str(path), opts)


def _motion_language(style: dict) -> str:
    return (style.get("motion") or {}).get("language", "ui_cards")


def scene_files(scenes: list[ScenePlan], words, style: dict, plan_doc: dict | None = None) -> tuple[list[tuple[ScenePlan, str, str]], list]:
    geo = stage_geometry(style.get("layout"))
    doodle = _motion_language(style) == "doodle"
    board_h = int(round(style["layout"]["seam_y"] * H))
    if doodle:
        css = doodle_css(style["colors"], style.get("fonts") or {"body": style["font"]}, board_h)
        templates = {**TEMPLATES, **DOODLE_TEMPLATES}
    else:
        css = shared_css(style["colors"], style["font"]["family"], geo,
                         "\n".join((style.get("graphics") or {}).get("extra_css") or []))
        templates = TEMPLATES
    files, events = [], []

    def ends_split(sc):
        return bool(sc.layout_events) and sc.layout_events[-1][1] == "split"

    def starts_split(sc):
        return bool(sc.layout_events) and sc.layout_events[0][1] == "split" and sc.layout_events[0][0] < 0.01
    for k, sc in enumerate(scenes):
        sid = f"sc{sc.idx}"
        dur = round(sc.end - sc.start, 3)
        args = (sid, dur, style["colors"], anchor_resolver(words, sc), sc.layout_events)
        if doodle:
            s = DoodleScene(*args, first=sc.idx == 0, geo=geo, board_h=board_h, cfg=style.get("motion"))
            s.exit_style = sc.params.get("exit", (style.get("motion") or {}).get("default_exit", "lift"))
        else:
            s = Scene(*args, first=sc.idx == 0, geo=geo)
        s.enter_style = sc.params.get("enter", "push")
        s.exit_override = (style.get("graphics") or {}).get("exit")
        s.last = sc.idx == len(scenes) - 1
        # floating panels: consecutive panel scenes swap content in place instead of exit + entrance
        nxt = scenes[k + 1] if k + 1 < len(scenes) else None
        prv = scenes[k - 1] if k else None
        s.swap_in = bool(prv and ends_split(prv) and starts_split(sc) and prv.template == sc.template)
        s.swap_out = bool(nxt and ends_split(sc) and starts_split(nxt) and nxt.template == sc.template)
        s.prev_params = prv.params if prv else {}
        s.next_params = nxt.params if nxt else {}
        s.kicker = sc.params.get("kicker")
        items = (plan_doc or {}).get("tracker_items") or []
        states = sc.params.get("tracker")
        s.tracker = [(it["label"], it.get("icon", "doc"), st) for it, st in zip(items, states)] if states else None
        fn = templates.get(sc.template, templates["keyword"])
        fn(s, sc.params)
        files.append((sc, sid, s.build(css), s.tail))
        events += [(sc.start + t, k) for t, k in s.events if k != "none"]
    return files, events


def _write_fx(out_dir: Path, segs, words, style: dict, duration: float, plan_doc: dict | None,
              events: list) -> str:
    """Optional FX overlay (stickers + cut flashes); returns its host markup or ''."""
    from .overlay import flash_times, fx_html, graphic_windows, resolve_stickers
    stickers = resolve_stickers((plan_doc or {}).get("stickers") or [], words, duration, graphic_windows(segs))
    flashes = flash_times(segs) if (style.get("transitions") or {}).get("flash_on_layout_change") else []
    if not stickers and not flashes:
        return ""
    doc, fx_events = fx_html(stickers, flashes, style, duration)
    events += fx_events
    (out_dir / "compositions" / "fx.html").write_text(doc, encoding="utf-8")
    return (f'<div id="fx" data-composition-id="fx" data-composition-src="compositions/fx.html" data-start="0" '
            f'data-duration="{duration:.3f}" data-track-index="5" data-track-kind="graphics" data-width="1080" '
            f'data-height="1920" style="z-index:4"></div>')


def write_project(out_dir: Path, face_mp4: Path, segs, chunks, scenes, words, crop: FaceCropper,
                  style: dict, duration: float, plan_doc: dict | None = None) -> list:
    if out_dir.exists():
        shutil.rmtree(out_dir, onexc=lambda fn, path, exc: (os.chmod(path, stat.S_IWRITE), fn(path)))
    (out_dir / "compositions").mkdir(parents=True)
    (out_dir / "assets" / "fonts").mkdir(parents=True)
    shutil.copyfile(FONT_DIR / "PretendardVariable.ttf", out_dir / "assets" / "fonts" / "PretendardVariable.ttf")
    for f in (style.get("fonts") or {}).values():          # extra style fonts (OFL), e.g. a hand font
        if f.get("file") and f["file"] != "PretendardVariable.ttf":
            shutil.copyfile(FONT_DIR / f["file"], out_dir / "assets" / "fonts" / f["file"])
    bg_css = style["colors"]["background"]
    if (style.get("background") or {}).get("texture") == "paper":
        write_paper(out_dir / "assets" / "paper.png", W, H, style["background"], style["colors"])
        bg_css = f"{style['colors']['background']} url('assets/paper.png') 0 0 / {W}px {H}px no-repeat"
    shutil.copyfile(face_mp4, out_dir / "assets" / "face.mp4")

    write_avatar(face_mp4, crop, out_dir / "assets" / "avatar.jpg")
    files, events = scene_files(scenes, words, style, plan_doc)
    hosts = []
    host_z = int((style.get("graphics") or {}).get("host_z", 1))
    for sc, sid, src, tail in files:
        (out_dir / "compositions" / f"{sid}.html").write_text(src, encoding="utf-8")
        hosts.append(
            f'<div id="{sid}" data-composition-id="{sid}" data-composition-src="compositions/{sid}.html" '
            f'data-start="{sc.start:.3f}" data-duration="{min(duration, sc.end + max(OVERLAP, tail)) - sc.start:.3f}" data-track-index="1" '
            f'data-track-kind="graphics" data-width="1080" data-height="1920" style="z-index:{host_z}"></div>')
    if style["captions"].get("mode", "chunk") == "word_karaoke":
        from .captions_karaoke import captions_html as karaoke_html
        cap_doc, cap_events = karaoke_html(chunks, style, duration)
        events += cap_events
    else:
        cap_doc = captions_html(chunks, style, duration)
    (out_dir / "compositions" / "captions.html").write_text(cap_doc, encoding="utf-8")
    fx_host = _write_fx(out_dir, segs, words, style, duration, plan_doc, events)
    _subset_style_fonts(out_dir, style, "".join(f[2] for f in files))
    overlay_host = ""
    if (style.get("overlays") or {}).get("newsdesk"):
        src, ov_events = newsdesk.overlay_html(style, plan_doc or {}, words, duration)
        (out_dir / "compositions" / "newsdesk.html").write_text(src, encoding="utf-8")
        events += ov_events
        overlay_host = ("\n      " f'<div id="newsdesk" data-composition-id="newsdesk" data-composition-src="compositions/newsdesk.html" '
                        f'data-start="0" data-duration="{duration:.3f}" data-track-index="4" data-track-kind="graphics" '
                        f'data-width="1080" data-height="1920" style="z-index:4"></div>')
    faces, pan_js = face_clips(segs, crop, style)
    pan_js += _face_slide_js(segs, style, "#fb{i}")
    frame_html, frame_js = face_frame_html(segs, style)
    faces += frame_html
    pan_js += frame_js
    bg = style["colors"]["background"]
    index = f"""<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=1080, height=1920" />
    <script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
    <style>
      * {{ margin: 0; padding: 0; box-sizing: border-box; }}
      html, body {{ margin: 0; width: 1080px; height: 1920px; overflow: hidden; background: {bg}; }}
      #root {{ position: relative; width: 100%; height: 100%; overflow: hidden; }}
      #bg {{ position: absolute; inset: 0; background: {bg_css}; z-index: 0; }}
      .facebox {{ position: absolute; left: 0; width: 1080px; overflow: hidden; }}
      .facepan, .facezoom {{ position: absolute; inset: 0; }}
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="{duration:.3f}" data-width="1080" data-height="1920" data-fps="30">
      <div id="bg"></div>
      {chr(10).join('      ' + h for h in hosts)}
      {faces}{overlay_host}
      <div id="captions" data-composition-id="captions" data-composition-src="compositions/captions.html" data-start="0"
           data-duration="{duration:.3f}" data-track-index="3" data-track-kind="captions" data-width="1080" data-height="1920" style="z-index:5"></div>
      {fx_host}
    </div>
    <script>
      window.__timelines = window.__timelines || {{}};
      const tl = gsap.timeline({{ paused: true }});
      {chr(10).join('      ' + j for j in pan_js)}
      tl.set({{}},{{}},{duration:.3f});
      window.__timelines["main"] = tl;
    </script>
  </body>
</html>
"""
    (out_dir / "index.html").write_text(index, encoding="utf-8")
    (out_dir / "hyperframes.json").write_text(json.dumps({
        "$schema": "https://hyperframes.heygen.com/schema/hyperframes.json",
        "paths": {"blocks": "compositions", "components": "compositions/components", "assets": "assets"},
        "media": {"autoProxy": True}}, indent=2), encoding="utf-8")
    (out_dir / "meta.json").write_text(json.dumps({"id": out_dir.name, "name": out_dir.name}), encoding="utf-8")
    return events
