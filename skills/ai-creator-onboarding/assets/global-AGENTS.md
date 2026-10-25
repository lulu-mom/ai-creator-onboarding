# 사용자 작업 규칙 (Codex)

> Claude Code 의 전역 규칙(`~/.claude/CLAUDE.md`)을 Codex 에 맞게 옮긴 것이다. 위치: `~/.codex/AGENTS.md`.
> 한쪽을 고치면 다른 쪽도 맞춘다 (원본: 온보딩 스킬 `assets/global-CLAUDE.md` ↔ `assets/global-AGENTS.md`).

## Claude 용 글을 Codex 에서 읽는 법 (바꿔 읽기)
스킬·프로젝트 규칙(`CLAUDE.md`) 안에는 Claude Code 전용 표현이 섞여 있다. Codex 에서는 이렇게 바꿔서 그대로 따른다.

| 글에 이렇게 써 있으면 | Codex 에서는 |
|---|---|
| "Skill 도구로 `이름` 을 부른다" | 스킬 목록의 `이름` → 그 `SKILL.md` 를 열어 절차를 끝까지 따른다 (사용자는 `$이름` 으로 부를 수도 있다) |
| `~/.claude/skills/<이름>/...` | `~/.agents/skills/<이름>/...` (같은 스킬이 복사돼 있다. 없으면 `~/.claude/skills` 쪽을 읽는다) |
| 프로젝트 `CLAUDE.md` | 그대로 읽힌다 (`~/.codex/config.toml` 의 `project_doc_fallback_filenames = ["CLAUDE.md"]`). 그 폴더에 `AGENTS.md` 가 있으면 그쪽이 우선 |
| Agent 도구 / 서브에이전트 / `SendMessage` | 하위 에이전트(`spawn_agent`, `send_message`, `wait_agent`). 아래 "일하는 방식" 참고 |
| `isolation: "worktree"` | 자동 분리 없음 → `git worktree add` 로 폴더를 직접 나눈다 |
| `ecc:<에이전트>` (planner, code-reviewer …) | ECC 플러그인은 Claude 전용. 같은 역할을 직접 하거나 하위 에이전트에게 맡긴다. 지침 원문이 있으면 읽힌다: `~/.claude/plugins/cache/ecc/ecc/<버전>/agents/<이름>.md` |
| `claude mcp add / list` | `codex mcp add / list` (설정 파일 `~/.codex/config.toml`) |
| `/mcp` → Authenticate (로그인) | 터미널에서 `codex mcp login <이름>` |
| WebFetch / WebSearch | Codex 웹 검색(켜져 있으면), 아니면 `curl` / brightdata MCP |
| Artifact(결과 페이지) | HTML 파일을 만들어 브라우저로 연다 (`Start-Process <파일>`) |
| Glob / Read / Edit 도구 | 셸 명령(`Get-ChildItem`, `rg`)과 Codex 파일 편집 |
| "Claude Code 새 창에서 적용" | "Codex 새 창(새 세션)에서 적용" |

## 소통 방식 (기본 지침 — 항상 지킬 것)
- **모든 대화는 한국어로 한다.** 사용자에게 보이는 답변·보고·질문은 예외 없이 한국어 (코드·명령어·고유명사만 원문 그대로).
- 중요한 내용이 아니면 최대한 짧게 답한다. 긴 설명 대신 짧게 주고받는 대화(티키타카)로 진행한다.
- 한 번에 많이 쏟아내지 말고, 핵심 한두 줄 → 필요하면 이어서 설명한다.
- 사용자는 비개발자다. 항상 쉬운 한국어로 말하고, 전문용어는 피하거나 짧게 풀어서 설명한다.
  - (이 규칙은 **사용자와의 대화에만** 적용. 하위 에이전트에게 주는 지시, 할 일 카드·검토 요청 내용, 저장 기록 등 내부 작업에서는 정확한 개발 용어를 그대로 쓴다.)
  - 사용자와 대화할 때는 개발 용어를 그대로 쓰지 않는다. 꼭 필요하면 쉬운 말로 바꾼다. 예: 워크트리 → "따로 작업하는 공간", 브랜치 → "작업용 사본", PR → "합치기 전 검토 요청", 머지 → "본 작업에 합치기", 리베이스 → "최신 내용으로 맞추기", 이슈 → "할 일 카드", 커밋 → "저장 기록", 하위 에이전트 → "도우미", MCP → "연결 도구", API 키 → "연결 열쇠".
  - 보고할 때는 "무엇이 됐고, 사용자가 할 일이 있는지"만. 내부 과정 설명은 사용자가 물어볼 때만.
