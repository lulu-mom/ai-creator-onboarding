# 릴스 편집 스타일 카탈로그 (2026-10 조사)

목적: 지금 하나뿐인 자동 편집 스타일(크림 배경 + 위 그래픽/아래 얼굴 + 어두운 박스 자막)을 **고를 수 있는 8개 스타일**로 확장.
패키징: 스타일 1개 = 스킬 1개(`reel-style-*`). 공용 엔진 = `reel-toolkit/pipeline` + `quality/reel_score.py`. 선택용 스킬 `reel-maker` 1개.
특정 크리에이터의 에셋·폰트·로고는 복사하지 않는다. 아래는 모두 일반적인 스타일 문법으로만 서술.

## 조사 근거 (요약)

- YouTube (yt-dlp ytsearch, 2026-10-24): "릴스 편집 스타일 2026", "쇼츠 자막 스타일", "예능 자막 쇼츠", "정보성 릴스 편집", "릴스 자막 트렌드", "short form editing styles 2026", "talking head reel editing trends 2026".
  - 영문 편집 분석 영상(5만~120만 조회): 2026 토킹헤드는 ① 고밀도 B-roll/모션그래픽(스토리형), ② 책상 앞 튜토리얼형 = **50/50 분할** 또는 **사람 하단 + 위에 화면 시연**, ③ "그린스크린" 형(사람 컷아웃 + 뒤에 스크린샷/기사), ④ 얼굴 없는 보이스오버, ⑤ "심플 편집"(컷 + 깔끔한 자막만)이 각각 잘 됨. 공통 조언: *말하는 대상을 최대한 빨리 화면에 보여줄 것*, 자막은 가운데·크게·약한 그림자, 핵심 단어만 색 바꿈 또는 폰트 바꿈(세리프/스크립트), 슬라이드인마다 휙(whoosh) 효과음, 마무리로 비네트 + 노이즈 + 줌 블러.
  - 한국어: 예능형 "감정 데코 자막"(양옆 장식, 떨림·불꽃·물결 모션, 네온 와이프 등장) 템플릿이 꾸준히 인기. 자막 가독성 규칙 = 강한 명암 대비, 배경이 바뀌면 그림자/그라데이션 깔기, **세이프 영역 안**, 좌우 여백 약 10%, 큰 강조 자막은 최대 2줄, 얼굴은 가리지 않기. "상단 고정 제목 자막 + 하단 말자막" 구성이 정보성 쇼츠의 기본형으로 반복 등장. 쇼츠/릴스 자막 템플릿 묶음(65~110종) 배포 영상 다수 = 자막 스타일 다양화 수요 큼.
- 설치된 도구: hyperframes-registry(448개 항목, 아래 블록 이름은 `npx hyperframes catalog --query` 로 실제 확인), OpenMontage 스타일 플레이북(`OpenMontage/styles/*.yaml`: identity / visual_language / typography / motion.pacing_rules / audio 구조 — 스키마 설계에 참고), OpenMontage `remotion-composer/src/components/CaptionOverlay.tsx`(단어별 하이라이트 자막).
- 엔진 확인: `pipeline/steps/compose.py` 가 HyperFrames HTML(자막 `captions_html`, 장면 `scene_files`)을 만들므로 hyperframes 컴포넌트를 그대로 붙이는 게 가장 싸다. Remotion 은 별도 렌더러라 보조용.

## 한눈에 보기

