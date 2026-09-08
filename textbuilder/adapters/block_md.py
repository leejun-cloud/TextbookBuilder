#!/usr/bin/env python3
"""어댑터 (A): 레거시 블록 스킴 마크다운 → BookDocument.

기존 문서를 **읽기만** 한다. 원본을 고치거나 마이그레이션하지 않는다.
지원하지 못한 표시는 doc.warnings에 남겨 사람이 볼 수 있게 한다(조용한 손실 금지).

블록 스킴 명세는 docs/typst-integration-analysis.md §2(A) 참조.
"""
from __future__ import annotations

import os
import re
from typing import List

from ..model import BookDocument, Metadata, Page, Block, blk

RE_SECTION_NUM = re.compile(r'^(\d+)\.\s*(.+)$')
RE_BOX_OPEN = re.compile(r'^\[\[(BOX|NOTE):(.*?)\]\]$')
RE_BOX_CLOSE = re.compile(r'^\[\[/(BOX|NOTE)\]\]$')
RE_WRITING = re.compile(r'^\[\[WRITING_BOX:(\d+)\]\]$')
RE_TABLE_MARK = re.compile(r'^\[\[TABLE:(.*?)\]\]$')
RE_ANY_MARK = re.compile(r'^\[\[.*?\]\]$')
RE_KV = re.compile(r'^([^:]{1,20}):\s*(.*)$')


def _split_row(line: str) -> List[str]:
    cells = [c.strip() for c in line.strip().strip('|').split('|')]
    return cells


def _clean_inline(s: str) -> str:
    """인라인 표시를 의미만 남겨 정리한다. 굵게/코드 표시는 템플릿이 다루지 않으므로 벗긴다."""
    s = re.sub(r'\*\*(.+?)\*\*', r'\1', s)
    s = re.sub(r'`(.+?)`', r'\1', s)
    s = s.replace('<br/>', ' ').replace('\\_', '_')
    return s.strip()


def parse(path: str, *, theme: str = '', template: str = 'book/standard',
          page_size: str = 'B5') -> BookDocument:
    with open(path, encoding='utf-8') as f:
        text = f.read()

    doc = BookDocument(theme=theme or 'doctrine-stage3', template=template, source=os.path.abspath(path))
    doc.page_setup.size = page_size
    doc.assets_root = os.path.dirname(os.path.abspath(path))

    # 1) '# 헤더' 단위로 자른다 (기존 parse_blocks와 같은 규칙)
    sections: List[tuple[str, List[str]]] = []
    cur_h, cur_b = None, []
    for line in text.strip('\n').split('\n'):
        if line.startswith('# '):
            if cur_h is not None:
                sections.append((cur_h, cur_b))
            cur_h, cur_b = line[2:].strip(), []
        else:
            cur_b.append(line)
    if cur_h is not None:
        sections.append((cur_h, cur_b))

    page = Page(layout='flow')
    doc.pages.append(page)

    for header, body in sections:
        if header == 'COVER':
            for line in body:
                m = RE_KV.match(line.strip())
                if not m:
                    continue
                k, v = m.group(1).strip(), _clean_inline(m.group(2))
                if k in ('작은제목', '과'):
                    doc.metadata.kicker = doc.metadata.kicker or v
                elif k in ('큰제목', '대주제'):
                    doc.metadata.title = doc.metadata.title or v
                elif k in ('부제',):
                    doc.metadata.subtitle = v
                elif k in ('배지',):
                    doc.metadata.badge = v
                else:
                    doc.metadata.extra[k] = v
            continue

        if header == 'FOOTER':
            doc.metadata.footer = _clean_inline(' '.join(l.strip() for l in body if l.strip()))
            continue

        # 섹션 제목 → heading 블록
        m = RE_SECTION_NUM.match(header)
        if m:
            page.blocks.append(blk('heading', text=_clean_inline(m.group(2)),
                                   label=m.group(1), level=2, variant='banner'))
        else:
            page.blocks.append(blk('heading', text=_clean_inline(header), level=3))

        page.blocks.extend(_parse_body(body, doc.warnings, header))

    doc.warnings = _dedupe(doc.warnings)
    if not doc.metadata.title:
        doc.metadata.title = os.path.basename(os.path.dirname(os.path.abspath(path))) or 'document'
    return doc


