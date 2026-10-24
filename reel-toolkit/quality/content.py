"""Content & Craft rubric (내용·표현): anchored 1-5 scales judged by an independent
judge sub-agent from a judge pack, plus merging of judge score files.

Score -> 0..1 as score/5 (4/5 = 0.8 = PASS). Several judge files are averaged.
"""
from __future__ import annotations

import json
import os
import statistics

# id, Korean name, English name, weight (sum = content group weight), anchors 1..5
CONTENT_CRITERIA = [
    ("C1", "메시지 명료성", "Message clarity", 6, {
        1: "핵심이 무엇인지 알 수 없다. 주제가 여러 개로 흩어지거나 결론이 없다.",
        2: "주제는 알지만 핵심 주장/결론을 한 문장으로 말하기 어렵다. 군더더기가 많다.",
        3: "핵심은 전달되지만 곁가지(자랑·잡담·반복)가 섞여 한 번 보고 정확히 요약하긴 애매하다.",
        4: "한 번 보면 핵심을 한 문장으로 말할 수 있다. 곁가지는 1-2개 수준.",
        5: "한 번 보면 누구나 같은 한 문장으로 요약한다. 모든 문장이 그 핵심을 향한다."}),
    ("C2", "정보 구조", "Information structure", 5, {
        1: "순서가 없다. 훅·문제·해결·결말 중 2개 이상이 빠지고 흐름이 뒤엉킨다.",
        2: "구조의 일부만 있다(예: 해결만 나열). 단계 간 연결이 끊긴다.",
        3: "훅→문제→해결→결말이 대체로 있지만 한 단계가 약하거나 순서가 한 번 꼬인다.",
        4: "네 단계가 모두 있고 논리적으로 이어진다. 전환이 자연스럽다.",
        5: "네 단계가 명확하고 각 단계가 다음 단계를 당긴다(질문→답, 기대→보상). 낭비 없는 흐름."}),
    ("C3", "이해 보조 시각화", "Comprehension aids", 5, {
        1: "말로만 설명한다. 핵심 포인트가 화면에 시각화되지 않는다.",
        2: "핵심 포인트의 25% 미만만 화면에 보인다.",
        3: "핵심 포인트의 약 절반이 시각화된다. 중요한 숫자/단계가 빠지기도 한다.",
        4: "핵심 포인트의 대부분(75%+)이 말하는 순간 화면에 보인다.",
        5: "모든 핵심 포인트·숫자·단계가 말하는 바로 그 순간 시각화되어 소리 없이도 따라갈 수 있다."}),
    ("C4", "그래픽-내용 적합도", "Graphic-content fit", 5, {
        1: "그래픽이 내용과 무관한 장식(스톡, 의미 없는 아이콘)이다.",
        2: "그래픽이 주제와 막연히 관련될 뿐 말하는 내용을 설명하지 않는다.",
        3: "절반 정도의 그래픽이 실제 설명을 하고 나머지는 장식이다.",
        4: "대부분의 그래픽이 말하는 내용을 구체적으로 보여준다(실제 화면, 수치, 단계).",
        5: "모든 그래픽이 그 문장의 정보를 정확히 설명하고, 그래픽만 봐도 내용이 재구성된다."}),
    ("C5", "모션 디자인 완성도", "Motion design sophistication", 6, {
        1: "움직임이 없거나 선형(linear)·끊김·튐이 보인다. 요소가 그냥 나타났다 사라진다.",
        2: "기본 페이드/슬라이드만 있고 타이밍이 말과 어긋난다. 이징이 거칠다.",
        3: "이징은 있으나 모든 요소가 같은 방식으로 등장한다. 스태거·퇴장 연출이 거의 없다.",
        4: "부드러운 이징, 말 박자에 맞춘 등장, 요소별 스태거, 퇴장 연출이 대부분 있다.",
        5: "등장·강조·퇴장이 안무처럼 설계됨: 말 박자 정확, 스태거, 오버슈트/세틀, 주연·조연 모션 위계가 분명."}),
    ("C6", "타이포·레이아웃", "Typography & layout", 5, {
        1: "글자 크기·정렬이 제각각이고 대비가 낮아 읽기 어렵다. 한글 조판이 깨진다.",
        2: "위계가 약하고 여백·정렬이 불규칙하다. 일부 텍스트가 배경에 묻힌다.",
        3: "읽기는 편하지만 위계(제목/본문/강조)와 그리드가 부분적으로만 일관된다.",
        4: "명확한 위계, 일정한 여백·정렬, 충분한 대비, 자연스러운 한글 줄바꿈.",
        5: "디자인 시스템 수준: 일관된 그리드·간격·폰트 스케일, 강조색 절제, 한글 자간/행간까지 정돈."}),
    ("C7", "시각 일관성·마감", "Visual consistency & polish", 5, {
        1: "스타일이 장면마다 다르고 글리치·겹침·잘린 텍스트·빈 화면이 여러 번 보인다.",
        2: "팔레트/스타일이 자주 흔들리고 마감 결함이 2-3개 보인다.",
        3: "대체로 일관되나 마감 결함 1-2개(겹침, 잘림, 빈 프레임)가 있다.",
        4: "팔레트와 스타일이 일관되고 눈에 띄는 결함이 없다.",
        5: "브랜드처럼 통일된 팔레트·형태·질감. 프레임 단위로 봐도 결함이 없다."}),
    ("C8", "자막 완성도", "Caption craft", 4, {
        1: "자막이 없거나 오탈자·싱크 어긋남이 잦다.",
        2: "자막은 있으나 줄바꿈이 의미 단위를 무시하고 강조가 없다.",
        3: "의미 단위 줄바꿈은 대체로 맞지만 강조 선택이 단조롭거나 과하다.",
        4: "의미 단위로 끊기고 핵심어 강조가 적절하며 타이밍이 말과 맞는다.",
        5: "강조어 선택이 정확하고 리듬감 있게 끊기며 화면 다른 요소와 겹치지 않는다. 오류 0."}),
    ("C9", "페이싱·시청 유지", "Pacing & retention", 5, {
        1: "2초 이상 아무 변화 없는 구간이 반복된다. 에너지가 처진다.",
        2: "변화가 드물고 늘어지는 구간이 여러 번 있다.",
        3: "대체로 빠르지만 늘어지는 구간이 1-2번 있다. 에너지 곡선이 평평하다.",
        4: "모든 박자마다 시각 변화가 있고 늘어지는 구간이 없다.",
        5: "박자마다 변화가 있고 에너지 곡선이 설계됨(초반 고점, 중간 재자극, 결말 상승). 지루할 틈이 없다."}),
    ("C10", "훅(첫 2초)·엔딩/CTA", "Hook strength & ending/CTA", 5, {
        1: "첫 2초가 인사/빈 화면이고 엔딩이 그냥 끊긴다.",
        2: "훅이 약하거나 늦고(2초 이후), CTA가 없거나 불분명하다.",
        3: "훅이나 엔딩 중 하나만 강하다.",
        4: "첫 2초에 호기심/이득을 말과 화면으로 제시하고, 엔딩에 명확한 CTA/보상이 있다.",
        5: "첫 프레임부터 멈추게 만드는 시각+문장 훅, 엔딩이 훅을 회수하며 구체적 CTA로 끝난다."}),
    ("C11", "프로 편집자 출고 가능성", "Would a pro editor ship this", 4, {
        1: "초안 수준. 전면 재작업이 필요하다.",
        2: "방향은 맞지만 여러 곳을 다시 만들어야 한다.",
        3: "수정 몇 군데 후 출고 가능.",
        4: "사소한 손질만 하면 바로 출고.",
        5: "그대로 출고. 상위 크리에이터 채널에 올라가도 손색없다."}),
]

