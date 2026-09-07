#!/usr/bin/env python3
"""블록 스킴 마크다운 + 스타일 프로필(JSON) → 디자인된 Word(.docx).

`catechism_lesson_docx.py`를 일반화한 것이다. 두 가지가 달라졌다.

1. **색·폰트·여백이 코드에 없다.** 전부 `doc-styles/<name>.json`에서 읽는다.
   새 디자인을 만들려면 JSON 하나를 추가하면 되고 이 파일은 건드리지 않는다.
2. **섹션 제목을 보지 않는다.** 기존 렌더러는 "이 시간의 기대", "챌린지" 같은
   한국어 제목이 들어 있어야 전용 렌더러를 찾았고, 제목을 바꾸면 조용히 번호
   목록으로 떨어졌다. 이 렌더러는 제목 대신 **본문에 어떤 표시가 있는지**로
   판단하므로 어떤 주제·어떤 언어의 교재에도 그대로 쓸 수 있다.

## 블록 스킴

    # COVER              key: value 줄들 (순서대로 작은제목/큰제목/부제/배지)
    # <제목>              번호 없는 섹션 — 배너 없이 소제목으로
    # N. <제목>           번호 있는 섹션 — 배너로. 색은 프로필 banner_cycle 순환
    # FOOTER              한 줄 바닥글

    본문에서 쓰는 표시(있으면 그렇게 렌더링, 없으면 그냥 문단):
    ## 소제목             굵은 소제목
    [[BOX:제목]] … [[/BOX]]     제목이 붙은 강조 박스 (교리 확인, 핵심 정의 등)
    [[NOTE:제목]] … [[/NOTE]]   제목이 붙은 주의 박스 (읽기 주의, 경고 등)
    > 인용                왼쪽 선이 있는 콜아웃 박스
    문) / 답)             테두리 박스 안의 문답
    Q1. / A:              질문·답변 쌍 (라벨은 무엇이든 됨: 단서1./확인: 등)
    안내: / 나누기:        옅은 배경의 안내 박스
    → ...                 액센트 색 한 줄 안내
    1. / ① 항목           번호 목록
    - 항목                글머리 목록
    □ 항목                체크박스 목록 (문자는 프로필 decor.checkbox_char)
    "인용문" + — 출처      인용 박스
    [[WRITING_BOX:N]]     N줄 필기 칸 (밑줄)
    | a | b |             표
    [[TABLE:head+label+tall]]  바로 뒤 표 하나에만 적용 — head 머리 행 / label 라벨 열 /
                          tall 학생이 써 넣는 높은 칸. plain은 둘 다 끈다. 없으면 프로필 기본값

사용법:
    python3 lesson_docx.py <draft.md> -o <out.docx> [--style navy-catechism]
    python3 lesson_docx.py <draft.md> -o <out.docx> --style-file ../doc-styles/x.json
"""
import argparse
import json
import os
import re

import docx
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

STYLE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'doc-styles')

SECTION_NUM_RE = re.compile(r"^(\d+)\.\s*(.+)$")
QA_Q_RE = re.compile(r"^\S+\d+\.")
QA_A_RE = re.compile(r"^[^:：]{1,12}[:：]")
NUM_ITEM_RE = re.compile(r"^(?:\d+\.|[①-⑳])\s*(.+)$")
WRITING_RE = re.compile(r"\[\[WRITING_BOX:(\d+)\]\]")


# ---------- 스타일 ----------

def load_style(name=None, path=None):
    if path is None:
        path = os.path.join(STYLE_DIR, f"{name or 'navy-catechism'}.json")
    if not os.path.exists(path):
        available = sorted(f[:-5] for f in os.listdir(STYLE_DIR) if f.endswith('.json'))
        raise SystemExit(f"스타일을 찾을 수 없다: {path}\n쓸 수 있는 스타일: {', '.join(available)}")
    return json.load(open(path, encoding='utf-8'))


