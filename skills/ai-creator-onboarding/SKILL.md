---
name: ai-creator-onboarding
description: 비개발 크리에이터의 AI 콘텐츠·에이전트 작업 환경을 한 번에 세팅/점검/복구하는 온보딩. 새 컴퓨터·새 계정에서 처음 시작할 때, "온보딩", "세팅 다시 해줘", "환경 점검", "뭐 빠진 거 없어?", "처음부터 설치" 라고 할 때, 또는 설치된 스킬·MCP·키가 사라졌거나 동작하지 않을 때 사용한다. 소통 규칙·작업 방식·설치 도구·계정 연결까지 전체 내용을 담고 있다.
---

# AI 크리에이터 온보딩

사용자: 비개발자. AI 에이전트 개발, AI 쇼츠/영상, 콘텐츠 생성·자동 편집·배포를 한다.
GitHub에서 요즘 뜨는 무료 오픈소스 스킬·MCP를 가져다 쓰는 방식을 선호한다.

## 0. 진행 방식 (온보딩 중에도 동일)
- 짧게, 쉬운 말로, 티키타카. 기술 질문 금지.
- 설치·설정·테스트는 알아서. 사용자에게는 **회원가입/로그인만** 요청.
- 결제, 실제 SNS 게시, 되돌릴 수 없는 삭제만 먼저 묻기.
- 키 값은 채팅에 절대 보여주지 않는다.

## 1. 자동 설치 (스크립트 한 번)
```powershell
powershell -ExecutionPolicy Bypass -File "$HOME\.claude\skills\ai-creator-onboarding\scripts\setup.ps1"
```
다시 돌려도 안전하다(있는 건 건너뜀). 오래 걸리면 백그라운드로 돌리고 끝나면 SUMMARY 를 짧게 보고.
스크립트가 하는 일 = 아래 "설치 목록" 전부. 실패한 줄만 골라서 손으로 다시 한다.

## 2. 사람이 해야 하는 것 (로그인만)
브라우저 규칙: ego lite 우선. 사용자가 직접 할 페이지는 **일반 창**으로 연다
`& "C:\Program Files\Citro Labs\ego lite\Application\ego.exe" --profile-directory="<기본 프로필>" "<url>"`
(에이전트 TaskSpace 탭은 사용자에게 안 보임. 구글 로그인은 agent-browser에서 막힘. GitHub이 막히면 평소 크롬.)

| 항목 | 사용자 할 일 | 그 다음 Claude가 할 일 |
|---|---|---|
| ego lite 브라우저 | https://lite.ego.app/ 에서 설치, 첫 실행 때 "크롬 데이터 가져오기" | `ego-browser nodejs -e "console.log('ok')"` 로 확인 |
| GitHub | 크롬에서 `github.com/login/device` 로그인 + 코드 입력 | `gh auth login --web` 백그라운드 실행 → 코드 전달 → `gh auth status` |
| Upload-Post | 가입/로그인 (무료: 월 10회 업로드, 편집 30분) | ego TaskSpace로 `app.upload-post.com/api-keys` → 키 생성 → `setx UPLOAD_POST_API_KEY` → `GET https://api.upload-post.com/api/uploadposts/users` (헤더 `Authorization: Apikey <key>`) 200 확인 |
| Bright Data | 가입/로그인 (무료 크레딧 5,000) | `brightdata.com/cp/setting/users` → Show 버튼(오버레이 때문에 page.evaluate 로 클릭) → `setx BRIGHTDATA_API_KEY` → MCP 추가(`claude mcp add --scope user --transport sse brightdata "https://mcp.brightdata.com/sse?token=<key>"`) |
| Higgsfield, Meta Ads | 새 창에서 `/mcp` → 항목 선택 → Authenticate → 로그인 | 연결 확인. katana 같은 힉스필드 전용 기능은 로그인 후 확인 |
| ECC 플러그인 설정 2개 | `/plugin configure ecc@ecc` | — |

키 발급 자동화 요령: 키가 화면에 마스킹돼 있으면 Reveal/Show 버튼 클릭 후 `page.evaluate` 로 값만 꺼내 Node `execFileSync("setx", [...])` 로 저장, 출력은 길이만. 스냅샷 출력 시 긴 토큰은 정규식으로 가린다.

