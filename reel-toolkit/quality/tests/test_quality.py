"""Unit tests for the pure parts of the reel quality checker (no video needed)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import captions  # noqa: E402
import probe  # noqa: E402
import rubric  # noqa: E402
import speech  # noqa: E402
from vision import OcrObs, TextBox  # noqa: E402


def _good_metrics(**over):
    m = {"width": 1080, "height": 1920, "fps": 30.0, "video_bitrate_mbps": 8.0,
         "loudness_i": -14.0, "true_peak": -1.5, "black_total_s": 0.0, "freeze_longest_s": 0.0,
         "sharpness_median": 300.0, "dead_air_ratio": 0.01, "longest_gap_s": 0.3,
         "cuts_per_min": 25.0, "avg_shot_s": 2.4, "longest_shot_s": 5.0, "first_cut_s": 0.0,
         "speech_start_s": 0.0, "ocr_enabled": True, "first_caption_s": 0.0,
         "face_presence": 0.9, "face_safe_ratio": 0.95, "caption_coverage": 0.95,
         "sync_median_abs_ms": 80.0, "sync_mean_signed_ms": 10.0, "sync_n": 20,
         "caption_safe_ratio": 1.0, "caption_text_height": 0.04, "ocr_confidence": 0.95}
    m.update(over)
    return m


def test_ramps_and_band():
    assert rubric.ramp_low(1, 2, 4) == 1.0
    assert rubric.ramp_low(3, 2, 4) == 0.5
    assert rubric.ramp_high(1, 4, 2) == 0.0
    assert rubric.band(5.0, 1.5, 4.0, 2.0) == 0.5


def test_match_relative_and_absolute():
    assert rubric.match(110, 100, 0.2, True) == 1.0
    assert rubric.match(160, 100, 0.2, True) == 0.0
    assert rubric.match(0.45, 0.40, 0.05, False) == 1.0


def test_perfect_reel_passes_everything():
    report = rubric.score_report(_good_metrics())
    assert report["verdict"] == "PASS"
    assert all(r["status"] in ("PASS", "N/A") for r in report["rows"])
    assert report["overall"] > 99


def test_zero_times_count_as_instant_hook():
    # regression: 0.0 s used to be treated as "missing" (falsy)
    report = rubric.score_report(_good_metrics(first_caption_s=0.0, first_cut_s=0.0))
    hook = next(r for r in report["rows"] if r["id"] == "E3")
    assert hook["score"] == 1.0


def test_gate_failure_fails_verdict_even_with_high_score():
    report = rubric.score_report(_good_metrics(loudness_i=-30.0))
    assert "T4" in report["gate_fails"]
    assert report["verdict"] == "FAIL"


def test_reference_identical_scores_full():
    m = _good_metrics(caption_y_center=0.5, face_height=0.2, motion_mean=10.0)
    report = rubric.score_report(m, dict(m))
    assert abs(report["groups"]["reference"] - 100.0) < 1e-9


def test_visual_scores_mapping():
    report = rubric.score_report(_good_metrics(), visual={k: 4 for k in rubric.VISUAL_KEYS})
    vis = [r for r in report["rows"] if r["group"] == "visual"]
    assert len(vis) == 5 and all(r["status"] == "PASS" for r in vis)


def test_parse_filter_log():
    log = ("[scdet] lavfi.scd.score: 28.4, lavfi.scd.time: 1.633333\n"
           "[silencedetect] silence_start: 2.0\n[silencedetect] silence_end: 2.6 | silence_duration: 0.6\n"
           "[blackdetect] black_start:0 black_end:0.2 black_duration:0.2\n"
           "[freezedetect] lavfi.freezedetect.freeze_start: 5.0\n"
           "Summary:\n  I:         -14.1 LUFS\n  LRA:         2.2 LU\n  Peak:       -0.7 dBFS\n")
    st = probe.parse_filter_log(log, duration=10.0)
    assert st.cut_times == [1.633333]
    assert st.silences == [(2.0, 2.6)]
    assert st.blacks == [(0.0, 0.2)]
    assert st.freezes == [(5.0, 10.0)]          # unterminated freeze runs to the end
    assert (st.loudness_i, st.loudness_lra, st.true_peak) == (-14.1, 2.2, -0.7)


def test_speech_metrics_dead_air():
    words = [speech.Word(0.0, 1.0, "a"), speech.Word(2.0, 3.0, "b")]
    m = speech.speech_metrics(words, duration=4.0)
    assert abs(m["dead_air_ratio"] - 0.5) < 1e-9      # 1 s gap + 1 s tail
    assert m["speech_start_s"] == 0.0


def _box(text, y=0.5, h=0.04):
    return TextBox(text, 0.95, 0.2, y - h / 2, 0.8, y + h / 2)


def test_split_by_speech_separates_captions_from_graphics():
    words = [speech.Word(0.0, 0.5, "영상"), speech.Word(0.5, 1.0, "편집")]
    ocr = [OcrObs(0.4, [_box("영상 편집"), _box("MediaPipe Apache-2.0", y=0.1)])]
    cap, gfx = captions.split_by_speech(ocr, words)
    assert [b.text for b in cap[0].boxes] == ["영상 편집"]
    assert [b.text for b in gfx[0].boxes] == ["MediaPipe Apache-2.0"]


def test_caption_events_and_safe_zone():
    ocr = [OcrObs(0.0, []), OcrObs(0.33, [_box("hello")]), OcrObs(0.66, [_box("hello")]),
           OcrObs(1.0, [_box("world", y=0.9)])]
    events = captions.caption_events(ocr)
    assert [e["text"] for e in events] == ["hello", "world"]
    assert events[0]["t_before"] == 0.0 and events[0]["t_seen"] == 0.33
    assert captions.safe_zone_ratio(ocr, rubric.IG_SAFE_ZONE) == 2 / 3


def test_match_word_prefers_text_match():
    words = [speech.Word(1.0, 1.3, "그냥"), speech.Word(1.3, 1.8, "알려드릴게요")]
    w = captions._match_word("알려드릴게요", 1.2, words)
    assert w.text == "알려드릴게요"


def test_content_scores_average_and_key_mapping(tmp_path):
    import json as _json
    import content
    pack = tmp_path / "pack"
    pack.mkdir()
    (tmp_path / "pack_key.json").write_text(_json.dumps({"labels": {"A": "reference", "B": "output"}}))
    for j, (a, b) in enumerate([(5, 3), (4, 4)]):
        data = {"videos": {"A": {cid: {"score": a, "evidence": ["1.0s x"]} for cid in content.CONTENT_IDS},
                           "B": {cid: {"score": b} for cid in content.CONTENT_IDS}}}
        (pack / f"scores_j{j}.json").write_text(_json.dumps(data))
    scores = content.load_scores([str(pack / "scores_j0.json"), str(pack / "scores_j1.json")])
    assert scores["reference"]["C1"]["score"] == 4.5
    assert scores["output"]["C1"]["score"] == 3.5 and scores["output"]["C1"]["judges"] == 2


def test_content_group_dominates_weighting():
    import content
    m = _good_metrics()
    low = {cid: {"score": 2.0, "judges": 1, "spread": 0} for cid in content.CONTENT_IDS}
    report = rubric.score_report(m, content=low)
    # perfect technical/editing cannot rescue weak content
    assert report["standalone"] < 65   # (40*55 + 100*30) / 85 = 61.2
    assert all(r["status"] == "FAIL" for r in report["rows"] if r["group"] == "content")


def test_ocr_runs_without_angle_classifier():
    # upright video text: the angle classifier flipped outlined captions upside down
    import numpy as np
    import vision

    calls = {}

    class FakeEngine:
        def __call__(self, img, **kw):
            calls.update(kw)

            class R:
                boxes = txts = scores = None
            return R()

    ocr = vision._Ocr.__new__(vision._Ocr)
    ocr._eng = FakeEngine()
    assert ocr.read(np.zeros((40, 40, 3), np.uint8)) == []
    assert calls.get("use_cls") is False
