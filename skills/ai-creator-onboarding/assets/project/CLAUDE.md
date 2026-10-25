# <프로젝트 이름>

AI 에이전트 · AI 쇼츠/영상 · 콘텐츠 생성·자동 편집·배포 실험 프로젝트.
사용자 작업 규칙(소통 방식, 자율 진행, 링크 → 구현, 오픈소스 우선)은 `~/.claude/CLAUDE.md` 를 따른다.

## 브라우저 작업
웹사이트 열기, 회원가입·로그인, API 키 발급, 폼 입력, 스크린샷, SNS 페이지 보기 등 브라우저가 필요하면 **ego lite (`ego-browser` 스킬)** 를 기본으로 쓴다.

- 실행 파일: `%USERPROFILE%\.local\share\ego\active_version_dir\ego-browser.exe` (새 터미널에서는 `ego-browser` 로도 됨)
- **Bash 도구 + heredoc** 로 실행하는 게 가장 간단하다:
  ```bash
  ego-browser nodejs <<'EOF'
  const task = await taskSpace("<목표 이름>");
  const page = task.page("p1");
  await page.goto("https://...");
  console.log(task.spaceId, await page.snapshot());
  EOF
  ```
  PowerShell 에서는 따옴표·한글이 깨지므로 쓰지 않는다 (꼭 써야 하면 `.mjs` 파일 방식).
- 목표 하나당 TaskSpace 하나. 이름을 같게 주면 이어서 쓴다 (예: `api-key-setup`).
- 사용자의 크롬 로그인 상태를 그대로 쓰므로 구글 로그인도 된다. 사용자가 쓰는 탭은 건드리지 않는다.
- 관찰은 `snapshot()` 우선, 화면 확인이 필요할 때만 `screenshot()`. 여러 동작은 한 번에 실행하고 마지막에 snapshot 한 번.
- 사용자 입력이 필요한 순간(회원가입, 로그인, 2단계 인증, 결제)에만 "브라우저에서 ○○만 해주세요"라고 짧게 요청한다. 나머지는 직접 한다.
  - 에이전트 TaskSpace 탭은 사용자 눈에 잘 안 보인다 (handOff 해도 안 보였음, 확인됨). **사용자가 직접 해야 하는 페이지는 일반 창으로 연다:**
    `& "C:\Program Files\Citro Labs\ego lite\Application\ego.exe" --profile-directory="<기본 프로필>" "<url1>" "<url2>"`
    (기본 프로필 ID는 ego-browser 의 `await profiles()` 에서 isDefault 인 것)
  - 사용자가 "했어"라고 하면 같은 프로필의 TaskSpace(`taskSpace(...)`, 기본 프로필)로 키 발급 페이지에 가서 나머지를 처리한다. 로그인 쿠키는 프로필 단위로 공유된다.
- 결제·유료 플랜 선택, 실제 SNS 게시는 반드시 먼저 물어본다.
- 대체 수단: ego lite가 안 될 때만 `agent-browser` (단, 구글 로그인은 막힘), 단순 페이지 읽기는 WebFetch.

## API 키 보관
- 키는 사용자 환경변수(`setx 이름 값`) 또는 해당 도구 설정(`claude mcp add ...`)에만 저장한다. 채팅·파일·git 에 키 값을 남기지 않는다.
- 현재 쓰는 이름: `UPLOAD_POST_API_KEY`, `BRIGHTDATA_API_KEY` (선택: `GEMINI_API_KEY`)

## 말하면 바로 쓰는 스킬
사용자가 쉬운 말로 부탁하면 아래 표에서 맞는 스킬을 바로 부른다(Skill 도구). 여러 개가 맞으면 위에 있는 것 먼저. 애매하면 가장 가까운 걸로 진행하고 결과에 "○○로 했어요"라고 한 줄 남긴다.
**새 스킬을 설치하면 이 표에도 한 줄 추가한다** (전역 `~/.claude/CLAUDE.md` 의 "자주 쓰는 말 → 스킬" 에도). 빠진 스킬 찾기: 온보딩 스킬의 `scripts/check-routing.ps1`.

