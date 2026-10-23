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
