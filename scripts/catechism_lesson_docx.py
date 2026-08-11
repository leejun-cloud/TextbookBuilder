#!/usr/bin/env python3
"""소요리문답 성경공부 draft.md → 디자인된 Word(docx) 변환기 (v3, 압축 간격).

draft.md 포맷 (# 헤더로 구분되는 블록):
  # COVER            과/대주제/부제/문답 (key: value 4줄)
  # 오늘의 말씀        성경구절(줄바꿈 여러 줄) + "→ ..." 묵상 유도 줄
  # N. 이 시간의 기대   번호 목록(1. 2. 3.)
  # N. 오프닝          서술 문단 + "나누기: 질문"
  # N. 말씀 깊이 파기 — 소요리문답 제 N 문
                      "웨스트민스터 소요리문답 제 N 문" / "문) ..." / "답) ..."
                      뒤이어 "## 말씀 속으로 한 걸음" + Q1./A: 페어들
  # N. 내 삶에 담아가기 "안내: ..." + 번호 목록
  # N. 이번 주 챌린지    "안내: ..." + "□ ..." 목록
  # N. 명언으로 마무리   "인용문" / "— 저자" 페어 여러 개
  # N. 내 말로 정리하기  안내문 + [[WRITING_BOX:N]]
  # FOOTER            "성경공부 | 제 N 과 | 소요리문답 제 N 문" 한 줄

간격 원칙 (참조본 실측 기반, v2에서 페이지가 늘어났던 문제 수정):
  - 빈 문단(스페이서)은 "표 바로 다음에 표가 또 나올 때"만 삽입한다.
    문단 뒤에 표가 오거나 표 뒤에 문단이 오는 경우는 그 문단 자체의
    space_before/space_after 값으로 간격을 준다 (별도 빈 줄 금지).
  - 모든 간격 수치(4/6/8/12pt 등)는 사용자가 직접 손본 참조본에서
    실측한 값을 그대로 쓴다. 임의로 늘리지 않는다.
  - "내 말로 정리하기"의 필기 칸은 테두리 박스(표)가 아니라 밑줄
    문단(하단 테두리)으로 구현한다 — 표 셀 여백만큼의 낭비가 없다.

사용법: python3 catechism_lesson_docx.py <draft.md> -o <out.docx>
"""
import re
import argparse

import docx
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

FONT = "맑은 고딕"

NAVY = RGBColor(0x1A, 0x3A, 0x5C)
BLUE = RGBColor(0x2E, 0x6D, 0xA4)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
BODY = RGBColor(0x44, 0x44, 0x44)
GOLD = RGBColor(0xD4, 0xA0, 0x17)
QUOTE_TEXT = RGBColor(0x5C, 0x40, 0x08)
QUOTE_ATTR = RGBColor(0x8B, 0x60, 0x14)
SUBTITLE = RGBColor(0xC0, 0xD8, 0xF0)
FOOTER_GRAY = RGBColor(0x88, 0x88, 0x88)

NAVY_HEX = "1A3A5C"
BLUE_HEX = "2E6DA4"
LIGHT_BLUE_BG = "EEF4FB"
CREAM_BG = "FFF8E7"
QUOTE_BG = "FDF6E3"

# 섹션 순번(1~7)에 대응하는 배너 색 — 참조본 실측값 그대로
BANNER_COLOR_BY_POSITION = {1: NAVY_HEX, 2: BLUE_HEX, 3: NAVY_HEX, 4: NAVY_HEX,
                            5: BLUE_HEX, 6: NAVY_HEX, 7: BLUE_HEX}


def set_font(run, size=10.5, bold=False, italic=False, color=BODY, name=FONT):
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    run.font.name = name
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.find(qn('w:rFonts'))
    if rfonts is None:
        rfonts = OxmlElement('w:rFonts')
        rpr.append(rfonts)
    rfonts.set(qn('w:eastAsia'), name)
    if color is not None:
        run.font.color.rgb = color


def add_run(p, text, **kw):
    r = p.add_run(text)
    set_font(r, **kw)
    return r


def set_cell_bg(cell, hex_color):
    tcpr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'), 'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'), hex_color)
    tcpr.append(shd)


def set_cell_margins(cell, top=80, bottom=80, left=140, right=140):
    tcpr = cell._tc.get_or_add_tcPr()
    mar = OxmlElement('w:tcMar')
    for tag, val in (('top', top), ('bottom', bottom), ('left', left), ('right', right)):
        el = OxmlElement(f'w:{tag}')
        el.set(qn('w:w'), str(val))
        el.set(qn('w:type'), 'dxa')
        mar.append(el)
    tcpr.append(mar)