### 영상 편집
| 사용자가 이렇게 말하면 | 쓸 스킬 | 비고 |
|---|---|---|
| "릴스 만들어줘", "이 영상 편집해줘", "쇼츠로 만들어줘", "자막 넣어줘" + mp4 | `reel-maker` | 스타일 고르기 → 자동 편집 → 품질 검사. "알아서"면 대본 보고 스타일 선택 |
| "스플릿 카드로", "뉴스 브리핑으로", "큰 자막 토크로", "화이트보드 낙서로" | `reel-style-split-card` / `reel-style-news-brief` / `reel-style-bold-talk` / `reel-style-doodle` | 스타일 이름을 말하면 그 스타일로 바로 |
| "긴 영상에서 쇼츠 뽑아줘", "클립 여러 개 잘라줘", "오늘 클립 묶음" | `autoshorts` | 마지막 게시 단계는 사용자 확인 후 |
| "코드로 영상 만들어줘", "HTML 영상", "타이틀·자막 애니메이션", "렌더해줘" | `hyperframes` (+ `hyperframes-cli`, `hyperframes-registry`) | 기성 효과(전환·글리치·차트 등)는 registry 먼저 |
| "멋진 타이틀 인트로", "로고 등장 효과", "제목이 짠 나타나게" | `canopy-part-title` / `code-slice-hero` / `glass-shard-title` / `wireframe-portal-title` / `frost-sequence-camera-orbit` / `cuboid-carousel` / `orbit-card` | HyperFrames 블록(가로 1920x1080). 세로 릴스면 맞춰 수정 |
| "배경음악·효과음·아이콘·목소리 넣어줘", "로고 따줘" | `media-use` | HyperFrames 영상용 소재 |
| "피그마 디자인으로 영상" + figma 링크 | `figma` | |
| "발표 슬라이드 만들어줘", "발표 화면" | `slideshow` | |
| "리모션으로 영상", "리모션 자막/지도/렌더" | `remotion-create` / `remotion-best-practices` / `remotion-captions` / `remotion-maps` / `remotion-render` / `remotion-studio` / `remotion-docs` / `remotion-interactivity` / `remotion-markup` / `remotion-multimedia` / `remotion-saas` / `remotion-upgrade` | 새로 시작은 `remotion-create` |
| "리모션 걸 하이퍼프레임으로 옮겨줘" | `remotion-to-hyperframes` | |
| "움직임 부드럽게", "애니메이션 효과 넣어줘", "스크롤하면 움직이게" | `gsap-core` / `gsap-timeline` / `gsap-scrolltrigger` / `gsap-plugins` / `gsap-utils` / `gsap-react` / `gsap-frameworks` / `gsap-performance` | 웹·HTML 영상 안의 애니메이션 |
| "이 바이럴 영상처럼 만들어줘", "AI로 영상 연출해줘" | `hypit` | |
| "AI로 영상/이미지 만들어줘" | MCP `higgsfield` | 유료 크레딧 → 먼저 확인 |

### 인스타그램 (글·기획만. 로그인·게시 안 함)
| 사용자가 이렇게 말하면 | 쓸 스킬 | 비고 |
|---|---|---|
| "릴스 대본 써줘", "훅 뽑아줘", "뭐라고 말하지?", "○○로 릴스 하나" (영상 없음) | `ig-reel` | 훅·대본·화면 문구·시간표 |
| "캡션 써줘", "해시태그 뭐 달아?", "설명란 써줘" | `ig-caption` | |
| "카드뉴스 만들어줘", "슬라이드 게시물", "넘겨보는 거" | `ig-carousel` | 1080x1350 이미지까지 |
| "스토리 뭐 올려?", "스토리 구성", "투표 스티커 아이디어" | `ig-story` | |
| "이번 주 뭐 올려?", "콘텐츠 계획 짜줘", "올릴 게 없어" | `ig-plan` | |
| "프로필 점검해줘", "바이오 고쳐줘", "내 계정 몇 점?" | `ig-profile` | |
| "요즘 뜨는 릴스 찾아줘", "떡상 영상 뭐 있어?", "잘 되는 거 따라 하고 싶어" | `ig-viral` (+ `last30days`) | |
| "인사이트 봐줘", "성과 분석", "왜 이건 망했어?" | `ig-audit` | |
| "이 게시물에 댓글 달아줘", "남의 글에 뭐라고 쓰지?" | `ig-comment` | |
| "내 댓글 답장해줘", "댓글 정리해줘" | `ig-reply` | |
| "DM 써줘", "협업 제안 메시지", "답장 없는데 다시 보낼까?" | `ig-dm` | |
| "AI 티 안 나게", "사람이 쓴 것처럼", "자연스럽게 고쳐줘" | `ig-human` | 어떤 글이든 내보내기 전 마지막 단계 |
| "긴 영상/유튜브를 릴스 여러 개로", "이걸로 일주일 치" | 기획 `ig-repurpose` → 편집 `autoshorts` 또는 `reel-maker` | |

