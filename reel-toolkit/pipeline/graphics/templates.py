"""Card templates. Each takes (Scene, params) and fills markup + timeline.

params["at"] maps template beat names to transcript anchor words; Scene.at() resolves
them to seconds (relative to scene start) with a fallback default.
"""
from __future__ import annotations

from .icons import icon
from .scene import Scene, esc


def _a(p: dict, key: str):
    return (p.get("at") or {}).get(key)


def _beats(s: Scene, p: dict, keys: list[str], start: float = 0.35, end_frac: float = 0.8) -> list[float]:
    """Resolve a list of beat keys; un-anchored beats are spread evenly."""
    n = len(keys)
    span = max(0.3, s.dur * end_frac - start)
    return [s.at(_a(p, k), start + span * i / max(1, n - 1) if n > 1 else start) for i, k in enumerate(keys)]


# --------------------------------------------------------------------------- agents
def agents(s: Scene, p: dict) -> None:
    """N AI workers running in parallel: cards pop, progress bars run together."""
    items = p.get("agents", [])
    title = p.get("title", "AI 도우미")
    head = (f'<div id="{s.id("hl")}" style="font-size:54px;font-weight:800;letter-spacing:-1.5px;line-height:1.2;margin:0 0 24px">'
            f'{p["headline"]}</div>' if p.get("headline") else "")
    s.add(f'<div class="rk-card" id="{s.id("card")}">{s.card_header("bot", title, p.get("tag"), "tag")}{head}'
          f'<div style="display:flex;gap:20px">')
    for i, a in enumerate(items):
        s.add(f'<div id="{s.id(f"a{i}")}" style="flex:1;background:{s.c["card_soft"]};border-radius:26px;padding:24px 20px 22px;">'
              f'<div class="rk-ibox" style="width:66px;height:66px;margin-bottom:16px">{icon(a.get("icon", "bot"), 38, 2.2)}</div>'
              f'<div style="font-size:28px;font-weight:700;color:{s.c["ink_soft"]}">{esc(a.get("name", ""))}</div>'
              f'<div style="font-size:33px;font-weight:800;margin:4px 0 18px;white-space:nowrap">{esc(a.get("task", ""))}</div>'
              f'<div class="rk-bar"><div class="rk-fill" id="{s.id(f"f{i}")}"></div></div>'
              f'<div id="{s.id(f"st{i}")}" style="margin-top:14px;font-size:27px;font-weight:700;color:{s.c["accent"]}">작업 중…</div>'
              f'</div>')
    s.add('</div>')
    if p.get("stamp"):
        s.add(f'<div class="rk-stamp" id="{s.id("st")}" style="right:24px;top:-30px;font-size:40px;padding:8px 22px">{esc(p["stamp"])}</div>')
    s.add('</div>')
    s.enter_card()
    t_items = 0.0 if s.first else s.at(_a(p, "items"), 0.25)
    t_run = 0.15 if s.first else s.at(_a(p, "run"), max(t_items + 0.5, s.dur * 0.45))
    for i in range(len(items)):
        if not s.first:
            s.pop(f"a{i}", t_items + 0.09 * i, "pop" if i == 0 else "none", from_scale=.7)
        s.grow(f"f{i}", 0, 0.01, to=0.0)
        s.grow(f"f{i}", t_run, max(0.6, s.dur - t_run - 0.25) * (0.75 + 0.1 * i), to=0.35 + 0.22 * i,
               ease="power1.inOut")
    s.ev(t_run, "whoosh")
    if p.get("stamp"):
        s.stamp("st", s.at(_a(p, "stamp"), 1.0), rot=-8)
    if p.get("tag"):
        s.pop("tag", t_run, "none")


# --------------------------------------------------------------------------- command / dispatch
def command(s: Scene, p: dict) -> None:
    """Chat-style input: text types in, task chips attach, send button is clicked."""
    chips = p.get("chips", [])
    s.add(f'<div class="rk-card" id="{s.id("card")}">{s.card_header(p.get("icon", "send"), p.get("title", ""), p.get("tag"))}'
          f'<div style="border:3px solid {s.c["placeholder"]};border-radius:26px;padding:24px 26px;">'
          f'<div style="display:flex;gap:12px;flex-wrap:wrap;margin-bottom:18px">')
    for i, ch in enumerate(chips):
        s.add(f'<span class="rk-chip" id="{s.id(f"c{i}")}" style="opacity:0">{icon(ch.get("icon", "doc"), 30, 2.2, s.c["accent"])}{esc(ch["label"])}</span>')
    s.add(f'</div><div style="display:flex;align-items:center;gap:18px">'
          f'<div style="flex:1;font-size:36px;font-weight:600;min-height:48px;white-space:nowrap" id="{s.id("txt")}"></div>'
          f'<div class="rk-btn" id="{s.id("btn")}">{icon("send", 32, 2.4, "#fff")}보내기</div></div></div>'
          f'<div id="{s.id("sent")}" style="opacity:0;margin-top:20px;font-size:28px;font-weight:700;color:{s.c["good"]};display:flex;align-items:center;gap:10px">'
          f'{icon("check", 30, 3, s.c["good"])}{esc(p.get("done", "전송 완료"))}</div>'
          f'{s.cursor_markup()}</div>')
    s.enter_card()
    tc = _beats(s, p, [f"c{i}" for i in range(len(chips))], 0.3, 0.45)
    for i, t in enumerate(tc):
        s.pop(f"c{i}", t, ghost=.3)
    t_type = s.at(_a(p, "type"), 0.2)
    s.type_text("txt", t_type, p.get("text", ""), cps=18)
    t_send = s.at(_a(p, "send"), s.dur * 0.75)
    s.cursor("cur", [(max(0, t_send - 0.8), 520, 330), (t_send, 820, 214)], [t_send])
    s.press("btn", t_send)
    s.rise("sent", t_send + 0.15, "ding")