| # | 이름 | 스킬 이름 | 잘 맞는 콘텐츠 | 핵심 그림 |
|---|---|---|---|---|
| 1 | 스플릿 카드 | `reel-style-split-card` | 업무 자동화·툴 사용 후기·사례 | 위 UI 카드 / 아래 얼굴, 크림 배경 (현재 스타일) |
| 2 | 큰 자막 토크 | `reel-style-bold-talk` | 강한 주장·돈/숫자·동기부여·꿀팁 | 얼굴 꽉 + 화면 가운데 굵은 단어 자막, 펀치 줌 |
| 3 | 예능 자막 | `reel-style-variety` | 일상·리액션·후기·웃긴 썰 | 알록달록 테두리 자막 + 이모지/말풍선 스티커 |
| 4 | 뉴스 브리핑 | `reel-style-news-brief` | AI 뉴스·업계 소식·트렌드 정리 | 상단 헤드라인 바 + 하단 자막띠 + 티커 |
| 5 | 다큐 시네마틱 | `reel-style-docu` | 개인 스토리·실패담·인터뷰 | 레터박스, 작은 세리프 자막, 필름 질감 |
| 6 | 화이트보드 낙서 | `reel-style-doodle` | 개념 설명·단계·공부 정리 | 종이 배경 + 손글씨 화살표·동그라미 |
| 7 | 미니멀 타이포 | `reel-style-minimal-type` | 명언·인사이트·브랜드 메시지 | 여백 많은 화면에 큰 단어 한두 개 |
| 8 | 화면 시연 | `reel-style-screen-demo` | 툴 튜토리얼·AI 툴 리뷰·따라하기 | 위(또는 전체)에 화면 녹화, 아래 원형/컷아웃 얼굴, 커서 줌 |

---

## 1. 스플릿 카드 (현재 스타일, 기준점)

- 스킬: `reel-style-split-card` — "크림 배경 위 UI 카드 모션그래픽 + 아래 얼굴 분할 화면. 업무·툴 사례를 차분하고 깔끔하게 보여주는 기본 스타일."
- 잘 맞는 콘텐츠: 업무 자동화 사례, 툴 결과 보여주기, "AI에게 보고서를 맡겨봤다" 같은 과정 스토리.
- 레이아웃: split(위 그래픽 0~0.45H / 아래 얼굴) ↔ face_full(22%) ↔ graphic_full(12%) 교대. 기존 `pipeline/styles/reference.json` 그대로.
- 자막: Pretendard 700, 70px, 어두운 반투명 박스(`rgba(30,26,26,.92)`, radius 10), 핵심어 주황, 이음매(0.48H) 위치, 0.07s 팝인, 최대 3단어/8자.
- 색: 배경 `#F0EAE6`, 카드 `#FFFFFF`, 잉크 `#1E1B1A`, 포인트 `#E0654A`, 강조 자막 `#F07650`, 성공 `#2FA36B`.
- 모션 언어: 앱 창 모양 UI 카드, 항목 차례로 채워짐, 히어로 카드 "슬램" + 도장, 진행 트래커.
- 전환: 카드 교체(밀어내기), 펀치 인/아웃, 콜드오픈.
- 속도: 컷 약 19회/분, 세그먼트 1.0~2.1초, 말 속도 1.15배.
- 소리: 컷마다 작은 틱/팝(-20dB), 히어로에 스탬프. 음악은 가볍고 밝은 로파이.
- 구현: 현재 엔진 + `ai-chat-reveal`, `notification-pileup`, `success-check`, `count-up`, `mk-progress-stat`, `screen-flow-carousel`.
- 자동 선택: 툴/서비스 이름 + "만들었다/맡겼다/결과" + 단계 숫자가 함께 나오는 과정형 이야기 → 이 스타일 (기본값).

## 2. 큰 자막 토크