def rgb(hex_str):
    return RGBColor(int(hex_str[0:2], 16), int(hex_str[2:4], 16), int(hex_str[4:6], 16))


class Style:
    """프로필 JSON을 감싸 색/치수를 꺼내기 쉽게 한다."""

    def __init__(self, profile):
        self.p = profile
        self.pal = profile['palette']
        self.ts = profile['type_scale']
        self.sp = profile['spacing']
        self.decor = profile.get('decor', {})
        self.box = profile.get('box', {})

    def color(self, key):
        return rgb(self.pal[key])

    def hexc(self, key):
        return self.pal[key]

    def size(self, key):
        return self.ts[key]

    def banner_hex(self, position):
        cycle = self.p['banner_cycle']
        return cycle[(position - 1) % len(cycle)]

    @property
    def font(self):
        return self.p['font']['main']

    @property
    def heading_font(self):
        return self.p['font'].get('heading', self.font)


# ---------- 저수준 그리기 ----------

def set_font(run, st, size=None, bold=False, italic=False, color_hex=None, font=None):
    run.font.size = Pt(size if size is not None else st.size('body'))
    run.font.bold = bold
    run.font.italic = italic
    name = font or st.font
    run.font.name = name
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.find(qn('w:rFonts'))
    if rfonts is None:
        rfonts = OxmlElement('w:rFonts')
        rpr.append(rfonts)
    rfonts.set(qn('w:eastAsia'), name)
    if color_hex:
        run.font.color.rgb = rgb(color_hex)


def add_md_runs(p, text, st, **kw):
    """**굵게** 표시를 살려 여러 run으로 넣는다. 나머지 인라인 표시는 strip_md가 지운다."""
    parts = re.split(r'\*\*(.+?)\*\*', text)
    for idx, seg in enumerate(parts):
        if not seg:
            continue
        kw2 = dict(kw)
        if idx % 2 == 1:
            kw2['bold'] = True
            if 'strong_hex' in kw2:
                kw2['color_hex'] = kw2['strong_hex']
        kw2.pop('strong_hex', None)
        add_run(p, strip_md(seg), st, **kw2)
    if not parts:
        add_run(p, '', st, **{k: v for k, v in kw.items() if k != 'strong_hex'})


def add_run(p, text, st, **kw):
    r = p.add_run(text)
    set_font(r, st, **kw)
    return r


def set_cell_bg(cell, hex_color):
    tcpr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'), 'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'), hex_color)
    tcpr.append(shd)


def set_cell_margins(cell, margins):
    tcpr = cell._tc.get_or_add_tcPr()
    mar = OxmlElement('w:tcMar')
    for tag, val in zip(('top', 'bottom', 'left', 'right'), margins):
        el = OxmlElement(f'w:{tag}')
        el.set(qn('w:w'), str(val))
        el.set(qn('w:type'), 'dxa')
        mar.append(el)
    tcpr.append(mar)


def set_col_widths(table, ncol, pcts):
    """열 너비를 백분율로 못박는다. Word의 자동 배분이 라벨 열을 반쪽까지 늘리는 것을 막는다."""
    tblpr = table._tbl.tblPr
    layout = OxmlElement('w:tblLayout')
    layout.set(qn('w:type'), 'fixed')
    tblpr.append(layout)
    w = OxmlElement('w:tblW')
    w.set(qn('w:w'), '5000')
    w.set(qn('w:type'), 'pct')
    tblpr.append(w)
    for row in table.rows:
        for j, cell in enumerate(row.cells[:ncol]):
            tcw = cell._tc.get_or_add_tcPr().find(qn('w:tcW'))
            if tcw is None:
                tcw = OxmlElement('w:tcW')
                cell._tc.get_or_add_tcPr().append(tcw)
            tcw.set(qn('w:w'), str(int(pcts[j] * 50)))
            tcw.set(qn('w:type'), 'pct')