# --------------------------------------------------------------------------- question meter
def question(s: Scene, p: dict) -> None:
    """Big question: 'A = B?' with a meter that wobbles and a pulsing question mark."""
    s.add(f'<div class="rk-card" id="{s.id("card")}" style="text-align:center">'
          f'{s.card_header(p.get("icon", "question"), p.get("title", ""), p.get("tag"))}'
          f'<div style="display:flex;align-items:center;justify-content:center;gap:34px;margin:10px 0 26px">'
          f'<div id="{s.id("l")}" style="text-align:center"><div class="rk-ibox" style="width:120px;height:120px;border-radius:34px;margin:0 auto 10px;background:{s.c["card_soft"]}">{icon(p.get("left_icon", "bot"), 70, 2)}</div>'
          f'<div style="font-size:32px;font-weight:800">{esc(p.get("left", ""))}</div></div>'
          f'<div id="{s.id("eq")}" style="font-size:80px;font-weight:800;color:{s.c["ink_soft"]}">=</div>'
          f'<div id="{s.id("r")}" style="text-align:center"><div style="width:120px;height:120px;margin:0 auto 10px;display:flex;align-items:center;justify-content:center">{s.avatar(112)}</div>'
          f'<div style="font-size:32px;font-weight:800">{esc(p.get("right", ""))}</div></div>'
          f'<div id="{s.id("q")}" class="rk-acc" style="font-size:150px;font-weight:900;line-height:1">?</div></div>'
          f'<div class="rk-bar" style="height:26px;border-radius:13px"><div class="rk-fill" id="{s.id("m")}"></div></div>'
          f'<div style="display:flex;justify-content:space-between;font-size:27px;font-weight:700;margin-top:10px;color:{s.c["ink_soft"]}"><span>0</span><span>{esc(p.get("meter_label", "1명 몫"))}</span></div></div>')
    s.enter_card()
    tl_, tr_ = s.at(_a(p, "left"), 0.2), s.at(_a(p, "right"), 0.6)
    s.pop("l", tl_, ghost=.3)
    s.pop("eq", (tl_ + tr_) / 2, "none")
    s.pop("r", tr_, ghost=.3)
    tq = s.at(_a(p, "q"), s.dur * 0.6)
    s.stamp("q", tq, rot=8)
    s.grow("m", 0, 0.01, to=0)
    s.grow("m", tr_, 0.9, to=0.5, ease="power3.out")   # fills once, then holds on the question


# --------------------------------------------------------------------------- document extract
def doc_extract(s: Scene, p: dict) -> None:
    """Document card with placeholder lines; extracted fields slide out one by one."""
    fields = p.get("fields", [])
    s.add(f'<div class="rk-card" id="{s.id("card")}">{s.card_header("doc", p.get("title", ""), p.get("tag"))}'
          f'<div style="display:flex;gap:24px">'
          f'<div id="{s.id("doc")}" style="width:300px;flex:none;background:{s.c["card_soft"]};border-radius:24px;padding:20px 18px 22px">'
          f'<div style="font-size:28px;font-weight:800;margin-bottom:6px">{esc(p.get("doc", "문서"))}</div>')
    lines = p.get("lines") or ["", "", "", "", "", ""]
    for i, ln in enumerate(lines):
        if ln:
            s.add(f'<div id="{s.id(f"ln{i}")}" style="font-size:27px;font-weight:600;line-height:1.35;margin-top:10px;'
                  f'padding:2px 8px;border-radius:8px;color:{s.c["ink"]};white-space:nowrap;overflow:hidden">{esc(ln)}</div>')
        else:
            s.add(f'<div class="rk-ph" id="{s.id(f"ln{i}")}" style="width:{[92, 70, 84, 60, 88, 52][i % 6]}%"></div>')
    s.add('</div><div style="flex:1;display:flex;flex-direction:column;gap:14px;justify-content:center">')
    for i, f in enumerate(fields):
        val = (f'<span style="font-size:32px;font-weight:800;color:{s.c["accent"]}">{esc(f["value"])}</span>'
               if f.get("value") else "")
        s.add(f'<div class="rk-row" id="{s.id(f"f{i}")}" style="margin:0;padding:14px 18px;opacity:0;background:{s.c["accent_soft"]}">'
              f'<div class="rk-ibox" style="width:50px;height:50px">{icon(f.get("icon", "user"), 30, 2.2)}</div>'
              f'<span class="rk-lbl" style="font-size:28px;font-weight:700;color:{s.c["ink_soft"]}">{esc(f["label"])}</span>{val}</div>')
    s.add('</div></div>')
    if p.get("result"):
        s.add(f'<div id="{s.id("res")}" style="opacity:0;margin-top:22px;display:flex;justify-content:center">'
              f'<span class="rk-btn" style="font-size:30px;padding:16px 30px">{icon("list", 30, 2.4, "#fff")}{esc(p["result"])}</span></div>')
    s.add('</div>')
    s.enter_card()
    tf = _beats(s, p, [f"f{i}" for i in range(len(fields))], 0.6, 0.7)
    hls = p.get("highlight") or [min(i * 2 + 1, len(lines) - 1) for i in range(len(fields))]
    for i, tt in enumerate(tf):
        s.tint(f"ln{hls[i]}", tt - 0.05, s.c["accent_soft"] if lines[hls[i]] else s.c["accent"])
        s.rise(f"f{i}", tt, "pop", ghost=.3)
    if p.get("result"):
        s.pop("res", s.at(_a(p, "result"), s.dur * 0.8), ghost=.4)