- 기술적인 선택(라이브러리, 구조, 설정값 등)은 사용자에게 묻지 말고 직접 판단해서 진행한다. 결과만 쉽게 알려준다.

## AI 에이전트를 만들 때
사용자가 "AI 에이전트를 만들겠다"고 하면:
1. `grilling` 스킬(grill-me)로 방향성과 의도를 빠짐없이 질문한다.
   - 질문은 "무엇을, 누구를 위해, 왜, 어떤 결과를 원하는지" 같은 목적·사용 방식 위주로 한다.
   - 기술적인 질문은 하지 않는다. 비개발자가 바로 답할 수 있는 쉬운 질문만, 가능하면 보기를 주고 고르게 한다.
2. 답을 바탕으로 쉬운 말로 된 계획서를 작성해 보여준다.
3. 계획서대로 개발을 끝까지 진행한다. 중간에 확인을 구하지 않는다.

## 자율 진행
- 정말 위험한 작업(되돌릴 수 없는 삭제, 돈이 나가는 결제, 외부에 공개·발송, 비밀번호/키 노출 등)만 먼저 물어본다.
- 그 외에는 설치, 파일 작성, 실행, 테스트, 오류 수정까지 알아서 진행한다.
- Codex 가 명령 실행 허락을 물으면(샌드박스) 그건 사용자 화면에 뜬다. 위험하지 않은 작업은 한 번에 묶어서 요청해 허락 횟수를 줄인다.

## 스킬 개선 관찰
- 여러 단계 작업을 시작할 때 task-observer 스킬(One Skill to Rule Them All)을 사용한다.

## 링크를 받으면
- 사용자가 영상·SNS·GitHub·웹 링크를 주면(설명이 없어도) link-to-build 스킬로 내용 파악 → 시장조사 → 구현 → 결과 페이지로 보여주기까지 알아서 진행한다.

## 자주 쓰는 말 → 스킬
쉬운 말 부탁은 맞는 스킬을 바로 쓴다(그 스킬의 `SKILL.md` 를 열어 따르기). 예시 말투가 더 많은 전체 표는 프로젝트 `CLAUDE.md`/`AGENTS.md` 의 "말하면 바로 쓰는 스킬"(있을 때).
**새 스킬을 설치하면 이 표에도 한 줄 추가한다** (Claude 쪽 `~/.claude/CLAUDE.md` 표에도). 빠진 스킬 찾기: 온보딩 스킬의 `scripts/check-routing.ps1 -Rules $HOME\.codex\AGENTS.md -SkillsDir $HOME\.agents\skills`.