### 유튜브 (글·기획만)
| 사용자가 이렇게 말하면 | 쓸 스킬 | 비고 |
|---|---|---|
| "유튜브 대본 써줘", "오프닝 뭐라고 해?" | `yt-script` | |
| "제목 뭐로 해?", "썸네일 문구" | `yt-package` | |
| "설명란·태그 써줘", "검색에 안 걸려" | `yt-seo` | |
| "챕터·타임스탬프 달아줘" | `yt-chapters` | |
| "이 녹화본 어디 자를까?", "늘어지는 데 잘라줘" | `yt-edit` | 자를 목록(타임코드)까지 |
| "유튜브 영상에서 쇼츠 뭐 뽑지?" | `yt-shorts` | 실제 자르기는 `autoshorts`/`reel-maker` |
| "유튜브 업로드 계획", "다음에 뭐 찍지?" | `yt-plan` | |
| "요즘 유튜브에서 뜨는 거" | `yt-viral` | |
| "내 채널 점검해줘", "왜 안 커?" | `yt-audit` | |
| "사람들이 어디서 나가?", "시청 지속률" | `yt-retention` | |
| "유튜브 댓글 답장해줘" | `yt-comment` | |
| "유튜브 자막 뽑아줘", "이 영상 내용 정리" + 유튜브 링크 | `baoyu-youtube-transcript` | |

### 배포 (초안·예약안까지만 자동. 실제 게시·예약 등록·광고 집행은 사용자 확인 후)
| 사용자가 이렇게 말하면 | 쓸 스킬 | 비고 |
|---|---|---|
| "올려줘", "예약해줘", "인스타·틱톡·유튜브에 게시" | `upload-post` | |
| "AI로 만들어서 바로 올려줘" | `higgsfield-to-social` | 유료 크레딧 |
| "웹사이트로 카드뉴스 자동으로 계속" | `viraloop` | |
| "앱/제품 홍보 슬라이드 틱톡에" | `tiktok-app-marketing` | |
| "댓글에 키워드 달면 DM 자동으로" | `comment-funnel` | |
| "광고 성과 봐줘", "메타 광고 만들어줘" | MCP `meta-ads` | 돈 나감 → 먼저 확인 |

### 조사·수집
| 사용자가 이렇게 말하면 | 쓸 스킬 | 비고 |
|---|---|---|
| "요즘 사람들 반응 어때?", "최근 한 달 트렌드" | `last30days` | 소셜 반응 1순위 |
| "제대로 조사해줘", "공식 문서로 확인" | `research` (+ `search-strategy`) | |
| "이런 스킬/도구 있어?", "○○ 하는 방법" | `find-skills` | 새 기능은 `oss-scout` 먼저 |
| "이 페이지 글로 저장해줘", "웹페이지 마크다운으로" | `baoyu-url-to-markdown` | |
| "검색해줘", "구글 결과 뽑아줘" | `search` / `discover-api` | Bright Data(무료 크레딧). 단순 조회는 WebSearch 로 충분 |
| "이 사이트 긁어와", "페이지 내용 가져와" | `scrape` / `bright-data-mcp` / `brightdata-cli` | 단순 읽기는 WebFetch 로 충분 |
| "아마존·인스타·링크드인 데이터 뽑아줘" | `data-feeds` | |
| "스크래퍼 만들어줘" | `scraper-builder` / `scraper-studio` | |
| "깊게 리서치해서 보고서로" | `live-research` | |
| "우리 브랜드 평판", "사람들이 우리 얘기 뭐래?" | `brand-listening` | |
| "경쟁사 분석" | `competitive-intel` | |
| "최저가 찾아줘", "가격 비교" | `price-comparison` | |
| "내 사이트 SEO 점검" | `seo-audit` | |
| "저 사이트 디자인처럼 바꿔줘" | `design-mirror` | |
| "검색 엔진/RAG 만들어줘" | `rag-pipeline` | |
| 코드에 Bright Data 붙이기 | `brightdata-sdk` / `brightdata-sdk-js` / `brightdata-proxy` / `bright-data-best-practices` | 개발용 |
| "Bright Data 처음 세팅" / 수집 실패 원인 | `agent-onboarding` / `brd-browser-debug` | |

