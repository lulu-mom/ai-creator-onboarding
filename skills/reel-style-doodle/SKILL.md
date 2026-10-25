---
name: reel-style-doodle
description: 종이(모눈) 배경 위에 손글씨 화살표·동그라미·밑줄·형광펜이 그려지며 개념과 단계를 설명하는 화이트보드 낙서(공부 노트) 스타일 릴스. Use when the user picks the "화이트보드 낙서" / "낙서" / "공부 노트" style (directly or via reel-maker), or when a Korean talking-head video explains a concept, steps, a comparison (A vs B) or a framework - 개념 설명, "○○ 하는 3단계", 첫째·둘째, 차이·방법·원리, 공부·자기계발 요약. Runs the reel-toolkit engine with this folder's style.json and a per-video content plan (dd_* drawn scenes), renders, and loops on the blind-judge quality bar (total >= 86.8, all C1-C11 >= 4).
---

# 릴스 스타일: 화이트보드 낙서 (`doodle`)

미리보기: `preview.png` (같은 폴더, 예시 대본 + 가짜 화자 그림으로 만든 샘플 프레임). 스타일 값: `style.json` (= 엔진 `pipeline/styles/doodle.json` 사본).
품질: 실제 토킹헤드 영상으로 블라인드 심사 기준(총점 86.8 이상, C1~C11 모두 4 이상)을 통과한 스타일이다.

## 언제 쓰나
- 잘 맞는 영상: 개념 설명, "○○ 하는 3단계", 비교(A vs B), 공부·자기계발 요약, 과정 정리, 프레임워크 소개.
  신호: "개념·원리·차이·방법·단계", "첫째·둘째·1단계", "vs·반면", "○○란".
- 안 맞는 영상: 화면 녹화 튜토리얼(→ 화면 시연), 감정·일상 썰(→ 예능 자막), 속보·뉴스(→ 뉴스 브리핑).

## 어떤 모습인가
- 배경: 코드로 만든 종이 질감(얼룩·결·섬유) + 연한 모눈. 위 0~0.47H = 종이 보드, 아래 = 화면 폭 가득한 얼굴(위쪽 경계는 찢어진 종이 가장자리 + 마스킹테이프 2장).
- 보드 그림: 손으로 그린 상자·화살표·동그라미·체크·X·형광펜이 **선이 그려지듯(draw-on)** 나타남. 아이콘도 펜 선으로 그려짐.
  제목·숫자·큰 문구는 손글씨(Gaegu Bold, OFL), 목록·설명 문장은 굵은 고딕(Pretendard 800) — 폰에서도 읽히게.
- 큰 순간(결과 도착!, 잠깐 STOP, 10분!)은 작게 → 크게 튕겼다 자리 잡는 **히어로 등장**.
- 보드 전체 화면(얼굴 없음) 박자: 아래쪽에 손글씨 큰 문구(히어로) + 형광 밑줄 + 보조 한 줄(sub) 또는 **실제 결과물 미니 카드 줄**(예: 10분 / 2시간→10분).
- 얼굴 ↔ 보드 전환: 하드컷 그대로 + 테이프가 떨어지듯 붙고(복귀) 벗겨지며 날아감(퇴장) — 얼굴 자체는 미끄러지지 않는다.
- 자막: 화면 0.5H 고정, 흰 종이띠(살짝 기울임) 76px, 핵심어는 **노란 형광펜이 칠해지는** 강조. 의미 단위로 끊김.
- 모션 위계: 뼈대는 첫 프레임부터 보이되 순서대로 솟아오르며 자리 잡음(스태거), 보조 글자는 빠른 페이드 + 튕기는 상승, 핵심(히어로)은 0.45→1.14→0.97→1 오버슈트.
- 장면 퇴장: 왼쪽/위/축소로 번갈아 0.24초 이동, 투명해지는 건 마지막 0.1초만(잔상 최소).
- 색: 종이 `#FAF7F0`, 연필 `#2B2B2B`, 빨간펜 `#E8590C`, 파란펜 `#1864AB`, 형광 `#FFE066`, 모눈 `#E9E4D8`.
- 소리: 연필 사각(scribble)·마커·종이 효과음(코드로 합성), 말 1.15배, 컷 약 15회/분, -14 LUFS.