- 스킬: `reel-style-bold-talk` — "얼굴을 크게 두고 화면 가운데 굵은 단어 자막이 한 단어씩 튀어나오는 고에너지 토킹헤드 스타일."
- 잘 맞는 콘텐츠: 강한 주장, 돈·숫자 이야기, 동기부여, "이거 모르면 손해" 꿀팁, 말이 빠른 영상.
- 레이아웃: face_full 90% 이상(얼굴 눈높이 0.30H), 핵심 문장에서만 짧은 B-roll/스크린샷 전체화면 0.8~1.5초.
- 자막: 한 번에 1~3단어, 화면 0.60~0.65H(턱 아래), Pretendard 900(또는 Black Han Sans·Gmarket Sans Bold) 96~110px, 흰 글자 + 검정 외곽선 8~10px + 약한 그림자, **현재 말하는 단어만** 노랑/형광초록으로 색 + 1.12배. 숫자·돈은 한 단어 단독 크게(140px). 등장: 0.9→1.08→1.0 스프링 팝 0.12초, 퇴장 없음(바로 교체).
- 색: 글자 `#FFFFFF`, 외곽선 `#000000`, 강조 `#FFE14D`, 보조 강조 `#3DFF8A`, 경고 `#FF4D4D`. 화면 그레이드 대비 약간 올림.
- 모션 언어: 펀치 줌(1.0↔1.15, 2~3초마다), 카메라 흔들림 짧게, 핵심어 화면 가득 슬램, 이모지 1~2개 팝.
- 전환: 하드컷 위주, 강조에서 줌 블러 컷, 흰 플래시 1프레임.
- 속도: 매우 빠름. 컷 25~35회/분, 무음 0, 세그먼트 0.8~1.6초, 말 속도 1.1~1.2배.
- 소리: 강조어마다 "팝/딩", 줌마다 휙, 숫자에 계산기 "칭". 음악 BPM 110~130 드라이브감 있는 비트, -24dB 이하 덕킹.
- 구현: `caption-highlight`(단어별 배경 스윕), `caption-pill-karaoke`, `caption-kinetic-slam`(단어 단독 슬램), `caption-emoji-pop`, `number-pop-in`, 컴포넌트 `camera-shake`, `yt-camera-move`, 전환 `cinematic-zoom`, `beat-freeze-cut`.
- 자동 선택: 말 속도 빠름(≥5.5음절/초) + 단정형 문장("~입니다", "무조건", "절대") + 숫자·금액 빈도 높음 → 이 스타일.

## 3. 예능 자막

- 스킬: `reel-style-variety` — "한국 예능처럼 감정이 드러나는 알록달록 테두리 자막, 말풍선·이모지 스티커, 효과음으로 웃기고 친근하게 만드는 스타일."
- 잘 맞는 콘텐츠: 일상 브이로그, 리액션, 사용 후기, 실수담·웃긴 썰, 캐릭터가 강한 화자.
- 레이아웃: face_full 기본, 리액션 순간 얼굴 확대(1.3배) + 정지 프레임, 가끔 2분할(전/후 비교).
- 자막 2층 구조:
  - 말자막: 하단 0.78H, Pretendard 800 64px, 흰 글자 + 검정 외곽선 6px.
  - 예능 데코 자막(감정 단어만): 얼굴 옆 빈 공간, Jua·Do Hyeon·Black Han Sans 같은 둥근/굵은 무료 폰트 90~120px, **2중 외곽선**(안쪽 색 테두리 10px + 바깥 검정 4px), 감정별 색(웃음 노랑, 당황 하늘, 분노 빨강, 감동 분홍), 살짝 기울임(-6°~6°), 양옆 작은 장식(별·땀방울·불꽃 선). 등장: 가로 눌림→튕김 팝 또는 와이프, 유지 중 미세 떨림/물결.
- 색: `#FFD43B`(웃음), `#4DABF7`(당황), `#FF6B6B`(분노), `#F783AC`(감동), `#69DB7C`(정답), 외곽선 `#1A1A1A`.
- 모션 언어: 스티커/이모지 팝, 말풍선, 집중선·땀방울, 화면 흔들림, 정지 + 확대 리액션.
- 전환: 하드컷, 리액션 전 "띠용" 줌, 장면 바뀔 때 별 와이프.
- 속도: 빠름. 컷 22~30회/분, 리액션 순간엔 0.5초 정지(웃음 포인트 살리기).
- 소리: 예능 효과음 팩(뿅, 띠용, 박수, 까마귀, 두둥) — 무료 라이선스만. 음악은 통통 튀는 우쿨렐레/칩튠.
- 구현: `caption-emoji-pop`, `caption-neon-accent`(흔들리는 강조), `hw-text-cloud`(말풍선), `spring-pop`, `badge-pop`, `rgb-glitch-text`(당황), `camera-shake`, 전환 `transitions-scale`. 감정 분류는 대본 LLM 태깅.
- 자동 선택: 웃음(ㅋㅋ/하하), 감탄사("헐", "대박", "와"), 1인칭 일상 사건, 질문·반문이 많은 대화체 → 이 스타일.

## 4. 뉴스 브리핑