선택(지금은 안 씀): `GEMINI_API_KEY`(autoshorts 장면 고르기 — 대신 Claude가 대본 보고 고름), last30days의 X/TikTok/IG 키(무료 소스만으로 사용).

## 3. 규칙 파일
- 전역 규칙: `assets/global-CLAUDE.md` → `~/.claude/CLAUDE.md` (없으면 복사, 있으면 빠진 섹션만 합치기)
  - 소통 방식(짧게·쉽게·티키타카), AI 에이전트 만들 땐 grilling → 계획서 → 개발, 자율 진행, task-observer, 링크 → link-to-build, 오픈소스 우선(oss-scout), 로그인/키 처리 규칙
- 프로젝트 규칙 예시: `assets/project/CLAUDE.md` (브라우저 작업·키 보관 규칙). 새 프로젝트에 맞게 복사.
- 프로젝트 git 작성자: `git config user.name <github-id>` / `user.email <id>+<github-id>@users.noreply.github.com` (gh api user 로 id 확인)

## 4. 설치 목록 (무엇이 왜 있는지)
**플러그인/MCP**
- ECC (Everything Claude Code) 플러그인
- MCP: higgsfield(AI 이미지·영상 생성, OAuth), meta-ads(메타 광고, OAuth), brightdata(웹 수집, 키), playwright(브라우저, 무료), headroom(토큰 압축, 무료)

**스킬**
- 영상: hyperframes 계열, remotion-* , gsap-* , hypit(바이럴 영상 참고 제작)
- 유튜브: yt-* 11종 (youtube-agent-skill)
- 배포: upload-post, autoshorts, viraloop, higgsfield-to-social, comment-funnel, tiktok-app-marketing
- 조사: find-skills, last30days, research, search-strategy, baoyu-youtube-transcript, baoyu-url-to-markdown, Bright Data 스킬 21종
- 작업 방식: grill-me/grilling, task-observer, agent-browser, ego-browser
- 직접 만든 것: **link-to-build**(링크 → 조사 → 구현 → 결과 페이지), **oss-scout**(무료 오픈소스 먼저 끝까지 찾기)

**프로그램**
- ffmpeg, gh, yt-dlp, faster-whisper, Silero VAD, MediaPipe, headroom-ai, hypit CLI, agent-browser(+Chrome), ego lite
- OpenMontage: `<projects>\OpenMontage` (venv + remotion-composer + piper-tts)
- `python3` 별칭(=python.exe 복사본): last30days 가 필요로 함

## 5. 점검 (온보딩 끝에 한 번)
```powershell
claude mcp list; claude plugin list; gh auth status
python -c "import faster_whisper, silero_vad, mediapipe; print('py ok')"
ffmpeg -version | Select-Object -First 1; hypit version; yt-dlp --version
[Environment]::GetEnvironmentVariable("UPLOAD_POST_API_KEY","User").Length
[Environment]::GetEnvironmentVariable("BRIGHTDATA_API_KEY","User").Length
```
결과는 ✅/⚠️ 목록으로 짧게. ⚠️ 는 "로그인만 해주세요" 형태로 요청.

## 6. 알아둔 함정
- 새로 설치한 것은 **Claude Code 새 창**에서부터 적용.
- winget 으로 깐 프로그램은 현재 셸 PATH에 없음 → `RefreshPath` 또는 새 터미널.
- PowerShell 5.1 에서 ego-browser 스크립트는 따옴표/한글이 깨짐 → Bash 도구 heredoc 사용.
- `skills add` 의 개발자용 부속 스킬(예: ego-lite-simplify)은 지운다.
- headroom 의 `wrap claude`(프록시 실행)는 Claude 실행 방식을 바꾸므로 켜지 않았다(MCP만 사용).
- bright-data-mcp 스킬은 "모든 웹 작업을 Bright Data로" 라고 주장하지만, 무료 크레딧을 아끼려면 단순 조회는 WebFetch/WebSearch 로 충분.