# --------------------------------------------------------------------------- mail
def mail(s: Scene, p: dict) -> None:
    """Inbox row arrives; optional question bubble types; optional reply draft writes itself."""
    s.add(f'<div class="rk-card" id="{s.id("card")}">{s.card_header("mail", p.get("title", ""), p.get("tag"))}'
          f'<div class="rk-row" id="{s.id("in")}" style="margin-top:0;opacity:0">'
          f'<div class="rk-ibox" style="background:{s.c["accent_soft"]}">{icon("user", 32, 2.2)}</div>'
          f'<div style="flex:1"><div style="font-size:30px;font-weight:800">{esc(p.get("from", "고객"))}</div>'
          f'<div style="font-size:27px;color:{s.c["ink_soft"]};font-weight:600">{esc(p.get("subject", ""))}</div></div>'
          f'<span class="rk-pill" style="background:{s.c["accent"]};color:#fff">새 메일</span></div>')
    if p.get("question"):
        s.add(f'<div id="{s.id("qb")}" style="opacity:0;margin-top:20px;background:{s.c["card_soft"]};border-radius:26px 26px 26px 8px;padding:24px 28px;font-size:36px;font-weight:700;min-height:50px">'
              f'<span id="{s.id("qt")}"></span></div>')
    if p.get("reply"):
        s.add(f'<div id="{s.id("rp")}" style="opacity:0;margin-top:20px;margin-left:110px;border:3px dashed {s.c["accent"]};border-radius:26px 26px 8px 26px;padding:20px 26px">'
              f'<div style="display:flex;align-items:center;gap:10px;font-size:28px;font-weight:800;color:{s.c["accent"]}">{icon("spark", 28, 2.4)}{esc(p["reply"])}</div>'
              + "".join(f'<div id="{s.id(f"r{k}")}" style="font-size:28px;font-weight:600;margin-top:8px;white-space:nowrap;min-height:36px"></div>'
                        for k, x in enumerate((p.get("reply_lines") or ["", "", ""])[:3]))
              + '</div>')
    s.add('</div>')
    s.enter_card()
    s.rise("in", s.at(_a(p, "in"), 0.25), "pop", ghost=.5)
    if p.get("question"):
        tq = s.at(_a(p, "question"), 0.3)
        s.rise("qb", tq, None)
        s.type_text("qt", tq + 0.1, p["question"], cps=20)
    if p.get("reply"):
        tr = s.at(_a(p, "reply"), s.dur * 0.6)
        s.rise("rp", tr, "pop", ghost=.4)
        for i, x in enumerate((p.get("reply_lines") or [])[:3]):
            s.type_text(f"r{i}", tr + 0.15 + 0.45 * i, x, cps=26)


# --------------------------------------------------------------------------- rule
def rule(s: Scene, p: dict) -> None:
    """IF -> THEN rule card with a stamp."""
    s.add(f'<div class="rk-card" id="{s.id("card")}">{s.card_header("flag", p.get("title", "규칙"), p.get("tag"))}'
          f'<div style="display:flex;align-items:center;gap:20px">'
          f'<div class="rk-row" id="{s.id("if")}" style="flex:1;margin:0;opacity:0"><span class="rk-pill">IF</span><span class="rk-lbl">{esc(p.get("if", ""))}</span></div>'
          f'<div id="{s.id("ar")}" style="color:{s.c["ink_soft"]};opacity:0">{icon("arrow", 50, 3)}</div>'
          f'<div class="rk-row" id="{s.id("then")}" style="flex:1;margin:0;opacity:0;background:{s.c["accent_soft"]}"><span class="rk-pill" style="background:{s.c["accent"]};color:#fff">THEN</span><span class="rk-lbl">{esc(p.get("then", ""))}</span></div>'
          f'</div><div style="height:80px"></div>'
          f'<div class="rk-stamp" id="{s.id("st")}" style="left:200px;top:215px">{icon("x", 50, 4)} {esc(p.get("stamp", ""))}</div></div>')
    s.enter_card()
    s.rise("if", s.at(_a(p, "if"), 0.25), "pop", ghost=.3)
    t2 = s.at(_a(p, "then"), s.dur * 0.45)
    s.pop("ar", t2 - 0.1, "none")
    s.rise("then", t2, "pop", ghost=.3)
    if p.get("stamp"):
        s.stamp("st", s.at(_a(p, "stamp"), s.dur * 0.7))


