"""Automatic reel editor (single command).

python pipeline/make_reel.py --input <mp4> --out out/<name>.mp4 [--style styles/reference.json]
                             [--plan plans/<content>.json] [--quality draft|standard|high]

Steps: transcribe -> VAD + bad-take/filler cut -> face track -> plan (captions, layouts,
cards) -> HyperFrames project -> render -> SFX + loudness -> mux.
Intermediate files are cached in work/<input-stem>/ (delete it to start fresh).
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

PIPE = Path(__file__).resolve().parent
ROOT = PIPE.parent
sys.path.insert(0, str(PIPE))
os.environ.setdefault("GLOG_minloglevel", "2")
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")


def refresh_path() -> None:
    """On Windows, merge the registry PATH (winget installs ffmpeg there)."""
    if sys.platform != "win32" or shutil.which("ffmpeg"):
        return
    import winreg
    parts = []
    for hive, key in ((winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment"),
                      (winreg.HKEY_CURRENT_USER, r"Environment")):
        try:
            with winreg.OpenKey(hive, key) as k:
                parts.append(os.path.expandvars(winreg.QueryValueEx(k, "Path")[0]))
        except OSError:
            pass
    os.environ["PATH"] = os.pathsep.join(parts + [os.environ.get("PATH", "")])


def log(msg: str) -> None:
    print(f"[make_reel {time.strftime('%H:%M:%S')}] {msg}", flush=True)


def render_hf(project: Path, out_mp4: Path, quality: str, workers: str) -> None:
    npx = shutil.which("npx") or shutil.which("npx.cmd")
    cmd = [npx, "--prefix", str(ROOT), "hyperframes", "render", str(project), "-o", str(out_mp4),
           "--quality", quality, "--video-bitrate", "9M", "--fps", "30", "--workers", workers, "--quiet"]
    res = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace")
    (project / "render.log").write_text(res.stdout + "\n" + res.stderr, encoding="utf-8")
    if res.returncode != 0 or not out_mp4.exists():
        raise RuntimeError(f"hyperframes render failed, see {project / 'render.log'}\n{res.stderr[-2000:]}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--style", default=str(PIPE / "styles" / "reference.json"))
    ap.add_argument("--plan", default=None, help="content plan JSON (cards anchored to transcript words)")
    ap.add_argument("--work", default=None)
    ap.add_argument("--whisper-model", default="large-v3-turbo")
    ap.add_argument("--quality", default="high", help="hyperframes render quality: draft|standard|high")
    ap.add_argument("--workers", default="auto")
    ap.add_argument("--no-render", action="store_true", help="stop after writing the HyperFrames project")
    args = ap.parse_args(argv)
    refresh_path()

    from steps import compose, cut, face_track, media, plan, transcribe, vad

    src_in = Path(args.input).resolve()
    out = Path(args.out).resolve()
    work = Path(args.work).resolve() if args.work else ROOT / "work" / src_in.stem
    work.mkdir(parents=True, exist_ok=True)
    style = json.loads(Path(args.style).read_text(encoding="utf-8"))
    content = json.loads(Path(args.plan).read_text(encoding="utf-8")) if args.plan else None

    src = work / "source.mp4"
    if not src.exists() or src.stat().st_size != src_in.stat().st_size:
        shutil.copy2(src_in, src)  # never touch the original
    info = media.probe(src)
    vst = next(s for s in info["streams"] if s["codec_type"] == "video")
    num, den = map(int, vst["r_frame_rate"].split("/"))
    src_fps = num / den
    duration = float(info["format"]["duration"])

    wav16 = work / "audio16k.wav"
    if not wav16.exists():
        media.run([media.ffmpeg_bin(), "-y", "-v", "error", "-i", str(src), "-ac", "1", "-ar", "16000", str(wav16)])
    log("transcribe")
    tr = transcribe.transcribe(wav16, work / "transcript.json", args.whisper_model)
    log("vad")
    regions = vad.speech_regions(wav16, work / "vad.json")
    log("face track")
    track = face_track.track_faces(src, work / "face_src.json")

    log("cut plan")
    sents, keeps, cut_log = cut.plan_cuts(tr, regions, style["cuts"], duration,
                                          (content or {}).get("drop_sentences"),
                                          (content or {}).get("cold_open"),
                                          (content or {}).get("cold_open_from"))
    keeps = media.snap_keeps(keeps, src_fps)
    speed = float(style.get("speed", 1.0))
    em = cut.EditMap(keeps, speed)
    (work / "cuts.json").write_text(json.dumps({"keeps": keeps, "log": cut_log, "edited_duration": em.duration},
                                               ensure_ascii=False, indent=1), encoding="utf-8")
    for line in cut_log:
        log("  " + line)
    log(f"  {len(keeps)} kept pieces, {duration:.1f}s -> {em.duration:.1f}s")

    face_mp4, voice_wav = work / "face.mp4", work / "voice.wav"
    grade = media.grade_filter(style)
    keep_sig = json.dumps([keeps, speed, grade])
    sig_file = work / "face.sig"
    if not face_mp4.exists() or not sig_file.exists() or sig_file.read_text() != keep_sig:
        log("edit video")
        media.edit_video(src, keeps, face_mp4, voice_wav, speed, grade=grade)
        sig_file.write_text(keep_sig)
    finfo = media.probe(face_mp4)
    fst = next(s for s in finfo["streams"] if s["codec_type"] == "video")
    edited_dur = min(em.duration, float(finfo["format"]["duration"]))

    log("plan captions / layouts / scenes")
    words, chunks, segs, scenes = plan.build_plan(sents, em, style, content)
    for c in chunks:
        c.end = min(c.end, edited_dur)
    segs[-1].end = min(segs[-1].end, edited_dur)
    scenes[-1].end = min(scenes[-1].end, edited_dur)
    dump = {
        "duration": edited_dur,
        "chunks": [{"t": round(c.start, 2), "e": round(c.end, 2), "text": c.text, "emph": c.emph} for c in chunks],
        "segments": [{"t": round(s.start, 2), "e": round(s.end, 2), "layout": s.layout, "scene": s.scene,
                      "text": " / ".join(c.text for c in s.chunks)} for s in segs],
        "scenes": [{"idx": s.idx, "template": s.template, "t": round(s.start, 2), "e": round(s.end, 2)} for s in scenes],
    }
    (work / "plan.json").write_text(json.dumps(dump, ensure_ascii=False, indent=1), encoding="utf-8")
    words_json = json.dumps([{"start": w.start, "end": w.end, "text": w.text} for w in words], ensure_ascii=False)
    (work / "words.json").write_text(words_json, encoding="utf-8")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.with_suffix(".words.json").write_text(words_json, encoding="utf-8")
    lay_counts = {k: sum(1 for s in segs if s.layout == k) for k in ("split", "face", "graphic")}
    log(f"  {len(chunks)} captions, {len(segs)} segments {lay_counts}, {len(scenes)} scenes")

    crop = compose.FaceCropper(track, em, int(fst["width"]), int(fst["height"]))
    project = work / "hf"
    events = compose.write_project(project, face_mp4, segs, chunks, scenes, words, crop, style, edited_dur, content)
    if style["audio"].get("sfx_on_cuts", True):
        events += [(s.start, "cut") for i, s in enumerate(segs) if i > 0 and s.layout != segs[i - 1].layout]
    if args.no_render:
        log(f"project written: {project}")
        return 0

    log("render (hyperframes)")
    hf_mp4 = work / "hf_render.mp4"
    t0 = time.time()
    render_hf(project, hf_mp4, args.quality, args.workers)
    log(f"  rendered in {time.time() - t0:.0f}s")

    log("audio: sfx + loudness")
    sfx_wav = work / "sfx.wav"
    n_sfx = media.sfx_track(events, edited_dur, sfx_wav, style["audio"]["sfx_gain_db"])
    final_wav = work / "final_audio.wav"
    meas = media.mix_and_normalize(voice_wav, sfx_wav, final_wav, style["audio"]["target_lufs"],
                                   style["audio"]["true_peak"], edited_dur)
    log(f"  {n_sfx} sfx, input loudness {meas['input_i']} LUFS")
    media.mux(hf_mp4, final_wav, out)
    log(f"done -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