- 스킬: `reel-style-news-brief` — "상단 헤드라인 바와 하단 자막띠, 흐르는 티커로 소식을 빠르고 믿음직하게 전하는 뉴스 앵커 스타일."
- 잘 맞는 콘텐츠: AI/IT 뉴스, 업계 소식, 주간 트렌드 정리, "오늘 나온 ○○ 3가지".
- 레이아웃: 상단 0~0.18H 고정 제목 바(이번 꼭지 제목), 가운데 얼굴(또는 위 기사/스크린샷 카드 + 아래 얼굴), 하단 0.80~0.88H 자막띠, 맨 아래 티커.
- 자막: 하단 자막띠 안, Pretendard 700 60px, 흰 글자 on 남색 바(직사각, radius 0~4), 핵심어는 빨간 배경 블록. 등장: 바가 왼쪽에서 와이프 → 글자 페이드. 출처·날짜는 작은 회색 태그.
- 색: 남색 `#0B1F3A`, 빨강 `#E03131`, 흰색 `#FFFFFF`, 회색 `#ADB5BD`, 배경 `#F1F3F5`, 속보 노랑 `#FFD43B`.
- 모션 언어: 방송 하단 자막(lower third), "LIVE/속보" 라벨, 숫자 카운트, 순위 보드, 기사 카드 확대 + 형광펜 줄.
- 전환: 꼭지마다 바 스윕/푸시 전환 + 번호 카드("1/3"), 그 안에서는 하드컷.
- 속도: 중간~빠름. 컷 18~24회/분, 꼭지당 8~15초.
- 소리: 뉴스 인트로 짧은 징글, 꼭지 전환 "슉", 라벨 등장 틱. 음악은 긴장감 있는 펄스 베드 -26dB.
- 구현: `news-ticker`, `lower-third-bild`, `lt-stack-bars`, `lt-color-block`, `split-flap-board`(순위/숫자), `count-up`, `mk-callout-highlight`, `inline-highlight`, 전환 `transitions-push`.
- 자동 선택: 날짜/"오늘·이번 주", "발표·출시·공개·업데이트", 회사·제품명 다수, 항목 나열("첫 번째 소식") → 이 스타일.

## 5. 다큐 시네마틱

- 스킬: `reel-style-docu` — "레터박스와 필름 질감, 작은 세리프 자막, 느린 줌으로 개인 이야기를 영화처럼 진지하게 보여주는 스타일."
- 잘 맞는 콘텐츠: 개인 성장 스토리, 실패담·회고, 인터뷰, 창업 이야기, 감정선이 있는 내레이션.
- 레이아웃: face_full(위아래 검은 띠 2.35:1 느낌, 9:16 안에서 상하 8%), 장면 사이 B-roll·사진 켄번스, 인물 이름 하단 표시.
- 자막: 하단 0.80H, Noto Serif KR(또는 나눔명조) 500 48~54px, 박스 없음, 흰 글자 + 부드러운 그림자, 한 줄 최대 16자·2줄. 강조는 색 대신 **이탤릭/굵기 변화** 또는 따뜻한 금색. 등장: 블러 → 선명 0.3초 페이드.
- 색: 거의 검정 `#0E0E0E`, 따뜻한 흰색 `#F5F1E8`, 금색 `#C9A86A`, 그레이드 = 대비 낮추고 하이라이트 따뜻하게, 채도 -10%.
- 모션 언어: 느린 푸시인(1.0→1.06/5초), 필름 그레인, 빛샘, 연도/장소 타이틀 카드, 미니멀 하단 이름표.
- 전환: 디졸브, 블랙 딥, 빛샘 전환, 소리 먼저 들리는 J컷.
- 속도: 느림. 컷 8~14회/분, 세그먼트 2.5~5초, 침묵 0.4~0.8초는 일부러 남김, 속도 1.0배.
- 소리: 피아노/앰비언트 시네마틱, 효과음 최소(필름 프로젝터·바람 정도), 끝에 음악 상승.
- 구현: `grain-overlay`, `organic-light-leak-overlay`, `light-leak`(전환), `lt-kicker-name`, `lt-mask-reveal`, `blur-in`, `caption-weight-shift`, `canopy-part-title`/`glass-shard-title`(오프닝 타이틀, 9:16 로 줄여서), `grade-split-reveal`(전후).
- 자동 선택: 과거형 1인칭 서사("그때 저는", "~년 전"), 감정어(힘들었다·포기·눈물), 말 속도 느림(≤4음절/초), 영상 길이 60초 이상 → 이 스타일.

