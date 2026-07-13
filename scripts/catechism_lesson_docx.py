#!/usr/bin/env python3
"""소요리문답 성경공부 draft.md → 디자인된 Word(docx) 변환기.

draft.md는 고정된 9단계 섹션 구조를 따른다 (project.md 포맷 기준 참조):
제목(##) / 오늘의 말씀 / 오프닝 / 이 시간의 기대 / 말씀 깊이 파기 /
말씀 속으로 한 걸음 / 내 삶에 담아가기 / 이번 주 챌린지 /
명언으로 마무리 / 내 말로 정리하기.

각 섹션은 "### 제목 이모지" 헤더로 시작한다. "말씀 깊이 파기"와
"말씀 속으로 한 걸음"은 **문**/**답**, **Q1**/**A** 페어를 인식해
전용 스타일을 적용한다. "내 말로 정리하기" 섹션의 [[WRITING_BOX:N]]
마커는 N줄짜리 필기 칸으로 렌더링된다.

사용법: python3 catechism_lesson_docx.py <draft.md> -o <out.docx>
"""
import re
import sys
import argparse

import docx
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

NAVY = RGBColor(0x1B, 0x2A, 0x4A)
GOLD = RGBColor(0xA9, 0x7A, 0x1F)
GRAY = RGBColor(0x6B, 0x6B, 0x6B)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
CREAM_BG = "FBF3DF"
NAVY_BG = "1B2A4A"
LIGHT_BG = "F2F2F2"
GOLD_BORDER = "A97A1F"
FONT = "맑은 고딕"


def set_font(run, size=11, bold=False, italic=False, color=None, name=FONT):
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


def set_cell_border(cell, color=GOLD_BORDER, sz=6, edges=('top', 'left', 'bottom', 'right')):
    tcpr = cell._tc.get_or_add_tcPr()
    borders = OxmlElement('w:tcBorders')
    for edge in edges:
        el = OxmlElement(f'w:{edge}')
        el.set(qn('w:val'), 'single')
        el.set(qn('w:sz'), str(sz))
        el.set(qn('w:color'), color)
        borders.append(el)
    tcpr.append(borders)


def set_cell_margins(cell, top=120, bottom=120, left=180, right=180):
    tcpr = cell._tc.get_or_add_tcPr()
    mar = OxmlElement('w:tcMar')
    for tag, val in (('top', top), ('bottom', bottom), ('left', left), ('right', right)):
        el = OxmlElement(f'w:{tag}')
        el.set(qn('w:w'), str(val))
        el.set(qn('w:type'), 'dxa')
        mar.append(el)
    tcpr.append(mar)


def bottom_rule(p, color=GOLD_BORDER, sz=6):
    pPr = p._p.get_or_add_pPr()
    pbdr = OxmlElement('w:pBdr')
    bottom = OxmlElement('w:bottom')
    bottom.set(qn('w:val'), 'single')
    bottom.set(qn('w:sz'), str(sz))
    bottom.set(qn('w:space'), '4')
    bottom.set(qn('w:color'), color)
    pbdr.append(bottom)
    pPr.append(pbdr)


def parse_sections(md_text):
    lines = md_text.strip("\n").split("\n")
    title = None
    sections = []  # (header, [body_lines])
    cur_header, cur_body = None, []
    for line in lines:
        if line.startswith("## ") and title is None:
            title = line[3:].strip()
        elif line.startswith("### "):
            if cur_header is not None:
                sections.append((cur_header, cur_body))
            cur_header = line[4:].strip()
            cur_body = []
        else:
            cur_body.append(line)
    if cur_header is not None:
        sections.append((cur_header, cur_body))
    return title, sections


def strip_bold(text):
    return re.sub(r"\*\*(.+?)\*\*", r"\1", text)


def section_banner(doc, text):
    table = doc.add_table(rows=1, cols=1)
    table.autofit = True
    cell = table.rows[0].cells[0]
    set_cell_bg(cell, NAVY_BG)
    set_cell_margins(cell, top=100, bottom=100, left=200, right=200)
    p = cell.paragraphs[0]
    add_run(p, text, size=13, bold=True, color=WHITE)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)


def add_scripture_box(doc, body_lines):
    text_lines = [l for l in body_lines if l.strip() and not l.startswith("→")]
    arrow_lines = [l for l in body_lines if l.strip().startswith("→")]
    table = doc.add_table(rows=1, cols=1)
    cell = table.rows[0].cells[0]
    set_cell_bg(cell, CREAM_BG)
    set_cell_border(cell, color=GOLD_BORDER, sz=8)
    set_cell_margins(cell, top=180, bottom=180, left=260, right=260)
    p = cell.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    for i, line in enumerate(text_lines):
        if i > 0:
            p.add_run().add_break()
        add_run(p, line, size=12, italic=True, color=NAVY)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)
    for line in arrow_lines:
        ap = doc.add_paragraph()
        add_run(ap, line, size=10, italic=True, color=GRAY)