def no_split(table):
    """표(=박스·배너)가 페이지 경계에서 갈라지지 않게 한다."""
    for row in table.rows:
        trpr = row._tr.get_or_add_trPr()
        el = OxmlElement('w:cantSplit')
        trpr.append(el)


def set_borders(table, hex_color, sz=4, sides=('top', 'bottom', 'left', 'right')):
    tblpr = table._tbl.tblPr
    borders = OxmlElement('w:tblBorders')
    for side in ('top', 'left', 'bottom', 'right', 'insideH', 'insideV'):
        el = OxmlElement(f'w:{side}')
        if side in sides:
            el.set(qn('w:val'), 'single')
            el.set(qn('w:sz'), str(sz))
            el.set(qn('w:color'), hex_color)
        else:
            el.set(qn('w:val'), 'none')
        el.set(qn('w:space'), '0')
        borders.append(el)
    tblpr.append(borders)


def side_rule(p, hex_color, side='left', sz=18):
    pPr = p._p.get_or_add_pPr()
    pbdr = OxmlElement('w:pBdr')
    el = OxmlElement(f'w:{side}')
    el.set(qn('w:val'), 'single')
    el.set(qn('w:sz'), str(sz))
    el.set(qn('w:space'), '8')
    el.set(qn('w:color'), hex_color)
    pbdr.append(el)
    pPr.append(pbdr)


def box(doc, st, fill_key, bordered=None, border_key='box_border'):
    """1×1 표로 만든 색 박스. (table, cell) 반환."""
    table = doc.add_table(rows=1, cols=1)
    no_split(table)
    cell = table.rows[0].cells[0]
    set_cell_bg(cell, st.hexc(fill_key))
    set_cell_margins(cell, st.box.get('margins_dxa', [80, 80, 140, 140]))
    use_border = st.box.get('bordered', True) if bordered is None else bordered
    if use_border:
        set_borders(table, st.hexc(border_key))
    else:
        set_borders(table, 'FFFFFF', sides=())
    return table, cell


def spacer(doc, pt):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(0)
    p.paragraph_format.line_spacing = Pt(pt)


def para(doc, st, text, size=None, bold=False, italic=False, color_key='ink',
         before=None, after=None, indent_cm=None, align=None, font=None):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(st.sp['para_before_pt'] if before is None else before)
    p.paragraph_format.space_after = Pt(st.sp['para_after_pt'] if after is None else after)
    if indent_cm:
        p.paragraph_format.left_indent = Cm(indent_cm)
    if align:
        p.alignment = align
    add_md_runs(p, text, st, size=size, bold=bold, italic=italic,
                color_hex=st.hexc(color_key), font=font, strong_hex=st.hexc('heading'))
    return p


# ---------- 블록 파서 ----------

def parse_blocks(md_text):
    blocks, header, body = [], None, []
    for line in md_text.strip('\n').split('\n'):
        if line.startswith('# '):
            if header is not None:
                blocks.append((header, body))
            header, body = line[2:].strip(), []
        else:
            body.append(line)
    if header is not None:
        blocks.append((header, body))
    return blocks


def parse_kv(body):
    kv = []
    for line in body:
        if ':' in line and line.strip():
            k, v = line.split(':', 1)
            kv.append((k.strip(), v.strip()))
    return kv


def group_paragraphs(lines):
    """빈 줄로 끊어 문단 묶음 목록을 만든다."""
    groups, cur = [], []
    for line in lines:
        if line.strip():
            cur.append(line.strip())
        elif cur:
            groups.append(cur)
            cur = []
    if cur:
        groups.append(cur)
    return groups


# ---------- 조각 렌더러 ----------

