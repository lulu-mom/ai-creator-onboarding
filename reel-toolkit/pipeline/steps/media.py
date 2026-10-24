"""FFmpeg media steps: edit the source by keep-intervals, synthesize SFX, mix + loudnorm, mux."""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import wave
from pathlib import Path

import numpy as np

SR = 48000
GRADE = "eq=gamma=1.26:brightness=0.03:contrast=1.07:saturation=0.92"


def grade_filter(style: dict) -> str:
    """ffmpeg eq filter for the style's colour grade (style "grade"; default = GRADE)."""
    g = style.get("grade")
    if not g:
        return GRADE
    if isinstance(g, str):
        return g
    return (f"eq=gamma={g.get('gamma', 1.0)}:brightness={g.get('brightness', 0.0)}"
            f":contrast={g.get('contrast', 1.0)}:saturation={g.get('saturation', 1.0)}")


def ffmpeg_bin(name: str = "ffmpeg") -> str:
    exe = shutil.which(name)
    if not exe:
        raise RuntimeError(f"{name} not found on PATH")
    return exe


def run(cmd: list[str], capture: bool = False) -> str:
    res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if res.returncode != 0:
        raise RuntimeError(f"command failed ({res.returncode}): {' '.join(cmd[:6])}...\n{res.stderr[-3000:]}")
    return res.stderr if capture else ""


def probe(path: Path) -> dict:
    out = subprocess.run([ffmpeg_bin("ffprobe"), "-v", "error", "-print_format", "json", "-show_streams",
                          "-show_format", str(path)], capture_output=True, text=True, encoding="utf-8")
    return json.loads(out.stdout)


def snap_keeps(keeps: list[list[float]], fps: float) -> list[list[float]]:
    """Snap intervals to the source frame grid so video and audio cuts stay in sync."""
    out = []
    for s, e in keeps:
        a, b = round(s * fps) / fps, round(e * fps) / fps
        if b - a >= 2 / fps:
            out.append([round(a, 5), round(b, 5)])
    return out


def edit_video(src: Path, keeps: list[list[float]], out_mp4: Path, out_wav: Path, speed: float = 1.0,
               width: int = 1080,
               grade: str | None = None) -> None:
    grade = grade or GRADE
    parts, vlab, alab = [], [], []
    for i, (s, e) in enumerate(keeps):
        d = e - s
        parts.append(f"[0:v]trim=start={s:.5f}:end={e:.5f},setpts=PTS-STARTPTS[v{i}]")
        parts.append(f"[0:a]atrim=start={s:.5f}:end={e:.5f},asetpts=PTS-STARTPTS,"
                     f"afade=t=in:d=0.008,afade=t=out:st={max(0, d - 0.012):.4f}:d=0.012[a{i}]")
        vlab.append(f"[v{i}]")
        alab.append(f"[a{i}]")
    n = len(keeps)
    parts.append(f"{''.join(vlab)}concat=n={n}:v=1:a=0[vc]")
    parts.append(f"{''.join(alab)}concat=n={n}:v=0:a=1[ac]")
    parts.append(f"[vc]setpts=PTS/{speed:.4f},fps=30,scale={width}:-2:flags=lanczos,unsharp=5:5:0.55:5:5:0.0,{grade},format=yuv420p[vo]")
    tempo = f"atempo={speed:.4f}," if abs(speed - 1.0) > 1e-3 else ""
    parts.append(f"[ac]{tempo}aresample=48000,aformat=channel_layouts=stereo[ao]")
    fc = ";\n".join(parts)
    fc_file = out_mp4.with_suffix(".filter.txt")
    fc_file.write_text(fc, encoding="utf-8")
    run([ffmpeg_bin(), "-y", "-v", "error", "-i", str(src), "-/filter_complex", str(fc_file),
         "-map", "[vo]", "-c:v", "libx264", "-preset", "medium", "-crf", "14", "-g", "15", "-an", str(out_mp4),
         "-map", "[ao]", "-c:a", "pcm_s16le", str(out_wav)])


