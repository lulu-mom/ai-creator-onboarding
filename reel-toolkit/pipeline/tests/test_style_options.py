"""Unit tests for the style-selected engine options (bold-talk and friends). No video needed."""
import json
import sys
from pathlib import Path

PIPE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PIPE))

from graphics.kinetic import big_size, slam  # noqa: E402
from graphics.scene import Scene  # noqa: E402
from graphics.templates import TEMPLATES  # noqa: E402
from steps import captions_karaoke as ck  # noqa: E402
from steps import media, overlay  # noqa: E402
from steps.plan import Chunk, EWord, ScenePlan, Segment, assign_layouts, is_number_word, make_chunks  # noqa: E402

BOLD = json.loads((PIPE / "styles" / "bold-talk.json").read_text(encoding="utf-8"))
REF = json.loads((PIPE / "styles" / "reference.json").read_text(encoding="utf-8"))


def _words(texts, step=0.3):
    return [EWord(t, round(i * step, 3), round(i * step + step - 0.02, 3), 0) for i, t in enumerate(texts)]


def test_number_words_detected():
    assert is_number_word(EWord("20%", 0, 1, 0))
    assert is_number_word(EWord("3가지", 0, 1, 0))
    assert not is_number_word(EWord("사과", 0, 1, 0))


def test_solo_numbers_get_their_own_caption():
    words = _words(["매출이", "20%", "늘었습니다"])
    chunks = make_chunks(words, {**BOLD["captions"], "solo_numbers": True}, 2.0)
    assert [c.text for c in chunks] == ["매출이", "20%", "늘었습니다"]


def test_without_solo_numbers_chunking_is_unchanged():
    words = _words(["매출이", "20%", "늘었습니다"])
    chunks = make_chunks(words, {**REF["captions"]}, 2.0)
    assert len(chunks) < 3


def _segs(n):
    words = _words([f"단어{i}" for i in range(n)])
    chunks = [Chunk([w], w.start, w.end) for w in words]
    segs = [Segment([c], start=c.start, end=c.end) for c in chunks]
    scenes = [ScenePlan(0, "blank", {}, first_chunk=0)]
    return words, chunks, segs, scenes


def test_default_face_layout_with_graphic_hint():
    words, chunks, segs, scenes = _segs(5)
    assign_layouts(segs, scenes, chunks, words, {"graphic": ["단어2"]}, BOLD["rhythm"], BOLD["layout"])
    assert [s.layout for s in segs] == ["face", "face", "graphic", "face", "face"]
    # consecutive face segments alternate punch-in so each boundary is a visible cut
    assert segs[0].punch != segs[1].punch


def test_split_style_still_starts_on_split():
    words, chunks, segs, scenes = _segs(3)
    assign_layouts(segs, scenes, chunks, words, None, REF["rhythm"], REF["layout"])
    assert segs[0].layout == "split"


def test_karaoke_fit_size_shrinks_long_lines():
    assert ck.fit_size(["짧다"], 104, 864, 1.12) == 104
    assert ck.fit_size(["아주아주긴", "캡션문장이", "들어왔습니다"], 104, 864, 1.12) < 104


def test_karaoke_html_marks_active_words_and_numbers():
    words = _words(["매출이", "20%"])
    c1, c2 = Chunk([words[0]], 0.0, 0.3, emph_words=[True]), Chunk([words[1]], 0.3, 0.6, emph_words=[False])
    for c in (c1, c2):
        c.y = 0.6
    doc, events = ck.captions_html([c1, c2], BOLD, 1.0)
    assert 'id="w0_0"' in doc and "paint-order: stroke fill" in doc
    assert f'font-size:{BOLD["captions"]["number_size"]}px' in doc
    assert (0.0, "pop") in events and any(k == "ding" for _, k in events)


def test_warning_words_use_warning_role():
    assert ck.word_role("안됩니다", False) == "warn"
    assert ck.word_role("메모장", True) == "keyword"


def test_stickers_resolve_and_do_not_overlap():
    words = _words(["첫", "번째", "단계", "두", "번째"], step=1.0)
    st = overlay.resolve_stickers([{"anchor": "첫 번째", "text": "a", "dur": 5},
                                   {"anchor": "두 번째", "text": "b"},
                                   {"anchor": "없는말", "text": "c"}], words, 10.0)
    assert [s["text"] for s in st] == ["a", "b"]
    assert st[0]["t1"] <= st[1]["t0"]


def test_flash_only_on_graphic_boundaries():
    segs = [Segment([], "face", start=0, end=1), Segment([], "face", start=1, end=2),
            Segment([], "graphic", start=2, end=3), Segment([], "face", start=3, end=4)]
    assert overlay.flash_times(segs) == [2, 3]


def test_fx_html_uses_style_sticker_top():
    doc, events = overlay.fx_html([{"text": "x", "t0": 0.5, "t1": 2.0}], [1.0], BOLD, 3.0)
    assert f"top: {BOLD['motion']['sticker_top']}px" in doc and events == [(0.5, "pop")]


def test_grade_filter_default_and_style():
    assert media.grade_filter(REF) == media.GRADE
    assert "contrast=1.12" in media.grade_filter(BOLD)


def test_kinetic_slam_is_fullscreen_with_exit():
    assert "slam" in TEMPLATES and "blank" in TEMPLATES
    s = Scene("sc1", 4.0, BOLD["colors"], lambda a, d: d, [(0.0, "graphic"), (1.2, "face")])
    slam(s, {"big": "AI 도우미 <span class=\"rk-acc\">3명</span>", "icons": [{"icon": "doc", "label": "메모"}]})
    out = s.build("")
    assert s.fullscreen and "rk-stage" not in out
    assert 'tl.fromTo("#sc1-w0"' in out and "x:-1080" in out   # not the hook: words build in; card pushes out
    assert s.graphic_window() == (0.0, 1.2)


