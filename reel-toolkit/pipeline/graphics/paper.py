"""Procedural paper texture (no image assets): warm base, soft mottling, grain, fibres
and an optional faint graph-paper grid. Deterministic for a given seed."""
from __future__ import annotations

from pathlib import Path

import numpy as np


def _hex(c: str) -> np.ndarray:
    c = c.lstrip("#")
    return np.array([int(c[i:i + 2], 16) for i in (0, 2, 4)], dtype=np.float32)


def _smooth_noise(h: int, w: int, cell: int, rng: np.random.Generator) -> np.ndarray:
    """Bilinear-upsampled value noise in [-1, 1]."""
    gh, gw = h // cell + 2, w // cell + 2
    g = rng.uniform(-1, 1, (gh, gw)).astype(np.float32)
    ys = np.linspace(0, gh - 1.001, h)
    xs = np.linspace(0, gw - 1.001, w)
    y0, x0 = ys.astype(int), xs.astype(int)
    fy, fx = (ys - y0)[:, None], (xs - x0)[None, :]
    a = g[y0][:, x0]
    b = g[y0][:, x0 + 1]
    c = g[y0 + 1][:, x0]
    d = g[y0 + 1][:, x0 + 1]
    return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy


def paper_texture(width: int, height: int, base: str, grid: str | None = None, grid_px: int = 0,
                  seed: int = 7) -> np.ndarray:
    """Return an HxWx3 uint8 paper image."""
    rng = np.random.default_rng(seed)
    img = np.broadcast_to(_hex(base), (height, width, 3)).copy()
    mottle = 0.6 * _smooth_noise(height, width, 180, rng) + 0.4 * _smooth_noise(height, width, 60, rng)
    img += mottle[..., None] * 4.0
    img += rng.normal(0, 2.2, (height, width))[..., None]
    if grid and grid_px > 0:
        gcol = _hex(grid)
        lines = np.zeros((height, width), dtype=np.float32)
        lines[:, ::grid_px] = 1.0
        lines[::grid_px, :] = 1.0
        wobble = 0.55 + 0.45 * (0.5 + 0.5 * _smooth_noise(height, width, 90, rng))
        a = (lines * wobble)[..., None] * 0.55
        img = img * (1 - a) + gcol * a
    # a few faint fibres
    for _ in range(140):
        x, y = rng.integers(0, width), rng.integers(0, height)
        ln = rng.integers(8, 28)
        ang = rng.uniform(0, np.pi)
        for k in range(ln):
            xx, yy = int(x + k * np.cos(ang)), int(y + k * np.sin(ang))
            if 0 <= xx < width and 0 <= yy < height:
                img[yy, xx] -= 6.0
    return np.clip(img, 0, 255).astype(np.uint8)


def write_paper(out_png: Path, width: int, height: int, cfg: dict, colors: dict) -> None:
    from PIL import Image
    base = colors.get(cfg.get("color", "background"), cfg.get("color", "#FAF7F0"))
    grid = colors.get(cfg.get("grid_color", "grid"), cfg.get("grid_color")) if cfg.get("grid_px") else None
    arr = paper_texture(width, height, base, grid, int(cfg.get("grid_px", 0)), int(cfg.get("seed", 7)))
    Image.fromarray(arr).save(out_png, optimize=True)
