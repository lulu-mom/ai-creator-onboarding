"""Build a blind judge pack for the Content & Craft rubric.

Layout (DIR):
  JUDGE_PROMPT.md            rubric with anchors, procedure, output schema
  A/ (B/)                    one folder per video, labels randomised
    transcript.txt           timestamped speech lines
    timeline.json            duration, cut times, caption timeline, graphic events
    strips/seg_XX.png        dense frame strips (3 fps, 4 s per strip)
    motion/ev_XX.png         10 fps strips around graphic entrances / cuts
DIR_key.json (sibling, NOT inside the pack): label -> role/file. The judge must
never see it.
"""
from __future__ import annotations

import json
import os
import random

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

import captions
import content

SEG_FPS, SEG_SECONDS, SEG_COLS = 3.0, 4.0, 6
SEG_CELL_W = 200
MOTION_FPS, MOTION_PRE, MOTION_POST, MOTION_COLS = 10.0, 0.3, 1.0, 7
MOTION_CELL_W = 170
MAX_MOTION_EVENTS = 12
MIN_EVENT_GAP_S = 1.5
LINE_GAP_S, LINE_MAX_CHARS = 0.4, 40
FONT_PATH = r"C:\Windows\Fonts\malgun.ttf"


def _font(size):
    try:
        return ImageFont.truetype(FONT_PATH, size)
    except OSError:
        return ImageFont.load_default()


