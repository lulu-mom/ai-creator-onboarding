---
name: reel-style-split-card
description: 크림 배경 위 UI 카드 모션그래픽 + 아래 얼굴 분할 화면으로 업무·툴 사례를 차분하고 깔끔하게 보여주는 릴스 스타일. Use when the user picks the "스플릿 카드" style (directly or via reel-maker) to auto-edit a vertical Korean talking-head video into a reel with top UI cards / bottom face, 1-3 word captions with orange key words. Runs the reel-toolkit engine, writes the per-video content plan, renders, and loops on the blind-judge quality bar (total >= 86.8, all C1-C11 >= 4).
---

# 릴스 스타일: 스플릿 카드 (`split-card`)

미리보기: `preview.png` (같은 폴더, 예시 대본 + 가짜 화자 그림으로 만든 샘플 프레임). 스타일 값: `style.json` (= 엔진 `pipeline/styles/reference.json` 사본).

## 어떤 스타일인가
- 배경 크림 `#F0EAE6`. 화면 위쪽(0~0.45H)에 흰 앱 창 모양 **UI 카드**, 아래쪽에 말하는 **얼굴**. 사이사이 얼굴 전체(약 22%) / 그래픽 전체(약 12%) 화면으로 교대.
- 자막: Pretendard 700, 70px, 어두운 반투명 박스, **한 번에 1~3단어(최대 8자)**, 핵심어는 **주황** `#F07650`. 위치는 이음매(0.48H).
- 모션: 카드 역할별로 다른 등장/퇴장(push·zoom·drop·rise·wipe·flip·slam), 항목이 말에 맞춰 차례로 채워짐, 히어로 카드 슬램 + 도장, 하단 진행 트래커(칩), 콜드오픈(뒤의 반전 문장을 맨 앞에 2초).
- 속도: 말 1.15배, 컷 약 19회/분, 세그먼트 1.0~2.1초. 컷마다 작은 틱, 히어로에 스탬프 효과음. -14 LUFS.
- 잘 맞는 영상: 업무 자동화 사례, 툴 결과 보여주기, "AI에게 ○○ 시켜봤다" 같은 과정 스토리(툴 이름 + 단계 숫자 + 결과).
- 안 맞는 영상: 화면 녹화 위주 튜토리얼, 감정·일상 썰, 얼굴이 안 나오는 영상.

## 엔진 위치
PowerShell 에서 PATH 새로고침 후 엔진 위치를 찾는다(없으면 `reel-maker` 스킬 2단계의 설치를 먼저 한다):
```powershell
$env:Path = [Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [Environment]::GetEnvironmentVariable("Path","User")
$ENGINE = @([Environment]::GetEnvironmentVariable("REEL_TOOLKIT_DIR","User"), "$HOME\projects\ai-creator-onboarding\reel-toolkit") |
  Where-Object { $_ -and (Test-Path "$_\pipeline\make_reel.py") } | Select-Object -First 1
```
`$SKILL` = 이 폴더 (`$HOME\.claude\skills\reel-style-split-card`). `<stem>` = 입력 영상 파일 이름(확장자 제외).

## 절차 (끝까지 자동으로 진행, 사용자에게 중간 확인 안 받음)

### a. 받아쓰기 + 컷 (엔진)
```powershell
cd $ENGINE
python pipeline/make_reel.py --input "<영상.mp4>" --out out/<stem>_v1.mp4 --style "$SKILL\style.json" --no-render
```
- 결과(모두 `work/<stem>/`, git 제외 폴더): `transcript.json`(원본 받아쓰기, 단어 타임스탬프), `cuts.json`(잘린 구간·이유 로그), `words.json`(편집 후 단어), `plan.json`(자막·레이아웃·장면 요약).
- 같은 영상을 다시 돌리면 받아쓰기·VAD·얼굴 추적은 캐시 재사용(처음부터 하려면 `work/<stem>/` 삭제).
- 다른 스타일로 이미 받아쓰기/컷을 했다면 그 `work/<stem>/` 를 그대로 쓴다(`--work` 로 같은 폴더 지정 가능).

