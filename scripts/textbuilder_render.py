#!/usr/bin/env python3
"""TextBuilder 렌더 CLI — 하나의 문서를 여러 출력 엔진으로 낸다.

    # 유년부 교재 JSON → B5 PDF (Typst)
    python3 scripts/textbuilder_render.py projects/.../lesson.json \
        --renderer typst --template workbook/junior --theme kids-junior \
        --page-size B5 -o build/유년부_1과.pdf

    # 레거시 블록 스킴 md → 기존 docx 경로 그대로
    python3 scripts/textbuilder_render.py projects/.../draft.md --renderer legacy -o out.docx

    # 미리보기 PNG (2쪽만)
    python3 scripts/textbuilder_render.py in.json --preview --pages 2 -o build/preview.png

    # 무엇을 쓸 수 있는지
    python3 scripts/textbuilder_render.py --list
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from textbuilder import load, RenderOptions, available_renderers, resolve_renderer  # noqa: E402
from textbuilder.theme import list_themes  # noqa: E402
from textbuilder.typst_gen import TEMPLATE_ROOT, generate  # noqa: E402


def list_templates():
    out = []
    for root, _dirs, files in os.walk(TEMPLATE_ROOT):
        if 'main.typ' in files:
            out.append(os.path.relpath(root, TEMPLATE_ROOT).replace(os.sep, '/'))
    return sorted(out)


def main():
    ap = argparse.ArgumentParser(description='TextBuilder 렌더 CLI')
    ap.add_argument('input', nargs='?', help='블록 스킴 .md 또는 콘텐츠/모델 .json')
    ap.add_argument('-o', '--out', default='', help='산출 경로 (.pdf/.png/.docx)')
    ap.add_argument('--renderer', default='typst', help='typst | legacy (기본 typst)')
    ap.add_argument('--fallback', default='', help='주 렌더러 불가 시 대체 렌더러')
    ap.add_argument('--template', default='', help='예: workbook/junior, book/standard')
    ap.add_argument('--theme', default='', help='doc-styles/<이름>.json')
    ap.add_argument('--page-size', default='', help='A4|A5|B5|210x210|6x9in')
    ap.add_argument('--font', default='', help='본문 폰트 강제 지정')
    ap.add_argument('--preview', action='store_true', help='PNG 미리보기')
    ap.add_argument('--final', action='store_true', help='최종 PDF: 경고 차단 + 실제 PDF 사후검사')
    ap.add_argument('--min-image-dpi', type=float, default=150, help='최종 PDF 이미지 최소 해상도')
    ap.add_argument('--expected-pages', type=int, help='최종 PDF의 예상 실제 쪽수 (표지 포함)')
    ap.add_argument('--pages', default='', help='렌더할 쪽 (예: 1,3)')
    ap.add_argument('--ppi', type=int, default=144)
    ap.add_argument('--keep-source', action='store_true', help='생성된 .typ 보존')
    ap.add_argument('--dump-model', default='', help='정규화 모델 JSON을 이 경로에 쓴다')
    ap.add_argument('--dump-typst', default='', help='생성된 .typ 소스를 이 경로에 쓴다')
    ap.add_argument('--list', action='store_true', help='렌더러·템플릿·테마 목록')
    ap.add_argument('--timeout', type=int, default=120)
    a = ap.parse_args()

    if a.list:
        print('렌더러:')
        for name, (ok, why) in available_renderers().items():
            print(f'  {"✓" if ok else "✗"} {name:8} {why}')
        print('\n템플릿:')
        for t in list_templates():
            print(f'  {t}')
        print('\n테마 (doc-styles/):')
        for t in list_themes():
            print(f'  {t}')
        return 0

    if not a.input:
        ap.error('입력 파일이 필요하다 (또는 --list)')
    if a.final and (a.preview or a.pages or a.renderer != 'typst' or a.fallback):
        ap.error('--final은 typst 전체 PDF 출력에만 사용할 수 있다 (미리보기·부분출력·fallback 불가)')

    kw = {}
    if a.theme:
        kw['theme'] = a.theme
    if a.template:
        kw['template'] = a.template
    if a.page_size:
        kw['page_size'] = a.page_size
    doc = load(a.input, **kw)
    if a.font:
        doc.metadata.extra['font_override'] = a.font

    if a.dump_model:
        os.makedirs(os.path.dirname(os.path.abspath(a.dump_model)) or '.', exist_ok=True)
        with open(a.dump_model, 'w', encoding='utf-8') as f:
            f.write(doc.to_json())
        print(f'모델 저장: {a.dump_model}')

    if a.dump_typst:
        src, warns = generate(doc)
        os.makedirs(os.path.dirname(os.path.abspath(a.dump_typst)) or '.', exist_ok=True)
        with open(a.dump_typst, 'w', encoding='utf-8') as f:
            f.write(src)
        print(f'Typst 소스 저장: {a.dump_typst}')
        for w in warns:
            print(f'  경고 {w}')

    problems = doc.validate()
    for p in problems:
        print(f'  점검 {p}', file=sys.stderr)
    if a.final and problems:
        return 1

    renderer, notes = resolve_renderer(a.renderer, a.fallback or a.renderer)
    for n in notes:
        print(f'  {n}', file=sys.stderr)

    fmt = 'png' if a.preview else ('docx' if renderer.name == 'legacy' else
                                   os.path.splitext(a.out)[1].lstrip('.').lower() or 'pdf')
    opts = RenderOptions(
        out_path=a.out, fmt=fmt, ppi=a.ppi, keep_source=a.keep_source, timeout_sec=a.timeout,
        final=a.final, extra={'min_image_dpi': a.min_image_dpi, 'expected_pages': a.expected_pages},
        pages=[int(x) for x in a.pages.split(',') if x.strip()] if a.pages else None)

    res = renderer.preview(doc, opts) if a.preview else renderer.render(doc, opts)

    for w in res.warnings:
        print(f'  경고 {w}', file=sys.stderr)
    if res.ok:
        print(f'{renderer.name} · {res.summary()}')
        for o in res.outputs:
            print(f'  → {o}')
        if res.source_path:
            print(f'  소스 {res.source_path}')
        if res.meta:
            print('  ' + json.dumps(res.meta, ensure_ascii=False))
        return 0
    print(f'{renderer.name} · 실패', file=sys.stderr)
    for e in res.errors:
        print(f'  오류 {e}', file=sys.stderr)
    if res.source_path:
        print(f'  소스 {res.source_path}', file=sys.stderr)
    return 1


if __name__ == '__main__':
    sys.exit(main())