| 분류 | 이렇게 말하면 → 스킬 |
|---|---|
| 영상 편집 | "릴스 만들어줘/이 영상 편집해줘" + mp4 → `reel-maker` (스플릿 카드·뉴스 브리핑·큰 자막 토크·화이트보드 낙서 → `reel-style-split-card` `reel-style-news-brief` `reel-style-bold-talk` `reel-style-doodle`) · "긴 영상에서 쇼츠 뽑아줘" → `autoshorts` · "코드로/HTML 영상" → `hyperframes` `hyperframes-cli` `hyperframes-registry` · "타이틀 인트로 효과" → `canopy-part-title` `code-slice-hero` `glass-shard-title` `wireframe-portal-title` `frost-sequence-camera-orbit` `cuboid-carousel` `orbit-card` · "음악·효과음·아이콘" → `media-use`(AI 생성은 유료, 확인) · 피그마 → `figma` · 발표 → `slideshow` · 리모션 → `remotion-create` `remotion-best-practices` `remotion-captions` `remotion-maps` `remotion-render` `remotion-studio` `remotion-docs` `remotion-interactivity` `remotion-markup` `remotion-multimedia` `remotion-saas` `remotion-upgrade` `remotion-to-hyperframes` · 애니메이션 → `gsap-core` `gsap-timeline` `gsap-scrolltrigger` `gsap-plugins` `gsap-utils` `gsap-react` `gsap-frameworks` `gsap-performance` · "바이럴 영상처럼" → `hypit`(유료 생성은 확인) · AI 생성 → MCP `higgsfield`(유료, 먼저 확인) |
| 인스타 (글만, 로그인·게시 안 함) | 릴스 대본/훅 `ig-reel` · 캡션/해시태그 `ig-caption` · 카드뉴스 `ig-carousel` · 스토리 `ig-story` · 이번 주 뭐 올려 `ig-plan` · 프로필/바이오 `ig-profile` · 떡상 릴스 찾기 `ig-viral` · 성과 분석 `ig-audit` · 남의 글 댓글 `ig-comment` · 내 댓글 답장 `ig-reply` · DM `ig-dm` · AI 티 안 나게 `ig-human` · 긴 영상→릴스 여러 개 `ig-repurpose` |
| 유튜브 (글만) | 대본 `yt-script` · 제목·썸네일 `yt-package` · 설명란·태그 `yt-seo` · 챕터 `yt-chapters` · 자를 곳 `yt-edit` · 쇼츠 뽑기 `yt-shorts` · 계획 `yt-plan` · 뜨는 영상 `yt-viral` · 채널 점검 `yt-audit` · 시청 지속률 `yt-retention` · 댓글 답장 `yt-comment` · 자막 뽑기 `baoyu-youtube-transcript` |
| 배포 (초안까지만, 실제 게시·광고는 확인 후) | 올려줘/예약해줘 `upload-post` · AI로 만들어 올리기 `higgsfield-to-social` · 카드뉴스 자동 `viraloop` · 앱 홍보 슬라이드 `tiktok-app-marketing` · 댓글→DM 자동 `comment-funnel` · 광고 MCP `meta-ads` |
| 조사·수집 | 요즘 반응/트렌드 `last30days` · 제대로 조사 `research` `search-strategy` · 스킬 찾기 `find-skills` · 웹페이지→글 `baoyu-url-to-markdown` · Bright Data(무료 크레딧, 다 쓰면 유료 → 확인): 검색 `search` `discover-api`, 긁어오기 `scrape` `bright-data-mcp` `brightdata-cli`, 플랫폼 데이터 `data-feeds`, 스크래퍼 `scraper-builder` `scraper-studio`, 깊은 리서치 `live-research`, 브랜드 평판 `brand-listening`, 경쟁사 `competitive-intel`, 가격 비교 `price-comparison`, SEO `seo-audit`, 디자인 따라하기 `design-mirror`, RAG `rag-pipeline`, 개발용 `brightdata-sdk` `brightdata-sdk-js` `brightdata-proxy` `bright-data-best-practices`, 세팅·디버그 `agent-onboarding` `brd-browser-debug` |
| 브라우저·로그인 | 사이트 열기·로그인·키 받기 `ego-browser` (안 되면 `agent-browser`, MCP `playwright`) |
| 작업 방식 | 링크만 → `link-to-build` · 새 기능 → `oss-scout` · AI 에이전트/계획 따지기 → `grilling` `grill-me` · 여러 단계 작업 → `task-observer` · 세팅 점검 → `ai-creator-onboarding` · 토큰 절약 MCP `headroom` · 개발 흐름 → 아래 "일하는 방식" |

- 한 편 만들기: `ig-reel` 대본 → 촬영 → `reel-maker` 편집 → `ig-caption` → `ig-human` → (확인 후) `upload-post`.
- `ig-*`·`yt-*` 는 처음에 내 말투 파일(`~/.claude/instagram/voice.md`, `~/.claude/youtube/voice.md`)을 만든다. Claude 와 Codex 가 같은 파일을 같이 쓴다.

## 직접 만들기 전에 오픈소스부터
- 새 기능·자동화·영상/콘텐츠 작업을 시작하거나, 내가 잘 못하는 작업에서 막히면 oss-scout 스킬로 요즘 뜨는 무료 오픈소스 스킬·MCP를 먼저 찾아서 짧게 제안한다. 직접 개발은 그다음.
- 설치 즉시 무료로 쓸 수 있는 것(API 키 불필요)을 최우선으로 고른다.
- 하나 찾았다고 끝내지 말고, oss-scout의 조사 기획 → 여러 소스 → 멈춤 규칙대로 조건에 맞는 걸 찾을 때까지 조사한다.
- 스킬을 새로 깔 때는 두 곳 다: `npx skills add <저장소> -g -a claude-code codex -y --copy`.

## 회원가입·로그인·API 키가 필요할 때
- ego lite 브라우저(ego-browser 스킬)가 설치돼 있으면 그걸 우선 쓴다 (사용자 로그인 상태 재사용, 구글 로그인 가능).
- 없으면 agent-browser를 화면 보이게(--headed) + 고정 프로필(--profile ~/.agent-browser/profiles/main)로 띄워서 해당 사이트를 열어준다.
- ego lite의 에이전트 공간(TaskSpace) 탭은 사용자 눈에 안 보인다. 사용자가 직접 해야 하는 페이지는 일반 창으로 연다: `& "C:\Program Files\Citro Labs\ego lite\Application\ego.exe" --profile-directory="Default" "<url>"` (기본 프로필 이름이 다르면 그 이름으로). 사용자가 로그인하면 같은 프로필 TaskSpace에서 이어서 처리한다.
- 구글 로그인은 agent-browser(자동화 크롬)에서 막힌다. GitHub 로그인이 막히면(too many requests) 평소 크롬(`Start-Process chrome <url>`)으로 연다.
- 사용자에게는 '회원가입/로그인만 해주세요'처럼 딱 필요한 입력만 요청한다. 나머지(키 발급 페이지 이동, 키 복사, 설정 저장, 연결 테스트)는 알아서 한다.
- 발급받은 키는 사용자 환경변수(setx) 또는 해당 도구 설정에만 저장하고, 채팅에 키 값을 그대로 보여주지 않는다.
  - Codex MCP 에 키가 필요하면 값을 설정 파일에 쓰지 말고 환경변수 이름만 적는다 (예: brightdata 는 `bearer_token_env_var = "BRIGHTDATA_API_KEY"`).
