#!/usr/bin/env python3
"""BookDocument → .typ 소스 생성기 (TypstAdapter).

**설계 원칙:** Typst 마크업을 문자열로 조립하지 않는다. 문서를 Typst **데이터 리터럴**(dict/array)로
직렬화하고 템플릿 함수 하나를 호출한다.

    #import "/templates/typst/workbook/junior/main.typ": render-book
    #let doc = ( metadata: (..), page: (..), theme: (..), pages: (..) )
    #render-book(doc)

이렇게 하면
  1) 사용자 텍스트가 Typst 코드로 해석될 위험이 사라진다(이스케이프 = 문자열 리터럴 이스케이프뿐).
  2) 레이아웃 지식이 전부 템플릿(.typ)에 남는다 → 콘텐츠/레이아웃/렌더러 분리(요청서 §3).
  3) 같은 데이터로 템플릿만 바꿔 다른 판형·디자인을 낼 수 있다.
"""
from __future__ import annotations

import os
from typing import Any, Dict, List

from .model import BookDocument, Block
from .theme import load_profile, to_typst_theme, check_fonts

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE_ROOT = os.path.join(REPO_ROOT, 'templates', 'typst')


# ---------------------------------------------------------------- 리터럴 직렬화

def q(s: Any) -> str:
    """Typst 문자열 리터럴. 백슬래시와 인용부호만 이스케이프하면 안전하다."""
    t = '' if s is None else str(s)
    t = t.replace('\\', '\\\\').replace('"', '\\"')
    t = t.replace('\r\n', '\n').replace('\r', '\n').replace('\n', '\\n')
    return f'"{t}"'


def lit(v: Any, indent: int = 0) -> str:
    """파이썬 값 → Typst 리터럴 (dict/list/str/num/bool/None)."""
    pad = '  ' * indent
    if v is None:
        return 'none'
    if isinstance(v, bool):
        return 'true' if v else 'false'
    if isinstance(v, (int, float)):
        return repr(v)
    if isinstance(v, str):
        return q(v)
    if isinstance(v, (list, tuple)):
        if not v:
            return '()'
        inner = ',\n'.join(f'{pad}  {lit(x, indent + 1)}' for x in v)
        trail = ',' if len(v) == 1 else ''      # 1-원소 배열은 후행 콤마 필수
        return f'(\n{inner}{trail}\n{pad})'
    if isinstance(v, dict):
        if not v:
            return '(:)'
        parts = []
        for k, val in v.items():
            key = str(k)
            if not key.replace('-', '').replace('_', '').isalnum():
                raise ValueError(f'Typst 키로 쓸 수 없는 이름: {key!r}')
            parts.append(f'{pad}  {key}: {lit(val, indent + 1)}')
        return '(\n' + ',\n'.join(parts) + f',\n{pad})'
    raise TypeError(f'직렬화할 수 없는 값: {type(v).__name__}')


# ---------------------------------------------------------------- 자산 해결

class AssetError(Exception):
    pass


def resolve_asset(doc: BookDocument, src: str) -> str:
    """이미지 경로를 typst --root 기준 절대경로(/로 시작)로 바꾼다."""
    if not src:
        raise AssetError('빈 이미지 경로')
    if src.startswith('/'):
        cand = os.path.join(REPO_ROOT, src.lstrip('/'))
    else:
        base = doc.assets_root or ''
        if base and not os.path.isabs(base):
            # 상대 assets_root는 문서 파일 위치 기준으로 푼다(cwd 기준이 아니다)
            anchor = os.path.dirname(os.path.abspath(doc.source)) if doc.source else REPO_ROOT
            base = os.path.join(anchor, base)
        if not base:
            base = os.path.dirname(os.path.abspath(doc.source)) if doc.source else REPO_ROOT
        cand = os.path.join(base, src)
    cand = os.path.abspath(cand)
    if not os.path.isfile(cand):
        raise AssetError(f'이미지를 찾을 수 없다: {src} (찾은 위치: {cand})')
    if not cand.startswith(REPO_ROOT):
        raise AssetError(f'저장소 밖의 이미지는 쓸 수 없다(typst --root 제약): {cand}')
    rel = os.path.relpath(cand, REPO_ROOT).replace(os.sep, '/')
    return '/' + rel


# ---------------------------------------------------------------- 블록 → 데이터