### b. 콘텐츠 계획 JSON 작성 (Claude 가 직접 씀 — 점수를 가장 크게 좌우)
`transcript.json` 과 `words.json` 을 끝까지 읽고 핵심 메시지 한 문장, 구조(훅 → 문제 → 과정 → 결과 → 반전/결론 → CTA)를 정한 뒤 `work/<stem>/content_plan.json` 에 쓴다.
**개인 영상의 계획은 `pipeline/plans/` 에 두지 않는다**(공개 저장소의 일부). 예시: `$ENGINE\pipeline\plans\example.json`.

스키마 (모든 시간은 타임스탬프가 아니라 **대본 단어 앵커**로 지정 → 컷이 바뀌어도 유지):
```jsonc
{
  "_about": "무슨 영상인지 한 줄",
  "cold_open": "그런데 이 보고서",     // (선택) 이 말로 시작하는 문장을 맨 앞에 한 번 더(플래시포워드 훅)
  "drop_sentences": ["잡담 시작 단어"], // (선택) 이 말로 시작하는 문장은 편집에서 제거
  "emphasis": ["3가지", "동시에"],      // 자막에서 주황으로 칠할 핵심어(앵커)
  "face": ["걸렸거든요"],               // 이 단어가 든 구간은 얼굴 전체 화면
  "graphic": ["결과가 나왔습니다"],      // 이 단어가 든 구간은 그래픽 전체 화면
  "auto_gap": 2,                        // 자동 레이아웃 교대 간격(구간 수). 힌트만 쓰려면 99
  "tracker_items": [{"label": "메모", "icon": "doc"}, ...],  // 하단 진행 칩(최대 3~4개)
  "scenes": [                           // 카드 장면: anchor 단어에서 시작해 다음 장면 전까지
    {
      "anchor": "그래서 AI에게",
      "template": "doc_extract",        // 아래 템플릿 표
      "params": {
        "title": "AI에게 맡긴 일", "tag": "추출",          // 카드 머리말 + 오른쪽 태그
        "at": {"f0": "메모를", "result": "뽑으라고"},      // 카드 안 동작 박자 → 앵커 단어
        "kicker": {"text": "메모 → <span class=\"rk-acc\">숫자 3개</span>", "sub": "핵심만 추출", "delay": 0.4},
                                                            // 그래픽 전체 화면일 때 카드 아래 큰 요약 (rk-acc = 주황)
        "enter": "wipe",                                    // push|zoom|drop|rise|wipe|flip|slam
        "tracker": ["done", "active", "todo"]               // tracker_items 상태: todo|active|done|warn
      }
    }
  ]
}
```

