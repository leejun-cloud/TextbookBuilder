#!/usr/bin/env python3
"""초등부 4·5·6학년 콘텐츠 JSON → 승인된 B5 디자인 HTML/PDF 조판기.

빌더는 문장을 만들지 않는다. content/g{4,5,6}/NNN.json의 문자열과
content/SCHEMA.md에 정의된 고정 문구만 지면에 넣는다.

사용법:
  python3 scripts/elem456_build.py --grade 4 [--only 1,2] [--book] [--pdf]
"""
import argparse
import html
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROJ = ROOT / "projects" / "elementary-456-v2"
CONTENT = PROJ / "content"
BUILD = PROJ / "build"
EXPORTS = PROJ / "exports"
PRINT_PDF = ROOT / "scripts" / "print_pdf.sh"

PAGE_SIZE_MM = "182mm 257mm"

# ---------------------------------------------------------------------------
# 학년 설정
# ---------------------------------------------------------------------------
GRADE_CONFIG = {
    4: {
        "accent": "#2E7D4E", "dark": "#173C2B", "lightbg": "#E9F4EC",
        "lightgray": "#F1F5F2", "border": "#D9E4DC",
        "mode_label": "관찰하고 관계 찾기",
        "think_title": "4학년 사고활동 · 본문에서 찾아 관계 잇기",
        "offset": 0,
        "compact_reading": False,
    },
    5: {
        "accent": "#2E5DA4", "dark": "#17325A", "lightbg": "#E8F0FA",
        "lightgray": "#F1F4F8", "border": "#D7E1EE",
        "mode_label": "두 본문의 의미 묶기",
        "think_title": "5학년 사고활동 · 두 본문을 한 문장으로 묶기",
        "offset": 40,
        "compact_reading": False,
    },
    6: {
        "accent": "#7A4FA3", "dark": "#43265E", "lightbg": "#F0EAF8",
        "lightgray": "#F3F1F6", "border": "#E0D8EA",
        "mode_label": "주장-근거-이유로 판단",
        "think_title": "6학년 사고활동 · 주장-근거-이유",
        "offset": 80,
        "compact_reading": True,
    },
}

USAGE_LINES = [
    "1 일상 스토리 — 내 하루에서 질문을 시작해요.",
    "2 말씀 탐험 — 성경을 직접 펴고 두 질문의 답을 찾아요. 확인구절은 답을 쓴 뒤 읽어요. "
    "그다음 말씀 이해를 읽고 사고활동을 해요.",
    "3 빈칸·미션 — 오늘의 한 문장을 확인하고 짧은 미션을 해요.",
    "4 결단 액션 — 이번 주 할 일 하나를 언제·어디서 할지까지 정해요.",
    "5 말씀 이어가기 — 가족·믿을 만한 어른·교사·혼자 기록 중 내가 골라요. 검사하지 않아요.",
    "도움 사다리 — 혼자 찾기 → 짝에게 절 위치 힌트 받기 → 교사에게 절 위치만 묻기. "
    "답 자체를 먼저 듣지 않아요.",
    "활동 기록은 믿음을 점수로 표시하는 칸이 아니에요.",
]


def esc(s):
    if s is None:
        return ""
    return html.escape(str(s), quote=False)