## 엔진 위치
이 스타일의 엔진 코드: `pipeline/graphics/doodle_kit.py`, `doodle_templates.py`, `paper.py`.
PowerShell 에서 PATH 새로고침 후 엔진 위치를 찾는다(없으면 `reel-maker` 스킬 2단계의 설치를 먼저 한다):
```powershell
$env:Path = [Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [Environment]::GetEnvironmentVariable("Path","User")
$ENGINE = @([Environment]::GetEnvironmentVariable("REEL_TOOLKIT_DIR","User"), "$HOME\projects\ai-creator-onboarding\reel-toolkit") |
  Where-Object { $_ -and (Test-Path "$_\pipeline\make_reel.py") } | Select-Object -First 1
```
`$SKILL` = 이 폴더 = 이 SKILL.md 가 있는 곳 (Claude: `$HOME\.claude\skills\reel-style-doodle`, Codex: `$HOME\.agents\skills\reel-style-doodle`). `<stem>` = 입력 영상 파일 이름(확장자 제외).

## 실행 명령 (이것 하나)
```powershell
cd $ENGINE
python pipeline/make_reel.py --input "<영상.mp4>" --out out/<stem>_doodle.mp4 --style "$SKILL\style.json" --plan work/<stem>/content_plan_doodle.json --workers 3
```
`--plan` 없이 돌리면 장면마다 손글씨 키워드 + 동그라미(`dd_keyword`)만 나온다. 품질 기준을 넘기려면 아래 b 단계 계획을 꼭 쓴다.

## 절차 (끝까지 자동으로 진행, 중간 확인 없음)

### a. 받아쓰기 + 컷
```powershell
python pipeline/make_reel.py --input "<영상.mp4>" --out out/<stem>_doodle.mp4 --style "$SKILL\style.json" --no-render
```
`work/<stem>/` 에 `transcript.json`, `cuts.json`, `plan.json`(자막·장면 시각) 이 생긴다. 다른 스타일로 돌린 캐시가 있으면 그대로 쓴다.

### b. 콘텐츠 계획 JSON (점수를 가장 크게 좌우)
대본을 끝까지 읽고 핵심 한 문장 + 구조(훅 → 질문 → 단계/항목 → 결과 → 반전/주의 → 결론(질문에 답) → 예고/CTA)를 정한 뒤
`work/<stem>/content_plan_doodle.json` 에 쓴다. 개인 영상 계획은 `pipeline/plans/` 에 두지 않는다(공개 저장소).
예시(예시 대본 기준 일반 계획): `$ENGINE\pipeline\plans\example_doodle.json`.

공통 키: `emphasis`(형광펜 칠할 단어, 숫자·핵심 명사 위주), `graphic`(보드 전체 화면으로 갈 앵커 문구, 9~12개 — 너무 적으면 컷이 모자라 E2 감점,
너무 많으면 얼굴이 자꾸 깜빡임), `drop_sentences`(편집으로 뺄 문장), `cold_open` + `cold_open_from`(반전 문장을 맨 앞으로, 접속사 제외),
`caption_keep`(자막에서 쪼개지 않을 구절 — 절·서술어 단위로 꼼꼼히), `caption_fixes`(자막 오타 교정, 예: `{"않을": "않은"}` — caption_keep 구절은 교정 전 원문으로 적는다), `auto_gap: 99`.

장면(`scenes`): `{"anchor": "<대본 문구>", "template": "dd_*", "params": {...}}` — `params.at` 은 박자 이름 → 대본 단어.
| template | 용도 | 주요 params | at |
|---|---|---|---|
| `dd_stop` | 훅/반전: 결과 종이 → 보내기 버튼에 빨간 X + 동그라미 경고 | title, items[3], button, stamp | block |
| `dd_branch` | 나 → 여러 일 분배(화살표 3갈래) | center, items[{label,sub,icon}], headline | run |
| `dd_versus` | A = B ? + 채워지는 미터 | left, right, line, meter(0~1) | right, line, q |
| `dd_note` | 노트 원문 → 형광펜 → 화살표로 항목 추출 | doc, lines[≤3], fields[{label,value,line}] | f0.. |
| `dd_handoff` | 물건(아이콘) → 화살표 → 담당자 상자 | icon, label, worker, note | give |
| `dd_chat` | 질문 말풍선(형광 표시) + 답장 초안 상자 | question("줄1\|줄2"), q_mark, reply, reply_lines | q_mark, reply |
| `dd_rule` | 조건 → 금지(X) + 동그라미 규칙 | if, then, stamp | if, then, stamp |
| `dd_bars` | 손그림 막대(빈 틀 → 빗금 채움) + 증가 화살표 | title, bars[{label,value,label_value}], delta, report | b0, b1, delta, report |
| `dd_burst` | 큰 한 줄(히어로) + 체크 / 줄 그은 항목 | text, checks, crossed[] | cross |
| `dd_list` | 체크리스트(실제 결과물·확인할 것을 note 로) | title, rows[{label,mark:check/pen/warn,note,circle}] | r0, m0, n0.. |
| `dd_kpi` | 전→후 숫자 줄 + 큰 증감(히어로 + 동그라미) | title, rows[{label,before,after}], delta, delta_note | k0.., delta |
| `dd_split` | AI \| 나 두 칸(흐린 미리보기 → 말할 때 진하게) + 결론 줄 | left/right{title,icon,items}, verdict | l0.., r0.., verdict |
| `dd_pick` | 선택지 → 동그라미 → 목표(예고) | title, options, pick(-1=전부), goal | pick, goal |
| `dd_wait` | 시계 + 진행 막대 3줄 | rows, text | r0, wait |