템플릿 (`pipeline/graphics/templates.py`) — 주요 params / `at` 박자:
| template | 용도 | params | at |
|---|---|---|---|
| `agents` | N명 AI가 동시에 일함 | `agents[{name,task,icon}]`, `headline`(HTML) | `items`, `run`, `stamp` |
| `command` | 채팅 입력 → 전송 | `text`, `chips[]`, `done`, `icon` | `type`, `send` |
| `question` | "A = B?" 질문 + 게이지 | `left`, `right`, `left_icon`, `meter_label` | `left`, `right`, `q` |
| `doc_extract` | 문서에서 항목 추출 | `doc`, `lines[]`, `highlight[]`, `fields[{label,icon,value}]`, `result` | `f0..fN`, `result` |
| `mail` | 메일 도착 / 질문 / 답장 초안 | `from`, `subject`, `question`, `reply`, `reply_lines[]` | `in`, `question`, `reply` |
| `rule` | IF → THEN 규칙 + 도장 | `if`, `then`, `stamp` | `if`, `then`, `stamp` |
| `bars` | 막대 2개 비교 | `bars[{label,value,display}]`, `badge`, `report` | `b0`, `b1`, `badge`, `report` |
| `checklist` | 항목이 말에 맞춰 체크 | `items[{label,icon,note}]`, `show_all_first` | `r0..rN` |
| `waiting` | 작업 목록 + 타이머 | `rows[{label,icon}]`, `timer_label`, `minutes` | `r0..rN`, `wait` |
| `big_stat` | 큰 숫자 카운트 | `from`, `to`, `prefix`, `suffix`, `unit`, `decimals`, `label`, `dots`, `stamp`, `icon` | `count`, `stamp` |
| `results` | 결과물 타일 | `items[{label,icon,lines[]}]` | `t0..tN` |
| `kpi` | KPI 타일 + 증가율 | `label`, `tiles[{label,icon,value}]`, `to` | `k0..kN`, `count` |
| `stop_send` | 보내기 직전 경고 도장 | `button`, `chips[{label,icon}]`, `stamp` | `block` |
| `roles` | 두 열(AI vs 나) 역할 | `columns[{name,icon,at,items[{label,at}]}]`, `meter{label,value,fill,at}` | (열/항목 안 `at`) |
| `pick` | 선택지 중 하나 고르기 + CTA | `options[{label,icon}]`, `pick`(번호), `result`, `result_icon`, `cta`, `cta_sub` | `o0..oN`, `pick`, `result`, `cta` |
| `keyword` | 아이콘 + 키워드(기본값) | `icon`, `keyword`, `sub` | — |

아이콘: alert arrow bot box calendar cart chart check clock doc eye flag hand list mail question search send spark up user won x.

좋은 계획 규칙 (블라인드 심사에서 배운 것):
- 말하는 모든 핵심 포인트를 카드로 **보여준다**(C3). 카드 문구는 실제 말과 같은 내용, 지어낸 숫자 금지(C4).
- 첫 0~2초에 궁금증 훅: 반전 문장을 `cold_open` 으로 + 첫 카드는 `slam`/`zoom`.
- 카드 역할마다 `enter` 를 다르게(문서·체크리스트 `wipe`, 결과·규칙 `flip`, 히어로 숫자 `slam`/`zoom`, 목록 `rise`, 일반 `push`). 같은 등장이 3번 연속되지 않게.
- 카드 안 글자는 적게(항목 3개 안팎, 한 줄 12자 안팎). 작은 글씨가 가장 흔한 감점.
- `at` 앵커는 실제 그 단어가 나오는 순간으로 — 항목이 말에 맞춰 채워져야 한다.
- 지루한 구간(설정 설명이 길게 이어지는 곳)은 `drop_sentences` 로 덜어내거나 `graphic` 힌트로 그래픽 전체 화면을 넣는다.
- CTA 는 말로도 해야 점수가 오른다(화면에만 있으면 C10 감점). 말에 없으면 사용자에게 알려준다.
- 앵커가 대본에 없으면 그 장면은 건너뛴다(로그 `[plan] anchor not found`). 렌더 전 `--no-render` 로 한 번 확인.

### c. 렌더
```powershell
python pipeline/make_reel.py --input "<영상.mp4>" --out out/<stem>_v1.mp4 --style "$SKILL\style.json" --plan work/<stem>/content_plan.json --quality standard
```
- 렌더 1회 **약 4~20분**(길이·PC 성능). 백그라운드로 돌리고 끝나면 이어서 진행.
- `out/<stem>_v1.words.json` 이 같이 생긴다(채점에 사용).

### d. 품질 루프 (통과할 때까지 반복)
1. 측정 + 블라인드 심사 묶음:
   ```powershell
   python quality/reel_score.py --output out/<stem>_vN.mp4 --words out/<stem>_vN.words.json --json out/reports/<stem>_vN.json --frames 8 --judge-pack out/judge_<stem>_vN
   ```
   (같은 스타일의 레퍼런스 릴스 파일이 있으면 `--reference <경로>` 를 붙여 비교 심사. 없어도 된다.)