def bottom_rule(p, color="AAAAAA", sz=4):
    pPr = p._p.get_or_add_pPr()
    pbdr = OxmlElement('w:pBdr')
    bottom = OxmlElement('w:bottom')
    bottom.set(qn('w:val'), 'single')
    bottom.set(qn('w:sz'), str(sz))
    bottom.set(qn('w:space'), '4')
    bottom.set(qn('w:color'), color)
    pbdr.append(bottom)
    pPr.append(pbdr)


def solid_box(doc, fill_hex, bordered=False, margins=(80, 80, 140, 140)):
    table = doc.add_table(rows=1, cols=1)
    if bordered:
        table.style = doc.styles['Table Grid']
    cell = table.rows[0].cells[0]
    set_cell_bg(cell, fill_hex)
    set_cell_margins(cell, *margins)
    return table, cell


def spacer(doc, pt=4):
    """표 바로 다음에 표가 이어질 때만 쓰는 얇은 스페이서."""
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(pt)
    return p


# ---------- 파싱 ----------

def parse_blocks(md_text):
    lines = md_text.strip("\n").split("\n")
    blocks = []  # (header, [body_lines])
    cur_header, cur_body = None, []
    for line in lines:
        if line.startswith("# "):
            if cur_header is not None:
                blocks.append((cur_header, cur_body))
            cur_header = line[2:].strip()
            cur_body = []
        else:
            cur_body.append(line)
    if cur_header is not None:
        blocks.append((cur_header, cur_body))
    return blocks


def parse_kv(body_lines):
    kv = {}
    for line in body_lines:
        if ":" in line:
            k, v = line.split(":", 1)
            kv[k.strip()] = v.strip()
    return kv


SECTION_NUM_RE = re.compile(r"^(\d+)\.\s*(.+)$")


# ---------- 렌더러 ----------

def render_cover(doc, kv):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(8)
    add_run(p, f"제  {kv.get('과','')}  과", size=16, bold=True, color=GOLD)

    _, cell = solid_box(doc, NAVY_HEX, bordered=False, margins=(200, 200, 200, 200))
    p1 = cell.paragraphs[0]
    p1.alignment = WD_ALIGN_PARAGRAPH.CENTER
    add_run(p1, kv.get("대주제", ""), size=22, bold=True, color=WHITE)
    p2 = cell.add_paragraph()
    p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    add_run(p2, kv.get("부제", ""), size=14, color=SUBTITLE)

    spacer(doc, 12)  # 표지 박스 다음 여백 (참조본 실측: 12pt)

    p3 = doc.add_paragraph()
    p3.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p3.paragraph_format.space_after = Pt(12)
    add_run(p3, kv.get("문답", ""), size=13, bold=True, color=BLUE)


def render_scripture(doc, body_lines):
    verse_lines = [l.strip() for l in body_lines if l.strip() and not l.strip().startswith("→")]
    arrow_lines = [l.strip() for l in body_lines if l.strip().startswith("→")]
    _, cell = solid_box(doc, LIGHT_BLUE_BG, bordered=True)
    p0 = cell.paragraphs[0]
    add_run(p0, "오늘의 말씀", size=10.5, color=NAVY)
    for line in verse_lines:
        p = cell.add_paragraph()
        add_run(p, line, size=10.5, color=NAVY)
    for line in arrow_lines:
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(6)
        add_run(p, line, size=10, color=BLUE)


def render_banner(doc, position, title):
    fill = BANNER_COLOR_BY_POSITION.get(position, NAVY_HEX)
    _, cell = solid_box(doc, fill, bordered=False)
    p = cell.paragraphs[0]
    add_run(p, title, size=13, bold=True, color=WHITE)


def render_numbered_list(doc, items):
    for i, item in enumerate(items, 1):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(4)
        p.paragraph_format.space_after = Pt(4)
        add_run(p, f"{i}.  ", size=10.5, bold=True, color=BLUE)
        add_run(p, item, size=10.5, color=BODY)


def render_expectation(doc, body_lines):
    items = [SECTION_NUM_RE.match(l.strip()).group(2) for l in body_lines if SECTION_NUM_RE.match(l.strip())]
    render_numbered_list(doc, items)