# ---------------------------------------------------------------------------
# CSS (1과.html의 학생용 3쪽 CSS를 그대로 가져오되 색을 변수화)
# ---------------------------------------------------------------------------
def build_css(cfg):
    accent = cfg["accent"]
    dark = cfg["dark"]
    lightbg = cfg["lightbg"]
    lightgray = cfg["lightgray"]
    border = cfg["border"]
    reading_line_height = "1.5" if cfg["compact_reading"] else "1.55"
    return f"""
@page {{ size: {PAGE_SIZE_MM}; margin: 0; }}
* {{ box-sizing: border-box; }}
body {{ margin:0; font-family:'NanumSquareRound','Apple SD Gothic Neo','맑은 고딕',sans-serif; color:#2F3A35; }}

.page {{
  width:182mm; height:257mm;
  box-sizing:border-box;
  padding: 11mm 12mm 13mm;
  page-break-after: always;
  position:relative;
  overflow:hidden;
  background:#fff;
  border-top: 4mm solid {accent};
}}
.page:last-child {{ page-break-after: auto; }}

.header-row {{
  display:flex; justify-content:space-between; align-items:baseline;
  font-size:8.5pt; color:#6B7785; margin-bottom:5mm;
}}
.header-row .right {{ color:{accent}; font-weight:700; }}

.badge-row {{ display:flex; align-items:center; gap:3mm; margin-bottom:3mm; }}
.pill {{
  display:inline-block; background:{accent}; color:#fff; font-weight:700;
  font-size:9pt; padding:1.2mm 4mm; border-radius:10mm;
}}
.meta-text {{ color:{accent}; font-weight:700; font-size:9pt; }}

h1.title {{ font-size:20pt; font-weight:700; color:{dark}; margin:0 0 4mm; }}

.chip-tabs {{ display:flex; gap:2.5mm; margin-bottom:5mm; }}
.chip {{
  flex:1; text-align:center; font-size:8.5pt; font-weight:700;
  padding:2.2mm 0; border-radius:6mm; background:{lightgray}; color:#6B7785;
}}
.chip.active {{ background:{accent}; color:#fff; }}

.sentence-box {{
  background:{lightbg}; border-left:3px solid {accent}; border-radius:2mm;
  padding:3.5mm 5mm; margin-bottom:5mm;
}}
.sentence-box .label {{ color:{accent}; font-weight:700; font-size:8.5pt; margin-bottom:1.5mm; }}
.sentence-box .body {{ font-size:12pt; font-weight:700; color:{dark}; }}

.section-header {{
  display:flex; justify-content:space-between; align-items:baseline;
  color:{accent}; font-weight:700; font-size:11pt; margin: 4mm 0 2.5mm;
}}
.section-header .time {{ color:#6B7785; font-weight:400; font-size:8.5pt; }}

.plain-box {{
  background:{lightgray}; border-radius:2mm; padding:3.5mm 5mm; font-size:9.5pt; line-height:1.55;
  margin-bottom:3mm;
}}

.write-line {{ margin-bottom:3mm; }}
.write-line .wl-label {{ font-weight:700; font-size:9pt; margin-bottom:1mm; }}
.write-line .wl-blank {{ height:7mm; border-bottom:0.35mm solid #B9C6BD; }}

.guide-line {{ font-weight:700; font-size:9.5pt; margin: 2mm 0 1.5mm; }}
.center-text {{ font-size:9.5pt; color:{dark}; font-weight:700; margin-bottom:3mm; }}

.qbox {{ font-weight:700; font-size:9.5pt; margin-bottom:1.5mm; }}

.check-box {{
  background:{lightgray}; border-radius:2mm; padding:3mm 5mm; margin-bottom:4mm;
}}
.check-box .label {{ color:{accent}; font-weight:700; font-size:8.5pt; margin-bottom:1mm; }}
.check-box .verse {{ color:{dark}; font-size:9.5pt; }}

.help-strip {{
  background:{lightbg}; font-size:8.5pt; color:#2F3A35; padding:2.5mm 5mm; border-radius:2mm; margin-bottom:4mm;
}}
.help-strip b {{ color:{accent}; }}

.understand-box {{
  background:#fff; border:0.35mm solid {accent}; border-radius:2mm; padding:3.5mm 5mm; margin-bottom:4mm;
}}
.understand-box .subtitle {{ color:{accent}; font-weight:700; font-size:9.5pt; margin-bottom:2mm; }}
.understand-box .label {{ font-weight:700; font-size:8.5pt; margin-bottom:1mm; }}
.understand-box .body {{ font-size:9.5pt; line-height:{reading_line_height}; }}
.understand-box .body p {{ margin:0 0 2.5mm; }}
.understand-box .body p:last-child {{ margin-bottom:0; }}

table.think-table {{ width:100%; border-collapse:collapse; font-size:9pt; margin-bottom:3mm; }}
table.think-table th {{ background:{accent}; color:#fff; font-weight:700; padding:2mm 2.5mm; text-align:left; }}
table.think-table td {{ border:0.3mm solid {border}; padding:2mm 2.5mm; }}

.blank-label-box {{
  background:{lightgray}; border-radius:2mm; padding:2mm 4mm; display:inline-block;
  font-weight:700; font-size:8.5pt; color:{accent}; margin-bottom:2mm;
}}
.blank-sentence {{ font-size:11pt; font-weight:700; color:{dark}; margin-bottom:3mm; }}
.mission-text {{ font-size:9.5pt; margin-bottom:2mm; }}

.decision-text {{ font-weight:700; font-size:10pt; margin-bottom:2.5mm; }}
table.decide-table {{ width:100%; border-collapse:collapse; font-size:9pt; margin-bottom:3mm; }}
table.decide-table th {{ background:{lightbg}; color:{dark}; font-weight:700; padding:2mm; border:0.3mm solid {border}; text-align:left; }}
table.decide-table td {{ border:0.3mm solid {border}; height:10mm; padding:2mm; }}

.checkbox-row {{ display:flex; gap:4mm; font-size:9pt; margin: 2mm 0 1mm; flex-wrap:nowrap; }}
.checkbox-note {{ font-size:8pt; color:#6B7785; margin-bottom:3mm; }}

.recite-box {{
  background:{lightbg}; border-radius:2mm; padding:3mm 5mm; margin-bottom:4mm;
}}
.recite-box .label {{ color:{accent}; font-weight:700; font-size:8.5pt; margin-bottom:1mm; }}
.recite-box .body {{ font-size:9.5pt; color:{dark}; }}

.small-gray {{ font-size:8pt; color:#6B7785; }}

.footer {{
  position:absolute; left:12mm; right:12mm; bottom:6mm;
  border-top:0.3mm solid {border}; padding-top:2mm;
  font-size:8pt; color:#6B7785;
}}

/* 표지 */
.cover-page {{ border-top:none; padding:0; }}
.cover-band {{
  background:{accent}; color:#fff; height:100mm; padding:16mm 14mm;
  display:flex; flex-direction:column; justify-content:center;
}}
.cover-band .kicker {{ font-size:11pt; font-weight:700; opacity:0.9; margin-bottom:4mm; }}
.cover-band .main {{ font-size:26pt; font-weight:700; line-height:1.3; }}
.cover-body {{ padding:16mm 14mm; }}
.cover-body .line {{ font-size:13pt; font-weight:700; color:{dark}; margin-bottom:5mm; }}
.cover-body .mode {{ font-size:11pt; color:{accent}; font-weight:700; }}

/* 차례 */
.toc-title {{ font-size:18pt; font-weight:700; color:{dark}; margin: 0 0 6mm; }}
.toc-unit {{ color:{accent}; font-weight:700; font-size:11pt; margin: 4mm 0 2mm; }}
.toc-grid {{ column-count:2; column-gap:10mm; }}
.toc-item {{ font-size:9.5pt; margin-bottom:2mm; break-inside:avoid; }}
.toc-item .no {{ color:{accent}; font-weight:700; margin-right:2mm; }}

/* 사용법 */
.usage-title {{ font-size:18pt; font-weight:700; color:{dark}; margin: 0 0 6mm; }}
.usage-line {{ font-size:10pt; line-height:1.7; margin-bottom:4mm; }}
.usage-note {{ font-size:9pt; color:#6B7785; margin-top:4mm; }}
"""