## 6. 화이트보드 낙서

- 스킬: `reel-style-doodle` — "종이 배경 위에 손글씨 화살표·동그라미·밑줄이 그려지며 개념을 단계별로 설명하는 공부 노트 스타일."
- 잘 맞는 콘텐츠: 개념 설명, "○○ 하는 3단계", 비교(A vs B), 공부·자기계발 요약, 프레임워크 소개.
- 레이아웃: split(위 종이 보드 0~0.5H / 아래 얼굴) 기본, 핵심 도식은 보드 전체화면, 얼굴은 종이 테두리 액자에 넣기도.
- 자막: 하단 얼굴 위 0.55H, Pretendard 700 62px 진회색 글자 + 흰 반투명 종이띠. 보드 위 키워드는 손글씨체(Nanum Pen Script·Gaegu 등 무료) 80~100px. 강조 = 형광펜 칠, 손그림 동그라미, 밑줄이 **그려지는** 애니메이션.
- 색: 종이 `#FAF7F0`, 연필 `#2B2B2B`, 형광 노랑 `#FFE066`, 빨간펜 `#E8590C`, 파란펜 `#1C7ED6`, 모눈 `#E9E4D8`.
- 모션 언어: 선 그리기(draw-on), 살짝 떨리는 손그림 선, 박스 → 화살표 → 다음 박스 순서도, 체크리스트 체크.
- 전환: 종이 넘김/찢기, 지우개 와이프, 같은 보드에서 카메라 팬.
- 속도: 중간. 컷 14~20회/분, 그리기 애니메이션은 말과 맞춰 0.4~0.8초.
- 소리: 연필·마커 사각 소리, 종이 넘김, 체크 "톡". 음악은 어쿠스틱 로파이.
- 구현: `marker-highlight`, `vox-annotate`, `hw-arrow`, `hw-box-label`, `hw-underline`, `hw-pipeline`(단계 도식), `hw-frame`(얼굴 액자), `hw-text-cloud`, `marker-checklist-card`, `cursor-annotate`, `paper-collage-reveal`, `torn-paper-rip`, `hw-boil`(손떨림).
- 자동 선택: "개념/원리/차이/방법/단계", 순서 표현(첫째·둘째, 1단계), 비교("vs", "반면"), 정의 문장("○○란") → 이 스타일.

## 7. 미니멀 타이포

- 스킬: `reel-style-minimal-type` — "넓은 여백에 큰 단어 한두 개만 타이포그래피로 움직여 메시지를 고급스럽게 남기는 미니멀 스타일."
- 잘 맞는 콘텐츠: 명언·인사이트 한 줄, 브랜드 메시지, 짧은 생각 정리, 차분한 화자.
- 레이아웃: face_full(밝고 깨끗한 배경) ↔ 단색 타이포 화면(얼굴 없이 큰 문장, 전체의 25~35%) 교대.
- 자막: 말자막은 작고 조용하게(Pretendard 500 44px, 박스 없음, 0.82H). 핵심 문장은 타이포 화면에서 Pretendard 800/300 대비 120~180px, 한 단어씩 쌓이거나 굵기가 변하며 강조. 색 하나만 포인트.
- 색 (라이트): 배경 `#FFFFFF`, 글자 `#111111`, 회색 `#9A9A9A`, 포인트 `#2F5BFF` 하나. (다크 변형: `#0D0D0D` / `#F2F2F2` / `#C8FF3D`)
- 모션 언어: 키네틱 타이포(글자 쌓기, 굵기 파도, 단어 교체 롤), 블러 인, 큰 여백, 그래픽 장식 없음.
- 전환: 컷 또는 짧은 페이드, 글자가 다음 장면으로 이어지는 매치 컷.
- 속도: 느림~중간. 컷 10~16회/분, 타이포 화면 1.5~2.5초 유지.
- 소리: 효과음 거의 없음(타이포 등장에 아주 작은 틱), 미니멀 신스 패드/피아노 -26dB.
- 구현: `kinetic-center-build`, `kinetic-type-swap`, `variable-axis-type`, `weight-wave`, `caption-weight-shift`, `caption-editorial-emphasis`, `blur-in`, `line-by-line-slide`, `morph-text`.
- 자동 선택: 전체 30초 이하 또는 문장 수 적음, 추상어(삶·관점·기준·본질) 많음, 숫자·툴 이름 거의 없음 → 이 스타일.