def render_opening(doc, body_lines):
    narrative = []
    share = None
    for line in body_lines:
        s = line.strip()
        if s.startswith("나누기:"):
            share = s.split(":", 1)[1].strip()
        elif s:
            narrative.append(s)
    if narrative:
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(4)
        p.paragraph_format.space_after = Pt(8)
        add_run(p, " ".join(narrative), size=10.5, color=BODY)
    if share:
        _, cell = solid_box(doc, CREAM_BG, bordered=True)
        p0 = cell.paragraphs[0]
        add_run(p0, "나누기", size=10.5, bold=True, color=NAVY)
        p1 = cell.add_paragraph()
        add_run(p1, share, size=10.5, color=NAVY)
        spacer(doc, 4)  # 나누기 박스 다음에 배너 표가 바로 이어지므로 스페이서 필요


def render_catechism(doc, body_lines):
    label, q, a, qa_lines = None, None, None, []
    qa_heading = "말씀 속으로 한 걸음"
    in_qa = False
    for line in body_lines:
        s = line.strip()
        if s.startswith("## "):
            in_qa = True
            custom = s[3:].strip()
            if custom:
                qa_heading = custom
            continue
        if in_qa:
            qa_lines.append(line)
            continue
        if s.startswith("문)"):
            q = s
        elif s.startswith("답)"):
            a = s
        elif s:
            label = s

    spacer(doc, 4)  # 배너 표 다음에 문답 표가 바로 이어지므로 스페이서 필요
    _, cell = solid_box(doc, LIGHT_BLUE_BG, bordered=True)
    p0 = cell.paragraphs[0]
    add_run(p0, label or "", size=10.5, color=NAVY)
    if q:
        pq = cell.add_paragraph()
        add_run(pq, q, size=10.5, color=NAVY)
    if a:
        pa = cell.add_paragraph()
        add_run(pa, a, size=10.5, color=NAVY)

    if qa_lines:
        hp = doc.add_paragraph()
        hp.paragraph_format.space_before = Pt(14)
        hp.paragraph_format.space_after = Pt(6)
        add_run(hp, qa_heading, size=12, bold=True, color=BLUE)
        render_qa(doc, qa_lines)


def render_qa(doc, body_lines):
    pairs = []
    q, a = None, None
    for line in body_lines:
        s = line.strip()
        if not s:
            continue
        if re.match(r"^\S+\d+\.", s):
            if q is not None:
                pairs.append((q, a))
            q, a = s, None
        elif re.match(r"^[^:：]{1,12}[:：]", s):
            a = re.split(r"[:：]", s, maxsplit=1)[1].strip()
    if q is not None:
        pairs.append((q, a))
    for q, a in pairs:
        pq = doc.add_paragraph()
        pq.paragraph_format.space_before = Pt(8)
        pq.paragraph_format.space_after = Pt(3)
        add_run(pq, re.sub(r"^(\S+\d+)\.\s*", r"\1.  ", q), size=10.5, bold=True, color=BLUE)
        pa = doc.add_paragraph()
        pa.paragraph_format.left_indent = Cm(0.5)
        pa.paragraph_format.space_before = Pt(2)
        pa.paragraph_format.space_after = Pt(6)
        add_run(pa, a or "", size=10.5, color=BODY)


def render_note_and_numbered(doc, body_lines):
    note = None
    items = []
    for line in body_lines:
        s = line.strip()
        if not s:
            continue
        if s.startswith("안내:"):
            note = s.split(":", 1)[1].strip()
        else:
            m = SECTION_NUM_RE.match(s)
            if m:
                items.append(m.group(2))
    if note:
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(4)
        p.paragraph_format.space_after = Pt(8)
        add_run(p, note, size=10.5, color=BODY)
    render_numbered_list(doc, items)


def render_note_and_checkbox(doc, body_lines):
    review, note = None, None
    items = []
    for line in body_lines:
        s = line.strip()
        if not s:
            continue
        if s.startswith("지난주:"):
            review = s.split(":", 1)[1].strip()
        elif s.startswith("안내:"):
            note = s.split(":", 1)[1].strip()
        elif s.startswith("□"):
            items.append(s.lstrip("□").strip())
    if review:
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(4)
        p.paragraph_format.space_after = Pt(8)
        add_run(p, review, size=10.5, bold=True, color=NAVY)
    if note:
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(4)
        p.paragraph_format.space_after = Pt(8)
        add_run(p, note, size=10.5, color=BODY)
    for item in items:
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(4)
        p.paragraph_format.space_after = Pt(4)
        add_run(p, "☐  ", size=10.5, bold=True, color=GOLD)
        add_run(p, item, size=10.5, color=BODY)