def test_card_scenes_keep_their_stage():
    s = Scene("sc0", 2.0, REF["colors"], lambda a, d: d, [(0.0, "split")])
    TEMPLATES["keyword"](s, {"keyword": "x"})
    assert "rk-stage" in s.build("")


def test_big_size_bounds():
    assert big_size("짧게") == 140
    assert 96 <= big_size("아주 길고 긴 헤드라인 문장입니다 정말로") < 140


def test_bound_noun_and_negative_auxiliary_do_not_start_a_caption():
    words = _words(["정말", "어른", "두", "명", "몫까지"])
    chunks = make_chunks(words, {**BOLD["captions"]}, 3.0)
    assert not any(c.text.startswith("몫") for c in chunks)


def test_hook_card_shows_first_line_on_frame_0():
    s = Scene("sc0", 3.0, BOLD["colors"], lambda a, d: d, [(0.0, "graphic"), (1.5, "face")], first=True)
    slam(s, {"tag": "t", "big": "바로 보내면<br>큰일", "hero": True})
    out = s.build("")
    assert "sc0-w0" in out and 'tl.fromTo("#sc0-w0"' not in out    # line 1 is static on frame 0
    assert 'tl.fromTo("#sc0-w2"' in out                            # line 2 builds in


def test_caption_fixes_replace_asr_words():
    from steps.plan import fix_caption_words
    c = Chunk(_words(["바뀌지", "않을"]))
    fix_caption_words([c], {"않을": "않은"})
    assert c.text == "바뀌지 않은"


def test_caption_phrases_force_meaning_breaks():
    words = _words(["메모를", "주고", "무엇을", "언제", "어디서", "할지만", "정리하라고"], step=0.2)
    chunks = make_chunks(words, {**BOLD["captions"]}, 2.0, ["무엇을 언제 어디서 할지만"])
    assert "무엇을 언제 어디서 할지만" in [c.text for c in chunks]


def test_graphic_hint_can_target_one_occurrence():
    words, chunks, segs, scenes = _segs(4)
    words[3].text = chunks[3].words[0].text = "단어0"
    assign_layouts(segs, scenes, chunks, words, {"graphic": [{"anchor": "단어0", "occurrence": 2}]},
                   BOLD["rhythm"], BOLD["layout"])
    assert [s.layout for s in segs] == ["face", "face", "face", "graphic"]


def test_long_captions_wrap_to_two_lines_instead_of_shrinking():
    words = ["무엇을", "언제", "할지", "정리하고", "확인하고", "보냈습니다"]
    lines = ck.split_lines(words, 104, 864, 2, 0.85)
    assert len(lines) == 2 and sum(len(ln) for ln in lines) == len(words)
    assert ck.split_lines(["짧은", "말"], 104, 864, 2, 0.85) == [[0, 1]]


def test_graphic_window_spans_all_graphic_runs():
    s = Scene("sc2", 6.0, BOLD["colors"], lambda a, d: d, [(0.0, "graphic"), (1.0, "face"), (2.0, "graphic"), (3.0, "face")])
    assert s.graphic_window() == (0.0, 3.0)


# ---------------------------------------------------------------- round 2: floating panel
def _panel_scene(events, dur=4.0, **kw):
    s = Scene("sc3", dur, BOLD["colors"], lambda a, d: d, events)
    for k, v in kw.items():
        setattr(s, k, v)
    return s


def test_scene_layout_param_sets_panel_segments():
    words, chunks, segs, _ = _segs(4)
    scenes = [ScenePlan(0, "blank", {}, first_chunk=0), ScenePlan(1, "panel", {"layout": "split"}, first_chunk=2)]
    assign_layouts(segs, scenes, chunks, words, None, BOLD["rhythm"], BOLD["layout"])
    assert [s.layout for s in segs] == ["face", "face", "split", "split"]
    # panel segments reframe only per scene, not per segment
    assert segs[2].punch == segs[3].punch


def test_panel_exit_ends_on_the_cut_before_a_face_beat():
    from graphics.panel import panel
    s = _panel_scene([(0.0, "split"), (3.0, "face")])
    panel(s, {"role": "setup", "tag": "t", "big": "a <span class=\"rk-acc\">b</span>",
              "lines": [{"text": "x"}, {"text": "y", "at": "y"}]})
    js = "\n".join(s.js)
    assert 'tl.set("#sc3-wrap",{opacity:0},3.000)' in js     # hidden exactly on the cut
    assert "y:-1040" in js                                     # setup panels push out of the top
    assert s.tail == 0.0                                       # nothing plays over the full-frame speaker


def test_panel_swap_kinds():
    from graphics.panel import panel
    out = _panel_scene([(0.0, "split")], swap_out=True, next_params={"role": "result"})
    panel(out, {"role": "result", "tag": "t", "big": "a"})
    assert 'tl.to("#sc3-in",{y:-34' in "\n".join(out.js)      # result -> result: content swap in place
    flip = _panel_scene([(0.0, "split")], swap_out=True, next_params={"role": "warn"})
    panel(flip, {"role": "setup", "tag": "t", "big": "a"})
    assert "rotationX:-70" in "\n".join(flip.js)               # any other pair flips (max 70 deg)


def test_sticker_windows_include_panels():
    segs = [Segment([], "face", start=0, end=1), Segment([], "split", start=1, end=2), Segment([], "graphic", start=2, end=3)]
    assert overlay.graphic_windows(segs) == [(1, 2), (2, 3)]


def test_custom_warn_words():
    assert ck.word_role("않은", False) == "warn"
    assert ck.word_role("않은", False, ["금지"]) == "plain"