def block_data(doc: BookDocument, b: Block, warnings: List[str]) -> Dict[str, Any]:
    d: Dict[str, Any] = {'kind': b.kind}
    if b.text:
        d['text'] = b.text
    if b.label:
        d['label'] = b.label
    if b.items:
        d['items'] = list(b.items)
    if b.head:
        d['head'] = list(b.head)
    if b.rows:
        d['rows'] = [list(r) for r in b.rows]
    if b.ref:
        d['ref'] = b.ref
    if b.variant:
        d['variant'] = b.variant
    if b.kind == 'heading':
        d['level'] = int(b.level)
    if b.kind in ('writing', 'spacer'):
        d['count'] = int(b.count)
    if b.kind == 'image':
        try:
            d['src'] = resolve_asset(doc, b.src)
        except AssetError as e:
            warnings.append(str(e))
            d['missing'] = True
            d['src'] = ''
            d['alt'] = b.attrs.get('alt', b.text or b.src)
        # 요청서 §8 이미지 속성
        d['role'] = b.role
        d['fit'] = b.fit
        for k in ('position', 'caption', 'alt', 'bleed', 'crop', 'radius', 'width', 'height'):
            if k in b.attrs:
                d[k] = b.attrs[k]
    # 그 밖의 부가 속성은 attrs로 통째로 넘긴다(템플릿이 알면 쓰고 모르면 무시).
    # attrs 안에 중첩된 그림(패널·캐릭터·암송 삽화)의 src도 같은 규칙으로 해결한다.
    extra = {k: v for k, v in b.attrs.items() if k not in d}
    if extra:
        d['attrs'] = _resolve_nested_assets(doc, extra, warnings)
    return d


def _resolve_nested_assets(doc: BookDocument, value, warnings: List[str]):
    """중첩 dict/list를 훑어 'src'를 가진 dict의 경로를 해결한다(깊이 무관)."""
    if isinstance(value, dict):
        out = {k: _resolve_nested_assets(doc, v, warnings) for k, v in value.items()}
        if 'src' in out and isinstance(out['src'], str) and out['src'] and not out['src'].startswith('/'):
            try:
                out['src'] = resolve_asset(doc, out['src'])
            except AssetError as e:
                warnings.append(str(e))
                out['missing'] = True
                out['src'] = ''
        return out
    if isinstance(value, (list, tuple)):
        return [_resolve_nested_assets(doc, v, warnings) for v in value]
    return value


def template_path(template: str) -> str:
    """'workbook/junior' → '/templates/typst/workbook/junior/main.typ' (typst --root 기준)."""
    t = template.strip('/')
    fs = os.path.join(TEMPLATE_ROOT, *t.split('/'), 'main.typ')
    if not os.path.isfile(fs):
        avail = []
        for root, _dirs, files in os.walk(TEMPLATE_ROOT):
            if 'main.typ' in files:
                avail.append(os.path.relpath(root, TEMPLATE_ROOT).replace(os.sep, '/'))
        raise FileNotFoundError(
            f'템플릿을 찾을 수 없다: {template}\n쓸 수 있는 템플릿: {", ".join(sorted(avail)) or "(없음)"}')
    return '/templates/typst/' + t + '/main.typ'


def document_data(doc: BookDocument) -> tuple[Dict[str, Any], List[str]]:
    warnings: List[str] = list(doc.warnings)
    profile = load_profile(doc.theme)
    theme = to_typst_theme(profile)
    fw, _usable = check_fonts(theme)
    warnings.extend(fw)

    w_mm, h_mm = doc.dimensions_mm()
    ps = doc.page_setup
    data = {
        'metadata': {
            'title': doc.metadata.title,
            'subtitle': doc.metadata.subtitle,
            'kicker': doc.metadata.kicker,
            'badge': doc.metadata.badge,
            'footer': doc.metadata.footer,
            'grade': doc.metadata.grade,
            'unit': doc.metadata.unit,
            'department': doc.metadata.department,
            'lesson_no': doc.metadata.lesson_no,
            # 어댑터가 넣은 부가 정보(mode·sensitivity 등). 템플릿이 알면 쓰고 모르면 무시한다.
            'extra': {str(k): v for k, v in (doc.metadata.extra or {}).items()
                      if isinstance(v, (str, int, float, bool))},
        },
        'page': {
            'width_mm': w_mm, 'height_mm': h_mm,
            'margin_top_mm': ps.margin_top_mm, 'margin_bottom_mm': ps.margin_bottom_mm,
            'margin_inside_mm': ps.margin_inside_mm, 'margin_outside_mm': ps.margin_outside_mm,
            'gutter_mm': ps.gutter_mm, 'bleed_mm': ps.bleed_mm,
            'facing_pages': ps.facing_pages, 'page_numbers': ps.page_numbers,
        },
        'theme': theme,
        'pages': [
            {
                'layout': p.layout or 'flow',
                'title': p.title,
                'attrs': p.attrs or {},
                'blocks': [block_data(doc, b, warnings) for b in p.blocks],
            }
            for p in doc.pages
        ],
    }
    return data, warnings


def generate(doc: BookDocument) -> tuple[str, List[str]]:
    """(.typ 소스, 경고 목록)."""
    data, warnings = document_data(doc)
    tpl = template_path(doc.template)
    src = '\n'.join([
        '// 이 파일은 textbuilder/typst_gen.py가 생성했다. 직접 고치지 마라.',
        f'// 원본: {doc.source or "(메모리)"} · 템플릿: {doc.template} · 테마: {doc.theme}',
        f'#import {q(tpl)}: render-book',
        '',
        '#let doc = ' + lit(data),
        '',
        '#render-book(doc)',
        '',
    ])
    return src, warnings