def render_cover(doc, st, kv):
    """COVER의 key: value를 순서대로 작은제목 / 큰제목 / 부제 / 배지로 그린다."""
    kicker = kv[0][1] if len(kv) > 0 else ''
    title = kv[1][1] if len(kv) > 1 else ''
    sub = kv[2][1] if len(kv) > 2 else ''
    badges = [v for _, v in kv[3:]]

    left = st.decor.get('cover_align', 'center') == 'left'
    al = WD_ALIGN_PARAGRAPH.LEFT if left else WD_ALIGN_PARAGRAPH.CENTER

    if kicker:
        para(doc, st, kicker, size=st.size('cover_kicker'), bold=True,
             color_key='cover_kicker', after=2 if left else 8, align=al)

    if st.decor.get('cover_boxed', True):
        _, cell = box(doc, st, 'cover_bg', bordered=False)
        set_cell_margins(cell, [300, 300, 260, 260])
        p1 = cell.paragraphs[0]
        p1.alignment = al
        add_run(p1, title, st, size=st.size('cover_title'), bold=True,
                color_hex=st.hexc('cover_title'), font=st.heading_font)
        if sub:
            p2 = cell.add_paragraph()
            p2.alignment = al
            add_run(p2, sub, st, size=st.size('cover_sub'), color_hex=st.hexc('cover_sub'))
    else:
        para(doc, st, title, size=st.size('cover_title'), bold=True,
             color_key='cover_title', before=0, after=1, align=al, font=st.heading_font)
        if sub:
            para(doc, st, sub, size=st.size('cover_sub'), color_key='cover_sub',
                 before=0, after=0, align=al)

    spacer(doc, 6 if left else 12)
    for b in badges:
        para(doc, st, b, size=st.size('cover_badge'), bold=True, color_key='cover_badge',
             after=10, align=al)


def render_banner(doc, st, position, title):
    fill = st.banner_hex(position)
    if st.decor.get('banner_full_width', True):
        table = doc.add_table(rows=1, cols=1)
        cell = table.rows[0].cells[0]
        set_cell_bg(cell, fill)
        set_cell_margins(cell, [90, 90, 150, 150])
        set_borders(table, st.hexc('box_border'), sides=())
        p = cell.paragraphs[0]
        add_run(p, title, st, size=st.size('banner'), bold=True,
                color_hex=st.hexc('banner_text'), font=st.heading_font)
    else:
        # 색면 대신 얇은 밑줄 — scripture-classic처럼 활자로 위계를 만드는 스타일
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(st.sp['section_gap_pt'])
        p.paragraph_format.space_after = Pt(2)
        add_run(p, title, st, size=st.size('banner'), bold=True,
                color_hex=st.hexc('heading'), font=st.heading_font)
        rule = doc.add_paragraph()
        rule.paragraph_format.space_before = Pt(0)
        rule.paragraph_format.space_after = Pt(st.sp['banner_after_pt'])
        side_rule(rule, st.hexc('accent'), side='top', sz=8)


def render_qa_pairs(doc, st, lines):
    pairs, q, a = [], None, None
    for s in lines:
        if not s.strip():
            continue
        s = s.strip()
        if QA_Q_RE.match(s):
            if q is not None:
                pairs.append((q, a))
            q, a = s, None
        elif QA_A_RE.match(s):
            a = re.split(r'[:：]', s, maxsplit=1)[1].strip()
        elif a is not None:
            a += ' ' + s
    if q is not None:
        pairs.append((q, a))
    for q, a in pairs:
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(8)
        p.paragraph_format.space_after = Pt(3)
        add_run(p, re.sub(r'^(\S+\d+)\.\s*', r'\1.  ', q), st,
                size=st.size('body'), bold=True, color_hex=st.hexc('accent'))
        pa = doc.add_paragraph()
        pa.paragraph_format.left_indent = Cm(0.5)
        pa.paragraph_format.space_before = Pt(2)
        pa.paragraph_format.space_after = Pt(6)
        add_run(pa, a or '', st, size=st.size('body'), color_hex=st.hexc('ink'))


