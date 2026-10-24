"""Tests for the doodle style additions (pure functions, no rendering)."""
import json
import os
import sys
from pathlib import Path

PIPE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PIPE))

import numpy as np  # noqa: E402

from graphics import doodle_kit as dk  # noqa: E402
from graphics.doodle_templates import DOODLE_TEMPLATES  # noqa: E402
from graphics.paper import paper_texture  # noqa: E402
from steps import compose, media  # noqa: E402
from steps.plan import Chunk, EWord, Segment  # noqa: E402

REF = json.loads((PIPE / "styles" / "reference.json").read_text(encoding="utf-8"))
DOODLE = json.loads((PIPE / "styles" / "doodle.json").read_text(encoding="utf-8"))


def _scene(dur=3.0, layout=(("split",),), first=False, **kw):
    events = [(0.0, "split"), (1.5, "graphic")]
    return dk.DoodleScene("sc1", dur, DOODLE["colors"], lambda a, d: d, events, first=first, board_h=902, **kw)


def test_rough_geometry_is_deterministic():
    a = dk.rough_rect(10, 10, 100, 50, dk._rng("x", 1))
    b = dk.rough_rect(10, 10, 100, 50, dk._rng("x", 1))
    c = dk.rough_rect(10, 10, 100, 50, dk._rng("x", 2))
    assert a == b and a != c
    assert a.startswith("M") and a.count("Q") == 4


def test_arrow_has_shaft_and_two_heads():
    paths = dk.arrow_paths(0, 0, 100, 0, dk._rng("a"))
    assert len(paths) == 3


def test_stroke_icon_tags_every_shape_for_draw_on():
    out = dk.stroke_icon("chart")
    assert out.count('class="dd-s"') == out.count("<")


def test_draw_and_write_emit_seek_safe_tweens():
    s = _scene()
    s.svg("box", [dk.rough_rect(0, 0, 10, 10, s.rng("b"))])
    s.text("t", 100, 100, "안녕")
    s.draw("box", 0.2)
    s.write("t", 0.5, 2)
    js = "\n".join(s.js)
    assert "strokeDashoffset:0" in js and 'clipPath:"inset(0% 0% 0% 0%)"' in js
    assert (0.0, "scribble") in s.events           # skeleton strokes are on the board from the cut
    assert 'tl.set("#sc1-box .dd-s",{strokeDashoffset:0},0);' in js


def test_opening_window_compresses_early_beats_only():
    s = _scene()
    assert s._opening(0.2, 0.5) == (0.2 * 0.3, s.OPEN_DUR)
    assert s._opening(0.8, 0.5) == (0.8, 0.5)
    assert _scene(first=True)._opening(0.2, 0.5) == (0.2, 0.5)


def test_times_are_clamped_inside_the_scene():
    s = _scene(dur=1.0)
    end = s.draw("x", 5.0, 0.3)
    assert end <= 1.0 - s.EXIT_GUARD + 1e-9         # finished before the exit starts


def test_build_has_board_kicker_tracker_and_eraser_exit():
    s = _scene()
    s.kicker = {"text": "업무 <span class=\"dd-acc\">3개</span>", "sub": "sub"}
    s.tracker = [("메모", "doc", "done"), ("메일", "mail", "active")]
    DOODLE_TEMPLATES["dd_keyword"](s, {"keyword": "핵심", "sub": "설명"})
    html = s.build(dk.doodle_css(DOODLE["colors"], DOODLE["fonts"], 902))
    assert 'class="dd-board"' in html and "sc1-kick-k1" in html
    assert 'opacity:0,x:-60' in html               # default 'lift' exit (sc1 -> slide-left variant), ends on the cut
    assert "Gaegu-Bold.ttf" in html


def test_eraser_exit_still_available():
    s = _scene()
    s.exit_style = "erase"
    assert any("inset(0% 0% 0% 100%)" in ln for ln in s.exit_js())


def test_every_template_builds_with_empty_params():
    for name, fn in DOODLE_TEMPLATES.items():
        s = _scene()
        fn(s, {})
        assert s.build(""), name


def test_paper_texture_shape_and_tone():
    img = paper_texture(64, 48, "#FAF7F0", "#E9E4D8", 16, seed=1)
    assert img.shape == (48, 64, 3) and img.dtype == np.uint8
    assert 230 < img.mean() < 252


def test_reference_captions_unchanged_without_new_keys():
    assert compose._caption_extra_css(REF["captions"], REF["colors"]) == ""
    assert compose._face_frame_cfg(REF) is None
    assert compose._motion_language(REF) == "ui_cards"


def test_marker_emphasis_css_and_tween():
    css = compose._caption_extra_css(DOODLE["captions"], DOODLE["colors"])
    assert ".mk" in css and DOODLE["colors"]["marker"] in css and ".chip" in css
    w = [EWord("AI", 0.5, 0.8, 0), EWord("도우미", 0.8, 1.1, 0)]
    c = Chunk(w, 0.5, 1.2, True, [True, False], 0.497)
    html = compose.captions_html([Chunk([EWord("시작", 0, .3, 0)], 0, .5, False, [False], .497), c], DOODLE, 2.0)
    assert '<span class="mk">AI</span>' in html and "backgroundSize" in html