## 8. 화면 시연

- 스킬: `reel-style-screen-demo` — "화면 녹화·스크린샷을 크게 보여주고 아래 작은 얼굴과 커서 줌으로 따라하기 쉽게 만드는 튜토리얼 스타일."
- 잘 맞는 콘텐츠: 툴 사용법, AI 툴 리뷰, 설정 따라하기, 프롬프트 공유. (해외 2026 분석에서 가장 흔한 '책상 튜토리얼' 형)
- 레이아웃: (a) 위 화면 0~0.62H / 아래 얼굴, (b) 화면 전체 + 오른쪽 아래 원형 얼굴 버블(지름 0.32W), (c) 얼굴 컷아웃을 화면 앞에 세우는 '그린스크린'형(사람 분리 필요, `media-use` 컷아웃). 화면 소스가 없으면 웹페이지 캡처 카드로 대체.
- 자막: 화면과 얼굴 경계 위, Pretendard 700 62px, 흰 글자 + 검정 둥근 박스 85%, 핵심어는 툴 브랜드색이 아닌 **스타일 포인트색**. 클릭할 버튼 이름은 화면 위 말풍선 라벨로 따로.
- 색: 배경 `#111318`, 패널 `#1C1F26`, 글자 `#F5F7FA`, 포인트 `#5B8CFF`, 클릭 표시 `#FFB020`, 성공 `#34C759`.
- 모션 언어: 커서 따라가는 자동 줌, UI 일부 확대 + 주변 어둡게(스포트라이트), 클릭 파동, 타이핑 재현, 단계 번호 배지.
- 전환: 줌 스루(누른 버튼 속으로 들어가기), 화면↔얼굴 휙 팬.
- 속도: 중간~빠름. 컷 18~26회/분, 화면 단계당 2~4초, 대기 화면은 잘라내기/배속.
- 소리: 마우스 클릭, 키보드 타이핑, 줌 휙, 완료 "딩". 음악은 테크 로파이 -24dB.
- 구현: `cursor-zoom-follow`, `ui-focus-zoom`, `browser-device-stage`, `agent-cursor`, `cursor-glyph-trail`, `gesture-tap`, `typewriter`, `ai-chat-reveal`, `chat-thread`, `zoom-through-transition`, `filmed-screen`, `comparison-split`. 화면 녹화가 있으면 Remotion `remotion-multimedia` 로 합성해도 됨.
- 자동 선택: 입력에 화면 녹화/스크린샷 파일이 있음, 또는 대본에 "클릭·들어가서·설정·메뉴·프롬프트·사이트" 같은 조작어가 많음 → 이 스타일.

---

## 스타일 JSON 확장안 (`style.json`, 기존 `reference.json` 상위 호환)

원칙: 기존 키(`canvas, colors, font, layout, captions, cuts, rhythm, audio, speed`)는 **그대로 유지** → 스플릿 카드는 수정 없이 동작. 새 키는 전부 선택사항이고 엔진 기본값이 있다.