def render_quotes(doc, body_lines):
    # 빈 줄로 구분되는 단락 단위로 그룹화한다. 각 그룹은
    # "인용문 + '— 출처' 줄"(따옴표 인용) 이거나, 출처 표기가 없는
    # 평서문 요약(원문 검증이 안 돼 인용부호 없이 서술한 경우) 둘 중 하나다.
    groups, cur = [], []
    for line in body_lines:
        s = line.strip()
        if not s:
            if cur:
                groups.append(cur)
                cur = []
            continue
        cur.append(s)
    if cur:
        groups.append(cur)

    first = True
    any_box = any(len(g) >= 2 and g[-1].startswith("—") for g in groups)
    for g in groups:
        if g[-1].startswith("—"):
            quote = " ".join(g[:-1])
            attribution = g[-1]
            if first and any_box:
                spacer(doc, 4)  # 배너 표 다음에 명언 표가 바로 이어지므로 스페이서 필요
                first = False
            _, cell = solid_box(doc, QUOTE_BG, bordered=False)
            p0 = cell.paragraphs[0]
            add_run(p0, quote, size=10.5, italic=True, color=QUOTE_TEXT)
            p1 = cell.add_paragraph()
            p1.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            add_run(p1, attribution, size=9.5, bold=True, color=QUOTE_ATTR)
        else:
            # 출처 표기 없는 평서문 요약 — 박스 없이 일반 문단으로 렌더링해서
            # 내용이 누락되지 않게 한다.
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(4)
            p.paragraph_format.space_after = Pt(8)
            add_run(p, " ".join(g), size=10.5, color=BODY)
    spacer(doc, 8)  # 마지막 명언 표 다음에 다음 섹션 배너 표가 이어지므로 스페이서 필요


def render_writing_box(doc, body_lines):
    instruction = [l.strip() for l in body_lines if l.strip() and not l.strip().startswith("[[")]
    n_lines = 2
    for line in body_lines:
        m = re.match(r"\[\[WRITING_BOX:(\d+)\]\]", line.strip())
        if m:
            n_lines = int(m.group(1))
    if instruction:
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(4)
        add_run(p, " ".join(instruction), size=10.5, color=BODY)
    for i in range(n_lines):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(4)
        p.paragraph_format.space_after = Pt(14)
        bottom_rule(p, color="AAAAAA", sz=4)
        add_run(p, " ", size=10.5)


def render_footer_line(doc, body_lines):
    text = next((l.strip() for l in body_lines if l.strip()), "")
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(8)
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    add_run(p, text, size=9, color=FOOTER_GRAY)


# ---------- 빌드 ----------

def build_docx(md_path, out_path):
    md_text = open(md_path, encoding="utf-8").read()
    blocks = parse_blocks(md_text)

    doc = docx.Document()
    style = doc.styles["Normal"]
    style.font.name = FONT
    style.font.size = Pt(10.5)
    rpr = style.element.get_or_add_rPr()
    rfonts = rpr.find(qn('w:rFonts'))
    if rfonts is None:
        rfonts = OxmlElement('w:rFonts')
        rpr.append(rfonts)
    rfonts.set(qn('w:eastAsia'), FONT)

    for section in doc.sections:
        section.top_margin = Cm(2.5)
        section.bottom_margin = Cm(2.0)
        section.left_margin = Cm(2.5)
        section.right_margin = Cm(2.5)

    position = 0
    for header, body in blocks:
        if header == "COVER":
            render_cover(doc, parse_kv(body))
        elif header == "오늘의 말씀":
            render_scripture(doc, body)
        elif header == "FOOTER":
            render_footer_line(doc, body)
        else:
            m = SECTION_NUM_RE.match(header)
            title_text = header
            if m:
                position += 1
                title_text = f"{m.group(1)}.  {m.group(2)}"
                topic = m.group(2)
            else:
                topic = header
            render_banner(doc, position, title_text)
            if "이 시간의 기대" in topic:
                render_expectation(doc, body)
            elif "오프닝" in topic:
                render_opening(doc, body)
            elif "깊이 파기" in topic:
                render_catechism(doc, body)
            elif "내 삶에 담아가기" in topic:
                render_note_and_numbered(doc, body)
            elif "챌린지" in topic:
                render_note_and_checkbox(doc, body)
            elif "명언으로 마무리" in topic:
                render_quotes(doc, body)
            elif "내 말로 정리하기" in topic:
                render_writing_box(doc, body)
            else:
                render_note_and_numbered(doc, body)

    doc.save(out_path)
    print(f"저장됨: {out_path}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("md_path")
    ap.add_argument("-o", "--out", required=True)
    a = ap.parse_args()
    build_docx(a.md_path, a.out)