# ---------------------------------------------------------------------------
# 공용 조각
# ---------------------------------------------------------------------------
def write_lines(label, count):
    parts = []
    for i in range(count):
        if i == 0:
            parts.append(
                f'<div class="write-line"><div class="wl-label">{esc(label)}</div>'
                f'<div class="wl-blank"></div></div>'
            )
        else:
            parts.append('<div class="write-line"><div class="wl-blank"></div></div>')
    return "\n  ".join(parts)


def header_row(cfg):
    return (
        '<div class="header-row">'
        '<span>다음세대 교리교육 · 초등부 학생용 교재</span>'
        f'<span class="right">{esc(cfg["mode_label"])}</span>'
        '</div>'
    )


def meta_text(lesson):
    no = lesson["no"]
    grade = lesson["grade"]
    year = grade - 3
    elem_no = no + GRADE_CONFIG[grade]["offset"]
    common_no = lesson["common_no"]
    txt = f'{no}과 · {year}년차 {no}과 · 초등부 {elem_no}과 · 공통 {common_no}과'
    if lesson.get("required_memory"):
        txt += " · ● 필수암송"
    return txt


def badge_row(lesson):
    return (
        '<div class="badge-row">'
        f'<span class="pill">{lesson["grade"]}학년</span>'
        f'<span class="meta-text">{esc(meta_text(lesson))}</span>'
        '</div>'
    )