# --------------------------------------------------------------------------- bars
def bars(s: Scene, p: dict) -> None:
    """Two-bar comparison with labels; optional delta badge and one-line report."""
    items = p.get("bars", [])
    mx = max([b["value"] for b in items] or [1])
    s.add(f'<div class="rk-card" id="{s.id("card")}">{s.card_header("chart", p.get("title", ""), p.get("tag"))}'
          f'<div style="display:flex;align-items:flex-end;justify-content:center;gap:90px;height:340px;border-bottom:3px solid {s.c["placeholder"]};position:relative">')
    for i, b in enumerate(items):
        h = int(300 * b["value"] / mx)
        col = s.c["accent"] if i == len(items) - 1 else "#CFC6C0"
        s.add(f'<div style="height:{h + 56}px;overflow:hidden;display:flex;align-items:flex-end">'
              f'<div id="{s.id(f"b{i}")}" style="display:flex;flex-direction:column;align-items:center;gap:10px">'
              f'<div id="{s.id(f"v{i}")}" style="font-size:36px;font-weight:800;color:{s.c["accent"] if i == len(items) - 1 else s.c["ink"]}">{esc(b.get("display", b["value"]))}</div>'
              f'<div style="width:170px;height:{h}px;border-radius:20px 20px 6px 6px;background:{col}"></div></div></div>')
    if p.get("badge"):
        s.add(f'<div class="rk-stamp" id="{s.id("badge")}" style="right:40px;top:0;font-size:58px;border:none;background:{s.c["accent"]};color:#fff">{icon("up", 46, 4, "#fff")} {esc(p["badge"])}</div>')
    s.add('</div><div style="display:flex;justify-content:center;gap:90px;margin-top:12px">')
    for b in items:
        s.add(f'<div style="width:170px;text-align:center;font-size:30px;font-weight:700;color:{s.c["ink_soft"]}">{esc(b["label"])}</div>')
    s.add('</div>')
    if p.get("report"):
        s.add(f'<div class="rk-row" id="{s.id("rep")}" style="opacity:0;background:{s.c["accent_soft"]}">'
              f'<div class="rk-ibox">{icon("doc", 32, 2.2)}</div><span class="rk-lbl">{esc(p["report"])}</span></div>')
    s.add('</div>')
    s.enter_card()
    tb = _beats(s, p, [f"b{i}" for i in range(len(items))], 0.35, 0.5)
    for i, tt in enumerate(tb):
        h = int(300 * items[i]["value"] / mx)
        start_y = int(h * 0.72) if i == 0 else h + 56   # only the first bar is pre-filled (never an empty chart)
        s._js(f'tl.fromTo("{s.sel(f"b{i}")}",{{y:{start_y}}},{{y:0,duration:.65,ease:"power2.out"}},{tt:.3f});')
        s.ev(tt, "rise")
    if p.get("badge"):
        s.stamp("badge", s.at(_a(p, "badge"), s.dur * 0.7), rot=-4)
    if p.get("report"):
        s.rise("rep", s.at(_a(p, "report"), s.dur * 0.75), "pop", ghost=.4)


# --------------------------------------------------------------------------- checklist
def checklist(s: Scene, p: dict) -> None:
    """Rows that appear and get checked on their anchor words."""
    items = p.get("items", [])
    ok = p.get("ok_color", False)
    s.add(f'<div class="rk-card" id="{s.id("card")}">{s.card_header(p.get("icon", "list"), p.get("title", ""), p.get("tag"))}')
    for i, it in enumerate(items):
        s.add(f'<div class="rk-row" id="{s.id(f"r{i}")}" style="opacity:0">'
              f'<div class="rk-ibox">{icon(it.get("icon", "check"), 32, 2.2)}</div>'
              f'<span class="rk-lbl">{esc(it["label"])}</span>'
              f'{"<span class=rk-soft style=font-size:28px;font-weight:700>" + esc(it["note"]) + "</span>" if it.get("note") else ""}'
              f'<div class="rk-chk{" ok" if ok else ""}" id="{s.id(f"k{i}")}">{icon("check", 30, 3.2, "#fff")}</div></div>')
    s.add('</div>')
    s.enter_card()
    show_all = p.get("show_all_first", False)
    tk = _beats(s, p, [f"r{i}" for i in range(len(items))], 0.3, 0.8)
    for i, t in enumerate(tk):
        if show_all:
            s.rise(f"r{i}", 0.12 + 0.08 * i, None)
            s.check(f"k{i}", t)
            s.tint(f"r{i}", t, s.c["accent_soft"])
        else:
            s.rise(f"r{i}", t, "pop", ghost=.3)
            s.check(f"k{i}", t + 0.35)
            s.pulse(f"r{i}", t + 0.35, 1.04)