- 보드 전체 화면 박자의 아래쪽: 장면 `params.kicker` = `{"text": "... <span class=\"dd-acc\">강조</span>", "sub": "보조 한 줄", "cards": [{"title": "10분", "lines": ["2시간→10분"], "color": "accent", "mark": "check"}]}`
  - `cards` 는 2~3장(마지막 CTA 는 1장 `"+ 팔로우" / "다음 편 알림 받기"`), 카드 글은 짧게(제목 ≤5자, 줄 ≤8자). 장식 아이콘(`icon(s)`)은 쓰지 않는다 — 심사위원이 '의미 없는 장식'으로 감점.
  - 손글씨 글꼴엔 가운뎃점(·)이 없다 — 손글씨 문구에선 띄어쓰기로 대신.
- `dd_list` 에 `"ghosts": true` 를 주면 아직 말하지 않은 줄이 연필로 흐리게 미리 보인다(빈 보드 방지, 말하는 순간 진하게 바뀜).
- 손글씨 글꼴에서 `몫` 이 `묶` 처럼 보일 수 있으니 보드 문구엔 피하고(자막은 괜찮음), 퇴장은 기본(`lift`)을 쓴다.
- 결론 장면에서 훅의 질문에 화면으로 답한다(결론 장면 kicker 의 `sub`, 예: "누가 썼을까? → AI가 초안, 검산은 사람"). 결과 장면에는 "체크"만이 아니라 실제 결과물 문장을 note 로 보여준다.

### c. 렌더 + 채점
```powershell
python pipeline/make_reel.py --input "<영상.mp4>" --out out/<stem>_doodle_v1.mp4 --style "$SKILL\style.json" --plan work/<stem>/content_plan_doodle.json --workers 3
python quality/reel_score.py --output out/<stem>_doodle_v1.mp4 --words out/<stem>_doodle_v1.words.json --caption-band 0.45,0.55 --judge-pack out/judge_<stem>_doodle_v1
```
- `--caption-band 0.45,0.55` 필수(자막 위치 고정 — 보드 손글씨를 자막으로 잘못 세지 않게).
- 새 도우미 2명에게 `out/judge_.../JUDGE_PROMPT.md` 만 주고 따로 채점시킨 뒤 `--content-scores .../scores_j1.json .../scores_j2.json` 로 합친다.
- 통과: 단독 총점 ≥ 86.8 그리고 C1~C11 평균 모두 ≥ 4. 못 넘으면 심사 의견(시각 근거)대로 계획/스타일을 고쳐 다시 렌더.
- 반복 기록은 `work/<stem>/ITERATIONS.md` 에 짧게(git 밖). 자주 나온 감점: 반쯤 그려진 채 장면 전환, 빈 보드 프레임,
  작은/가는 손글씨, 얼굴 화면 들어오고 나갈 때 튐(얼굴 슬라이드는 오히려 '깨짐'으로 보여 하드컷 유지), 자막이 구절 중간에서 끊김,
  0.5초 미만 자막 조각, 화면 반만 덮는 전환 프레임, 카드 글자가 테두리에 닿음.

## 사용자에게 보고
"화이트보드 낙서 스타일로 만들었어요" + 결과 파일 경로 + 점수 한 줄. 내부 과정 설명은 물을 때만.