### 브라우저·로그인
| 사용자가 이렇게 말하면 | 쓸 스킬 | 비고 |
|---|---|---|
| "이 사이트 열어줘", "로그인해서 키 받아줘", "가입해줘", "스크린샷" | `ego-browser` | 1순위(사용자 로그인 상태 재사용) |
| ego lite 가 안 될 때 | `agent-browser` / MCP `playwright` | 구글 로그인은 막힘 |

### 작업 방식
| 사용자가 이렇게 말하면 | 쓸 스킬 | 비고 |
|---|---|---|
| 링크만 줌 (유튜브·릴스·틱톡·GitHub·블로그), "이거 해보고 싶어" | `link-to-build` | 파악 → 조사 → 구현 → 결과 페이지 |
| "이런 기능 만들고 싶어", "자동화하고 싶어", "막혔어" | `oss-scout` | 무료 오픈소스 먼저, 직접 개발은 그다음 |
| "AI 에이전트 만들래", "내 계획 따져봐" | `grilling` / `grill-me` | 목적 질문 → 계획서 → 개발 |
| 여러 단계 작업 시작 | `task-observer` | 스킬 개선점 기록 |
| "세팅 다시 해줘", "뭐 빠진 거 없어?", "환경 점검" | `ai-creator-onboarding` | |
| 토큰 아끼기 | MCP `headroom` | 자동 |
| 개발·리뷰·테스트 | 아래 "ECC 활용" 표 | |

**한 편 만들기 순서 (예):** 아이디어 → `ig-reel` 대본 → 사용자 촬영 → `reel-maker` 편집 → `ig-caption` → `ig-human` → (사용자 확인 후) `upload-post`.

- `ig-*`·`yt-*` 는 처음 쓸 때 **내 말투 파일**을 만든다(`~/.claude/instagram/voice.md`, `~/.claude/youtube/voice.md`). 없으면 사용자 영상·글 3개를 받아 말투를 정리해 저장한다. 한 번 만들면 계속 쓴다.
- `ig-*`·`yt-*` 는 글·계획만 만든다. 인스타·유튜브에 로그인하거나 게시하지 않는다. 게시는 `upload-post` 로, 사용자 확인 후.

## ECC 활용 (이 프로젝트)
ECC(`ecc@ecc` 플러그인) 전체 흐름·공통 규칙은 전역(`~/.claude/CLAUDE.md`, `~/.claude/rules/ecc/common/`)에 있다. 여기엔 이 프로젝트에서 실제로 쓸 것만 적는다.
스킬은 `ecc:<이름>` 으로 부른다(Skill 도구), 에이전트는 `subagent_type: "ecc:<이름>"`. 목록이 헷갈리면 `ecc:ecc-guide` 로 실제 설치본을 확인한다.
`ecc:` 에이전트가 subagent 목록에 없으면(도우미 안에서 자주 그럼) `general-purpose` 에 "플러그인 `agents/<이름>.md` 지침대로 행동" 이라고 넘긴다.