# --------------------------------------------------------------------------- waiting
def waiting(s: Scene, p: dict) -> None:
    """Sent tasks + a ticking timer while 'hands off'."""
    rows = p.get("rows", [])
    s.add(f'<div class="rk-card" id="{s.id("card")}">{s.card_header("clock", p.get("title", ""), p.get("tag"))}'
          f'<div style="display:flex;gap:26px;align-items:stretch">'
          f'<div style="flex:1">')
    for i, r in enumerate(rows):
        s.add(f'<div class="rk-row" id="{s.id(f"r{i}")}" style="opacity:0;{"margin-top:0" if i == 0 else ""}">'
              f'<div class="rk-ibox">{icon(r.get("icon", "doc"), 30, 2.2)}</div><div style="flex:1"><div style="font-size:30px;font-weight:700">{esc(r["label"])}</div>'
              f'<div class="rk-bar" style="height:12px;margin-top:8px"><div class="rk-fill" id="{s.id(f"p{i}")}"></div></div></div>'
              f'<div class="rk-chk ok" id="{s.id(f"k{i}")}" style="width:40px;height:40px">{icon("check", 26, 3.4, "#fff")}</div></div>')
    s.add(f'</div><div id="{s.id("tm")}" style="width:300px;flex:none;background:{s.c["ink"]};color:#fff;border-radius:28px;display:flex;flex-direction:column;align-items:center;justify-content:center;opacity:0">'
          f'<div style="color:{s.c["accent"]}">{icon("hand", 74, 2)}</div>'
          f'<div id="{s.id("tt")}" style="font-size:66px;font-weight:800;font-variant-numeric:tabular-nums;margin-top:8px">00:00</div>'
          f'<div style="font-size:27px;font-weight:700;opacity:.7">{esc(p.get("timer_label", "손 떼고 대기"))}</div></div></div></div>')
    s.enter_card()
    tr = _beats(s, p, [f"r{i}" for i in range(len(rows))], 0.25, 0.45)
    for i, t in enumerate(tr):
        s.rise(f"r{i}", t, None, ghost=.3)
        s.check(f"k{i}", t + 0.2)
    tw = s.at(_a(p, "wait"), s.dur * 0.6)
    s.pop("tm", tw, "whoosh", ghost=.4)
    for i in range(len(rows)):
        s.grow(f"p{i}", 0, 0.01, to=0)
        s.grow(f"p{i}", tr[i] + 0.3, max(0.8, s.dur - tr[i] - 0.4), to=[0.92, 0.7, 0.55][i % 3], ease="power1.inOut")
    s._js(f'(function(){{const o={{v:0}};const el=document.querySelector("{s.sel("tt")}");'
          f'tl.to(o,{{v:{p.get("minutes", 3) * 60},duration:{max(.5, s.dur - tw - .2):.3f},ease:"none",onUpdate:function(){{'
          f'const m=Math.floor(o.v/60),x=Math.floor(o.v%60);el.textContent=String(m).padStart(2,"0")+":"+String(x).padStart(2,"0");}}}},{tw + .2:.3f});}})();')
    s.ev(tw + 0.2, "count")


# --------------------------------------------------------------------------- big stat
def big_stat(s: Scene, p: dict) -> None:
    """Huge counter with label and progress dots."""
    n = int(p.get("dots", 0))
    s.add(f'<div class="rk-card" id="{s.id("card")}" style="text-align:center;padding:44px 40px 46px">'
          f'{s.card_header(p.get("icon", "spark"), p.get("title", ""), p.get("tag"))}'
          f'<div style="display:flex;align-items:baseline;justify-content:center;gap:16px">'
          f'<span class="rk-big" id="{s.id("num")}">{esc(p.get("prefix", ""))}{esc(p.get("from", 0))}{esc(p.get("suffix", ""))}</span>'
          f'<span style="font-size:52px;font-weight:800" class="rk-soft">{esc(p.get("unit", ""))}</span></div>'
          f'<div style="font-size:34px;font-weight:700;margin-top:10px">{esc(p.get("label", ""))}</div>')
    if n:
        s.add('<div style="display:flex;justify-content:center;gap:16px;margin-top:26px">')
        for i in range(n):
            s.add(f'<div id="{s.id(f"d{i}")}" style="width:96px;height:22px;border-radius:11px;background:{s.c["placeholder"]}"></div>')
        s.add('</div>')
    if p.get("stamp"):
        s.add(f'<div class="rk-stamp" id="{s.id("st")}" style="right:22px;top:18px;font-size:40px;padding:8px 20px">{esc(p["stamp"])}</div>')
    s.add('</div>')
    s.enter_card()
    tc = s.at(_a(p, "count"), 0.2)
    dur = 0.45
    s.count("num", tc, float(p.get("from", 0)), float(p.get("to", 0)), dur, int(p.get("decimals", 0)),
            str(p.get("prefix", "")), str(p.get("suffix", "")))
    for i in range(n):
        s.tint(f"d{i}", tc + dur * (i + 1) / n, s.c["accent"], dur=.15)
    if p.get("stamp"):
        s.stamp("st", s.at(_a(p, "stamp"), tc + dur + 0.1), rot=-10)


