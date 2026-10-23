# ai-creator-onboarding

비개발자 크리에이터가 **Claude Code** 하나로 AI 에이전트 개발, AI 쇼츠·영상 제작, 콘텐츠 생성·자동 편집·배포까지 할 수 있게 해주는 온보딩 스킬 묶음입니다.
GitHub에서 요즘 뜨는 무료 오픈소스 스킬·MCP를 한 번에 설치하고, Claude가 "쉬운 말로 짧게, 알아서 끝까지" 일하도록 규칙을 세팅합니다.

> A Claude Code onboarding kit for non-developer creators: installs a curated set of trending open-source skills/MCP servers for AI video, shorts, content automation and agent building, plus working rules that let Claude run autonomously and only ask you to log in. (Windows / PowerShell)

## 들어있는 스킬

| 스킬 | 하는 일 |
|---|---|
| `ai-creator-onboarding` | 전체 환경 설치·점검·복구. "온보딩 해줘", "환경 점검해줘" |
| `link-to-build` | 유튜브·릴스·틱톡·GitHub 링크만 주면 → 내용 파악 → 시장조사 → 구현 → 결과 페이지 |
| `oss-scout` | 직접 만들기 전에 무료 오픈소스 스킬·MCP를 끝까지 찾아서 제안 (조사 기획 → 다중 소스 → 멈춤 규칙) |

**작업 방식**: 한국어 대화 + 총괄 비서 + 이슈별 워크트리 개발 (issue-worker 에이전트, ECC 규칙 연결) — 메인 세션은 대화·분배만, 개발은 이슈마다 워크트리에서 테스트·리뷰·PR·머지까지.

## 설치

```bash
npx skills add lulu-mom/ai-creator-onboarding -g -a claude-code
```

그다음 Claude Code에서:

```
온보딩 해줘
```

Claude가 `scripts/setup.ps1` 을 실행해 아래 도구를 설치하고, 로그인이 필요한 곳만 브라우저를 띄워 요청합니다.

## 설치되는 것

- **플러그인**: [ECC (Everything Claude Code)](https://github.com/affaan-m/ECC)
- **MCP**: Higgsfield(AI 이미지·영상), Meta Ads, Bright Data, Playwright, Headroom
- **영상**: HyperFrames, Remotion, GSAP, Hypit, OpenMontage, ffmpeg
- **음성/비전**: faster-whisper, Silero VAD, MediaPipe, yt-dlp
- **유튜브·배포**: youtube-agent-skill(yt-*), Upload-Post 스킬(autoshorts, viraloop 등)
- **조사**: find-skills, last30days, research, search-strategy, baoyu-youtube-transcript, Bright Data 스킬
- **작업 방식**: grill-me, task-observer(One Skill to Rule Them All), agent-browser, ego-browser(ego lite)

각 도구의 라이선스와 이용 약관은 원 저작자의 것을 따릅니다. 이 저장소는 설치 순서와 작업 규칙만 담고 있습니다.

## 계정 연결 (사용자는 로그인만)

| 서비스 | 필요한 것 |
|---|---|
| ego lite | https://lite.ego.app/ 설치 |
| GitHub | 로그인 |
| Upload-Post | 무료 가입 → Claude가 키 발급·저장 |
| Bright Data | 무료 가입 → Claude가 키 발급·저장 |
| Higgsfield, Meta Ads | Claude Code에서 `/mcp` → 로그인 |

키는 Windows 사용자 환경변수나 도구 설정에만 저장되며, 이 저장소에는 어떤 키도 들어있지 않습니다.

## 요구 사항
Windows 10/11, Claude Code, winget. (Node.js, Python, Git, ffmpeg, gh 는 없으면 스크립트가 설치)

## License
MIT
