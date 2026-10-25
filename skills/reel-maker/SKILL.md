---
name: reel-maker
description: 영상 하나를 넣으면 설치된 릴스 스타일 목록을 보여주고 고르게 하거나("알아서"면 대본을 보고 가장 어울리는 스타일을 골라) 자동 편집·품질 검사까지 끝내는 시작점. Use when the user says "릴스 만들어줘", "쇼츠 편집해줘", "영상 편집해줘", "릴스로 만들어줘", "이 영상 편집" together with a video file (mp4/mov path or attachment), or asks to re-render a reel "다른 스타일로".
---

# 릴스 메이커 (스타일 고르기 + 엔진 준비)

사용자는 비개발자다. 대화는 쉬운 한국어로 짧게. 기술 선택은 묻지 않는다.

## 1. 영상 확인
- 영상 파일 경로를 확인한다(없으면 "편집할 영상 파일을 알려주세요" 한 줄만 묻는다).
- `<stem>` = 파일 이름(확장자 제외).

## 2. 엔진 준비 (조용히, 필요할 때만)
엔진(`reel-toolkit`)은 이 공개 저장소(`lulu-mom/ai-creator-onboarding`)의 `reel-toolkit/` 폴더다. 로그인 없이 받을 수 있다.
PowerShell 에서 PATH 새로고침 후 엔진 위치를 찾는다:
```powershell
$env:Path = [Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [Environment]::GetEnvironmentVariable("Path","User")
$ENGINE = @([Environment]::GetEnvironmentVariable("REEL_TOOLKIT_DIR","User"), "$HOME\projects\ai-creator-onboarding\reel-toolkit") |
  Where-Object { $_ -and (Test-Path "$_\pipeline\make_reel.py") } | Select-Object -First 1
```
없으면 설치(필요한 폴더만 받기):
```powershell
$repo = "$HOME\projects\ai-creator-onboarding"
git clone --depth 1 --filter=blob:none --sparse https://github.com/lulu-mom/ai-creator-onboarding $repo
git -C $repo sparse-checkout set reel-toolkit
$ENGINE = "$repo\reel-toolkit"
```
그다음 엔진 `README.md` 의 **Setup** 명령을 그대로 실행한다(npm i → `npx playwright install chromium` → `models/face_landmarker.task` 다운로드 → pip 설치). ffmpeg 가 없으면 `winget install --id Gyan.FFmpeg -e`.
이미 있는 경우에도 `node_modules`·`models\face_landmarker.task` 가 없으면 해당 단계만 실행한다.
확인: `python pipeline/make_reel.py --help` 가 돌면 준비 완료. (`ai-creator-onboarding` 스킬의 `setup.ps1` 도 같은 일을 한다.)

## 3. 스타일 목록 만들기
설치된 스타일 스킬을 찾는다: `~/.claude/skills/reel-style-*/SKILL.md` (Codex: `~/.agents/skills/reel-style-*/SKILL.md`). 새 스타일 스킬을 설치하면 자동으로 목록에 뜬다.
각 파일의 frontmatter `description` **첫 문장**(첫 마침표까지)이 한 줄 설명이다. 스킬 이름에서 `reel-style-` 를 뺀 부분이 id.
쉬운 한국어 이름표(없는 id 는 description 첫 구절로):
| id | 이름 |
|---|---|
| split-card | 스플릿 카드 |
| bold-talk | 큰 자막 토크 |
| variety | 예능 자막 |
| news-brief | 뉴스 브리핑 |
| docu | 다큐 시네마틱 |
| doodle | 화이트보드 낙서 |
| minimal-type | 미니멀 타이포 |
| screen-demo | 화면 시연 |

사용자에게 번호 목록으로 보여준다(설치된 것만, 각 폴더에 `preview.png` 가 있으면 경로도 같이 알려 줄 수 있음):
```
어떤 스타일로 만들까요?
1. 스플릿 카드 — 크림 배경 위 UI 카드 + 아래 얼굴, 업무·툴 사례를 깔끔하게
2. ...
번호나 이름을 말해 주세요. "알아서"라고 하면 영상 내용을 보고 골라 드릴게요.
```
사용자가 처음부터 스타일 이름이나 "알아서"를 말했다면 목록은 건너뛴다.