def grab_frames(path: str, times: list[float], width: int) -> dict[float, np.ndarray]:
    """Sequential decode; returns {requested_time: frame} using the nearest frame."""
    wanted = sorted(set(round(t, 3) for t in times if t >= 0))
    cap = cv2.VideoCapture(path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    out, i, idx = {}, 0, 0
    try:
        while i < len(wanted):
            ok, frame = cap.read()
            if not ok:
                break
            t = idx / fps
            idx += 1
            while i < len(wanted) and wanted[i] <= t + 0.5 / fps:
                h, w = frame.shape[:2]
                out[wanted[i]] = cv2.resize(frame, (width, int(h * width / w)),
                                            interpolation=cv2.INTER_AREA)
                i += 1
    finally:
        cap.release()
    return out


def _grid(frames: list[tuple[float, np.ndarray | None]], cols: int, cell_w: int,
          title: str, dest: str) -> None:
    cell_h = cell_w * 16 // 9
    rows = (len(frames) + cols - 1) // cols
    img = Image.new("RGB", (cols * cell_w + (cols + 1) * 4, rows * (cell_h + 22) + 34), (20, 20, 24))
    d, f, ft = ImageDraw.Draw(img), _font(13), _font(16)
    d.text((6, 6), title, fill=(255, 255, 255), font=ft)
    for k, (t, fr) in enumerate(frames):
        x = 4 + (k % cols) * (cell_w + 4)
        y = 34 + (k // cols) * (cell_h + 22)
        d.text((x + 2, y + 2), f"{t:6.2f}s", fill=(255, 220, 90), font=f)
        if fr is not None:
            fr = cv2.resize(fr, (cell_w, cell_h), interpolation=cv2.INTER_AREA)
            img.paste(Image.fromarray(cv2.cvtColor(fr, cv2.COLOR_BGR2RGB)), (x, y + 20))
    img.save(dest)


def _transcript(words) -> str:
    lines, cur = [], []
    for w in words:
        if cur and (w.start - cur[-1].end > LINE_GAP_S
                    or sum(len(x.text) for x in cur) > LINE_MAX_CHARS):
            lines.append(cur)
            cur = []
        cur.append(w)
    if cur:
        lines.append(cur)
    return "\n".join(f"[{ln[0].start:6.2f} - {ln[-1].end:6.2f}] {' '.join(x.text for x in ln)}"
                     for ln in lines)


def graphic_events(vis, words, cut_times: list[float]) -> list[dict]:
    """New on-screen graphic text (not subtitles) + hard cuts, spread out in time."""
    events = []
    if vis.ocr_enabled and vis.ocr:
        ocr, _ = captions.split_static(vis.ocr)
        _, gfx = (captions.split_by_speech(ocr, words) if words
                  else (None, ocr))
        prev: set[str] = set()
        for o in gfx:
            cur = {captions.norm_text(b.text) for b in o.boxes if len(captions.norm_text(b.text)) >= 3}
            new = cur - prev
            if len(new) >= 2 or (new and not prev):
                events.append({"t": o.t, "kind": "graphic", "text": " / ".join(sorted(new))[:80]})
            prev = cur
    events += [{"t": t, "kind": "cut", "text": ""} for t in cut_times]
    events.sort(key=lambda e: (e["t"], e["kind"] != "graphic"))
    picked: list[dict] = []
    for e in sorted(events, key=lambda e: e["kind"] != "graphic"):   # graphics first
        if all(abs(e["t"] - p["t"]) >= MIN_EVENT_GAP_S for p in picked):
            picked.append(e)
        if len(picked) >= MAX_MOTION_EVENTS:
            break
    return sorted(picked, key=lambda e: e["t"])


def _video_pack(folder: str, label: str, path: str, metrics: dict, vis, words) -> dict:
    os.makedirs(os.path.join(folder, "strips"), exist_ok=True)
    os.makedirs(os.path.join(folder, "motion"), exist_ok=True)
    dur = metrics["duration"]
    seg_times = [round(i / SEG_FPS, 3) for i in range(int(dur * SEG_FPS))]
    events = graphic_events(vis, words, metrics.get("cut_times") or [])
    mot_times = [round(e["t"] - MOTION_PRE + k / MOTION_FPS, 3)
                 for e in events for k in range(int((MOTION_PRE + MOTION_POST) * MOTION_FPS) + 1)]
    seg_frames = grab_frames(path, seg_times, SEG_CELL_W)
    mot_frames = grab_frames(path, mot_times, MOTION_CELL_W)

    per = int(SEG_SECONDS * SEG_FPS)
    for n, start in enumerate(range(0, len(seg_times), per), 1):
        chunk = [(t, seg_frames.get(t)) for t in seg_times[start:start + per]]
        _grid(chunk, SEG_COLS, SEG_CELL_W,
              f"Video {label} - segment {n}  ({chunk[0][0]:.1f}s-{chunk[-1][0]:.1f}s, {SEG_FPS:g} fps)",
              os.path.join(folder, "strips", f"seg_{n:02d}.png"))
    n_mot = int((MOTION_PRE + MOTION_POST) * MOTION_FPS) + 1
    for n, e in enumerate(events, 1):
        ts = mot_times[(n - 1) * n_mot:n * n_mot]
        _grid([(t, mot_frames.get(t)) for t in ts], MOTION_COLS, MOTION_CELL_W,
              f"Video {label} - motion {n}: {e['kind']} at {e['t']:.2f}s ({MOTION_FPS:g} fps)",
              os.path.join(folder, "motion", f"ev_{n:02d}.png"))

    with open(os.path.join(folder, "transcript.txt"), "w", encoding="utf-8") as fh:
        fh.write(_transcript(words) or "(no speech detected)")
    timeline = {"duration_s": round(dur, 2), "cut_times_s": metrics.get("cut_times"),
                "captions": metrics.get("caption_samples"),
                "motion_events": [{"file": f"motion/ev_{i:02d}.png", **e}
                                  for i, e in enumerate(events, 1)]}
    with open(os.path.join(folder, "timeline.json"), "w", encoding="utf-8") as fh:
        json.dump(timeline, fh, ensure_ascii=False, indent=1)
    return {"segments": len(range(0, len(seg_times), per)), "motion_events": len(events)}


def build(pack_dir: str, videos: list[tuple[str, str, dict, object, list]], seed: int | None = None) -> str:
    """videos: [(role, path, metrics, vision_stats, words)]. Returns prompt path."""
    rng = random.Random(seed)
    order = list(videos)
    rng.shuffle(order)
    labels = "AB"[:len(order)]
    os.makedirs(pack_dir, exist_ok=True)
    key, info = {}, {}
    for label, (role, path, metrics, vis, words) in zip(labels, order):
        key[label] = role
        info[label] = _video_pack(os.path.join(pack_dir, label), label, path, metrics, vis, words)
        key[f"{label}_file"] = os.path.abspath(path)
    with open(pack_dir.rstrip("\\/") + "_key.json", "w", encoding="utf-8") as fh:
        json.dump({"labels": {lb: key[lb] for lb in labels}, "files": key}, fh, indent=1)
    prompt = os.path.join(pack_dir, "JUDGE_PROMPT.md")
    with open(prompt, "w", encoding="utf-8") as fh:
        fh.write(_prompt(pack_dir, labels, info))
    return prompt


def _prompt(pack_dir: str, labels: str, info: dict) -> str:
    vids = "\n".join(f"- Video {lb}: `{lb}/` — {info[lb]['segments']} segment strips, "
                     f"{info[lb]['motion_events']} motion strips" for lb in labels)
    schema = {"judge": "<your id>", "videos": {lb: {cid: {
        "score": "1-5 integer", "evidence": ["12.3s: what you saw/heard"],
        "fixes": ["concrete change that would raise the score"]} for cid in content.CONTENT_IDS[:1]}
        for lb in labels}}
    return f"""# Reel Content & Craft judge

You are an independent, strict senior short-form video editor. You did NOT make
these videos. Score each video on its own against the anchored scales below.
The videos are blind-labelled ({', '.join(labels)}); do not guess which is a
"reference" or "ours", and do not open anything outside this folder.

## Material
{vids}

Per video folder:
- `transcript.txt` — speech with timestamps (machine transcript; may contain small ASR errors).
- `timeline.json` — duration, hard-cut times, on-screen caption timeline, motion-event list.
- `strips/seg_XX.png` — every frame at 3 fps, 4 s per strip, in time order. View ALL of them.
- `motion/ev_XX.png` — 10 fps frame sequences from 0.3 s before to 1.0 s after a graphic
  entrance or cut. Judge motion (easing, staggering, overshoot, exits, jank) ONLY from these
  frame-to-frame sequences, never from a single frame.

## Procedure (follow in order)
1. Read the transcript first; write down the core message in one sentence.
2. View every segment strip in order with the transcript beside it; note timestamps of key
   points, visualised points, graphics, empty/dead moments, glitches, overlaps, cut-off text.
3. View every motion strip; note easing / timing on speech beats / stagger / exits.
4. For each criterion, pick the level whose anchor description best matches the evidence.
   If between two levels, choose the LOWER one. A 5 needs zero counter-examples.
   Do not let one strong area raise unrelated criteria (avoid halo effect).
5. Give 1-4 evidence items with timestamps per criterion, and 1-3 concrete fixes
   (fixes may be empty only for a 5).

## Anchored scales (1-5)
{content.rubric_markdown()}
## Output
Write ONLY valid JSON (UTF-8) to `{os.path.join(pack_dir, 'scores_<your id>.json')}` with
every criterion {', '.join(content.CONTENT_IDS)} for every video, shaped like:

```json
{json.dumps(schema, ensure_ascii=False, indent=1)}
```
Also include a top-level `"summary": {{"<label>": "one-sentence core message + one-line verdict"}}`.
"""