def render_table(doc, st, rows, mode=None):
    cells = [[c.strip() for c in r.strip().strip('|').split('|')] for r in rows]
    cells = [r for r in cells
             if not (any('-' in c for c in r) and all(set(c) <= set('-: ') for c in r))]
    if not cells:
        return
    ncol = max(len(r) for r in cells)
    head_row = st.decor.get('table_header_row', True)
    label_col = st.decor.get('table_label_col', False)
    tall_dxa = 0
    if mode:                       # [[TABLE:...]] 로 이 표만 따로 지정한 경우
        head_row = 'head' in mode
        label_col = 'label' in mode
        if 'tall' in mode:         # 학생이 칸 안에 써 넣는 표 — 빈 줄 높이를 준다
            tall_dxa = int(st.decor.get('table_tall_dxa', 900))
    head_fill = st.hexc('table_head_fill') if 'table_head_fill' in st.pal else st.hexc('box_fill')
    head_text = st.hexc('table_head_text') if 'table_head_text' in st.pal else st.hexc('heading')

    table = doc.add_table(rows=len(cells), cols=ncol)
    set_borders(table, st.hexc('box_border'))
    if label_col and ncol > 1:
        lab = float(st.decor.get('table_label_col_pct', 22))
        rest = (100.0 - lab) / (ncol - 1)
        set_col_widths(table, ncol, [lab] + [rest] * (ncol - 1))
    if tall_dxa:
        for r_i, row in enumerate(table.rows):
            if head_row and r_i == 0:
                continue
            trpr = row._tr.get_or_add_trPr()
            h = OxmlElement('w:trHeight')
            h.set(qn('w:val'), str(tall_dxa))
            h.set(qn('w:hRule'), 'atLeast')
            trpr.append(h)
    for i, row in enumerate(cells):
        for j in range(ncol):
            cell = table.rows[i].cells[j]
            set_cell_margins(cell, [60, 60, 100, 100])
            is_head = (head_row and i == 0) or (label_col and j == 0)
            if is_head:
                set_cell_bg(cell, head_fill if head_row and i == 0 else st.hexc('box_fill'))
            txt = row[j] if j < len(row) else ''
            p = cell.paragraphs[0]
            add_md_runs(p, txt, st, size=st.size('body') - 0.5, bold=is_head,
                        color_hex=(head_text if head_row and i == 0
                                   else st.hexc('heading') if is_head else st.hexc('ink')),
                        strong_hex=st.hexc('heading'))
    spacer(doc, st.sp['section_gap_pt'])


def strip_md(text, keep_strong=False):
    if not keep_strong:
        text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'`(.+?)`', r'\1', text)
    text = text.replace('<br/>', ' ').replace('\\_', '_')
    return text