## 4. "알아서" 자동 선택
1. 먼저 받아쓰기만 한다(선택한 스타일과 무관하게 재사용됨):
   `python pipeline/make_reel.py --input "<영상>" --out out/<stem>_probe.mp4 --no-render` (스타일 기본값 사용) → `work/<stem>/transcript.json`.
2. 대본에서 신호를 센다: 말 속도(음절/초), 숫자·금액 빈도, 날짜·"오늘/이번 주", "발표·출시·공개·업데이트", 툴/서비스 이름, "만들었다/맡겼다/결과", 단계 숫자, "개념/원리/차이/방법/단계"·순서어·"vs", 웃음·감탄사("헐/대박/와/ㅋㅋ"), 과거형 1인칭 서사·감정어, 조작어("클릭/설정/메뉴/프롬프트/사이트"), 영상 길이, 화면 녹화 파일 동봉 여부.
3. 설치된 스타일만 후보로, 카탈로그 규칙(`$ENGINE\styles\STYLE_CATALOG.md` 각 절의 "자동 선택")으로 점수를 매긴다:
   - 화면녹화 있음 또는 조작어 많음 → 화면 시연
   - 날짜 + 발표·출시 + 회사/제품명 다수 + 항목 나열 → 뉴스 브리핑
   - 툴 이름 + 만들었다/맡겼다/결과 + 단계 숫자(과정형) → 스플릿 카드
   - 개념/원리/단계/비교 → 화이트보드 낙서
   - 웃음·감탄사·일상 사건·대화체 → 예능 자막
   - 과거형 1인칭 서사 + 감정어 + 느린 말(≤4음절/초) + 60초 이상 → 다큐 시네마틱
   - 30초 이하 또는 문장 적음 + 추상어(삶·관점·기준·본질) → 미니멀 타이포
   - 빠른 말(≥5.5음절/초) + 단정형("무조건/절대") + 숫자·돈 → 큰 자막 토크
   - 동점 우선순위: 화면 시연 > 뉴스 > 스플릿 카드 > 화이트보드 > 예능 > 다큐 > 미니멀 > (기본값) 스플릿 카드
4. 1등으로 진행하고 한 줄로 알린다: "○○ 스타일로 만들게요. (이유: ~가 많아서요) 2등은 △△였어요 — 원하면 그걸로도 만들어 드릴게요."

## 5. 선택한 스타일 스킬 실행
- 선택한 `reel-style-<id>` 스킬을 불러(Claude: Skill 도구, Codex: 그 SKILL.md 열기) 그 SKILL.md 절차를 끝까지 따른다(받아쓰기·컷 → 계획 JSON 작성 → 렌더 → 품질 루프 → 결과 보여주기). `$ENGINE` 은 2단계에서 찾은 경로.
- 렌더는 1회 4~20분 걸린다. 시작할 때 "몇 분 걸려요, 끝나면 알려드릴게요" 한 줄만.

## 6. 다른 스타일로 다시 만들기
"다른 스타일로도", "○○ 스타일로 바꿔줘" 요청이면:
- 같은 `work/<stem>/` 를 그대로 쓴다(받아쓰기·VAD·얼굴 추적 캐시 재사용, 삭제하지 않음). 이미 정리한 내용(핵심 메시지, 잘라낼 문장 `drop_sentences`, `cold_open`)도 새 스타일의 계획에 옮겨 쓴다.
- 출력 이름에 스타일 id 를 붙인다: `out/<stem>_<id>_vN.mp4` — 이전 결과를 덮어쓰지 않는다.
- 새 스타일 스킬의 계획 스키마가 다르면 그 스킬 문서를 따른다.

## 지키기
- 사용자 영상·대본·계획은 엔진의 `work/` / `out/` 안에만(둘 다 git 제외). 엔진 `pipeline/plans/` 에 개인 계획을 넣지 않는다(공개 저장소의 일부).
- SNS 게시·외부 공개는 하지 않는다. 원하면 먼저 물어보고 `upload-post` 스킬.