```jsonc
{
  "schema_version": 2,
  "id": "bold-talk",                       // 스킬 이름 = "reel-style-" + id
  "label_ko": "큰 자막 토크",
  "description_ko": "얼굴을 크게 두고 ...",
  "best_for": ["강한 주장", "숫자/돈", "동기부여"],

  "canvas": { "width": 1080, "height": 1920, "fps": 30 },
  "colors": { "background": "#000000", "ink": "#FFFFFF", "accent": "#FFE14D", "...": "역할 이름 자유" },

  "fonts": {                               // 기존 "font" 는 fonts.body 의 별칭으로 계속 허용
    "body":     { "family": "Pretendard", "file": "PretendardVariable.ttf", "weight": 700 },
    "display":  { "family": "Black Han Sans", "file": "BlackHanSans-Regular.ttf", "license": "OFL" },
    "hand":     { "family": "Nanum Pen Script", "file": "NanumPenScript-Regular.ttf", "license": "OFL" }
  },

  "layouts": {                             // 사용할 레이아웃과 비율 (합 1.0), 기존 rhythm.*_ratio 대체 가능
    "allowed": { "split": 0.0, "face_full": 0.9, "graphic_full": 0.1, "screen_top": 0, "screen_full_bubble": 0, "letterbox": 0, "type_card": 0 },
    "face_anchor_y": 0.30,
    "push_in": { "from": 1.0, "to": 1.035 },
    "punch_zoom": { "scale": 1.15, "every_s": 2.5 },
    "letterbox": null,                     // 예: { "ratio": 0.08 }
    "title_bar": null                      // 예: { "y": [0, 0.18], "source": "section_title" }
  },

  "captions": {
    "mode": "word_karaoke",                // chunk | word_karaoke | single_word | line
    "max_words": 3, "max_chars": 8, "max_dur": 1.2, "max_lines": 1,
    "font": "body", "font_size": 104, "font_weight": 900,
    "fill": "#FFFFFF",
    "stroke": { "color": "#000000", "width": 9, "outer": null },   // outer: 2중 외곽선
    "shadow": { "color": "rgba(0,0,0,.5)", "blur": 8, "y": 3 },
    "box": null,                           // 기존 박스: { "bg": "rgba(...)", "radius": 10, "pad_x": 26, "pad_y": 12 }
    "position": { "face_full": 0.62, "split": 0.48, "graphic_full": 0.48, "safe_x": 0.10 },
    "emphasis": {
      "method": "color+scale",             // color | box | scale | marker | font_swap | italic | emoji | 조합은 +
      "color": "#FFE14D", "scale": 1.12, "font": null,
      "source": "llm_keywords"             // llm_keywords | numbers | active_word | emotion_tags
    },
    "animation": { "in": "spring_pop", "in_dur": 0.12, "out": "none", "idle": null },  // idle: wiggle | wave | shake
    "deco_layer": null,                    // 예능 데코 자막: { "trigger": "emotion_tags", "fonts": "display", "palette": {"joy":"#FFD43B",...}, "tilt_deg": 6 }
    "hf_component": "caption-highlight"    // 실제 렌더에 쓰는 hyperframes 컴포넌트(없으면 엔진 기본 박스 자막)
  },

  "motion": {
    "language": "kinetic_type",            // ui_cards | kinetic_type | sticker_pop | lower_thirds | doodle | screen_zoom | minimal
    "intensity": 0.8,                      // 0~1, 모션 밀도 전역 배율
    "blocks": ["caption-kinetic-slam", "caption-emoji-pop", "number-pop-in"],  // 플래너가 고를 수 있는 레지스트리 항목 화이트리스트
    "per_min": { "graphic": 6, "sticker": 4, "hero": 1 },
    "overlays": { "grain": false, "vignette": 0.0, "light_leak": false, "ticker": null, "lower_third": null }
  },

  "transitions": {
    "default": "hard_cut",
    "accent": ["cinematic-zoom", "flash_white_1f"],
    "accent_every_n_cuts": 6,
    "duration": 0.25,
    "j_cut": false
  },

  "rhythm": {                              // 기존 키 + 목표치
    "segment_min": 0.8, "segment_target": 1.2, "segment_max": 1.6,
    "cuts_per_min_target": 30,
    "keep_pause_s": 0.0                    // 다큐는 0.4~0.8
  },
  "speed": 1.15,

  "grade": { "gamma": 1.0, "contrast": 1.08, "saturation": 1.05, "warmth": 0.0, "lut": null },

  "audio": {
    "target_lufs": -14.0, "true_peak": -1.5,
    "music": { "mood": "driving beat 110-130bpm", "gain_db": -24, "duck": true, "source_dir": "assets/music/bold-talk" },
    "sfx": { "pack": "punchy", "gain_db": -18, "events": { "emphasis": "pop", "zoom": "whoosh", "number": "ching", "cut": null } }
  },

  "auto_select": {                         // reel-maker 가 점수 계산에 사용
    "signals": { "wps_min": 5.5, "number_density": 0.6, "assertive_words": ["무조건", "절대", "입니다"] },
    "weight": 1.0
  },

  "quality": {                             // 채점기가 스타일별 기준으로 비교하도록
    "reference": "research/<참고 릴스 폴더>",   // 없으면 레퍼런스 비교 항목 생략
    "targets": { "cuts_per_min": [25, 35], "dead_air_pct": [0, 2], "caption_y": [0.58, 0.66] }
  }
}
```

