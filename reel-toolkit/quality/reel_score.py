"""Reel quality scorer: measure a vertical reel, optionally against a reference.

Usage:
  python reel_score.py --output out.mp4 [--reference ref.mp4] [--json report.json]
                       [--frames 8] [--sheet sheet.png] [--visual-scores visual.json]
                       [--words words.json] [--lang ko] [--no-asr] [--no-ocr]

Content & Craft (55 % of the score) is judged by an independent sub-agent:
  1) --judge-pack DIR   writes blind A/B frame strips, motion strips, transcript
                        and JUDGE_PROMPT.md (label key goes to DIR_key.json)
  2) a fresh judge agent writes DIR/scores_<id>.json  (2 judges recommended)
  3) --content-scores DIR/scores_*.json   merges (averages) them; with both
     videos judged it prints the stopping rule: output standalone total >
     reference standalone total AND every content criterion >= 4/5.

Prints a criterion table with PASS/WARN/FAIL and an overall score /100.
--frames N writes a contact sheet of N reference|output frame pairs for the
visual (Claude) review; record that review as JSON with keys
caption_style, motion_graphics, zoom_reframe, pacing, hook (1-5) and pass it
back with --visual-scores to fold it into the score.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import pickle
import statistics
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("GLOG_minloglevel", "2")        # quiet mediapipe
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")
logging.getLogger("RapidOCR").setLevel(logging.ERROR)

import captions  # noqa: E402
import content  # noqa: E402
import judge_pack  # noqa: E402
import probe  # noqa: E402
import rubric  # noqa: E402
import speech  # noqa: E402
import vision  # noqa: E402
from sheet import contact_sheet  # noqa: E402


METRICS_VERSION = 5           # bump when measurement logic changes (invalidates cache)


def measure_cached(path: str, args: argparse.Namespace, words_file: str | None = None) -> dict:
    """measure() with a JSON cache keyed on file identity + analysis settings."""
    st = os.stat(path)
    key_src = json.dumps([METRICS_VERSION, os.path.abspath(path), st.st_size, st.st_mtime,
                          words_file, args.lang, args.whisper_model, args.sample_fps,
                          args.ocr_fps, args.no_asr, args.no_ocr, args.no_refine,
                          args.caption_band])
    cache = os.path.join(speech.CACHE_DIR, f"metrics_{hashlib.sha1(key_src.encode()).hexdigest()[:16]}.json")
    if not args.no_cache and os.path.exists(cache):
        with open(cache, encoding="utf-8") as fh:
            print(f"[cache] {os.path.basename(path)}")
            return json.load(fh)
    m = measure(path, args, words_file)
    os.makedirs(speech.CACHE_DIR, exist_ok=True)
    with open(cache, "w", encoding="utf-8") as fh:
        json.dump(m, fh, ensure_ascii=False, default=str)
    return m


def measure(path: str, args: argparse.Namespace, words_file: str | None = None) -> dict:
    t0 = time.time()
    info = probe.ffprobe(path)
    fstats = probe.analyze_filters(path, info)
    vis = _vision_cached(path, args)
    words = []
    if words_file:
        words = speech.load_words(words_file)
    elif not args.no_asr and info.has_audio:
        words = speech.transcribe(path, args.whisper_model, args.lang)

    m: dict = {"file": os.path.abspath(path), "width": info.width, "height": info.height,
               "fps": info.fps, "duration": info.duration,
               "video_bitrate_mbps": info.video_bitrate / 1e6,
               "loudness_i": fstats.loudness_i, "true_peak": fstats.true_peak,
               "loudness_lra": fstats.loudness_lra}
    m.update(_frame_metrics(info, fstats, vis))
    m.update(_speech_metrics(path, info, fstats, words))
    m.update(_caption_metrics(path, vis, words, args))
    m["n_words"] = len(words)
    m["analysis_seconds"] = round(time.time() - t0, 1)
    return m


def _vision_cached(path: str, args: argparse.Namespace) -> vision.VisionStats:
    """Frame sampling + OCR is the slow part; cache its raw result separately so
    scoring logic can change without re-running OCR."""
    st = os.stat(path)
    key_src = json.dumps([vision.VISION_VERSION, os.path.abspath(path), st.st_size, st.st_mtime,
                          args.sample_fps, args.ocr_fps, args.no_ocr, args.lang])
    cache = os.path.join(speech.CACHE_DIR, f"vision_{hashlib.sha1(key_src.encode()).hexdigest()[:16]}.pkl")
    if not args.no_cache and os.path.exists(cache):
        with open(cache, "rb") as fh:
            return pickle.load(fh)
    vis = vision.analyze(path, sample_fps=args.sample_fps, ocr_fps=args.ocr_fps,
                         use_ocr=not args.no_ocr, lang=args.lang)
    os.makedirs(speech.CACHE_DIR, exist_ok=True)
    with open(cache, "wb") as fh:
        pickle.dump(vis, fh)
    return vis


def _cut_metrics(cut_times: list[float], dur: float) -> dict:
    cuts = [t for t in cut_times if 0.05 < t < dur - 0.05]
    bounds = [0.0, *cuts, dur]
    shots = [b - a for a, b in zip(bounds, bounds[1:])]
    return {"n_cuts": len(cuts), "cut_times": [round(c, 3) for c in cuts],
            "cuts_per_min": len(cuts) / dur * 60, "avg_shot_s": statistics.fmean(shots),
            "longest_shot_s": max(shots), "first_cut_s": cuts[0] if cuts else None}


def _face_metrics(vis, n_samples: int) -> dict:
    faces = vis.faces
    framed = [f for f in faces if rubric.FACE_X[0] <= f.cx <= rubric.FACE_X[1]
              and f.top >= rubric.FACE_TOP_MIN and f.top + f.h <= rubric.FACE_BOTTOM_MAX]

    def med(xs):
        return statistics.median(xs) if xs else None

    return {"face_detector": vis.face_detector,
            "face_presence": len(faces) / max(n_samples, 1),
            "face_safe_ratio": len(framed) / len(faces) if faces else None,
            "face_center_x": med([f.cx for f in faces]),
            "face_center_y": med([f.cy for f in faces]),
            "face_height": med([f.h for f in faces])}


def _frame_metrics(info, fstats, vis) -> dict:
    early = [mv for t, mv in zip(vis.sample_times[1:], vis.motion) if t <= 3.0]
    motion_mean = statistics.fmean(vis.motion) if vis.motion else None
    out = {
        "black_total_s": sum(b - a for a, b in fstats.blacks),
        "freeze_longest_s": max((b - a for a, b in fstats.freezes), default=0.0),
        "freeze_total_s": sum(b - a for a, b in fstats.freezes),
        "sharpness_median": statistics.median(vis.sharpness) if vis.sharpness else None,
        "brightness": statistics.fmean(vis.brightness) if vis.brightness else None,
        "saturation": statistics.fmean(vis.saturation) if vis.saturation else None,
        "motion_mean": motion_mean,
        "hook_motion_ratio": (statistics.fmean(early) / motion_mean
                              if early and motion_mean else None),
    }
    out.update(_cut_metrics(fstats.cut_times, info.duration or 1e-6))
    out.update(_face_metrics(vis, len(vis.sample_times)))
    return out


def _speech_metrics(path, info, fstats, words) -> dict:
    out = speech.speech_metrics(words, info.duration) if words else {}
    if words:
        out["word_gap_dead_air_ratio"] = out.pop("dead_air_ratio")
        out["word_longest_gap_s"] = out.pop("longest_gap_s")
    if not info.has_audio:
        return {**out, "dead_air_ratio": None, "dead_air_source": "no audio"}
    try:
        out.update(speech.vad_dead_air(path, info.duration))
        out["dead_air_source"] = "silero VAD (faster-whisper), gaps > 0.5s"
    except Exception as exc:  # VAD unavailable -> ffmpeg silencedetect
        sil = [b - a for a, b in fstats.silences]
        out.update({"dead_air_ratio": sum(sil) / max(info.duration, 1e-6),
                    "longest_gap_s": max(sil, default=0.0),
                    "dead_air_source": f"ffmpeg silencedetect -35dB (VAD failed: {exc})"})
    return out


def _caption_metrics(path, vis, words, args) -> dict:
    if not vis.ocr_enabled:
        return {"ocr_enabled": False}
    ocr, static = captions.split_static(vis.ocr)
    if args.caption_band:
        band = tuple(float(x) for x in args.caption_band.split(","))
        cap, gfx = captions.split_caption_band(ocr, band)
        method = "fixed band"
    elif words:
        cap, gfx = captions.split_by_speech(ocr, words)
        ys = [(b.y0 + b.y1) / 2 for o in cap for b in o.boxes]
        band = (min(ys), max(ys)) if ys else None
        method = "text matches speech"
    else:
        band = captions.find_caption_band(ocr)
        cap, gfx = captions.split_caption_band(ocr, band)
        method = "auto band (no ASR)"
    events = captions.caption_events(cap)
    dur = max(vis.ocr[-1].t if vis.ocr else 0, 1e-6)
    out = {"ocr_enabled": True, "static_text": sorted(static)[:10],
           "caption_detect": method,
           "caption_band": [round(x, 3) for x in band] if band else None,
           "caption_coverage": captions.coverage(cap, words),
           "caption_safe_ratio": captions.safe_zone_ratio(cap, rubric.IG_SAFE_ZONE),
           "graphic_text_ratio": sum(1 for o in gfx if o.boxes) / max(len(gfx), 1),
           "first_caption_s": events[0]["t_seen"] if events else None,
           "caption_events": len(events), "caption_events_per_min": len(events) / dur * 60,
           "chars_per_caption": (statistics.fmean(len(captions.norm_text(e["text"])) for e in events)
                                 if events else None),
           "caption_samples": [{"t": round(e["t_seen"], 2), "text": e["text"]} for e in events[:60]]}
    out.update(captions.caption_layout(cap))
    if words and events:
        errs = captions.sync_errors(path, events, words, refine=not args.no_refine)
        out.update(captions.summarize_errors(errs))
    return out


# ----------------------------------------------------------------- printing
def print_table(report: dict, has_ref: bool) -> None:
    head = "ID  " + _pad("기준", 20) + _pad("측정값", 36) + (_pad("레퍼런스", 28) if has_ref else "") \
        + _pad("목표", 22) + "  점수  판정"
    print(head)
    print("-" * 118)
    for r in report["rows"]:
        score = "-" if r["score"] is None else f"{r['score'] * 100:.0f}"
        ref = _pad(str(r["reference"] or ""), 28) if has_ref else ""
        print(f"{r['id']:<4}{_pad(r['name'], 20)}{_pad(str(r['value']), 36)}{ref}"
              f"{_pad(r['target'], 22)}{score:>6}  {r['status']}")
    print("-" * 118)
    groups = "  ".join(f"{g}={v:.0f}" for g, v in report["groups"].items())
    print(f"그룹 점수: {groups}")
    gate = f"  (필수 기준 FAIL: {', '.join(report['gate_fails'])})" if report["gate_fails"] else ""
    print(f"종합 점수: {report['overall']:.1f} / 100  ->  {report['verdict']}{gate}")


def _pad(text: str, width: int) -> str:
    """Pad accounting for wide (Hangul) characters."""
    vis = sum(2 if ord(ch) > 0x1100 else 1 for ch in text)
    if vis > width - 1:
        out, n = "", 0
        for ch in text:
            n += 2 if ord(ch) > 0x1100 else 1
            if n > width - 2:
                break
            out += ch
        return out + "… " + " " * max(0, width - n - 2)
    return text + " " * (width - vis)


def parse_args(argv=None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Score a vertical reel against the rubric")
    p.add_argument("--output", required=True, help="our rendered reel (mp4)")
    p.add_argument("--reference", help="reference reel to compare against")
    p.add_argument("--json", help="write full report JSON here")
    p.add_argument("--frames", type=int, default=0, help="N paired frames for a contact sheet")
    p.add_argument("--sheet", help="contact sheet PNG path (default next to --json / output)")
    p.add_argument("--visual-scores", help="JSON with 1-5 scores from the visual review")
    p.add_argument("--words", help="word timestamps JSON for --output (skips ASR)")
    p.add_argument("--ref-words", help="word timestamps JSON for --reference")
    p.add_argument("--lang", default="ko")
    p.add_argument("--whisper-model", default="small")
    p.add_argument("--sample-fps", type=float, default=4.0)
    p.add_argument("--ocr-fps", type=float, default=3.0)
    p.add_argument("--no-asr", action="store_true")
    p.add_argument("--no-ocr", action="store_true")
    p.add_argument("--no-refine", action="store_true", help="skip frame-accurate caption onset")
    p.add_argument("--no-cache", action="store_true", help="re-measure even if cached")
    p.add_argument("--judge-pack", help="write a blind Content & Craft judge pack into DIR")
    p.add_argument("--seed", type=int, help="seed for A/B label randomisation")
    p.add_argument("--content-scores", nargs="+",
                   help="judge JSON file(s) to merge (several are averaged)")
    p.add_argument("--judge-key", help="pack key JSON (default: <pack dir>_key.json)")
    p.add_argument("--caption-band", help="force subtitle band as 'y0,y1' (fractions of height)")
    return p.parse_args(argv)


def _load_key(path: str | None) -> dict | None:
    if not path:
        return None
    with open(path, encoding="utf-8") as fh:
        return json.load(fh).get("labels")


def _words_for(path: str, args, words_file: str | None) -> list:
    if words_file:
        return speech.load_words(words_file)
    if args.no_asr:
        return []
    return speech.transcribe(path, args.whisper_model, args.lang)   # cached


def _make_judge_pack(args, out_m: dict, ref_m: dict | None) -> None:
    vids = [("output", args.output, out_m, _vision_cached(args.output, args),
             _words_for(args.output, args, args.words))]
    if args.reference:
        vids.append(("reference", args.reference, ref_m, _vision_cached(args.reference, args),
                     _words_for(args.reference, args, args.ref_words)))
    prompt = judge_pack.build(args.judge_pack, vids, seed=args.seed)
    print(f"[judge-pack] {prompt}  (key: {args.judge_pack.rstrip(chr(92) + '/')}_key.json — keep away from the judge)")


def _stopping_rule(report: dict, ref_report: dict | None, out_content: dict | None) -> dict:
    """Builder stops when output standalone total > reference total and every
    content criterion >= 4/5."""
    if not out_content:
        return {"ready": False, "reason": "no content scores for output"}
    low = [cid for cid, e in out_content.items() if e["score"] < content.CONTENT_MIN_FOR_STOP]
    if ref_report is None:
        return {"ready": False, "reason": "no content scores for reference", "content_below_4": low}
    beats = report["standalone"] > ref_report["standalone"]
    return {"ready": beats and not low, "output_total": report["standalone"],
            "reference_total": ref_report["standalone"], "content_below_4": low}


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = parse_args(argv)
    for f in filter(None, [args.output, args.reference]):
        if not os.path.isfile(f):
            print(f"error: file not found: {f}", file=sys.stderr)
            return 2
    print(f"[measure] output: {args.output}")
    out_m = measure_cached(args.output, args, args.words)
    ref_m = None
    if args.reference:
        print(f"[measure] reference: {args.reference}")
        ref_m = measure_cached(args.reference, args, args.ref_words)
    visual = None
    if args.visual_scores:
        with open(args.visual_scores, encoding="utf-8") as fh:
            visual = json.load(fh)
    scores = (content.load_scores(args.content_scores, _load_key(args.judge_key))
              if args.content_scores else {})
    out_c, ref_c = scores.get("output"), scores.get("reference")
    report = rubric.score_report(out_m, ref_m, visual, content=out_c)
    ref_report = rubric.score_report(ref_m, content=ref_c) if ref_m and ref_c else None
    print()
    print_table(report, ref_m is not None)
    print(f"단독 총점(내용+편집+기술, 레퍼런스와 같은 기준): {report['standalone']:.1f}")
    if ref_report:
        print(f"레퍼런스 단독 총점: {ref_report['standalone']:.1f}")
    stop = _stopping_rule(report, ref_report, out_c) if args.content_scores else None
    if stop:
        print(f"중단 규칙(출력 > 레퍼런스, 내용 기준 모두 4점 이상): {'충족' if stop['ready'] else '미충족'} {stop}")
    if args.judge_pack:
        _make_judge_pack(args, out_m, ref_m)

    sheet_path = None
    if args.frames > 0:
        base = os.path.splitext(args.json or args.output)[0]
        sheet_path = args.sheet or base + "_sheet.png"
        contact_sheet(args.output, args.reference, args.frames, sheet_path,
                      rubric.IG_SAFE_ZONE)
        print(f"[sheet] {sheet_path}  (score 1-5: {', '.join(rubric.VISUAL_KEYS)})")
    if args.json:
        payload = {"overall": report["overall"], "verdict": report["verdict"],
                   "gate_fails": report["gate_fails"], "groups": report["groups"],
                   "standalone": report["standalone"], "stopping_rule": stop,
                   "content_scores": scores or None,
                   "reference_report": ref_report,
                   "rows": report["rows"], "output_metrics": out_m,
                   "reference_metrics": ref_m, "visual_scores": visual,
                   "contact_sheet": sheet_path,
                   "visual_review_template": {k: None for k in rubric.VISUAL_KEYS}}
        os.makedirs(os.path.dirname(os.path.abspath(args.json)), exist_ok=True)
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2, default=str)
        print(f"[json] {args.json}")
    return 0 if report["verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
