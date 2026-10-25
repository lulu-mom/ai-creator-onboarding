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
| `reel-maker` | 세로 토크 영상 하나를 주면 "릴스 만들어줘" 한마디로 스타일 고르기 → 자동 편집 → 품질 검사까지 ("알아서"면 대본을 보고 스타일도 골라 줌) |
| `reel-style-split-card` | 스플릿 카드: 크림 배경 위 UI 카드 + 아래 얼굴. 업무·툴 사례를 깔끔하게 |
| `reel-style-news-brief` | 뉴스 브리핑: 상단 헤드라인 바 + 방송 자막띠 + 티커. 소식·실험 결과 정리 |
| `reel-style-bold-talk` | 큰 자막 토크: 굵은 단어 자막 + 떠 있는 패널 + 색 카드. 강한 주장·숫자 이야기 |
| `reel-style-doodle` | 화이트보드 낙서: 종이 보드에 손글씨 화살표·동그라미가 그려짐. 개념·단계 설명 |

**릴스 자동 편집 엔진** `reel-toolkit/`: 받아쓰기(faster-whisper) → 말 끊김·NG 컷 → 얼굴 추적 → 자막·카드 계획 → HyperFrames 렌더 → 효과음·음량 맞추기까지 한 번에 하는 편집기와 품질 채점기. 위 `reel-*` 스킬이 이 엔진을 씁니다. 한국어 세로(9:16) 토크 영상용이고, 얼굴이 보이는 영상이어야 합니다. 각 스타일 폴더의 `preview.png` 는 예시 대본과 가짜 화자 그림으로 만든 샘플입니다.

**말하면 바로 쓰는 스킬**: "릴스 만들어줘", "캡션 써줘", "카드뉴스 만들어줘", "요즘 뜨는 릴스 찾아줘" 같은 쉬운 말을 맞는 스킬로 바로 연결하는 표가 규칙 파일에 들어 있습니다. 설치가 끝나면 표에 빠진 스킬이 없는지 자동으로 점검합니다(`scripts/check-routing.ps1`).

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
- **릴스 자동 편집**: 이 저장소의 `reel-toolkit/` 폴더만 `~\projects\ai-creator-onboarding\reel-toolkit` 에 받아서(로그인 불필요) npm 패키지·크로미엄·얼굴 인식 모델·파이썬 패키지까지 설치, 스킬 `reel-maker` + 스타일 4종
- **음성/비전**: faster-whisper, Silero VAD, MediaPipe, yt-dlp
- **유튜브·인스타·배포**: youtube-agent-skill(yt-*), instagram-agent-skill(ig-* — 릴스 대본·캡션·카드뉴스·스토리·DM 문구, 글만 쓰고 게시·로그인 없음), Upload-Post 스킬(autoshorts, viraloop 등)
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
