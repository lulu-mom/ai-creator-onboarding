---
name: reel-style-news-brief
description: 상단 남색 헤드라인 바(꼭지 번호 + 제목)와 하단 방송식 자막띠, 흐르는 티커, 1/3·2/3·3/3 꼭지 전환 카드로 소식·실험 결과를 빠르고 믿음직하게 전하는 뉴스 앵커 스타일 릴스. Use when the user picks the "뉴스 브리핑" style (directly or via reel-maker) or when a Korean talking-head video is news-like - AI/IT 소식, 업계 뉴스, 주간 트렌드, "오늘 나온 ○○ 3가지", 날짜·발표·출시·업데이트 말이 많고 항목을 순서대로 나열하는 영상. Runs the reel-toolkit engine with this folder's style.json, writes the per-video content plan (cards + sections + ticker), renders, and loops on the blind-judge quality bar (total >= 86.8, all C1-C11 >= 4).
---

# 릴스 스타일: 뉴스 브리핑 (`news-brief`)

미리보기: `preview.png` (같은 폴더, 예시 대본 + 가짜 화자 그림으로 만든 샘플 프레임). 스타일 값: `style.json` (= 엔진 `pipeline/styles/news-brief.json` 사본).
품질: 실제 토킹헤드 영상으로 블라인드 심사 기준(총점 86.8 이상, C1~C11 모두 4 이상)을 통과한 스타일이다.

## 언제 쓰나
- 잘 맞는 영상: AI/IT 뉴스, 업계 소식, 주간 트렌드 정리, "오늘 나온 ○○ 3가지", 실험·리뷰 결과를 항목별로 정리하는 영상.
  신호: 날짜("오늘·이번 주"), "발표·출시·공개·업데이트", 회사·제품 이름 여러 개, "첫 번째/두 번째/세 번째".
- 안 맞는 영상: 감정·일상 썰(→ 예능 자막), 개인 서사(→ 다큐), 화면 녹화 튜토리얼(→ 화면 시연).

## 어떤 모습인가
- **위**: 남색 헤드라인 바. 작은 줄(라벨 `EP.1` 등 + 브랜드 + 출처·날짜 회색 태그), 큰 줄(노란 칩 `1/3`·`결과`·`결론` + 이번 꼭지 제목, 노란 강조어). 꼭지가 바뀌면 제목이 아래에서 밀려 올라옴.
- **가운데**: 흰 사각 카드(남색 윗줄, 빨간 태그) 안에서 말하는 내용이 그대로 그려짐. 아래쪽은 얼굴(분할) 또는 큰 요약 문구(그래픽 전체).
- **자막**: 화면 0.55~0.62H 고정 띠. 남색 바 + 왼쪽 빨간 줄, 흰 글자 Pretendard 700 74px, **핵심어는 그 단어를 말하는 순간 빨간 블록**. 말이 쉬었다 시작하면 바가 왼쪽에서 와이프.
- **꼭지 전환**: `1/3`, `2/3`, `3/3`, `결과` 같은 큰 번호 카드가 화면을 쓸고 지나감(방향이 매번 바뀜).
- **맨 아래**: 빨간 라벨 + 흐르는 티커(핵심 숫자·사실).
- 색: 남색 `#0B1F3A`, 빨강 `#E03131`, 노랑 `#FFD43B`, 회색 `#ADB5BD`, 배경 `#F1F3F5`. 말 1.15배, 컷 약 20회/분, -14 LUFS.

## 엔진 위치
PowerShell 에서 PATH 새로고침 후 엔진 위치를 찾는다(없으면 `reel-maker` 스킬 2단계의 설치를 먼저 한다):
```powershell
$env:Path = [Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [Environment]::GetEnvironmentVariable("Path","User")
$ENGINE = @([Environment]::GetEnvironmentVariable("REEL_TOOLKIT_DIR","User"), "$HOME\projects\ai-creator-onboarding\reel-toolkit") |
  Where-Object { $_ -and (Test-Path "$_\pipeline\make_reel.py") } | Select-Object -First 1
```
`$SKILL` = 이 폴더 = 이 SKILL.md 가 있는 곳 (Claude: `$HOME\.claude\skills\reel-style-news-brief`, Codex: `$HOME\.agents\skills\reel-style-news-brief`). `<stem>` = 입력 영상 파일 이름(확장자 제외).

## 실행 명령 (이것 하나)
```powershell
cd $ENGINE
python pipeline/make_reel.py --input "<영상.mp4>" --out out/<stem>_news.mp4 --style "$SKILL\style.json" --plan work/<stem>/content_plan_news.json
```
계획 파일 없이(`--plan` 생략) 돌리면 자동 키워드 카드만 나온다 — 품질 기준을 넘기려면 아래 b 단계 계획을 꼭 쓴다.

## 절차 (끝까지 자동으로 진행, 중간 확인 없음)