def add_opening(doc, body_lines):
    narrative = []
    share = None
    for line in body_lines:
        if line.strip().startswith("**나누기**"):
            share = line.strip()
        elif line.strip():
            narrative.append(line.strip())
    if narrative:
        p = doc.add_paragraph()
        add_run(p, " ".join(narrative), size=10.5, color=RGBColor(0x33, 0x33, 0x33))
        p.paragraph_format.space_after = Pt(10)
    if share:
        m = re.match(r"\*\*나누기\*\*:\s*(.+)", share)
        content = m.group(1) if m else share
        table = doc.add_table(rows=1, cols=1)
        cell = table.rows[0].cells[0]
        set_cell_bg(cell, LIGHT_BG)
        set_cell_border(cell, color="BBBBBB", sz=4)
        set_cell_margins(cell)
        p = cell.paragraphs[0]
        add_run(p, "🤝 나누기  ", size=10.5, bold=True, color=GOLD)
        add_run(p, content, size=10.5, color=RGBColor(0x22, 0x22, 0x22))
    doc.add_paragraph().paragraph_format.space_after = Pt(2)


def add_expectation(doc, body_lines):
    items = [l.strip() for l in body_lines if l.strip()]
    for item in items:
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(6)
        add_run(p, item, size=11, color=RGBColor(0x22, 0x22, 0x22))


def add_catechism_box(doc, body_lines):
    q, a = None, None
    for line in body_lines:
        s = line.strip()
        if s.startswith("**문**"):
            q = strip_bold(s).split(":", 1)[1].strip()
        elif s.startswith("**답**"):
            a = strip_bold(s).split(":", 1)[1].strip()
    table = doc.add_table(rows=1, cols=1)
    cell = table.rows[0].cells[0]
    set_cell_bg(cell, NAVY_BG)
    set_cell_border(cell, color=GOLD_BORDER, sz=10)
    set_cell_margins(cell, top=220, bottom=220, left=280, right=280)
    p = cell.paragraphs[0]
    add_run(p, "문  ", size=11, bold=True, color=RGBColor(0xE8, 0xC5, 0x6A))
    add_run(p, q or "", size=11, bold=True, color=WHITE)
    p2 = cell.add_paragraph()
    p2.paragraph_format.space_before = Pt(6)
    add_run(p2, "답  ", size=11, bold=True, color=RGBColor(0xE8, 0xC5, 0x6A))
    add_run(p2, a or "", size=11, color=WHITE)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)


def add_qa(doc, body_lines):
    pairs = []
    q, a = None, None
    for line in body_lines:
        s = line.strip()
        if re.match(r"\*\*Q\d+\*\*", s):
            if q is not None:
                pairs.append((q, a))
            q = re.sub(r"\*\*Q\d+\*\*:\s*", "", s)
            a = None
        elif s.startswith("**A**"):
            a = strip_bold(s).split(":", 1)[1].strip()
    if q is not None:
        pairs.append((q, a))
    for i, (qt, at) in enumerate(pairs, 1):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(8)
        p.paragraph_format.space_after = Pt(2)
        add_run(p, f"Q{i}  ", size=11, bold=True, color=GOLD)
        add_run(p, qt, size=11, bold=True, color=NAVY)
        pa = doc.add_paragraph()
        pa.paragraph_format.left_indent = Cm(0.5)
        pa.paragraph_format.space_after = Pt(6)
        add_run(pa, at or "", size=10.5, color=RGBColor(0x33, 0x33, 0x33))
        if i < len(pairs):
            divider = doc.add_paragraph()
            divider.paragraph_format.space_after = Pt(2)
            bottom_rule(divider, color="DDDDDD", sz=4)


def add_numbered_note(doc, body_lines, note_color=GOLD):
    header_note = None
    items = []
    for line in body_lines:
        s = line.strip()
        if not s:
            continue
        m = re.match(r"(\d+)\.\s*(.+)", s)
        if m:
            items.append(m.group(2))
        else:
            header_note = s
    if header_note:
        p = doc.add_paragraph()
        add_run(p, header_note, size=9.5, italic=True, color=GRAY)
        p.paragraph_format.space_after = Pt(6)
    for i, item in enumerate(items, 1):
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(6)
        p.paragraph_format.left_indent = Cm(0.3)
        add_run(p, f"{i}. ", size=10.5, bold=True, color=note_color)
        add_run(p, item, size=10.5, color=RGBColor(0x22, 0x22, 0x22))


