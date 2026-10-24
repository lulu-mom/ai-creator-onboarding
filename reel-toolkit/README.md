# reel-toolkit

Automatic editor for vertical (9:16) Korean talking-head reels, plus a quality scorer.
Used by the `reel-maker` and `reel-style-*` skills in this repository (`../skills/`).

- `pipeline/make_reel.py` — one command: transcribe (faster-whisper) -> VAD + bad-take/filler cut ->
  face track (MediaPipe) -> plan captions / layouts / UI cards -> HyperFrames project -> render ->
  SFX + loudness -> mux.
- `pipeline/styles/*.json` — visual styles: `reference.json` (split-card: cream background, UI card on top,
  face below, 1-3 word captions with orange key words), `bold-talk.json`, `news-brief.json`, `doodle.json`.
- `pipeline/plans/example*.json` — generic content plans (cards anchored to transcript words) for one sample
  script, one per style. Copy one and rewrite it for your own video.
- `quality/reel_score.py` — technical / editing metrics plus a blind "Content & Craft" judge pack (C1-C11)
  for independent judge agents.
- `styles/STYLE_CATALOG.md` — catalog of planned styles and the `reel-style-*` skill layout.

## Setup (Windows)

`skills/ai-creator-onboarding/scripts/setup.ps1` does all of this automatically. Manual steps:

Prerequisites: Python 3.11+, Node.js 20+, git, ffmpeg (`winget install --id Gyan.FFmpeg -e`).

```powershell
git clone --depth 1 --filter=blob:none --sparse https://github.com/lulu-mom/ai-creator-onboarding "$HOME\projects\ai-creator-onboarding"
git -C "$HOME\projects\ai-creator-onboarding" sparse-checkout set reel-toolkit
cd "$HOME\projects\ai-creator-onboarding\reel-toolkit"
npm i
npx playwright install chromium
New-Item -ItemType Directory -Force models | Out-Null
curl.exe -L -o models/face_landmarker.task https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task
python -m pip install faster-whisper mediapipe opencv-contrib-python silero-vad rapidocr pytest pillow numpy
```

Check: `python pipeline/make_reel.py --help` and `python -m pytest -q` (inside `reel-toolkit`).

The first transcription downloads the Whisper model (Hugging Face cache). A CUDA GPU is used when
available, otherwise CPU int8.

## Make a reel

```powershell
python pipeline/make_reel.py --input <video.mp4> --out out/<name>.mp4 `
  --style pipeline/styles/reference.json --plan work/<name>/content_plan.json --quality standard
```

- Intermediate files are cached in `work/<input-stem>/` (`transcript.json`, `cuts.json`, `words.json`,
  `plan.json`, `hf/`). Re-running with a new plan or style reuses the transcript, VAD and face track.
  Delete the folder to start fresh.
- `--no-render` stops after writing the HyperFrames project (fast plan check).
- A render takes about 4-20 minutes depending on length and machine.
- The input needs Korean speech and a visible face (the crop follows the face; without one it centres).

## Score a reel

```powershell
python quality/reel_score.py --output out/<name>.mp4 --words out/<name>.words.json `
  --json out/reports/<name>.json --frames 8 --judge-pack out/judge_<name>
# two independent judge agents read out/judge_<name>/JUDGE_PROMPT.md and write scores_j1.json / scores_j2.json
python quality/reel_score.py --output out/<name>.mp4 --words out/<name>.words.json `
  --content-scores out/judge_<name>/scores_j1.json out/judge_<name>/scores_j2.json
```

`--reference <reel.mp4>` adds a side-by-side comparison against a reference reel of your own (not included).

## Privacy

Footage, transcripts, `words.json`, renders, `work/` and `out/` are git-ignored. Content plans for real videos
contain the speaker's words: keep them in `work/<stem>/`, never in `pipeline/plans/` (only the generic
`example*.json` plans live there).

## Style: news brief (`pipeline/styles/news-brief.json`)

Navy headline bar with the current section (chip + title), numbered chapter cards (1/3, 2/3, 3/3) that wipe over the
content area, broadcast lower-third captions (red key-word blocks on the spoken word) and a bottom ticker.
All engine options are opt-in; styles without them render exactly as before.

- Style keys: `layout.stage_cy / stage_graphic_cy / graphic_scale / fit_max_h / kicker_top / face_full_top`,
  `graphics.extra_css` (card restyle), `graphics.exit` (card exit override, `{"*": "<GSAP vars>"}`),
  `captions.style: "lower_third"` (+ `captions.bar`, `captions.letter_spacing`), `overlays.newsdesk`.
- Plan keys: `sections` (`anchor`, `chip`, `title`, `chip_style: "alert"`, `sweep`, `sweep_title`), `ticker_items`,
  `newsdesk` (`brand`, `date`, `source`, `live`), `caption_keep` (phrases never split, broken at their edges),
  `cold_open_from` (start the cold-open teaser at a later word), `results.flag` (`["<item>_<line>"]` in red).
- Example plan: `pipeline/plans/example_news.json`.
- Score with a fixed caption band: `python quality/reel_score.py ... --caption-band 0.54,0.64`.

## Style: bold talk (`pipeline/styles/bold-talk.json`)

Big outlined word-karaoke captions over a continuous speaker. Content appears in a floating panel above the speaker
(scene `params.layout: "split"`, template `panel`: role `setup` / `result` / `warn`, `tag`, `big`, `lines` | `number` |
`icons`), with 2-4 full-screen hero slams (template `slam`, `hero`, `foot`). Consecutive panels swap in place.
Opt-in keys: `layout.split_fade / split_punch / return_punch_from`, `graphics.host_z`, `captions.emphasis.warn_words`.
Example plan: `pipeline/plans/example_bold.json`. Score with `--caption-band 0.54,0.64`.

## Style: doodle (`pipeline/styles/doodle.json`)

Paper board (procedural paper texture + grid) on top, full-width face below a torn paper edge. Hand-drawn boxes,
arrows, circles and highlighter draw on in sync with speech (`dd_*` templates in `pipeline/graphics/doodle_templates.py`).
Example plan: `pipeline/plans/example_doodle.json`. Score with `--caption-band 0.45,0.55`.

## Fonts

`pipeline/assets/fonts/`: Pretendard (SIL OFL 1.1) and Gaegu (SIL OFL 1.1); license files alongside.
