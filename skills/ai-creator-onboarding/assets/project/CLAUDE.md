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