def chip_tabs(active_set):
    labels = {
        1: "1 일상 스토리", 2: "2 말씀 탐험", 3: "3 빈칸·미션",
        4: "4 결단 액션", 5: "5 말씀 이어가기",
    }
    chips = []
    for i in range(1, 6):
        cls = "chip active" if i in active_set else "chip"
        chips.append(f'<div class="{cls}">{labels[i]}</div>')
    return '<div class="chip-tabs">' + "".join(chips) + '</div>'


def footer(lesson, page_no):
    grade = lesson["grade"]
    no = lesson["no"]
    year = grade - 3
    common_no = lesson["common_no"]
    return (
        f'<div class="footer">{grade}학년 · {no}과 · {year}년차 {no}과 · '
        f'공통 {common_no}과 · {page_no}/3</div>'
    )


# ---------------------------------------------------------------------------
# 과 3쪽 조판
# ---------------------------------------------------------------------------
def build_lesson_pages(lesson, cfg):
    title = esc(lesson["title"])

    # ---- 1쪽 ----
    p1 = []
    p1.append('<div class="page">')
    p1.append(header_row(cfg))
    p1.append(badge_row(lesson))
    p1.append(f'<h1 class="title">{title}</h1>')
    p1.append(chip_tabs({1, 2}))
    p1.append(
        '<div class="sentence-box"><div class="label">오늘의 한 문장</div>'
        f'<div class="body">{esc(lesson["core"])}</div></div>'
    )
    p1.append('<div class="section-header"><span>1  일상 스토리</span><span class="time">6분</span></div>')
    p1.append(f'<div class="plain-box">{esc(lesson["story"])}</div>')
    for label in lesson["story_lines"]:
        p1.append(write_lines(label, 1))
    p1.append('<div class="section-header"><span>2  말씀 탐험</span><span class="time">12분</span></div>')
    p1.append('<div class="guide-line">성경을 직접 펴서 먼저 답을 찾아요. 확인구절은 답을 쓴 뒤 읽어요.</div>')
    p1.append(f'<div class="center-text">중심 본문 {esc(lesson["center"])}</div>')
    q0 = lesson["q"][0]
    p1.append(f'<div class="qbox">① {esc(q0["label"])}</div>')
    p1.append(write_lines("찾은 답", 1))
    p1.append(
        f'<div class="check-box"><div class="label">답을 쓴 뒤 맞추어 보기{(" · " + esc(q0["ref"])) if q0.get("ref") else ""}</div>'
        f'<div class="verse">{esc(q0.get("verse", ""))}</div></div>'
    )
    p1.append(footer(lesson, 1))
    p1.append('</div>')

    # ---- 2쪽 ----
    p2 = []
    p2.append('<div class="page">')
    p2.append(header_row(cfg))
    p2.append(badge_row(lesson))
    p2.append(f'<h1 class="title">{title}</h1>')
    p2.append(chip_tabs({2}))
    q1 = lesson["q"][1]
    p2.append(f'<div class="qbox">② {esc(q1["label"])}</div>')
    p2.append(write_lines("찾은 답", 1))
    p2.append(
        f'<div class="check-box"><div class="label">답을 쓴 뒤 맞추어 보기{(" · " + esc(q1["ref"])) if q1.get("ref") else ""}</div>'
        f'<div class="verse">{esc(q1.get("verse", ""))}</div></div>'
    )
    p2.append(
        '<div class="help-strip"><b>도움 사다리</b>  혼자 찾기 → 짝에게 절 위치 힌트 받기 → '
        '교사에게 절 위치만 묻기</div>'
    )
    p2.append('<div class="section-header"><span>2단계 계속 · 성경에서 찾고 확인한 뒤 읽어요</span></div>')
    reading_paras = "".join(f'<p>{esc(p)}</p>' for p in lesson["reading"])
    p2.append(
        '<div class="understand-box">'
        f'<div class="subtitle">{esc(lesson["reading_title"])}</div>'
        '<div class="label">말씀 이해 · 읽기</div>'
        f'<div class="body">{reading_paras}</div>'
        '</div>'
    )
    p2.append(f'<div class="section-header"><span>{esc(cfg["think_title"])}</span></div>')
    think_head = lesson["think_head"]
    think_row = lesson["think_row"]
    p2.append('<table class="think-table">')
    p2.append('<tr>' + "".join(f'<th>{esc(h)}</th>' for h in think_head) + '</tr>')
    p2.append('<tr>' + "".join(f'<td>{esc(c)}</td>' for c in think_row) + '</tr>')
    p2.append('</table>')
    p2.append(write_lines(lesson["think_line_label"], lesson["think_line_count"]))
    p2.append(footer(lesson, 2))
    p2.append('</div>')

    # ---- 3쪽 ----
    p3 = []
    p3.append('<div class="page">')
    p3.append(header_row(cfg))
    p3.append(badge_row(lesson))
    p3.append(f'<h1 class="title">{title}</h1>')
    p3.append(chip_tabs({3, 4, 5}))
    p3.append('<div class="section-header"><span>3  빈칸·미션</span><span class="time">10분</span></div>')
    p3.append('<div class="blank-label-box">빈칸은 딱 하나</div>')
    p3.append(f'<div class="blank-sentence">{esc(lesson["blank"])}</div>')
    p3.append(f'<div class="mission-text">{esc(lesson["mission"])}</div>')
    p3.append(write_lines(lesson["mission_line_label"], lesson["mission_line_count"]))
    p3.append('<div class="section-header"><span>4  결단 액션</span><span class="time">7분</span></div>')
    p3.append(f'<div class="decision-text">{esc(lesson["decision"])}</div>')
    cols = lesson["decision_cols"]
    p3.append('<table class="decide-table">')
    p3.append('<tr>' + "".join(f'<th>{esc(c)}</th>' for c in cols) + '</tr>')
    p3.append('<tr>' + "".join('<td></td>' for _ in cols) + '</tr>')
    p3.append('</table>')
    p3.append('<div class="section-header"><span>5  말씀 이어가기</span><span class="time">5분</span></div>')
    p3.append(f'<div class="plain-box">{esc(lesson["share_intro"])}</div>')
    p3.append(
        '<div class="checkbox-row"><span>☐ 가족과</span><span>☐ 믿을 만한 어른과</span>'
        '<span>☐ 교사와</span><span>☐ 혼자 기록</span></div>'
    )
    p3.append('<div class="checkbox-note">네 방법은 모두 동등한 참여입니다.</div>')
    p3.append(f'<div class="mission-text">{esc(lesson["share_label"])}: {esc(lesson["share_text"])}</div>')
    p3.append(
        f'<div class="recite-box"><div class="label">암송 · {esc(lesson["memory_ref"])}</div>'
        f'<div class="body">{esc(lesson["memory_text"])}</div></div>'
    )
    p3.append('<div class="section-header"><span>오늘의 한 문장을 내 말로 말해요</span></div>')
    p3.append(write_lines("내 말", 2))
    p3.append('<div class="small-gray">※ 활동 기록은 믿음을 점수로 표시하는 칸이 아닙니다.</div>')
    p3.append(footer(lesson, 3))
    p3.append('</div>')

    return "\n".join(p1) + "\n" + "\n".join(p2) + "\n" + "\n".join(p3)


