"""Step 3a: per-frame face tracking with MediaPipe FaceLandmarker.

Output JSON: {"fps", "width", "height", "frames": [[t, cx, cy, face_h] | [t, null, null, null]]}
cx, cy, face_h are normalised to the source frame (0..1).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import cv2
import numpy as np

MODEL_PATH = Path(__file__).resolve().parents[2] / "models" / "face_landmarker.task"
SAMPLE_FPS = 12.0  # enough for a smoothed crop path


def track_faces(video_path: Path, out_json: Path, sample_fps: float = SAMPLE_FPS) -> dict:
    if out_json.exists():
        return json.loads(out_json.read_text(encoding="utf-8"))
    import mediapipe as mp
    from mediapipe.tasks.python import BaseOptions, vision

    opts = vision.FaceLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=str(MODEL_PATH)),
        running_mode=vision.RunningMode.VIDEO, num_faces=1,
        min_face_detection_confidence=0.4, min_tracking_confidence=0.4,
    )
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"cannot open {video_path}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    step = max(1, int(round(fps / sample_fps)))
    frames: list[list] = []
    with vision.FaceLandmarker.create_from_options(opts) as lm:
        idx = 0
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            if idx % step == 0:
                t = idx / fps
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img = mp.Image(image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(rgb))
                res = lm.detect_for_video(img, int(t * 1000))
                if res.face_landmarks:
                    pts = np.array([[p.x, p.y] for p in res.face_landmarks[0]])
                    x0, y0 = pts.min(axis=0)
                    x1, y1 = pts.max(axis=0)
                    frames.append([round(t, 3), round(float((x0 + x1) / 2), 4),
                                   round(float((y0 + y1) / 2), 4), round(float(y1 - y0), 4)])
                else:
                    frames.append([round(t, 3), None, None, None])
            idx += 1
    cap.release()
    out = {"fps": fps, "width": w, "height": h, "frames": frames}
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(out), encoding="utf-8")
    return out


def face_path(track: dict) -> tuple[np.ndarray, np.ndarray]:
    """Return (times, [cx, cy, fh]) with gaps interpolated and smoothed."""
    rows = track["frames"]
    t = np.array([r[0] for r in rows], dtype=float)
    vals = np.array([[np.nan if v is None else v for v in r[1:]] for r in rows], dtype=float)
    for c in range(3):
        col = vals[:, c]
        good = ~np.isnan(col)
        if good.sum() == 0:
            col[:] = [0.5, 0.4, 0.3][c]
        else:
            col[~good] = np.interp(t[~good], t[good], col[good])
        vals[:, c] = col
    # centred moving average (~0.5 s) to kill jitter
    k = max(1, int(round(0.5 * len(t) / max(t[-1], 1e-6))))
    if k > 1:
        kernel = np.ones(k) / k
        for c in range(3):
            padded = np.pad(vals[:, c], (k // 2, k - 1 - k // 2), mode="edge")
            vals[:, c] = np.convolve(padded, kernel, mode="valid")
    return t, vals


if __name__ == "__main__":
    tr = track_faces(Path(sys.argv[1]), Path(sys.argv[2]))
    miss = sum(1 for r in tr["frames"] if r[1] is None)
    print(f"frames={len(tr['frames'])} missing={miss}")