# --------------------------------------------------------------------------- results
def results(s: Scene, p: dict) -> None:
    """Output tiles: each result appears with its own mini visual."""
    items = p.get("items", [])
    s.add(f'<div class="rk-card" id="{s.id("card")}">{s.card_header("spark", p.get("title", ""), p.get("tag"))}'
          f'<div style="display:flex;gap:18px">')
    for i, it in enumerate(items):
        texts = (it.get("lines") or ["", "", ""])[:3]
        flagged = {int(k.split("_")[1]) for k in p.get("flag", []) if k.split("_")[0] == str(i)}
        lines = "".join(f'<div style="display:flex;align-items:center;gap:10px;margin-top:12px">'
                        f'<div id="{s.id(f"x{i}_{j}")}" style="width:30px;height:30px;border-radius:9px;border:3px solid {s.c["accent"]};flex:none"></div>'
                        + (f'<div id="{s.id(f"l{i}_{j}")}" style="font-size:24px;font-weight:700;white-space:nowrap'
                           + (f';color:{s.c["accent"]};font-weight:900' if j in flagged else "") + f'">{esc(tx)}</div></div>' if tx else
                           f'<div class="rk-ph" style="margin:0;flex:1;width:{80 - 14 * j}%"></div></div>')
                        for j, tx in enumerate(texts))
        s.add(f'<div id="{s.id(f"t{i}")}" style="flex:1;opacity:0;background:{s.c["card_soft"]};border-radius:26px;padding:22px 20px 26px">'
              f'<div class="rk-ibox" style="margin-bottom:12px">{icon(it.get("icon", "doc"), 32, 2.2)}</div>'
              f'<div style="font-size:30px;font-weight:800;white-space:nowrap">{esc(it["label"])}</div>{lines}</div>')
    s.add('</div></div>')
    s.enter_card()
    tt = _beats(s, p, [f"t{i}" for i in range(len(items))], 0.3, 0.75)
    for i, ti in enumerate(tt):
        s.rise(f"t{i}", ti, "pop", ghost=.3)
        nxt = tt[i + 1] if i + 1 < len(tt) else s.dur - 0.2
        step = max(0.18, (nxt - ti - 0.3) / 3)
        for j in range(3):
            tj = ti + 0.3 + step * j
            s.tint(f"x{i}_{j}", tj, s.c["accent"], dur=.12)
            s._js(f'tl.fromTo("{s.sel(f"l{i}_{j}")}",{{opacity:.35,x:-10}},{{opacity:1,x:0,duration:.25,ease:"expo.out"}},{tj:.3f});')
            s.ev(tj, "tick")


# --------------------------------------------------------------------------- kpi
def kpi(s: Scene, p: dict) -> None:
    """KPI tiles with up arrows and a big delta counter."""
    tiles = p.get("tiles", [])
    s.add(f'<div class="rk-card" id="{s.id("card")}">{s.card_header("chart", p.get("title", ""), p.get("tag"))}'
          f'<div style="display:flex;gap:18px;margin-bottom:22px">')
    for i, t in enumerate(tiles):
        s.add(f'<div class="rk-row" id="{s.id(f"k{i}")}" style="flex:1;margin:0;opacity:0">'
              f'<div class="rk-ibox">{icon(t.get("icon", "cart"), 32, 2.2)}</div>'
              f'<div style="flex:1"><div style="font-size:26px;font-weight:700;color:{s.c["ink_soft"]}">{esc(t["label"])}</div>'
              f'<div style="font-size:29px;font-weight:800;white-space:nowrap;letter-spacing:-.5px">{esc(t.get("value", ""))}</div></div>'
              f'<span style="color:{s.c["good"]}">{icon("up", 40, 3.4)}</span></div>')
    s.add(f'</div><div style="display:flex;align-items:center;justify-content:center;gap:22px;background:{s.c["accent_soft"]};border-radius:28px;padding:18px">'
          f'<span style="font-size:36px;font-weight:800">{esc(p.get("label", ""))}</span>'
          f'<span class="rk-big rk-acc" id="{s.id("num")}" style="font-size:130px;opacity:.35">+?%</span></div></div>')
    s.enter_card()
    tk = _beats(s, p, [f"k{i}" for i in range(len(tiles))], 0.3, 0.45)
    for i, t in enumerate(tk):
        s.rise(f"k{i}", t, "pop", ghost=.3)
    t_say = s.at(_a(p, "count"), s.dur * 0.55)
    tc = max(0.3, t_say - 0.55)          # the count lands exactly when the number is spoken
    s._js(f'tl.to("{s.sel("num")}",{{opacity:1,duration:.15}},{tc:.3f});')
    s.count("num", tc, 0, float(p.get("to", 20)), t_say + 0.1 - tc, 0, "+", "%")
    s.pulse("num", t_say + 0.12, 1.14)