def build_lesson_html(lesson):
    cfg = GRADE_CONFIG[lesson["grade"]]
    css = build_css(cfg)
    body = build_lesson_pages(lesson, cfg)
    title = esc(lesson["title"])
    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<title>{lesson["no"]}과</title>
<style>{css}</style>
</head>
<body>
{body}
</body>
</html>
"""


# ---------------------------------------------------------------------------
# 표지 / 차례 / 사용법
# ---------------------------------------------------------------------------
def build_cover_page(grade, cfg):
    return f"""<div class="page cover-page">
  <div class="cover-band">
    <div class="kicker">다음세대 교리교육</div>
    <div class="main">초등부 {grade}학년 교리교재</div>
  </div>
  <div class="cover-body">
    <div class="line">40과 · B5 학생용</div>
    <div class="mode">{esc(cfg["mode_label"])}</div>
  </div>
</div>"""


def build_toc_pages(lessons, max_items_per_page=48):
    # unit별로 묶는다 (원래 순서 유지)
    units = []
    unit_index = {}
    for lesson in lessons:
        u = lesson["unit"]
        if u not in unit_index:
            unit_index[u] = len(units)
            units.append((u, []))
        units[unit_index[u]][1].append(lesson)

    # unit 헤더 포함해서 항목 수를 대략 세어 페이지 단위로 분할
    pages = []
    current = []
    count = 0
    for unit, unit_lessons in units:
        needed = 1 + len(unit_lessons)
        if count + needed > max_items_per_page and current:
            pages.append(current)
            current = []
            count = 0
        current.append((unit, unit_lessons))
        count += needed
    if current:
        pages.append(current)
    if not pages:
        pages = [[]]

    html_pages = []
    for i, page_units in enumerate(pages):
        parts = ['<div class="page">']
        parts.append(f'<h2 class="toc-title">차례{"" if i == 0 else " (계속)"}</h2>')
        parts.append('<div class="toc-grid">')
        for unit, unit_lessons in page_units:
            parts.append(f'<div class="toc-unit">{esc(unit)}</div>')
            for lesson in unit_lessons:
                parts.append(
                    f'<div class="toc-item"><span class="no">{lesson["no"]}과</span>'
                    f'{esc(lesson["title"])}</div>'
                )
        parts.append('</div>')
        parts.append('</div>')
        html_pages.append("\n".join(parts))
    return "\n".join(html_pages)


def build_usage_page():
    lines = "".join(f'<div class="usage-line">{esc(l)}</div>' for l in USAGE_LINES[:-1])
    note = f'<div class="usage-note">{esc(USAGE_LINES[-1])}</div>'
    return f"""<div class="page">
  <h2 class="usage-title">이 책을 쓰는 법</h2>
  {lines}
  {note}