CONTENT_IDS = [c[0] for c in CONTENT_CRITERIA]
CONTENT_MIN_FOR_STOP = 4      # builder stopping rule: no content criterion below 4/5


def rubric_markdown() -> str:
    lines = []
    for cid, ko, en, w, anchors in CONTENT_CRITERIA:
        lines.append(f"### {cid} {ko} ({en}) — weight {w}")
        lines += [f"- **{lvl}**: {txt}" for lvl, txt in anchors.items()]
        lines.append("")
    return "\n".join(lines)


def load_scores(paths: list[str], key: dict | None = None) -> dict[str, dict]:
    """Average judge files. Returns {"output"|"reference": {cid: {...}}}.

    Judge file format: {"judge": str, "videos": {"A": {"C1": {"score": 4,
    "evidence": [...], "fixes": [...]}, ...}, "B": {...}}}
    `key` maps pack labels to roles ({"A": "reference", "B": "output"}); without
    a key a single label is treated as "output".
    """
    per_role: dict[str, dict[str, list]] = {}
    for path in paths:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        k = key or _find_key(path)
        for label, crit in (data.get("videos") or {}).items():
            role = (k or {}).get(label, "output")
            for cid in CONTENT_IDS:
                entry = crit.get(cid)
                if entry is None or entry.get("score") is None:
                    continue
                per_role.setdefault(role, {}).setdefault(cid, []).append(entry)
    out: dict[str, dict] = {}
    for role, crits in per_role.items():
        out[role] = {}
        for cid, entries in crits.items():
            scores = [float(e["score"]) for e in entries]
            out[role][cid] = {
                "score": statistics.fmean(scores), "judges": len(scores),
                "spread": max(scores) - min(scores),
                "evidence": [ev for e in entries for ev in (e.get("evidence") or [])][:8],
                "fixes": [fx for e in entries for fx in (e.get("fixes") or [])][:6]}
    return out


def _find_key(scores_path: str) -> dict | None:
    pack_dir = os.path.dirname(os.path.abspath(scores_path))
    key_path = pack_dir.rstrip("\\/") + "_key.json"
    if os.path.exists(key_path):
        with open(key_path, encoding="utf-8") as fh:
            return json.load(fh).get("labels")
    return None


def content_rows(scores: dict | None, group_weight: float) -> list[dict]:
    total_w = sum(c[3] for c in CONTENT_CRITERIA)
    rows = []
    for cid, ko, _en, w, _anchors in CONTENT_CRITERIA:
        entry = (scores or {}).get(cid)
        s = None if entry is None else max(0.0, min(1.0, entry["score"] / 5))
        val = "-" if entry is None else f"{entry['score']:.1f}/5" + (
            f" (±{entry['spread'] / 2:.1f}, {entry['judges']}명)" if entry["judges"] > 1 else "")
        rows.append({"id": cid, "group": "content", "name": ko,
                     "weight": w * group_weight / total_w, "target": ">= 4/5",
                     "value": val, "reference": None, "score": s,
                     "status": _status(s)})
    return rows


def _status(score):
    from rubric import status
    return status(score)