# ------------------------------------------------------------------ SFX synthesis (original, CC0)
def _env(n: int, attack: float, decay: float) -> np.ndarray:
    t = np.arange(n) / SR
    a = np.clip(t / max(attack, 1e-4), 0, 1)
    return a * np.exp(-t / decay)


def _sine_sweep(f0: float, f1: float, dur: float) -> np.ndarray:
    n = int(dur * SR)
    f = np.geomspace(f0, f1, n)
    return np.sin(2 * np.pi * np.cumsum(f) / SR)


def _noise(n: int, seed: int) -> np.ndarray:
    return np.random.default_rng(seed).standard_normal(n)


def _bandpass(x: np.ndarray, lo: float, hi: float) -> np.ndarray:
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    X[(f < lo) | (f > hi)] = 0
    return np.fft.irfft(X, len(x))


def synth(kind: str, seed: int = 0) -> np.ndarray:
    if kind == "pop":
        n = int(0.09 * SR)
        x = _sine_sweep(950, 420, 0.09) * _env(n, 0.002, 0.03)
    elif kind == "tick":
        n = int(0.04 * SR)
        x = np.sin(2 * np.pi * 2400 * np.arange(n) / SR) * _env(n, 0.001, 0.008)
    elif kind == "ding":
        n = int(0.45 * SR)
        t = np.arange(n) / SR
        x = (np.sin(2 * np.pi * 1318 * t) + 0.5 * np.sin(2 * np.pi * 1976 * t)) * _env(n, 0.003, 0.12)
    elif kind == "whoosh":
        n = int(0.32 * SR)
        x = _bandpass(_noise(n, seed), 500, 5000)
        t = np.linspace(0, 1, n)
        x *= np.sin(np.pi * t) ** 2 * 0.6
    elif kind == "click":
        n = int(0.025 * SR)
        x = _bandpass(_noise(n, seed + 7), 1500, 9000) * _env(n, 0.0005, 0.004)
    elif kind == "stamp":
        n = int(0.22 * SR)
        x = 1.2 * np.sin(2 * np.pi * 95 * np.arange(n) / SR) * _env(n, 0.002, 0.06)
        x += 0.5 * _bandpass(_noise(n, seed + 3), 200, 3000) * _env(n, 0.001, 0.02)
    elif kind == "rise":
        n = int(0.22 * SR)
        x = 0.7 * _sine_sweep(300, 760, 0.22) * _env(n, 0.03, 0.12)
    elif kind == "count":
        n = int(0.5 * SR)
        x = np.zeros(n)
        tk = synth("tick")
        for k in range(6):
            o = int(k * 0.07 * SR * (1 + k * 0.12))
            if o + len(tk) < n:
                x[o:o + len(tk)] += tk * (0.9 - 0.1 * k)
    elif kind == "type":
        n = int(0.4 * SR)
        x = np.zeros(n)
        ck = synth("click", seed)
        for k in range(5):
            o = int(k * 0.075 * SR)
            x[o:o + len(ck)] += ck * 0.7
    elif kind in ("scribble", "marker", "erase"):
        # pen / marker / eraser on paper: band-passed noise with stroke-rate amplitude wobble
        dur, lo, hi, rate = {"scribble": (0.34, 1800, 7000, 11.0), "marker": (0.26, 900, 4200, 7.0),
                             "erase": (0.30, 400, 2600, 16.0)}[kind]
        n = int(dur * SR)
        t = np.arange(n) / SR
        x = _bandpass(_noise(n, seed + 11), lo, hi)
        x *= (0.55 + 0.45 * np.abs(np.sin(np.pi * rate * t))) * np.sin(np.pi * t / dur) ** 0.6
    elif kind == "paper":
        n = int(0.3 * SR)
        x = _bandpass(_noise(n, seed + 5), 300, 4500) * _env(n, 0.02, 0.09)
    else:
        return np.zeros(1)
    peak = np.max(np.abs(x)) or 1.0
    return x / peak