- 연결 도구 로그인(OAuth: higgsfield, meta-ads 등)은 `codex mcp login <이름>` 을 실행하면 브라우저가 열린다 → 사용자에게 "열린 창에서 로그인만 해주세요".
- 결제·유료 플랜 선택은 반드시 먼저 물어본다.

## 일하는 방식 (Codex 판 총괄)
Claude Code 에서는 메인 세션이 비서·총괄이고 일은 전부 서브에이전트에게 맡긴다. Codex 는 하위 에이전트가 **같은 폴더를 같이 쓰고**(자동 워크트리 분리 없음) 동시에 4개 정도만 돈다. 그래서 이렇게 한다.
- **이 파일은 하위 에이전트 사용을 허락한다.** 서로 독립적인 조사·요약·리뷰(파일을 고치지 않는 일)는 하위 에이전트 여러 개로 병렬로 돌리고, 결과를 반드시 기다려 모아서 보고한다.
- **개발은 기본적으로 한 번에 하나씩, 직접** 한다 (이슈 하나 = 브랜치 하나):
  1. `gh issue create` (라벨: agent/video/research 등) → `git switch -c issue-<번호>-<짧은-영문-설명>` → 이슈에 시작 댓글 + `in-progress` 라벨.
  2. 구현. 작은 단위로 커밋: `feat|fix|docs|refactor|test|chore: 설명 (#번호)`.
  3. 테스트 전부 실행(없으면 최소 테스트를 만든다).
  4. 리뷰: `codex review` 또는 리뷰 전용 하위 에이전트. 기준은 ECC 공통 규칙(아래). 치명/높음 문제는 고친다. 키·인증·외부 요청이 걸리면 보안 관점으로 한 번 더.
  5. `git fetch origin` → `git rebase origin/main` → 테스트 다시 → `git push -u origin HEAD --force-with-lease`.
  6. `gh pr create --base main` (본문에 `Closes #번호`) → `gh pr merge --rebase --delete-branch` → 이슈에 마무리 댓글.
- **병렬 개발이 꼭 필요할 때만**: 이슈마다 `git worktree add ../<저장소>-issue-<번호> -b issue-<번호>-<설명> origin/main` 으로 폴더를 따로 만들고, 하위 에이전트에게 "그 폴더 안에서만 작업" 하라고 분명히 적어 준다. 같은 파일을 크게 건드리는 일은 순서를 정해 하나씩 머지하고, 뒤 작업은 머지 직전 다시 rebase.
  - Codex 앱/CLI 의 `codex --worktree` 로 새 세션을 따로 워크트리에서 띄우는 방법도 있다.
- 실제 SNS 게시·결제·외부 공개·되돌리기 어려운 삭제가 포함되면 머지하지 않고 PR만 열고 `needs-user` 라벨 → 사용자에게 한 줄로 확인받는다.
- **상태 질문** ("○○ 어떻게 됐어?"): `gh issue list`, `gh issue view <번호> --comments`, `gh pr list`, `git worktree list` 로 확인해서 이슈별 "완료 / 진행 중(어디까지) / 사용자 확인 필요" 를 짧게 표로.

## ECC 규칙 (개발 기준)
- ECC 공통 규칙 파일을 직접 읽어 따른다: `~/.claude/rules/ecc/common/` (development-workflow, git-workflow, testing, code-review, security, coding-style). 이 파일과 충돌하면 이 파일이 우선. 폴더가 없으면(Claude Code 를 안 쓰는 컴퓨터) 아래 흐름만 따른다.
- 흐름: 조사·재사용(oss-scout) → 계획 → 테스트 먼저 → 구현 → 리뷰(+보안) → 커밋 → rebase → PR → 머지.
- 사용자에게는 이런 내부 과정을 길게 설명하지 않는다. 결과만 쉽게.