def render_body(doc, st, lines):
    """본문을 표시 기호에 따라 그린다. 제목 문자열은 보지 않는다."""
    i = 0
    n = len(lines)
    qa_mode = False  # '## 소제목'을 만난 뒤부터는 Q&A 쌍으로 읽는다
    qa_buffer = []
    table_mode = None  # [[TABLE:...]] 로 다음 표 하나에만 적용

    def flush_qa():
        nonlocal qa_buffer
        if qa_buffer:
            render_qa_pairs(doc, st, qa_buffer)
            qa_buffer = []

    while i < n:
        raw = lines[i]
        s = raw.strip()

        if not s:
            i += 1
            continue

        # 소제목
        if s.startswith('## '):
            flush_qa()
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(st.sp['section_gap_pt'])
            p.paragraph_format.space_after = Pt(st.sp['para_after_pt'])
            add_run(p, s[3:].strip(), st, size=st.size('subhead'), bold=True,
                    color_hex=st.hexc('accent'), font=st.heading_font)
            qa_mode = True
            i += 1
            continue

        if qa_mode:
            qa_buffer.append(s)
            i += 1
            continue

        # 제목 있는 강조 박스 — [[BOX:제목]] … [[/BOX]] / [[NOTE:제목]] … [[/NOTE]]
        mbox = re.match(r'^\[\[(BOX|NOTE):(.*?)\]\]$', s)
        if mbox:
            kind, title = mbox.group(1), mbox.group(2).strip()
            inner = []
            i += 1
            while i < n and not re.match(rf'^\[\[/{kind}\]\]$', lines[i].strip()):
                inner.append(lines[i].rstrip())
                i += 1
            i += 1  # 닫는 표시를 건너뛴다
            fill = 'box_fill' if kind == 'BOX' else 'note_fill'
            border = 'box_border' if kind == 'BOX' else 'note_border'
            _, cell = box(doc, st, fill, bordered=True, border_key=border)
            first = True
            if title:
                p0 = cell.paragraphs[0]
                add_run(p0, title, st, size=st.size('body'), bold=True,
                        color_hex=st.hexc('heading'), font=st.heading_font)
                first = False
            for chunk in group_paragraphs(inner):
                # 박스 본문의 **굵게**는 add_md_runs가 살린다 — 여기서 지우면 핵심 문장 강조가 사라진다
                text = ' '.join(strip_md(c, keep_strong=True) for c in chunk)
                p = cell.paragraphs[0] if first else cell.add_paragraph()
                first = False
                # 성경 인용(「」)은 액센트 색으로 구별한다
                is_verse = text.startswith('「') or '」' in text[:40]
                vi = st.decor.get('verse_italic', True)
                add_md_runs(p, text, st, size=st.size('body'), italic=is_verse and vi,
                            color_hex=st.hexc('accent') if is_verse else st.hexc('ink'),
                            strong_hex=st.hexc('heading'))
            spacer(doc, st.sp['section_gap_pt'])
            continue

        # 표 — 바로 앞 줄의 [[TABLE:head|label|plain]] 로 이 표만 다르게 그린다
        mtm = re.match(r'^\[\[TABLE:(.*?)\]\]$', s)
        if mtm:
            table_mode = mtm.group(1).strip().lower() or 'plain'
            i += 1
            continue

        if s.startswith('|'):
            rows = []
            while i < n and lines[i].strip().startswith('|'):
                rows.append(lines[i])
                i += 1
            render_table(doc, st, rows, table_mode)
            table_mode = None
            continue

        # 필기 칸
        m = WRITING_RE.search(s)
        if m:
            for _ in range(int(m.group(1))):
                p = doc.add_paragraph()
                p.paragraph_format.space_before = Pt(4)
                p.paragraph_format.space_after = Pt(st.sp['writing_line_gap_pt'])
                side_rule(p, st.hexc('rule'), side='bottom', sz=4)
                add_run(p, ' ', st)
            i += 1
            continue

        # 문답 박스
        if s.startswith('문)') or s.startswith('답)'):
            qbox = []
            while i < n and lines[i].strip() and (
                    lines[i].strip().startswith(('문)', '답)')) or not lines[i].strip().startswith('#')):
                qbox.append(lines[i].strip())
                i += 1
                if i < n and not lines[i].strip():
                    break
            spacer(doc, 4)
            _, cell = box(doc, st, 'box_fill', bordered=True)
            first = True
            for line in qbox:
                p = cell.paragraphs[0] if first else cell.add_paragraph()
                first = False
                add_run(p, strip_md(line), st, size=st.size('body'),
                        bold=line.startswith('문)'), color_hex=st.hexc('heading'))
            spacer(doc, 4)
            continue

        # 인용(콜아웃)
        if s.startswith('> '):
            quote = []
            while i < n and lines[i].strip().startswith('>'):
                quote.append(lines[i].strip().lstrip('>').strip())
                i += 1
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(st.sp['para_before_pt'])
            p.paragraph_format.space_after = Pt(st.sp['para_after_pt'])
            p.paragraph_format.left_indent = Cm(0.3)
            side_rule(p, st.hexc('accent'), side='left', sz=18)
            add_md_runs(p, ' '.join(q for q in quote if q), st, size=st.size('body'),
                        italic=st.decor.get('verse_italic', True),
                        color_hex=st.hexc('quote_text'), strong_hex=st.hexc('heading'))
            i += 1 if i < n else 0
            continue

        # 안내 박스
        if re.match(r'^(안내|나누기)[:：]', s):
            label, text = re.split(r'[:：]', s, maxsplit=1)
            _, cell = box(doc, st, 'note_fill', bordered=True, border_key='note_border')
            p0 = cell.paragraphs[0]
            add_run(p0, label.strip(), st, size=st.size('body'), bold=True,
                    color_hex=st.hexc('heading'))
            p1 = cell.add_paragraph()
            add_run(p1, strip_md(text.strip()), st, size=st.size('body'),
                    color_hex=st.hexc('ink'))
            spacer(doc, 4)
            i += 1
            continue

        # 화살표 한 줄 안내
        if s.startswith('→'):
            para(doc, st, strip_md(s), size=st.size('body'), color_key='accent', after=6)
            i += 1
            continue

        # 체크박스 목록
        if s.startswith(('□', '☐')):
            while i < n and lines[i].strip().startswith(('□', '☐')):
                item = lines[i].strip().lstrip('□☐').strip()
                p = doc.add_paragraph()
                p.paragraph_format.space_before = Pt(4)
                p.paragraph_format.space_after = Pt(4)
                add_run(p, st.decor.get('checkbox_char', '☐') + '  ', st,
                        size=st.size('body'), bold=True,
                        color_hex=st.decor.get('checkbox_color', st.hexc('accent')))
                add_md_runs(p, item, st, size=st.size('body'), color_hex=st.hexc('ink'),
                            strong_hex=st.hexc('heading'))
                i += 1
            continue

        # 인용문 + 출처 (— 로 시작하는 줄이 뒤따르는 묶음)
        if i + 1 < n and lines[i + 1].strip().startswith('—'):
            _, cell = box(doc, st, 'quote_fill', bordered=False)
            p0 = cell.paragraphs[0]
            add_run(p0, strip_md(s), st, size=st.size('quote'), italic=True,
                    color_hex=st.hexc('quote_text'))
            p1 = cell.add_paragraph()
            p1.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            add_run(p1, strip_md(lines[i + 1].strip()), st, size=st.size('quote_attr'),
                    bold=True, color_hex=st.hexc('quote_attr'))
            spacer(doc, st.sp['section_gap_pt'])
            i += 2
            continue

        # 번호 목록 — 원 번호(①②③)는 글쓴이가 매긴 것이므로 그대로 두고,
        # "1." 형식만 렌더러가 다시 매긴다 (중간에 다른 블록이 끼어도 이어지도록)
        if NUM_ITEM_RE.match(s):
            k = 1
            while i < n and NUM_ITEM_RE.match(lines[i].strip()):
                raw_item = lines[i].strip()
                m_item = NUM_ITEM_RE.match(raw_item)
                item = m_item.group(1)
                marker = raw_item[0] if raw_item[0] in '①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳' else f'{k}.'
                p = doc.add_paragraph()
                p.paragraph_format.space_before = Pt(4)
                p.paragraph_format.space_after = Pt(4)
                add_run(p, f'{marker}  ', st, size=st.size('body'),
                        bold=st.decor.get('list_number_bold', True), color_hex=st.hexc('accent'))
                add_md_runs(p, item, st, size=st.size('body'), color_hex=st.hexc('ink'),
                            strong_hex=st.hexc('heading'))
                k += 1
                i += 1
            continue

        # 글머리 목록
        if s.startswith(('- ', '* ')):
            while i < n and lines[i].strip().startswith(('- ', '* ')):
                item = lines[i].strip()[2:]
                p = doc.add_paragraph()
                p.paragraph_format.space_before = Pt(3)
                p.paragraph_format.space_after = Pt(3)
                p.paragraph_format.left_indent = Cm(0.4)
                add_run(p, '•  ', st, size=st.size('body'), bold=True, color_hex=st.hexc('accent'))
                add_md_runs(p, item, st, size=st.size('body'), color_hex=st.hexc('ink'),
                            strong_hex=st.hexc('heading'))
                i += 1
            continue

        # 그 밖에는 문단 — 빈 줄까지 이어 붙인다
        chunk = []
        while i < n and lines[i].strip() and not lines[i].strip().startswith(
                ('#', '|', '>', '□', '☐', '→', '- ', '* ')):
            chunk.append(lines[i].strip())
            i += 1
        if chunk:
            para(doc, st, ' '.join(chunk), size=st.size('body'))

    flush_qa()


