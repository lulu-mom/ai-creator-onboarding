"""ffprobe / ffmpeg filter based measurements (no Python deps beyond stdlib).

One ffmpeg pass collects: blackdetect, freezedetect, scdet (video) and
ebur128 + silencedetect (audio).
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from dataclasses import dataclass, field

SCALE_W, SCALE_H = 270, 480          # downscale for fast video filters
SCDET_THRESHOLD = 10.0               # scdet score (0-100) counted as a cut
SILENCE_NOISE_DB = -35               # silencedetect noise floor
SILENCE_MIN_S = 0.35                 # silencedetect minimum duration
BLACK_MIN_S = 0.1
FREEZE_MIN_S = 1.0


def _bin(name: str) -> str:
    path = shutil.which(name)
    if not path:
        raise RuntimeError(f"{name} not found on PATH (refresh PATH: Machine + User)")
    return path


def _run(cmd: list[str], timeout: int = 1800) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                          errors="replace", timeout=timeout)


@dataclass
class StreamInfo:
    width: int = 0
    height: int = 0
    fps: float = 0.0
    duration: float = 0.0
    video_bitrate: float = 0.0   # bits/s
    video_codec: str = ""
    has_audio: bool = False
    audio_codec: str = ""
    sample_rate: int = 0


def ffprobe(path: str) -> StreamInfo:
    res = _run([_bin("ffprobe"), "-v", "error", "-show_streams", "-show_format",
                "-of", "json", path])
    if res.returncode != 0:
        raise RuntimeError(f"ffprobe failed for {path}: {res.stderr.strip()[:300]}")
    data = json.loads(res.stdout)
    info = StreamInfo()
    fmt = data.get("format", {})
    info.duration = float(fmt.get("duration") or 0)
    total_br = float(fmt.get("bit_rate") or 0)
    audio_br = 0.0
    for st in data.get("streams", []):
        if st.get("codec_type") == "video" and not info.width:
            info.width, info.height = int(st["width"]), int(st["height"])
            num, _, den = (st.get("avg_frame_rate") or "0/1").partition("/")
            info.fps = float(num) / float(den or 1) if float(den or 1) else 0.0
            info.video_bitrate = float(st.get("bit_rate") or 0)
            info.video_codec = st.get("codec_name", "")
            rot = _rotation(st)
            if rot in (90, 270):
                info.width, info.height = info.height, info.width
        elif st.get("codec_type") == "audio" and not info.has_audio:
            info.has_audio = True
            info.audio_codec = st.get("codec_name", "")
            info.sample_rate = int(st.get("sample_rate") or 0)
            audio_br = float(st.get("bit_rate") or 0)
    if not info.video_bitrate and total_br:
        info.video_bitrate = max(total_br - audio_br, 0)
    return info


def _rotation(stream: dict) -> int:
    for sd in stream.get("side_data_list", []) or []:
        if "rotation" in sd:
            return abs(int(sd["rotation"])) % 360
    return abs(int((stream.get("tags") or {}).get("rotate", 0))) % 360


@dataclass
class FilterStats:
    loudness_i: float | None = None      # LUFS
    loudness_lra: float | None = None    # LU
    true_peak: float | None = None       # dBTP
    silences: list[tuple[float, float]] = field(default_factory=list)
    blacks: list[tuple[float, float]] = field(default_factory=list)
    freezes: list[tuple[float, float]] = field(default_factory=list)
    cut_times: list[float] = field(default_factory=list)


_FLOAT = r"(-?\d+(?:\.\d+)?|-?inf|nan)"


def analyze_filters(path: str, info: StreamInfo) -> FilterStats:
    vchain = (f"[0:v]scale={SCALE_W}:{SCALE_H},"
              f"blackdetect=d={BLACK_MIN_S}:pix_th=0.10,"
              f"freezedetect=n=-60dB:d={FREEZE_MIN_S},"
              f"scdet=threshold={SCDET_THRESHOLD}:sc_pass=0[v]")
    graph = vchain
    maps = ["-map", "[v]"]
    if info.has_audio:
        graph += (f";[0:a]ebur128=peak=true,"
                  f"silencedetect=noise={SILENCE_NOISE_DB}dB:d={SILENCE_MIN_S}[a]")
        maps += ["-map", "[a]"]
    res = _run([_bin("ffmpeg"), "-hide_banner", "-nostats", "-i", path,
                "-filter_complex", graph, *maps, "-f", "null", "-"])
    if res.returncode != 0:
        raise RuntimeError(f"ffmpeg filter pass failed: {res.stderr.strip()[-400:]}")
    return parse_filter_log(res.stderr, info.duration)


def parse_filter_log(log: str, duration: float) -> FilterStats:
    st = FilterStats()
    summary = log[log.rfind("Summary:"):] if "Summary:" in log else ""
    if summary:
        st.loudness_i = _grab(rf"I:\s+{_FLOAT}\s+LUFS", summary)
        st.loudness_lra = _grab(rf"LRA:\s+{_FLOAT}\s+LU\b", summary)
        st.true_peak = _grab(rf"Peak:\s+{_FLOAT}\s+dBFS", summary)
    st.silences = _pairs(log, r"silence_start:\s*" + _FLOAT, r"silence_end:\s*" + _FLOAT, duration)
    st.blacks = [(float(a), float(b)) for a, b in
                 re.findall(rf"black_start:{_FLOAT}\s+black_end:{_FLOAT}", log)]
    st.freezes = _pairs(log, r"freeze_start:\s*" + _FLOAT, r"freeze_end:\s*" + _FLOAT, duration)
    st.cut_times = sorted(float(t) for t in re.findall(rf"lavfi\.scd\.time:\s*{_FLOAT}", log))
    return st


def _grab(pattern: str, text: str) -> float | None:
    m = re.findall(pattern, text)
    if not m:
        return None
    try:
        val = float(m[-1])
    except ValueError:
        return None
    return val if val == val and abs(val) != float("inf") else None


def _pairs(log: str, start_pat: str, end_pat: str, duration: float) -> list[tuple[float, float]]:
    """Pair start/end events in log order; an unterminated start ends at duration."""
    events = sorted(
        [(m.start(), "s", float(m.group(1))) for m in re.finditer(start_pat, log)]
        + [(m.start(), "e", float(m.group(1))) for m in re.finditer(end_pat, log)])
    out, cur = [], None
    for _, kind, t in events:
        if kind == "s":
            cur = t
        elif cur is not None:
            out.append((max(cur, 0.0), t))
            cur = None
    if cur is not None and duration:
        out.append((max(cur, 0.0), duration))
    return out


def extract_frame(path: str, t: float, width: int = 360):
    """Grab one frame at time t as a BGR numpy array (via ffmpeg, accurate seek)."""
    import numpy as np
    res = subprocess.run(
        [_bin("ffmpeg"), "-hide_banner", "-loglevel", "error", "-ss", f"{max(t, 0):.3f}",
         "-i", path, "-frames:v", "1", "-vf", f"scale={width}:-2", "-f", "image2pipe",
         "-vcodec", "png", "-"], capture_output=True, timeout=120)
    if res.returncode != 0 or not res.stdout:
        return None
    import cv2
    return cv2.imdecode(np.frombuffer(res.stdout, np.uint8), cv2.IMREAD_COLOR)
