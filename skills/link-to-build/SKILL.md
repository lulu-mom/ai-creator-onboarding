---
name: link-to-build
description: 사용자가 유튜브·쇼츠·릴스·틱톡·인스타·X·블로그·GitHub 링크를 주면(설명이 없거나 "이거 해보고 싶어", "이렇게 만들어줘" 정도만 있어도) 내용을 파악하고, 시장조사를 하고, 직접 구현해서 결과물을 보여주는 전 과정 자동 워크플로. 링크만 단독으로 붙여넣은 경우에도 반드시 사용한다. AI 에이전트, AI 쇼츠/영상, 콘텐츠 생성·자동 편집·배포 아이디어가 대상.
---

# 링크 → 조사 → 구현 → 결과 보여주기

사용자는 비개발자다. 링크만 받아도 끝까지 알아서 진행하고, 쉬운 말로 짧게 보고한다.
정말 위험한 일(돈이 나가는 결제, 실제 SNS에 게시, 계정 비밀번호/키 노출, 되돌릴 수 없는 삭제)만 먼저 물어본다.

## 0. 시작 알림 (한 줄)
"링크 보고 있어요 → 조사 → 만들기 순서로 진행할게요" 정도로 짧게 알린다.

## 1. 링크 내용 파악
작업 폴더: `<작업폴더>\<짧은-영문-이름>\` 를 만들고 그 안 `source/` 에 자료를 모은다.

- **영상 링크 (YouTube, Shorts, Reels, TikTok, X 등)**
  1. 정보·자막: `yt-dlp --skip-download --write-info-json --write-auto-subs --sub-langs "ko,en" -o "source/%(id)s" <링크>`
  2. 자막이 없으면 음성만 받아서 받아쓰기:
     `yt-dlp -x --audio-format mp3 -o "source/audio.%(ext)s" <링크>` 후
     `python <이 스킬 폴더>/scripts/transcribe.py source/audio.mp3 source/transcript.txt` (이 스킬 폴더 = 이 SKILL.md 가 있는 곳. Claude: `~/.claude/skills/link-to-build`, Codex: `~/.agents/skills/link-to-build`)
  3. 화면 구성이 중요하면 영상을 받아 ffmpeg로 몇 장면 캡처해서 직접 본다
     (`ffmpeg -i video.mp4 -vf fps=1/5 source/frame_%03d.jpg`).
  4. 설명란·고정댓글에 나온 GitHub/도구 링크도 따라가서 읽는다.
  - 인스타/틱톡이 로그인 때문에 막히면 Bright Data 스킬(scrape)로 시도하고, 그래도 안 되면 사용자에게 "영상 설명을 복사해 주세요"라고 쉽게 부탁한다.
- **GitHub 링크**: README와 설치 방법을 읽는다. 스킬/MCP/플러그인이면 설치까지 한다.
- **글/웹페이지**: WebFetch 로 읽는다.

정리: "이 영상이 실제로 하는 것", "쓰인 도구", "결과물이 어떤 모습인지"를 `source/요약.md` 에 적는다.

## 2. 시장조사 (가볍고 빠르게)
- 같은 주제로 요즘 뜨는 영상/채널/서비스를 3~5개 찾는다 (WebSearch, yt-viral 스킬, Bright Data 스킬 활용).
- 확인할 것: 왜 뜨는지, 비슷한 서비스·가격, 사용자가 따라 할 때 필요한 것(유료 API, 계정 등), 차별화 아이디어 1~2개.
- `조사.md` 에 쉬운 말로 정리한다.

## 3. 방향 정하기
- 링크 내용이 분명하면 바로 구현으로 넘어간다.
- AI 에이전트를 새로 만드는 일이거나 방향이 여러 갈래면 `grilling` 스킬로 쉬운 질문만 몇 개 해서 의도를 확인하고, 짧은 계획서를 보여준 뒤 진행한다.
- 유료 API 키가 꼭 필요하면 무료 대안(로컬 도구: faster-whisper, ffmpeg, Remotion, HyperFrames, piper TTS 등)으로 먼저 데모를 만든다. 키가 필요한 부분은 마지막 보고 때 한 줄로 알린다.

## 4. 구현
설치된 도구를 적극 활용한다:
- 영상 제작/편집: `hyperframes`, `remotion-*`, `gsap-*`, OpenMontage(`<작업폴더>\OpenMontage`), ffmpeg
- 쇼츠 자르기·자막: `autoshorts`, `yt-shorts`, `remotion-captions`, faster-whisper, Silero VAD, MediaPipe(얼굴 추적 크롭)
- AI 이미지/영상 생성: Higgsfield MCP, `higgsfield-to-social`
- 유튜브 기획: `yt-script`, `yt-package`, `yt-seo` 등
- 데이터 수집: Bright Data 스킬
- 배포: `upload-post` — **실제 게시는 반드시 사용자 확인 후에만**

직접 실행해 보고 오류는 스스로 고친다. 실제로 돌아가는 결과물을 만드는 게 목표다.

## 5. 결과 보여주기
Artifact 로 결과 페이지를 하나 만들어 보여준다:
- 한 줄 요약: 무엇을 만들었는지
- 결과물: 생성된 영상/이미지 경로, 미리보기(가능하면), 실행 방법(복사해서 쓰는 한 줄)
- 시장조사 핵심 3줄
- 다음에 할 수 있는 것 2~3개

채팅 보고는 짧게:
"다 만들었어요 ✅ [무엇]. 결과는 여기서 보세요 → (링크). 다음으로 ○○ 해볼까요?"