def _parse_body(body: List[str], warnings: List[str], where: str) -> List[Block]:
    out: List[Block] = []
    i, n = 0, len(body)
    para: List[str] = []
    pending_table_variant = ''

    def flush_para():
        if para:
            t = _clean_inline(' '.join(x.strip() for x in para if x.strip()))
            if t:
                out.append(blk('text', text=t))
            para.clear()

    while i < n:
        raw = body[i]
        s = raw.strip()

        if not s:
            flush_para()
            i += 1
            continue

        m = RE_BOX_OPEN.match(s)
        if m:
            flush_para()
            kind_mark, title = m.group(1), _clean_inline(m.group(2))
            inner: List[str] = []
            i += 1
            while i < n and not RE_BOX_CLOSE.match(body[i].strip()):
                inner.append(body[i])
                i += 1
            i += 1
            chunks, cur = [], []
            for ln in inner:
                if ln.strip():
                    cur.append(ln.strip())
                elif cur:
                    chunks.append(' '.join(cur)); cur = []
            if cur:
                chunks.append(' '.join(cur))
            texts = [_clean_inline(c) for c in chunks if _clean_inline(c)]
            first = texts[0] if texts else ''
            variant = 'note' if kind_mark == 'NOTE' else ('verse' if first.startswith('「') else 'box')
            b = blk('callout' if variant != 'verse' else 'verse',
                    label=title, text=first, items=texts[1:], variant=variant)
            out.append(b)
            continue

        m = RE_WRITING.match(s)
        if m:
            flush_para()
            out.append(blk('writing', count=int(m.group(1))))
            i += 1
            continue

        m = RE_TABLE_MARK.match(s)
        if m:
            flush_para()
            pending_table_variant = m.group(1)
            i += 1
            continue

        if s.startswith('|'):
            flush_para()
            rows = []
            while i < n and body[i].strip().startswith('|'):
                cells = _split_row(body[i])
                if not all(re.fullmatch(r'-{2,}|:?-+:?', c or '-') for c in cells):
                    rows.append([_clean_inline(c) for c in cells])
                i += 1
            variant = pending_table_variant or 'plain'
            pending_table_variant = ''
            head, rest = ([], rows)
            if 'head' in variant and rows:
                head, rest = rows[0], rows[1:]
            out.append(blk('table', head=head, rows=rest, variant=variant))
            continue

        if RE_ANY_MARK.match(s):
            warnings.append(f'[{where}] 알 수 없는 블록 표시를 건너뛴다: {s[:40]}')
            i += 1
            continue

        if s.startswith('□'):
            flush_para()
            items = []
            while i < n and body[i].strip().startswith('□'):
                items.append(_clean_inline(body[i].strip().lstrip('□').strip()))
                i += 1
            out.append(blk('checklist', items=items))
            continue

        if s.startswith('>'):
            flush_para()
            out.append(blk('callout', text=_clean_inline(s.lstrip('>').strip()), variant='aside'))
            i += 1
            continue

        if s.startswith('→'):
            flush_para()
            out.append(blk('text', text=_clean_inline(s.lstrip('→').strip()), variant='accent'))
            i += 1
            continue

        if s.startswith('문)'):
            flush_para()
            qtext = _clean_inline(s[2:].strip())
            ans = ''
            if i + 1 < n and body[i + 1].strip().startswith('답)'):
                ans = _clean_inline(body[i + 1].strip()[2:].strip())
                i += 1
            out.append(blk('question', text=qtext, label=ans, variant='qa'))
            i += 1
            continue

        para.append(raw)
        i += 1

    flush_para()
    return out


def _dedupe(xs: List[str]) -> List[str]:
    seen, out = set(), []
    for x in xs:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out