def render_footer(doc, st, body):
    text = next((l.strip() for l in body if l.strip()), '')
    para(doc, st, strip_md(text), size=st.size('footer'), color_key='footer',
         before=st.sp['section_gap_pt'], after=0, align=WD_ALIGN_PARAGRAPH.CENTER)


# ---------- 빌드 ----------

def setup_document(style):
    """빈 Document를 만들어 기본 글꼴·여백을 프로필대로 세팅한다. 합본에서도 재사용."""
    st = Style(style)
    doc = docx.Document()
    normal = doc.styles['Normal']
    normal.font.name = st.font
    normal.font.size = Pt(st.size('body'))
    rpr = normal.element.get_or_add_rPr()
    rfonts = rpr.find(qn('w:rFonts'))
    if rfonts is None:
        rfonts = OxmlElement('w:rFonts')
        rpr.append(rfonts)
    rfonts.set(qn('w:eastAsia'), st.font)

    m = style['page']['margins_cm']
    for section in doc.sections:
        section.top_margin = Cm(m['top'])
        section.bottom_margin = Cm(m['bottom'])
        section.left_margin = Cm(m['left'])
        section.right_margin = Cm(m['right'])
    return doc, st


def render_lesson(doc, st, md_text):
    """한 과의 블록 전체를 이미 만들어진 doc에 이어서 그린다. 배너 순번은 과마다 새로 센다."""
    blocks = parse_blocks(md_text)
    position = 0
    for header, body in blocks:
        if header == 'COVER':
            render_cover(doc, st, parse_kv(body))
        elif header == 'FOOTER':
            render_footer(doc, st, body)
        else:
            mnum = SECTION_NUM_RE.match(header)
            if mnum:
                position += 1
                fmt = st.decor.get('banner_number_format', '{n}.  {t}')
                render_banner(doc, st, position,
                              fmt.format(n=mnum.group(1), t=mnum.group(2)))
            else:
                para(doc, st, header, size=st.size('banner'), bold=True, color_key='heading',
                     before=st.sp['section_gap_pt'], after=st.sp['banner_after_pt'])
            render_body(doc, st, body)


