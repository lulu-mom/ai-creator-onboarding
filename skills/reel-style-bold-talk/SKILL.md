---
name: reel-style-bold-talk
description: 말하는 얼굴을 계속 보여주면서 화면 가운데 굵은 단어 자막(말하는 단어가 톡 튀고 핵심어는 노랑)이 나오고, 설명이 필요한 문장에서는 얼굴 위에 떠 있는 어두운 패널(노랑=과정, 초록=결과, 빨강=경고)이 내용을 보여주며, 훅·반전·결론·예고에서만 화면 전체 색 카드가 쾅 들어오는 고에너지 토킹헤드 스타일 릴스. Use when the user picks the "큰 자막 토크" style (directly or via reel-maker) or when a Korean talking-head video is assertive / number-heavy / fast-spoken - 강한 주장, 돈·숫자 이야기, 동기부여, "이거 모르면 손해" 꿀팁, 말이 빠른 영상. Runs the reel-toolkit engine with this folder's style.json and a per-video content plan, renders, and loops on the blind-judge quality bar (total >= 86.8, all C1-C11 >= 4).
---

# 릴스 스타일: 큰 자막 토크 (`bold-talk`)

미리보기: `preview.png` (같은 폴더, 예시 대본 + 가짜 화자 그림으로 만든 샘플 프레임). 스타일 값: `style.json` (= 엔진 `pipeline/styles/bold-talk.json` 사본).
계획 예시: `example-plan.json` (= 엔진 `pipeline/plans/example_bold.json`, 보고서 자동화 예시 대본용 일반 계획).
품질: 실제 토킹헤드 영상으로 블라인드 심사 기준(총점 86.8 이상, C1~C11 모두 4 이상)을 통과한 스타일이다.

## 언제 쓰나
- 잘 맞는 영상: 단정형 주장("무조건", "절대", "~입니다"), 돈·숫자 이야기, 동기부여, 꿀팁, 말이 빠른 영상.
- 안 맞는 영상: 차분한 서사(→ 다큐), 화면 녹화 튜토리얼(→ 화면 시연).

## 어떤 모습인가 (세 가지 화면)
- **얼굴 화면**: 말하는 사람이 화면 전체. 자막은 0.585H, Pretendard 900 104px 흰 글자 + 검정 외곽선, 박스 없음.
  말하는 단어가 살짝 커지고(1.06), 핵심어는 노랑, 경고어(안 됩니다·금지·마세요)만 빨강. 단계 이름표 스티커는 이 화면에서만.
- **패널 화면(대부분의 설명)**: 얼굴은 아래(머리 약 y 1500)로 내려가 계속 보이고, 위쪽에 어두운 둥근 패널
  (x 60, y 220, 960×780). 패널 위 색 띠 = 역할(노랑 과정 / 초록 결과 / 빨강 경고), 태그 + 진행 점 3개, 큰 제목 1줄~2줄,
  몸통 하나(행 최대 3줄 / 큰 숫자 / 타일). 자막은 패널과 얼굴 사이 같은 높이에 고정 — 패널이 자막을 절대 지나가지 않는다.
- **히어로 카드(2~4번만)**: 훅·반전·결론·예고에서 화면 전체 색 카드(빨강/검정/노랑) + 아래 한 줄 알약 + 진행 칩. 자막은 어두운 박스.

움직임: 주인공 하나(강조 단어나 숫자가 1.4배에서 쾅), 제목 단어는 올라오며 자리잡음, 행은 그 말을 하는 순간 채워짐.
들어올 때 역할별(과정=살짝 커지며, 결과=위에서 떨어짐, 경고=쾅+흔들림), 이어지는 패널끼리는 제자리에서 넘김(뒤집기 70도 이하,
결과끼리는 내용만 교체), 나갈 때는 컷 직전에 끝남(과정=위로 밀려 나감, 결과=위로 접힘, 경고=태그 쪽으로 접힘).
소리: 핵심어 팝, 숫자 딩, 패널 휙/스탬프. 말 1.15배, -14 LUFS.

## 엔진 위치
PowerShell 에서 PATH 새로고침 후 엔진 위치를 찾는다(없으면 `reel-maker` 스킬 2단계의 설치를 먼저 한다):
```powershell
$env:Path = [Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [Environment]::GetEnvironmentVariable("Path","User")
$ENGINE = @([Environment]::GetEnvironmentVariable("REEL_TOOLKIT_DIR","User"), "$HOME\projects\ai-creator-onboarding\reel-toolkit") |
  Where-Object { $_ -and (Test-Path "$_\pipeline\make_reel.py") } | Select-Object -First 1
```
`$SKILL` = 이 폴더 = 이 SKILL.md 가 있는 곳 (Claude: `$HOME\.claude\skills\reel-style-bold-talk`, Codex: `$HOME\.agents\skills\reel-style-bold-talk`). `<stem>` = 입력 영상 파일 이름(확장자 제외).