# --------------------------------------------------------------------------- stop / warning
def stop_send(s: Scene, p: dict) -> None:
    """A send button about to be clicked, then blocked by a warning stamp."""
    s.add(f'<div class="rk-card" id="{s.id("card")}">{s.card_header("send", p.get("title", ""), p.get("tag"))}'
          f'<div style="display:flex;gap:14px;margin-bottom:24px">')
    for i, ch in enumerate(p.get("chips", [])):
        s.add(f'<span class="rk-chip" id="{s.id(f"c{i}")}">{icon(ch.get("icon", "doc"), 28, 2.2, s.c["accent"])}{esc(ch["label"])}</span>')
    s.add(f'</div><div style="display:flex;justify-content:flex-end">'
          f'<div class="rk-btn" id="{s.id("btn")}" style="font-size:40px;padding:24px 46px">{icon("send", 38, 2.4, "#fff")}{esc(p.get("button", "그대로 보내기"))}</div></div>'
          f'<div class="rk-stamp" id="{s.id("st")}" style="left:120px;top:150px;font-size:64px">{icon("alert", 58, 3.2)} {esc(p.get("stamp", "잠깐!"))}</div>'
          f'{s.cursor_markup()}</div>')
    s.enter_card()
    tb = s.at(_a(p, "block"), s.dur * 0.6)
    s.cursor("cur", [(0.25, 300, 300), (max(0.7, tb - 0.15), 700, 238)], [])
    s.tint("btn", tb, "#BDB4AE", dur=.15)
    s.stamp("st", tb)
    s.shake("card", tb + 0.3, 16)


# --------------------------------------------------------------------------- roles
def roles(s: Scene, p: dict) -> None:
    """Two columns (AI vs me) whose duties light up on their anchor words."""
    cols = p.get("columns", [])
    s.add(f'<div class="rk-card" id="{s.id("card")}">{s.card_header("user", p.get("title", ""), p.get("tag"))}'
          f'<div style="display:flex;gap:20px">')
    for ci, col in enumerate(cols):
        acc = ci == len(cols) - 1
        s.add(f'<div id="{s.id(f"col{ci}")}" style="flex:1;opacity:0;border-radius:28px;padding:24px;background:{s.c["accent_soft"] if acc else s.c["card_soft"]}">'
              f'<div style="display:flex;align-items:center;gap:12px;font-size:34px;font-weight:800;margin-bottom:8px">'
              f'{s.avatar(54) if acc else "<div class=rk-ibox>" + icon(col.get("icon", "bot"), 32, 2.2) + "</div>"}{esc(col["name"])}</div>')
        for ri, it in enumerate(col.get("items", [])):
            s.add(f'<div id="{s.id(f"i{ci}_{ri}")}" style="opacity:0;display:flex;align-items:center;gap:10px;margin-top:14px;background:#fff;border-radius:18px;padding:16px 18px;font-size:30px;font-weight:700;white-space:nowrap">'
                  f'<span style="color:{s.c["accent"] if acc else s.c["good"]}">{icon("check", 30, 3.2)}</span>{esc(it["label"])}</div>')
        s.add('</div>')
    s.add('</div>')
    if p.get("meter"):
        m = p["meter"]
        s.add(f'<div id="{s.id("mt")}" style="margin-top:22px;opacity:0"><div style="display:flex;justify-content:space-between;font-size:28px;font-weight:800;margin-bottom:10px">'
              f'<span>{esc(m.get("label", ""))}</span><span class="rk-acc" id="{s.id("mv")}">{esc(m.get("value", ""))}</span></div>'
              f'<div class="rk-bar" style="height:26px;border-radius:13px"><div class="rk-fill" id="{s.id("mf")}"></div></div></div>')
    s.add('</div>')
    s.enter_card()
    if p.get("meter"):
        tm = s.at(p["meter"].get("at"), s.dur * 0.75)
        s.rise("mt", tm, "pop", ghost=.4)
        s.grow("mf", 0, 0.01, to=0)
        s.grow("mf", tm + 0.1, 0.6, to=float(p["meter"].get("fill", 0.5)), ease="expo.out")
    for ci, col in enumerate(cols):
        tcol = s.at(col.get("at"), 0.2 + 0.25 * ci)
        s.rise(f"col{ci}", tcol, "pop", ghost=.3)
        for ri, it in enumerate(col.get("items", [])):
            s.rise(f"i{ci}_{ri}", s.at(it.get("at"), tcol + 0.3 + 0.3 * ri), "tick", ghost=.3)