2. **새 도우미 2개를 동시에** 띄워 심사(서로·만든 쪽 맥락 모름). 각 도우미 프롬프트:
   "You are a blind reel judge. Read `<ENGINE>\out\judge_<stem>_vN\JUDGE_PROMPT.md` and follow it exactly, using only files inside that folder (never open `*_key.json` or anything outside). Write your scores to `<ENGINE>\out\judge_<stem>_vN\scores_jK.json` in the schema the prompt gives." (K = 1, 2)
3. 합산:
   ```powershell
   python quality/reel_score.py --output out/<stem>_vN.mp4 --words out/<stem>_vN.words.json --json out/reports/<stem>_vN.json --content-scores out/judge_<stem>_vN/scores_j1.json out/judge_<stem>_vN/scores_j2.json
   ```
   출력의 `단독 총점` (= JSON `standalone`)과 `content_scores.output.C1..C11.score` 를 본다.
4. **통과 = 단독 총점 ≥ 86.8 AND C1~C11 모두 ≥ 4** (두 심사 평균). 기술 게이트(`gate_fails`)가 있으면 그것부터 고친다.
5. 미통과면 심사의 `evidence`/`fixes` 와 `*_sheet.png` 를 보고 고친다 → 버전 올려 c 부터 다시:
   - 대부분은 **계획 JSON** 수정(카드 추가·문구 축약·앵커 조정·enter 변경·drop_sentences·cold_open).
   - 화면 밝기/줌/자막 크기 같은 스타일 값은 `$SKILL\style.json` 을 고친다(엔진 코드 수정은 엔진 저장소에서 별도 작업으로).
   - 매 회 무엇을 바꿨고 점수가 어떻게 됐는지 `work/<stem>/ITERATIONS.md` 에 짧게 남긴다(개인 내용이므로 git 밖).
   - 심사 점수는 쌍마다 ±2점 정도 흔들린다. 8회 넘게 못 넘으면 가장 좋은 버전을 보여주고 남은 감점 이유를 쉽게 설명한다.

### e. 결과 보여주기
- 통과 버전을 `out/<stem>_final.mp4` 로 복사, `Start-Process` 로 열어 준다.
- 사용자에게는 짧게: "완성됐어요 — 파일 위치, 점수(총점 / 기준 86.8), 잘 된 점 한 줄, 아쉬운 점 한 줄". 내부 과정 설명은 묻는 경우만.
- 게시(SNS 업로드)는 하지 않는다. 원하면 `upload-post` 스킬로, 반드시 먼저 물어본다.

## 알려진 한계
- 입력: 한국어 말, 세로(9:16) 또는 세로로 자를 수 있는 영상, 얼굴이 보여야 함(얼굴 추적으로 자름).
- 폰으로 가까이 찍은 영상은 얼굴이 크게(화면 높이 약 0.33) 나온다 — 옆을 지어내 채우지 않으므로 더 멀리 못 뺀다.
- 역광 영상은 밝기 보정을 해도 어둡게 나올 수 있다.
- 컷 수는 약 19회/분. 크림 배경 카드 교체는 측정기가 약한 컷으로 센다.
- CTA 를 말로 하지 않은 영상은 C10 이 낮게 나온다(화면 CTA 만으로는 한계).
- 카드 템플릿은 위 16종. 새 모양이 필요하면 엔진 `templates.py` 에 추가해야 한다.
- 받아쓰기 오류가 있으면 자막·앵커가 틀어진다 — `transcript.json` 확인 후 계획에서 실제 인식된 단어로 앵커를 잡는다.
- 렌더 4~20분 × 반복 횟수만큼 걸린다(통과까지 보통 3~8회).