### a. 받아쓰기 + 컷
```powershell
python pipeline/make_reel.py --input "<영상.mp4>" --out out/<stem>_news.mp4 --style "$SKILL\style.json" --no-render
```
`work/<stem>/` 에 `transcript.json`, `cuts.json`, `words.json`, `plan.json` 이 생긴다. 다른 스타일로 이미 돌렸으면 캐시를 그대로 쓴다.

### b. 콘텐츠 계획 JSON 작성 (점수를 가장 크게 좌우)
대본을 끝까지 읽고 핵심 한 문장 + 꼭지 구조(훅 → 소개 → 1/3·2/3·3/3 → 결과 → 주의/반전 → 결론 → 예고/CTA)를 정한 뒤
`work/<stem>/content_plan_news.json` 에 쓴다. **개인 영상 계획은 `pipeline/plans/` 에 두지 않는다**(공개 저장소로 올라감).
카드(`scenes`)·`emphasis`·`graphic`·`drop_sentences`·`cold_open` 등 공통 키와 템플릿 표는 `reel-style-split-card` 스킬의 b 단계와 같다.
이 스타일에서 추가로 쓰는 키:
```jsonc
{
  "newsdesk": {"brand": "AI 실험 브리핑", "date": "2026.10.25", "source": "직접 실험", "live": "EP.1"},
  "sections": [                                   // 헤드라인 바 꼭지 (대본 단어 앵커, 순서대로)
    {"anchor": "", "chip": "핵심", "chip_style": "alert", "title": "보고서, <span class=\"acc\">사람이 0줄</span>"},  // 첫 꼭지는 0초
    {"anchor": "매주 월요일", "chip": "1/3", "title": "기존: 매주 <span class=\"acc\">2시간</span>",
     "sweep": true, "sweep_title": "기존 방식"}  // sweep = 큰 번호 카드 전환 (번호 꼭지·결과에만)
  ],
  "ticker_items": ["보고서 작성 2시간 → 10분", "AI는 초안, 검산은 사람"],   // 말과 다른 표현의 핵심 사실·숫자
  "caption_keep": ["한 줄도 안 썼습니다", "핵심 숫자만"],  // 자막에서 절대 쪼개지 않을 구절(의미 단위)
  "cold_open": "그런데 이 보고서", "cold_open_from": "이",   // 콜드오픈 문장을 '이'부터 (군더더기 접속사 제거)
  "face": []                                        // 이 스타일은 얼굴 전체 화면을 쓰지 않는 편이 깔끔
}
```
- `results` 카드에 `"flag": ["0_2"]` 를 주면 그 줄(항목0의 2번째 줄)이 빨간 '문제' 표시.
- 카드 `enter` 는 `push / rise / zoom / drop` 만 (wipe·flip 은 카드가 반쯤 잘려 보이고, slam 은 화면 밖으로 넘침).
- `kicker` 에 `delay`·`at` 을 쓰지 않는다(그래픽 화면 아래 절반이 비어 보임).
- 강조어(`emphasis`)는 줄 3~4개당 1개 정도, 숫자·행동어 위주. 첫 자막은 짧게 끊어 훅이 1초 안에 읽히게.
- 예시 계획(예시 대본 기준): `$ENGINE\pipeline\plans\example_news.json`.

### c. 렌더 + 채점
```powershell
python pipeline/make_reel.py --input "<영상.mp4>" --out out/<stem>_news_v1.mp4 --style "$SKILL\style.json" --plan work/<stem>/content_plan_news.json --workers 3
python quality/reel_score.py --output out/<stem>_news_v1.mp4 --words out/<stem>_news_v1.words.json --caption-band 0.54,0.64 --judge-pack out/judge_<stem>_news_v1
```
- `--caption-band 0.54,0.64` 필수: 자막띠 위치가 고정이라 이 띠만 자막으로 잰다(안 쓰면 카드 글자가 자막으로 잡혀 싱크 점수가 망가짐).
- 새 도우미 2명에게 `out/judge_.../JUDGE_PROMPT.md` 만 주고 따로 채점시킨 뒤 `--content-scores .../scores_j1.json .../scores_j2.json` 로 합친다.
- 통과: 단독 총점 ≥ 86.8 그리고 C1~C11 평균 모두 ≥ 4. 못 넘으면 심사 의견(증거 시각)대로 계획/스타일을 고쳐 다시 렌더.
- 반복 기록은 `work/<stem>/ITERATIONS.md` 에 짧게(개인 내용이므로 git 밖). 자주 나온 감점: 전환 때 반투명·빈 프레임, 카드 잘림, 작은 카드 글씨, 훅 첫 문장 맥락 부족.

## 사용자에게 보고
"뉴스 브리핑 스타일로 만들었어요" + 결과 파일 경로 + 점수 한 줄. 내부 과정 설명은 물을 때만.