# --------------------------------------------------------------------------- pick one
def pick(s: Scene, p: dict) -> None:
    """Options grid; cursor picks one; the picked one is highlighted and tagged."""
    opts = p.get("options", [])
    k = int(p.get("pick", 0))
    s.add(f'<div class="rk-card" id="{s.id("card")}">{s.card_header(p.get("icon", "box"), p.get("title", ""), p.get("tag"))}'
          f'<div style="display:flex;gap:18px">')
    for i, o in enumerate(opts):
        s.add(f'<div id="{s.id(f"o{i}")}" style="flex:1;opacity:0;background:{s.c["card_soft"]};border:4px solid transparent;border-radius:28px;padding:26px 18px;text-align:center">'
              f'<div class="rk-ibox" style="margin:0 auto 14px;width:76px;height:76px">{icon(o.get("icon", "doc"), 44, 2.1)}</div>'
              f'<div style="font-size:30px;font-weight:800;white-space:nowrap">{esc(o["label"])}</div></div>')
    s.add('</div>')
    if p.get("result"):
        s.add(f'<div id="{s.id("res")}" style="opacity:0;margin-top:24px;display:flex;align-items:center;justify-content:center;gap:16px;'
              f'background:{s.c["ink"]};color:#fff;border-radius:26px;padding:22px;font-size:36px;font-weight:800">'
              f'<span style="color:{s.c["accent"]}">{icon(p.get("result_icon", "won"), 42, 2.6)}</span>{esc(p["result"])}</div>')
    if p.get("cta"):
        s.add(f'<div id="{s.id("cta")}" style="opacity:0;margin-top:18px;display:flex;align-items:center;gap:16px;'
              f'border:3px solid {s.c["placeholder"]};border-radius:26px;padding:16px 20px">{s.avatar(64, False)}'
              f'<div style="flex:1"><div style="font-size:30px;font-weight:800">{esc(p["cta"])}</div>'
              f'<div class="rk-soft" style="font-size:27px;font-weight:600">{esc(p.get("cta_sub", ""))}</div></div>'
              f'<span class="rk-btn" id="{s.id("ctab")}" style="font-size:28px;padding:14px 26px">팔로우</span></div>')
    s.add(f'{s.cursor_markup()}</div>')
    s.enter_card()
    to = _beats(s, p, [f"o{i}" for i in range(len(opts))], 0.2, 0.35)
    for i, t in enumerate(to):
        s.rise(f"o{i}", t, "pop" if i == 0 else None, ghost=.3)
    tp = s.at(_a(p, "pick"), s.dur * 0.55)
    x = 70 + 300 * k + 150
    s.cursor("cur", [(max(0.3, tp - 0.9), 520, 470), (tp, x, 250)], [tp])
    s._js(f'tl.to("{s.sel(f"o{k}")}",{{borderColor:"{s.c["accent"]}",backgroundColor:"{s.c["accent_soft"]}",duration:.2}},{tp:.3f});')
    s.pulse(f"o{k}", tp, 1.06)
    for i in range(len(opts)):
        if i != k:
            s.fade_to(f"o{i}", tp + 0.1, 0.4)
    if p.get("result"):
        s.rise("res", s.at(_a(p, "result"), tp + 0.6), "ding", ghost=.4)
    if p.get("cta"):
        tcta = s.at(_a(p, "cta"), max(tp + 0.9, s.dur - 1.1))
        s.rise("cta", tcta, "pop", ghost=.4)
        s.press("ctab", tcta + 0.45)
        s.ev(tcta + 0.45, "click")


# --------------------------------------------------------------------------- keyword (auto fallback)
def keyword(s: Scene, p: dict) -> None:
    """Generic: icon + keyword + placeholder lines (used by the auto planner)."""
    s.add(f'<div class="rk-card" id="{s.id("card")}" style="text-align:center;padding:50px 40px">'
          f'<div class="rk-ibox" id="{s.id("ic")}" style="margin:0 auto 22px;width:120px;height:120px;border-radius:36px;background:{s.c["accent"]};color:#fff">{icon(p.get("icon", "spark"), 70, 2)}</div>'
          f'<div id="{s.id("kw")}" style="font-size:76px;font-weight:800;letter-spacing:-2px">{esc(p.get("keyword", ""))}</div>'
          f'<div id="{s.id("sub")}" class="rk-soft" style="font-size:32px;font-weight:700;margin-top:10px">{esc(p.get("sub", ""))}</div></div>')
    s.enter_card()
    s.pop("ic", 0.15)
    s.rise("kw", 0.3, None)


TEMPLATES = {
    "agents": agents, "command": command, "question": question, "doc_extract": doc_extract,
    "mail": mail, "rule": rule, "bars": bars, "checklist": checklist, "waiting": waiting,
    "big_stat": big_stat, "results": results, "kpi": kpi, "stop_send": stop_send,
    "roles": roles, "pick": pick, "keyword": keyword,
}

# full-screen kinetic-type beats (talking-head styles); see graphics/kinetic.py
from .kinetic import KINETIC_TEMPLATES  # noqa: E402

TEMPLATES.update(KINETIC_TEMPLATES)

# floating panel cards over a continuous speaker (bold-talk round 2); see graphics/panel.py
from .panel import PANEL_TEMPLATES  # noqa: E402

TEMPLATES.update(PANEL_TEMPLATES)