SFX_LEVEL = {"pop": 0.0, "tick": -4.0, "ding": -3.0, "whoosh": -6.0, "click": -2.0, "stamp": 0.0,
             "rise": -5.0, "count": -6.0, "type": -8.0, "cut": -9.0,
             "scribble": -9.0, "marker": -10.0, "erase": -8.0, "paper": -7.0}


def sfx_track(events: list[tuple[float, str]], duration: float, out_wav: Path, gain_db: float) -> int:
    n = int(duration * SR) + SR
    buf = np.zeros(n)
    last_t = -1.0
    used = 0
    for i, (t, kind) in enumerate(sorted(events)):
        if t - last_t < 0.14:
            continue
        snd = synth("whoosh" if kind == "cut" else kind, seed=i)
        if snd.size < 2:
            continue
        g = 10 ** ((gain_db + SFX_LEVEL.get(kind, -4.0)) / 20)
        o = int(t * SR)
        m = min(len(snd), n - o)
        if m <= 0:
            continue
        buf[o:o + m] += snd[:m] * g
        last_t = t
        used += 1
    stereo = np.repeat(np.clip(buf, -1, 1)[:, None], 2, axis=1)
    with wave.open(str(out_wav), "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        wf.writeframes((stereo * 32767).astype(np.int16).tobytes())
    return used


# ------------------------------------------------------------------ mix + loudness
VOICE_CHAIN = ("highpass=f=75,afftdn=nf=-28,equalizer=f=3200:t=q:w=1.2:g=2.5,"
               "acompressor=threshold=-21dB:ratio=3.2:attack=6:release=90:makeup=3")


def mix_and_normalize(voice_wav: Path, sfx_wav: Path | None, out_wav: Path, lufs: float, tp: float,
                      duration: float) -> dict:
    inputs = ["-i", str(voice_wav)] + (["-i", str(sfx_wav)] if sfx_wav else [])
    if sfx_wav:
        pre = f"[0:a]{VOICE_CHAIN}[v];[v][1:a]amix=inputs=2:normalize=0:duration=first[m]"
    else:
        pre = f"[0:a]{VOICE_CHAIN}[m]"
    ln = f"loudnorm=I={lufs}:TP={tp}:LRA=9"
    err = run([ffmpeg_bin(), "-y", "-hide_banner"] + inputs +
              ["-filter_complex", f"{pre};[m]{ln}:print_format=json[o]", "-map", "[o]", "-f", "null", "-"],
              capture=True)
    js = json.loads(re.findall(r"\{[^{}]*\"input_i\"[^{}]*\}", err)[-1])
    meas = (f":measured_I={js['input_i']}:measured_TP={js['input_tp']}:measured_LRA={js['input_lra']}"
            f":measured_thresh={js['input_thresh']}:offset={js['target_offset']}:linear=true")
    # brickwall safety limiter: loud SFX transients can push the true peak past the target after loudnorm
    # (2 dB headroom for inter-sample peaks added by the AAC encode)
    limiter = f"alimiter=limit={10 ** ((tp - 2.0) / 20):.4f}:attack=1:release=50:level=disabled"
    run([ffmpeg_bin(), "-y", "-v", "error"] + inputs +
        ["-filter_complex", f"{pre};[m]{ln}{meas},aresample=48000,{limiter},atrim=0:{duration:.3f}[o]", "-map", "[o]",
         "-c:a", "pcm_s16le", str(out_wav)])
    return js


def mux(video: Path, audio: Path, out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    run([ffmpeg_bin(), "-y", "-v", "error", "-i", str(video), "-i", str(audio), "-map", "0:v:0", "-map", "1:a:0",
         "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-shortest", "-movflags", "+faststart",
         str(out)])