엔진 변경 포인트(구현 시 참고, 이번 작업에서는 코드 안 씀):
- `compose.captions_html`: `captions.mode / stroke / box(null 가능) / emphasis.method / hf_component` 분기.
- `compose._layout_box`, `face_clips`: `layouts.allowed` 에 새 레이아웃(`screen_top`, `screen_full_bubble`, `letterbox`, `type_card`) 추가.
- 플래너(`steps/plan.py`): `motion.blocks` 화이트리스트 안에서만 그래픽 고르기.
- 채점기: 지금 레퍼런스가 크림 스플릿 릴스 하나라 다른 스타일은 '레퍼런스 유사도'에서 손해. `quality.targets` 로 스타일별 목표를 받게 하거나, 스타일별 레퍼런스가 없으면 해당 항목 제외.

## 스킬 패키징안

스타일 스킬 폴더 (`~/.claude/skills/reel-style-<id>/`):
```
SKILL.md          # 이름·한 줄 설명·언제 쓰나·실행 명령 (엔진 경로 + --style 이 폴더의 style.json)
style.json        # 위 스키마
blocks.txt        # 필요한 hyperframes 항목 (`npx hyperframes add` 목록)
assets/           # 이 스타일 전용 폰트(OFL 등 무료만)·효과음·음악 (라이선스 파일 같이)
preview.jpg       # 고를 때 보여줄 대표 프레임 1장
```
실행 예: `python pipeline/make_reel.py --input <mp4> --out out/x.mp4 --style ~/.claude/skills/reel-style-bold-talk/style.json` (`--style` 인자는 이미 있음, 기본값 `pipeline/styles/reference.json`).

### 선택 스킬 `reel-maker`

- 설명: "영상 하나를 넣으면 설치된 릴스 스타일 목록을 보여주고 고르게 하거나, 대본을 분석해 가장 어울리는 스타일을 골라 자동 편집까지 끝내는 시작점."
- 동작:
  1. `~/.claude/skills/reel-style-*/style.json` 을 훑어 목록 표시(번호 · 이름 · 한 줄 설명 · 미리보기). 새 스타일 스킬을 설치하면 자동으로 목록에 뜸.
  2. 사용자가 번호/이름을 말하면 그 스타일로 실행. "알아서" / "자동" 이면 3번.
  3. 자동 선택: 먼저 받아쓰기(엔진 `transcribe` 재사용) → 신호 계산(말 속도, 숫자·날짜·툴 이름·조작어·감정어·과거형 1인칭 빈도, 길이, 화면녹화 파일 유무) → 각 스타일의 `auto_select` 규칙으로 점수 → 1등으로 편집, 이유 한 줄 + 2등 대안 제시("뉴스 브리핑으로 했어요. 날짜·출시 이야기가 많아서요. 예능 자막으로도 바꿀 수 있어요.").
  4. 완료 후 채점기 실행, 결과 파일과 점수 보고. 같은 영상으로 "다른 스타일로도" 요청 시 받아쓰기·컷 결과를 재사용해 스타일만 바꿔 재렌더.
- 자동 선택 우선순위(동점 처리): 화면녹화 입력 있음 → 화면 시연 > 뉴스 신호 > 과정형(스플릿 카드) > 개념 설명(화이트보드) > 감정/일상(예능) > 서사(다큐) > 짧은 메시지(미니멀) > 기본값 스플릿 카드.

## 주의
- 폰트: Pretendard(OFL), Black Han Sans·Do Hyeon·Jua·Gaegu·Nanum Pen Script·Noto Serif KR(Google Fonts, OFL) 처럼 상업 사용 무료인 것만. 유료/출처 불명 예능 폰트·MOGRT 템플릿은 쓰지 않음.
- 효과음·음악: 무료 라이선스(CC0 등)만, 라이선스 파일을 스타일 assets 에 같이 보관.
- hyperframes 블록 중 일부(`canopy-part-title`, `glass-shard-title` 등)는 1920×1080 가로 기준 → 9:16 로 쓰려면 변수/크기 조정 필요.