def add_page_break(doc):
    """다음 내용을 새 면에서 시작하게 한다.

    빈 문단에 w:br을 넣는 방식은 그 문단 자체가 앞 면에 들어가지 못하면 빈 면
    하나를 더 만든다. 그래서 문단에 pageBreakBefore를 걸고 높이를 1pt로 줄인다.
    """
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(0)
    p.paragraph_format.page_break_before = True
    p.add_run().font.size = Pt(1)


def build(md_path, out_path, style):
    doc, st = setup_document(style)
    md_text = open(md_path, encoding='utf-8').read()
    render_lesson(doc, st, md_text)
    doc.save(out_path)
    return out_path


def main():
    ap = argparse.ArgumentParser(description='블록 스킴 마크다운을 스타일 프로필로 Word로 바꾼다.')
    ap.add_argument('md_path')
    ap.add_argument('-o', '--out', required=True)
    ap.add_argument('--style', default='navy-catechism', help='doc-styles/<이름>.json')
    ap.add_argument('--style-file', help='프로필 JSON 경로를 직접 지정')
    a = ap.parse_args()

    style = load_style(a.style, a.style_file)
    out = build(a.md_path, a.out, style)
    print(f"저장됨: {out}  (스타일: {style['name']})")


if __name__ == '__main__':
    main()