## 실행 명령 (이것 하나)
```powershell
cd $ENGINE
python pipeline/make_reel.py --input "<영상.mp4>" --out out/<stem>_bold.mp4 --style "$SKILL\style.json" --plan work/<stem>/content_plan_bold.json
```
계획 파일 없이 돌리면 얼굴 + 큰 자막만 나온다(패널 없음).

## 절차

### a. 받아쓰기 + 컷
```powershell
python pipeline/make_reel.py --input "<영상.mp4>" --out out/<stem>_bold.mp4 --style "$SKILL\style.json" --no-render
```
`work/<stem>/plan.json` 의 자막 조각(chunks)과 시간표를 보고 장면을 나눈다.

### b. 콘텐츠 계획 JSON (`example-plan.json` 을 복사해서 고친다)
개인 영상 계획은 `work/<stem>/` 에 둔다(`pipeline/plans/` 는 공개 저장소).
- `scenes`: 시간 순서대로 장면을 빈틈없이 나열. 각 장면은 `anchor`(그 장면이 시작되는 대본 단어)부터 다음 장면 전까지.
  - 패널: `{"template": "panel", "params": {"layout": "split", "role": "setup|result|warn", "tag", "big", 몸통 하나}}`
    - 몸통: `lines`(최대 3행, 행마다 `"at"` = 그 말을 하는 단어, `tone: good|warn`) / `number`(`{"to":20,"prefix":"+","suffix":"%","source":"100만 → 120만"}`, `at.number`, `at.pulse`) / `icons`(2~3개 타일)
    - `big` 은 짧게(한 줄 9자 안팎), 강조 `<span class="rk-acc">…</span>` 1개, `at.hero` = 강조어가 쾅 들어올 단어
    - `tracker`: 진행 점 상태(`tracker_items` 순서, todo/active/done/warn)
  - 얼굴 쉼: `{"template": "blank", "params": {}}` — 패널 사이 1~2.5초. 패널이 8초 넘게 이어지지 않게 끊어 준다(컷 리듬 점수).
  - 히어로: `{"template": "slam", "params": {"layout": "graphic", "bg": "warn|dark|accent", "hero": true, "tag", "big", "foot", "tracker"}}`, CTA 는 `button`.
- `stickers`: 얼굴 쉼 구간 이름표(`{"anchor","text","icon","tone","side":"center","dur"}`), 순서대로.
- `emphasis`: 노랑으로 칠할 내용어(숫자·결정·금지), `caption_keep`: 한 자막으로 묶을 구절(한 단어 자막 방지), `caption_fixes`: 받아쓰기·띄어쓰기 고치기("안됩니다" → "안 됩니다").
- `drop_sentences`: 빼도 되는 연결 문장(템포), `cold_open` + `cold_open_from`: 반전 문장을 맨 앞 훅으로.

### c. 렌더 + 채점
```powershell
python pipeline/make_reel.py --input "<영상.mp4>" --out out/<stem>_bold.mp4 --style "$SKILL\style.json" --plan work/<stem>/content_plan_bold.json
python quality/reel_score.py --output out/<stem>_bold.mp4 --words out/<stem>_bold.words.json --caption-band 0.54,0.64 --judge-pack out/judge_<stem>_bold
```
새 블라인드 심사관 2명에게 `out/judge_<stem>_bold/JUDGE_PROMPT.md` 만 주고 `scores_j1.json`, `scores_j2.json` 을 받은 뒤
`--content-scores` 로 합친다. 통과 = 총점 86.8 이상 + C1-C11 모두 4 이상.

## 지켜야 할 것 (심사에서 깎였던 것)
- 색 카드 위 자막은 반드시 어두운 박스(빨강 위 빨강, 노랑 위 노랑 강조 금지).
- 패널이 얼굴 위에서 줄어들거나 퇴장하지 않게(퇴장은 컷 직전에 끝남). 행만 먼저 빠져 빈 카드가 보이면 안 됨.
- 숫자 카운트업 중간값 금지(최종값으로 바로). 한 단어 자막·긴 자막 축소 금지(`caption_keep` 으로 조절).
- 얼굴 위치를 더 내리면 얼굴 안전영역(E4) 실패 — `face_split_anchor_y` 0.53 유지.