| 상황 | 쓸 것 (ECC) | 비고 |
|---|---|---|
| 만들기 전 기존 도구 찾기 | `search-first`, `skill-scout` | 사용자 `oss-scout` 먼저, 보조로 |
| 시장·트렌드·경쟁 조사 | `deep-research`, `market-research`, `research-ops` | 소셜 반응은 `last30days` 우선 |
| AI 에이전트 설계 | `agent-harness-construction`, `agentic-engineering`, `autonomous-agent-harness` | 큰 구조 결정은 `ecc:architect` |
| 에이전트 반복 실행·품질 게이트 | `continuous-agent-loop`, `ecc:agent-evaluator` | 무인 루프엔 승인 지점 필수 |
| LLM 비용·프롬프트 | `cost-aware-llm-pipeline`, `prompt-optimizer`, `prompt-caching-strategy` | |
| 데이터 수집 에이전트 | `data-scraper-agent` | 실제 수집은 Bright Data 스킬 |
| 외부 API/MCP 연결 만들기 | `api-connector-builder`, `mcp-server-patterns` | 키는 환경변수만 |
| 쇼츠·영상 편집 | `video-editing` (FFmpeg/Remotion 파이프라인), `videodb` | 긴 영상→클립은 `autoshorts` 우선 |
| 코드로 영상 만들기 | `remotion-video-creation`, `manim-video` (설명 애니메이션) | HTML 영상은 `hyperframes` |
| AI 이미지·영상·음성 생성 | `fal-ai-media` | 유료 크레딧 → 먼저 확인 |
| 글·대본·콘텐츠 캘린더 | `content-engine`, `article-writing`, `brand-voice` | 유튜브 대본은 `yt-script` 도 있음 |
| 마케팅 캠페인·SEO | `marketing-campaign`, `ecc:marketing-agent`, `ecc:seo-specialist` | |
| 플랫폼별 배포 문구·예약 | `crosspost`, `social-publisher`, `x-api` | **게시는 아래 주의 참고** |
| 계획 / 테스트 먼저 | `ecc:planner`, `ecc:tdd-guide`, `tdd-workflow`, `python-testing` | |
| 리뷰 | `ecc:code-reviewer` + `ecc:python-reviewer` / `ecc:typescript-reviewer` | 키·인증·외부 요청이면 `ecc:security-reviewer` |
| 빌드 깨짐 / 마무리 검증 | `ecc:build-error-resolver`, `verification-loop` | |
| 병렬 워크트리 | `dmux-workflows`, `/ecc:multi-workflow`, `/ecc:prp-implement` | |

### 개발 흐름 (이 프로젝트 기준)
1. 할 일마다 GitHub 이슈. 라벨: 종류 `agent` / `video` / `research` (+ `bug`, `documentation`), 상태 `in-progress`(작업 중) / `needs-user`(사용자 확인 필요).
2. 브랜치 `issue-<번호>-<짧은-영문-slug>`, 워크트리 하나에 이슈 하나. 커밋 `feat|fix|docs|refactor|test|chore: 설명 (#번호)`.
3. 하위 프로젝트는 폴더 단위(`<기능>/`)로 두고 테스트도 그 폴더 안에서 돈다.
   - Python: `<폴더>/tests/` + `python -m pytest <폴더>`
   - Node: `<폴더>/package.json` 의 `npm test`
   - 영상/미디어: 짧은 샘플로 실제 결과물 1개를 만들고 `ffprobe` 로 길이·해상도 확인. 큰 결과물은 커밋하지 않는다(`.gitignore`).
   - 외부 API 는 테스트에서 가짜(mock)로. 실제 호출 테스트는 키가 있을 때만 따로 돌린다.
4. 완료 기준: 테스트 통과 → 리뷰 CRITICAL/HIGH 0 → `origin/main` 으로 rebase 후 재테스트 → PR(`Closes #번호`) → `gh pr merge --rebase --delete-branch` → 이슈 닫힘 + 마무리 댓글.
5. 실제 게시·결제·외부 공개·되돌리기 어려운 삭제가 들어가면 머지하지 않고 PR + `needs-user` 라벨로 멈춘다.

### 주의 / 쓰지 않을 것
- **자동 게시 금지**: `social-publisher`, `crosspost`, `x-api`, `upload-post` 계열은 초안·예약안 작성까지만 자동. 실제 게시·예약 등록은 사용자 확인 후.
- `agent-payment-x402`(지갑 결제), `fal-ai-media` 등 유료 API 생성은 양과 관계없이 돈이 나가므로 먼저 묻는다.
- `autonomous-agent-harness`·`continuous-agent-loop` 로 무인 반복 작업을 만들 때 외부 발송 단계엔 사람 승인 지점을 둔다.
- `/ecc:pr`·`/ecc:prp-pr` 등 ECC 명령이 전역 PR 규칙(rebase → PR → 머지)과 다르게 움직이면 전역 규칙을 따른다.
- 이 프로젝트와 무관한 언어·업종 스킬(Java/Kotlin/Laravel/healthcare/network 등)은 쓰지 않는다.
- ECC 훅은 플러그인이 자동 적용한다. 따로 설정하지 않는다.
