"""Tests for the opt-in news-brief engine options (stage geometry, lower-third captions,
newsdesk overlay) and that the default split-card style output is unchanged."""
import json
import sys
from pathlib import Path

PIPE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PIPE))

from graphics import newsdesk  # noqa: E402
from graphics.scene import Scene, shared_css, stage_geometry  # noqa: E402
from steps import compose  # noqa: E402
from steps.plan import Chunk, EWord, Segment  # noqa: E402

REF = json.loads((PIPE / "styles" / "reference.json").read_text(encoding="utf-8"))
NEWS = json.loads((PIPE / "styles" / "news-brief.json").read_text(encoding="utf-8"))


def _words():
    texts = ["그런데", "이건", "첫", "번째", "단계에서는", "메모장을", "주고"]
    return [EWord(t, i * 0.5, i * 0.5 + 0.4, 0 if i < 2 else 1) for i, t in enumerate(texts)]


def _chunks():
    w = _words()
    a = Chunk(w[:2], start=0.0, end=1.0, emph_words=[False, True], emph=True, y=0.605)
    b = Chunk(w[2:5], start=1.0, end=2.5, emph_words=[False, False, False], y=0.605)
    c = Chunk(w[5:], start=3.0, end=3.5, emph_words=[True, False], emph=True, y=0.605)
    return [a, b, c]


# ------------------------------------------------------------------ defaults unchanged
def test_stage_geometry_defaults_match_constants():
    g = stage_geometry(REF["layout"])
    assert g == {"split_cy": 478, "graphic_cy": 740, "graphic_scale": 1.08, "fit_max_h": 700, "kicker_top": 1040}


def test_default_css_has_original_stage_and_kicker():
    css = shared_css(REF["colors"], "Pretendard")
    assert ".rk-stage { position: absolute; left: 0; top: 0; width" in css
    assert "top: 1040px; text-align: center;" in css


def test_default_captions_are_chip_style():
    out = compose.captions_html(_chunks(), REF, 4.0)
    assert 'class="chip"' in out and "lt-bar" not in out


def test_default_face_box_is_full_height():
    seg = Segment([], layout="face")
    assert compose._layout_box(seg, REF) == (0, 0, 1920)


# ------------------------------------------------------------------ news options
def test_news_geometry_moves_stage_and_kicker():
    g = stage_geometry(NEWS["layout"])
    css = shared_css(NEWS["colors"], "Pretendard", g, "\n".join(NEWS["graphics"]["extra_css"]))
    assert f"top: {NEWS['layout']['stage_cy'] - 478}px; width" in css
    assert "top: 1268px; text-align: center;" in css
    assert ".rk-dots { display: none; }" in css


def test_news_face_box_starts_below_title_bar():
    seg = Segment([], layout="face")
    assert compose._layout_box(seg, NEWS) == (0, 300, 1620)


def test_no_stage_move_when_graphic_geometry_equals_split():
    s = Scene("sc1", 3.0, NEWS["colors"], lambda a, d: d, [(0.0, "split"), (1.0, "graphic")],
              geo=stage_geometry(NEWS["layout"]))
    assert not any("-stage" in ln and "tl.to" in ln for ln in s.stage_js())


def test_lower_third_captions_markup_and_motion():
    out = compose.captions_html(_chunks(), NEWS, 4.0)
    assert out.count('class="lt-bar"') == 3
    assert '<span class="lt-em"><i id="ce0_1"></i>' in out           # emphasised word becomes a red block
    assert "#cb2" in out and "clipPath" in out         # after a pause the bar wipes in
    assert 'tl.fromTo("#ct1",{opacity:0}' in out       # inside a run only the text swaps (short fade)
    assert "#cb0" not in out.split("<script>")[1]      # frame-0 caption is not animated


def test_section_times_resolve_in_order_and_first_is_zero():
    secs = [{"anchor": "이걸", "title": "A"}, {"anchor": "첫 번째", "title": "B"}, {"anchor": "없는말", "title": "C"}]
    got = newsdesk.section_times(secs, _words())
    assert [(round(t, 2), s["title"]) for t, s in got] == [(0.0, "A"), (1.0, "B")]


def test_overlay_html_has_bar_sweep_ticker_and_events():
    plan = {"sections": [{"anchor": "그런데", "chip": "속보", "title": "제목"},
                         {"anchor": "첫 번째", "chip": "1/3", "title": "메모장", "sweep": True}],
            "ticker_items": ["하나", "둘"], "newsdesk": {"brand": "브리핑", "date": "2026.10.24"}}
    src, events = newsdesk.overlay_html(NEWS, plan, _words(), 4.0)
    assert 'id="nd-h1"' in src and 'id="nd-sw1"' in src and 'id="nd-tks"' in src
    assert "2026.10.24" in src and "브리핑" in src
    kinds = sorted(k for _, k in events)
    assert kinds == ["tick", "whoosh"]


def test_overlay_without_sections_or_ticker_is_still_valid():
    src, events = newsdesk.overlay_html(NEWS, {}, _words(), 2.0)
    assert 'data-composition-id="newsdesk"' in src and events == []


def test_title_size_shrinks_long_titles():
    cfg = newsdesk.desk_config(NEWS, None)
    assert newsdesk._title_size("짧은 제목", cfg) == 64
    assert newsdesk._title_size("아주 아주 아주 긴 제목이 여기에 있습니다", cfg) < 64


# ------------------------------------------------------------------ caption keep phrases
def _cfg():
    return {"max_words": 2, "max_chars": 6, "max_dur": 5.0}


def test_make_chunks_without_keep_is_unchanged():
    from steps.plan import make_chunks
    a = [c.text for c in make_chunks(_words(), _cfg(), 4.0)]
    b = [c.text for c in make_chunks(_words(), _cfg(), 4.0, None)]
    assert a == b


def test_keep_phrase_is_one_chunk_with_breaks_at_edges():
    from steps.plan import make_chunks
    texts = [c.text for c in make_chunks(_words(), _cfg(), 4.0, ["번째 단계에서는 메모장을"])]
    assert "번째 단계에서는 메모장을" in texts


# ------------------------------------------------------------------ cold open start word
def test_cold_open_from_skips_the_dangling_opener():
    from steps.cut import Sentence, Word, cold_open
    s = Sentence(0, [Word("그런데", 10.0, 10.4), Word("이건", 10.5, 10.8), Word("보내면", 10.9, 11.4)])
    cfg = {"pad_before": 0.1, "pad_after": 0.1}
    keeps = [[0.0, 20.0]]
    full, _ = cold_open([s], keeps, "그런데 이건", cfg)
    late, _ = cold_open([s], keeps, "그런데 이건", cfg, "이건")
    assert full[0] == [9.9, 11.5]
    assert late[0] == [10.4, 11.5]
    assert full[1:] == late[1:] == keeps
