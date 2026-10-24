"""Frame-sampled measurements: sharpness, colour, motion, face position, OCR captions.

Streams the video once with OpenCV, keeping only per-sample statistics (no frame
buffer), so memory stays flat for long clips.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field

import cv2
import numpy as np

ANALYSIS_W = 540                     # analysis width (height keeps aspect)
FACE_MODEL = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "models",
                                           "face_landmarker.task"))
OCR_MIN_SCORE = 0.6
VISION_VERSION = 2            # bump when sampling/detection changes (invalidates cache)


@dataclass
class FaceObs:
    t: float
    cx: float          # normalised centre x (0-1)
    cy: float
    top: float         # normalised bbox top
    h: float           # normalised bbox height


@dataclass
class TextBox:
    text: str
    score: float
    x0: float          # normalised bbox
    y0: float
    x1: float
    y1: float


@dataclass
class OcrObs:
    t: float
    boxes: list[TextBox]


@dataclass
class VisionStats:
    sample_times: list[float] = field(default_factory=list)
    sharpness: list[float] = field(default_factory=list)     # Laplacian variance
    brightness: list[float] = field(default_factory=list)    # HSV V mean 0-255
    saturation: list[float] = field(default_factory=list)    # HSV S mean 0-255
    motion: list[float] = field(default_factory=list)        # mean |diff| vs prev sample
    faces: list[FaceObs] = field(default_factory=list)
    face_detector: str = "none"
    ocr: list[OcrObs] = field(default_factory=list)
    ocr_enabled: bool = False


class _FaceDetector:
    """mediapipe FaceLandmarker if the model exists, else OpenCV Haar cascade."""

    def __init__(self) -> None:
        self.kind = "none"
        self._mp = None
        self._haar = None
        if os.path.exists(FACE_MODEL):
            try:
                import mediapipe as mp
                from mediapipe.tasks.python import vision as mpv
                from mediapipe.tasks.python.core.base_options import BaseOptions
                opts = mpv.FaceLandmarkerOptions(
                    base_options=BaseOptions(model_asset_path=FACE_MODEL), num_faces=1)
                self._mp = (mp, mpv.FaceLandmarker.create_from_options(opts))
                self.kind = "mediapipe-face_landmarker"
            except Exception as exc:  # fall back, but say why
                print(f"[warn] mediapipe unavailable ({exc}); using Haar cascade")
        if self._mp is None:
            self._haar = cv2.CascadeClassifier(
                os.path.join(cv2.data.haarcascades, "haarcascade_frontalface_default.xml"))
            self.kind = "opencv-haar"

    def detect(self, bgr: np.ndarray, t: float) -> FaceObs | None:
        h, w = bgr.shape[:2]
        if self._mp is not None:
            mp, landmarker = self._mp
            img = mp.Image(image_format=mp.ImageFormat.SRGB,
                           data=cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))
            res = landmarker.detect(img)
            if not res.face_landmarks:
                return None
            xs = [p.x for p in res.face_landmarks[0]]
            ys = [p.y for p in res.face_landmarks[0]]
            x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
        else:
            gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
            found = self._haar.detectMultiScale(gray, 1.1, 5, minSize=(w // 12, w // 12))
            if len(found) == 0:
                return None
            fx, fy, fw, fh = max(found, key=lambda r: r[2] * r[3])
            x0, x1, y0, y1 = fx / w, (fx + fw) / w, fy / h, (fy + fh) / h
        return FaceObs(t, (x0 + x1) / 2, (y0 + y1) / 2, y0, y1 - y0)

    def close(self) -> None:
        if self._mp is not None:
            self._mp[1].close()


class _Ocr:
    def __init__(self, lang: str) -> None:
        from rapidocr import LangRec, ModelType, OCRVersion, RapidOCR
        lang_map = {"ko": LangRec.KOREAN, "en": LangRec.EN, "ja": LangRec.JAPAN,
                    "zh": LangRec.CH}
        params = {"Rec.lang_type": lang_map.get(lang, LangRec.KOREAN),
                  "Rec.ocr_version": OCRVersion.PPOCRV5,
                  "Rec.model_type": ModelType.MOBILE}
        if lang == "zh":
            params = {}
        self._eng = RapidOCR(params=params)

    def read(self, bgr: np.ndarray) -> list[TextBox]:
        h, w = bgr.shape[:2]
        # no text-angle classifier: video text is always upright, and the classifier flips large
        # white outlined captions upside down (a short Korean phrase came back as Latin garbage)
        res = self._eng(bgr, use_cls=False)
        if res.boxes is None or res.txts is None:
            return []
        out = []
        for box, txt, score in zip(res.boxes, res.txts, res.scores):
            if score < OCR_MIN_SCORE or not str(txt).strip():
                continue
            pts = np.asarray(box, dtype=float)
            out.append(TextBox(str(txt).strip(), float(score),
                               pts[:, 0].min() / w, pts[:, 1].min() / h,
                               pts[:, 0].max() / w, pts[:, 1].max() / h))
        return out


def analyze(path: str, sample_fps: float = 4.0, ocr_fps: float = 3.0,
            use_ocr: bool = True, lang: str = "ko") -> VisionStats:
    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        raise RuntimeError(f"OpenCV cannot open {path}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    stats = VisionStats()
    faces = _FaceDetector()
    stats.face_detector = faces.kind
    ocr = None
    if use_ocr:
        try:
            ocr = _Ocr(lang)
            stats.ocr_enabled = True
        except Exception as exc:
            print(f"[warn] OCR disabled: {exc}")
    next_sample, next_ocr, prev_gray, idx = 0.0, 0.0, None, 0
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            t = idx / fps
            idx += 1
            do_sample = t + 1e-6 >= next_sample
            do_ocr = ocr is not None and t + 1e-6 >= next_ocr
            if not (do_sample or do_ocr):
                continue
            small = _resize(frame)
            if do_sample:
                next_sample += 1.0 / sample_fps
                prev_gray = _sample_stats(stats, small, t, prev_gray)
                face = faces.detect(small, t)
                if face:
                    stats.faces.append(face)
            if do_ocr:
                next_ocr += 1.0 / ocr_fps
                stats.ocr.append(OcrObs(t, ocr.read(small)))
    finally:
        cap.release()
        faces.close()
    return stats


def _resize(frame: np.ndarray) -> np.ndarray:
    h, w = frame.shape[:2]
    if w == ANALYSIS_W:
        return frame
    return cv2.resize(frame, (ANALYSIS_W, int(round(h * ANALYSIS_W / w))),
                      interpolation=cv2.INTER_AREA)


def _sample_stats(stats: VisionStats, small: np.ndarray, t: float, prev_gray):
    gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
    hsv = cv2.cvtColor(small, cv2.COLOR_BGR2HSV)
    stats.sample_times.append(t)
    stats.sharpness.append(float(cv2.Laplacian(gray, cv2.CV_64F).var()))
    stats.saturation.append(float(hsv[:, :, 1].mean()))
    stats.brightness.append(float(hsv[:, :, 2].mean()))
    if prev_gray is not None and prev_gray.shape == gray.shape:
        stats.motion.append(float(cv2.absdiff(gray, prev_gray).mean()))
    return gray


def caption_region_signature(path: str, times: list[float], region: tuple[float, float, float, float]):
    """Return small grayscale crops of `region` (normalised x0,y0,x1,y1) at each time."""
    cap = cv2.VideoCapture(path)
    out = []
    try:
        for t in times:
            cap.set(cv2.CAP_PROP_POS_MSEC, max(t, 0) * 1000.0)
            ok, frame = cap.read()
            if not ok:
                out.append(None)
                continue
            h, w = frame.shape[:2]
            x0, y0, x1, y1 = region
            crop = frame[int(y0 * h):max(int(y1 * h), int(y0 * h) + 2),
                         int(x0 * w):max(int(x1 * w), int(x0 * w) + 2)]
            crop = cv2.resize(cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY), (160, 48))
            out.append(crop.astype(np.float32))
    finally:
        cap.release()
    return out