</div>"""


def build_book_html(grade, lessons):
    cfg = GRADE_CONFIG[grade]
    css = build_css(cfg)
    parts = [build_cover_page(grade, cfg), build_toc_pages(lessons), build_usage_page()]
    for lesson in lessons:
        parts.append(build_lesson_pages(lesson, cfg))
    body = "\n".join(parts)
    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<title>초등부 {grade}학년 교리교재</title>
<style>{css}</style>
</head>
<body>
{body}
</body>
</html>
"""


# ---------------------------------------------------------------------------
# 파일 I/O + CLI
# ---------------------------------------------------------------------------
def load_lessons(grade, only=None):
    grade_dir = CONTENT / f"g{grade}"
    files = sorted(grade_dir.glob("*.json"))
    lessons = []
    for f in files:
        data = json.loads(f.read_text(encoding="utf-8"))
        lessons.append(data)
    lessons.sort(key=lambda l: l["no"])
    if only is not None:
        lessons = [l for l in lessons if l["no"] in only]
    return lessons


def run_pdf(html_path, pdf_path):
    subprocess.run(
        ["bash", str(PRINT_PDF), str(html_path), str(pdf_path)],
        check=True,
    )


def main():
    ap = argparse.ArgumentParser(description="초등부 4·5·6학년 B5 학생용 교재 조판기")
    ap.add_argument("--grade", type=int, required=True, choices=[4, 5, 6])
    ap.add_argument("--only", type=str, default=None, help="과 번호(no) 콤마 목록, 예: 1,2")
    ap.add_argument("--book", action="store_true", help="학년 전체를 한 HTML/PDF로 합본")
    ap.add_argument("--pdf", action="store_true", help="과별 PDF도 생성")
    args = ap.parse_args()

    only = None
    if args.only:
        only = {int(x) for x in args.only.split(",")}

    lessons = load_lessons(args.grade, only=only)
    if not lessons:
        print(f"ERROR: content/g{args.grade}에 해당하는 과가 없다.", file=sys.stderr)
        sys.exit(1)

    out_dir = BUILD / f"g{args.grade}"
    out_dir.mkdir(parents=True, exist_ok=True)

    for lesson in lessons:
        html_out = out_dir / f"{lesson['no']:03d}.html"
        html_out.write_text(build_lesson_html(lesson), encoding="utf-8")
        print(f"작성됨: {html_out}")
        if args.pdf:
            pdf_out = out_dir / f"{lesson['no']:03d}.pdf"
            run_pdf(html_out, pdf_out)

    if args.book:
        # book 모드는 --only와 무관하게 그 학년에 있는 과 전체를 쓴다
        all_lessons = load_lessons(args.grade, only=None)
        book_html = build_book_html(args.grade, all_lessons)
        EXPORTS.mkdir(parents=True, exist_ok=True)
        tmp_html = BUILD / f"g{args.grade}" / "_book.html"
        tmp_html.write_text(book_html, encoding="utf-8")
        pdf_out = EXPORTS / f"초등{args.grade}학년_40과_B5_학생용교재_v2.pdf"
        run_pdf(tmp_html, pdf_out)
        print(f"작성됨: {pdf_out}")


if __name__ == "__main__":
    main()