def add_quotes(doc, body_lines):
    quote, attr = None, None
    for line in body_lines:
        s = line.strip()
        if not s:
            continue
        if s.startswith("—"):
            attr = s
            table = doc.add_table(rows=1, cols=1)
            cell = table.rows[0].cells[0]
            set_cell_bg(cell, LIGHT_BG)
            set_cell_border(cell, color="CCCCCC", sz=4, edges=('left',))
            set_cell_margins(cell, top=140, bottom=140, left=260, right=260)
            p = cell.paragraphs[0]
            add_run(p, quote or "", size=10.5, italic=True, color=RGBColor(0x33, 0x33, 0x33))
            p2 = cell.add_paragraph()
            p2.paragraph_format.space_before = Pt(4)
            add_run(p2, attr, size=9.5, bold=True, color=GOLD)
            doc.add_paragraph().paragraph_format.space_after = Pt(4)
        else:
            quote = s


def add_writing_box(doc, body_lines):
    instruction = [l.strip() for l in body_lines if l.strip() and not l.strip().startswith("[[")]
    n_lines = 2
    for line in body_lines:
        m = re.match(r"\[\[WRITING_BOX:(\d+)\]\]", line.strip())
        if m:
            n_lines = int(m.group(1))
    if instruction:
        p = doc.add_paragraph()
        add_run(p, " ".join(instruction), size=10.5, color=RGBColor(0x22, 0x22, 0x22))
        p.paragraph_format.space_after = Pt(8)
    table = doc.add_table(rows=1, cols=1)
    cell = table.rows[0].cells[0]
    set_cell_bg(cell, "FFFFFF")
    set_cell_border(cell, color=NAVY_BG, sz=10)
    set_cell_margins(cell, top=200, bottom=200, left=220, right=220)
    for i in range(n_lines):
        p = cell.paragraphs[0] if i == 0 else cell.add_paragraph()
        p.paragraph_format.space_after = Pt(220 if i < n_lines - 1 else 0)
        bottom_rule(p, color="AAAAAA", sz=4)
        add_run(p, " ", size=11)


SECTION_RENDERERS = [
    (re.compile("오늘의 말씀"), add_scripture_box),
    (re.compile("오프닝"), add_opening),
    (re.compile("이 시간의 기대"), add_expectation),
    (re.compile("말씀 깊이 파기"), add_catechism_box),
    (re.compile("말씀 속으로 한 걸음"), add_qa),
    (re.compile("내 삶에 담아가기"), add_numbered_note),
    (re.compile("이번 주 챌린지"), lambda d, b: add_numbered_note(d, b, note_color=NAVY)),
    (re.compile("명언으로 마무리"), add_quotes),
    (re.compile("내 말로 정리하기"), add_writing_box),
]


def build_docx(md_path, out_path):
    md_text = open(md_path, encoding="utf-8").read()
    title, sections = parse_sections(md_text)

    doc = docx.Document()
    style = doc.styles["Normal"]
    style.font.name = FONT
    style.font.size = Pt(11)
    rpr = style.element.get_or_add_rPr()
    rfonts = rpr.find(qn('w:rFonts'))
    if rfonts is None:
        rfonts = OxmlElement('w:rFonts')
        rpr.append(rfonts)
    rfonts.set(qn('w:eastAsia'), FONT)

    for section in doc.sections:
        section.top_margin = Cm(1.8)
        section.bottom_margin = Cm(1.8)
        section.left_margin = Cm(2.2)
        section.right_margin = Cm(2.2)

    # 제목 배너
    title_table = doc.add_table(rows=1, cols=1)
    tcell = title_table.rows[0].cells[0]
    set_cell_bg(tcell, NAVY_BG)
    set_cell_margins(tcell, top=260, bottom=260, left=300, right=300)
    tp = tcell.paragraphs[0]
    add_run(tp, title or "", size=20, bold=True, color=WHITE)
    doc.add_paragraph().paragraph_format.space_after = Pt(6)

    for header, body in sections:
        section_banner(doc, header)
        renderer = add_numbered_note
        for pattern, fn in SECTION_RENDERERS:
            if pattern.search(header):
                renderer = fn
                break
        renderer(doc, body)

    doc.save(out_path)
    print(f"저장됨: {out_path}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("md_path")
    ap.add_argument("-o", "--out", required=True)
    a = ap.parse_args()
    build_docx(a.md_path, a.out)