def test_face_frame_toggles_only_on_split():
    segs = [Segment([], "split", 0, 0.0, 1.0), Segment([], "graphic", 0, 1.0, 2.0), Segment([], "split", 0, 2.0, 3.0)]
    html, js = compose.face_frame_html(segs, DOODLE)
    assert 'id="faceframe"' in html
    toggles = [j for j in js if j.startswith('tl.set("#faceframe",{opacity:')]
    assert [j.split("opacity:")[1][0] for j in toggles][:2] == ["1", "0"]
    assert not [j for j in js if "fromTo" in j and '"#faceframe"' in j]   # the panel itself never slides


def test_torn_edge_panel_is_full_bleed_with_tape_accents():
    assert DOODLE["layout"]["face_frame"]["edge"] == "torn"
    assert compose._split_photo_box(DOODLE)[0] == 0 and compose._split_photo_box(DOODLE)[2] == 1080
    segs = [Segment([], "split", 0, 0.0, 1.0), Segment([], "graphic", 0, 1.0, 2.0), Segment([], "split", 0, 2.0, 3.0)]
    html, js = compose.face_frame_html(segs, DOODLE)
    assert "drop-shadow" in html and html.count('class="ff-tape"') == 2
    joined = " ".join(js)
    assert "rotation:12" in joined                 # tape peels away on the board cut
    assert "scale:1.3" in joined                   # tape slaps down when the photo returns


def test_solid_text_motion_hierarchy():
    cfg = {**DOODLE["motion"]}
    s = _scene(cfg=cfg)
    s.text("t", 100, 100, "안녕")
    s.write("t", 0.8, 2)
    s.hero("t", 1.2)
    js = " ".join(s.js)
    assert "opacity:1,duration:.1" in js and "back.out(1.7)" in js        # secondary: quick fade + eased rise
    assert "scale:.45" in js and "scale:1.14" in js and "scale:.97" in js  # hero: overshoot and settle
    lift = " ".join(s.exit_js())
    assert "y:-110" in lift and "duration:.24" in lift                    # directional exit ending on the cut


def test_skeleton_parts_rise_in_staggered():
    s = _scene(cfg={**DOODLE["motion"]})
    s.svg("a", [dk.rough_rect(0, 0, 10, 10, s.rng("a"))])
    s.svg("b", [dk.rough_rect(0, 0, 10, 10, s.rng("b"))])
    s.draw("a", 0.0)
    s.draw("b", 0.0)
    js = " ".join(s.js)
    assert '{y:44},{y:0,duration:.34,ease:"back.out(1.6)"},0.000' in js and "0.050);" in js


def test_kicker_cards_and_sheet_exit():
    s = _scene(cfg={**DOODLE["motion"]})
    s.kicker = {"text": "결과", "cards": [{"title": "할 일", "lines": ["목록"], "mark": "check"}, {"title": "답장", "lines": ["초안"]}]}
    s.exit_style = "sheet"
    DOODLE_TEMPLATES["dd_keyword"](s, {"keyword": "핵심"})
    html = s.build(dk.doodle_css(DOODLE["colors"], DOODLE["fonts"], 902))
    assert "sc1-kick-c1" in html and 'class="dd-m"' in html and 'id="sc1-sheet"' in html
    assert "y:1960" in html


def test_body_floor_applies_to_sans_text():
    s = _scene(cfg={"min_body_px": 56, "min_hand_px": 64})
    s.text("a", 0, 0, "x", size=40, font="body")
    s.text("b", 0, 0, "x", size=40)
    body = "".join(s.body)
    assert "font-size:56px" in body and "font-size:64px" in body


def test_face_slide_settle_when_configured():
    style = {**DOODLE, "layout": {**DOODLE["layout"], "face_slide": {"dy": 0, "scale": .95, "out_s": .3, "out_dy": 900}}}
    segs = [Segment([], "split", 0, 0.0, 1.0), Segment([], "graphic", 0, 1.0, 2.0), Segment([], "split", 0, 2.0, 3.0)]
    js = compose._face_slide_js(segs, style, "#fb{i}")
    assert len(js) == 2 and "y:900" in js[0]


def test_face_slide_off_for_reference_style():
    segs = [Segment([], "split", 0, 0.0, 1.0), Segment([], "graphic", 0, 1.0, 2.0)]
    assert compose._face_slide_js(segs, REF, "#fb{i}") == []


def test_paper_sfx_kinds_synthesise():
    for kind in ("scribble", "marker", "erase", "paper"):
        x = media.synth(kind, 3)
        assert x.size > 1000 and np.isclose(np.max(np.abs(x)), 1.0)

