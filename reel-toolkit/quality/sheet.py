"""Contact sheet of paired reference|output frames for the visual review step."""
from __future__ import annotations

import os

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

import probe

CELL_W = 300                     # each frame cell width (height = 16:9 portrait)
CELL_H = CELL_W * 16 // 9
LABEL_H = 34
PAIRS_PER_ROW = 3
FONT_PATH = r"C:\Windows\Fonts\malgun.ttf"


def _font(size: int):
    try:
        return ImageFont.truetype(FONT_PATH, size)
    except OSError:
        return ImageFont.load_default()


def _cell(path: str, t: float, zone) -> Image.Image:
    frame = probe.extract_frame(path, t, CELL_W)
    if frame is None:
        frame = np.zeros((CELL_H, CELL_W, 3), np.uint8)
    frame = cv2.resize(frame, (CELL_W, CELL_H), interpolation=cv2.INTER_AREA)
    img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    if zone:  # dashed-ish IG safe-zone guide
        d = ImageDraw.Draw(img)
        x0, y0, x1, y1 = (zone[0] * CELL_W, zone[1] * CELL_H, zone[2] * CELL_W, zone[3] * CELL_H)
        d.rectangle([x0, y0, x1, y1], outline=(0, 255, 120), width=1)
    return img


def contact_sheet(output: str, reference: str | None, n: int, dest: str, zone=None) -> str:
    """Frames sampled at the same relative position ((i+0.5)/n) in both videos."""
    out_dur = probe.ffprobe(output).duration
    ref_dur = probe.ffprobe(reference).duration if reference else 0
    videos = ([("REF", reference, ref_dur)] if reference else []) + [("OUT", output, out_dur)]
    pair_w = CELL_W * len(videos) + 12
    rows = (n + PAIRS_PER_ROW - 1) // PAIRS_PER_ROW
    sheet = Image.new("RGB", (pair_w * min(n, PAIRS_PER_ROW) + 12, rows * (CELL_H + LABEL_H) + 12),
                      (24, 24, 28))
    draw, font = ImageDraw.Draw(sheet), _font(16)
    for i in range(n):
        frac = (i + 0.5) / n
        ox = 12 + (i % PAIRS_PER_ROW) * pair_w
        oy = 12 + (i // PAIRS_PER_ROW) * (CELL_H + LABEL_H)
        for j, (tag, path, dur) in enumerate(videos):
            t = frac * dur
            sheet.paste(_cell(path, t, zone if tag == "OUT" else None), (ox + j * CELL_W, oy + LABEL_H))
            draw.text((ox + j * CELL_W + 4, oy + 6), f"#{i + 1} {tag} {t:5.1f}s",
                      fill=(255, 220, 90) if tag == "REF" else (120, 220, 255), font=font)
    os.makedirs(os.path.dirname(os.path.abspath(dest)), exist_ok=True)
    sheet.save(dest)
    return dest
