#!/usr/bin/env python3
"""테마 = 기존 `doc-styles/<이름>.json` 프로필. 새 포맷을 만들지 않는다.

CLAUDE.md 고정 규칙("디자인은 코드에 박지 않는다. JSON을 추가해 만든다")을 그대로 따르므로
기존 11종 프로필이 Typst에서도 그대로 살아난다. 프로필에 없는 값은 여기서 기본값을 채운다.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from typing import Any, Dict, List, Tuple

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STYLES_DIR = os.path.join(REPO_ROOT, 'doc-styles')

# 한글 폰트 폴백 체인 — 파일을 저장소에 넣지 않고 이름만 참조한다(라이선스 회피).
KO_FALLBACK = ['Apple SD Gothic Neo', 'NanumGothic', 'Noto Sans KR', 'Malgun Gothic', 'NanumBarunGothic']

DEFAULTS: Dict[str, Any] = {
    'type_scale': {
        'cover_kicker': 9, 'cover_title': 20, 'cover_sub': 10, 'cover_badge': 9.5,
        'banner': 12.5, 'subhead': 11.5, 'body': 10, 'quote': 10, 'quote_attr': 9, 'footer': 8.5,
    },
    'palette': {
        'ink': '3A3A3A', 'heading': '1F3864', 'accent': '2E6DA4', 'banner_text': 'FFFFFF',
        'box_fill': 'EAF1FA', 'box_border': '9FBEDD', 'note_fill': 'FDF6E3', 'note_border': 'E0C97F',
        'quote_fill': 'F4F7FB', 'quote_text': '2A4A6B', 'quote_attr': '1F3864',
        'table_head_fill': '1F3864', 'table_head_text': 'FFFFFF', 'rule': '9AA5B1', 'footer': '8A929B',
        'cover_kicker': '7A8899', 'cover_title': '1F3864', 'cover_sub': '6B7684', 'cover_badge': '2E6DA4',
    },
    'spacing': {'section_gap_pt': 8, 'para_gap_pt': 5, 'line_height': 1.55},
    'decor': {'radius_mm': 1.6, 'border_pt': 0.7, 'writing_line_mm': 7.0},
}


def list_themes() -> List[str]:
    if not os.path.isdir(STYLES_DIR):
        return []
    return sorted(f[:-5] for f in os.listdir(STYLES_DIR) if f.endswith('.json'))


def load_profile(name: str) -> Dict[str, Any]:
    path = name if name.endswith('.json') else os.path.join(STYLES_DIR, f'{name}.json')
    if not os.path.isfile(path):
        raise FileNotFoundError(
            f'테마를 찾을 수 없다: {name}\n쓸 수 있는 테마: {", ".join(list_themes())}')
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def _luma(hex_str: str) -> float:
    """상대 휘도(0=검정, 1=흰색). 색이 이상하면 0으로 본다."""
    h = str(hex_str).lstrip('#')
    if len(h) != 6:
        return 0.0
    try:
        r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    except ValueError:
        return 0.0
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _merged(profile: Dict[str, Any], key: str) -> Dict[str, Any]:
    out = dict(DEFAULTS.get(key, {}))
    out.update(profile.get(key, {}) or {})
    return out


def to_typst_theme(profile: Dict[str, Any], font_override: str = '') -> Dict[str, Any]:
    """프로필 → Typst 템플릿이 받는 theme 딕트. 색은 '#RRGGBB' 문자열로 넘긴다."""
    pal = _merged(profile, 'palette')
    scale = _merged(profile, 'type_scale')
    spacing = _merged(profile, 'spacing')
    decor = _merged(profile, 'decor')
    fonts = profile.get('font', {}) or {}

    body_font = font_override or fonts.get('main') or KO_FALLBACK[0]
    heading_font = font_override or fonts.get('heading') or body_font
    chain = [body_font] + [f for f in KO_FALLBACK if f != body_font]
    head_chain = [heading_font] + [f for f in KO_FALLBACK if f != heading_font]

    # 일부 프로필(kids-junior 등)은 표지 제목이 흰색이다 — 레거시 docx가 표지에 색 배경을 깔기 때문.
    # 흰 종이에 그대로 얹으면 글자가 사라지므로, 밝은 제목색이면 템플릿에 색 패널을 깔라고 알린다.
    cover_panel = _luma(pal.get('cover_title', '000000')) > 0.72

    return {
        'name': profile.get('name', 'unnamed'),
        'flags': {'cover_panel': cover_panel},
        'fonts': {'body': chain, 'heading': head_chain},
        'size': {k: float(v) for k, v in scale.items()},
        'color': {k: ('#' + str(v).lstrip('#')) for k, v in pal.items()},
        'banner_cycle': ['#' + str(c).lstrip('#') for c in (profile.get('banner_cycle') or [pal['heading']])],
        'spacing': {k: float(v) for k, v in spacing.items()},
        'decor': {k: (float(v) if isinstance(v, (int, float)) else v) for k, v in decor.items()},
    }


# ---------------------------------------------------------------- 폰트 점검

_font_cache: List[str] = []


def installed_fonts() -> List[str]:
    """typst가 보는 폰트 목록. typst가 없으면 빈 목록."""
    global _font_cache
    if _font_cache:
        return _font_cache
    exe = shutil.which('typst')
    if not exe:
        return []
    try:
        r = subprocess.run([exe, 'fonts'], capture_output=True, text=True, timeout=30)
        _font_cache = sorted({ln.strip() for ln in r.stdout.splitlines() if ln.strip()})
    except Exception:
        _font_cache = []
    return _font_cache


def check_fonts(theme: Dict[str, Any]) -> Tuple[List[str], List[str]]:
    """(경고, 실제로 쓸 수 있는 폰트 체인). 하나도 없으면 경고를 남기고 체인은 유지한다."""
    have = set(installed_fonts())
    warnings: List[str] = []
    usable: List[str] = []
    if not have:
        warnings.append('typst 폰트 목록을 확인할 수 없다(typst 미설치?). 폰트 폴백만 신뢰한다.')
        return warnings, theme['fonts']['body']
    for group in ('body', 'heading'):
        chain = theme['fonts'][group]
        found = [f for f in chain if f in have]
        if not found:
            warnings.append(
                f'{group} 폰트를 하나도 찾지 못했다: {", ".join(chain)}. '
                f'한글이 깨질 수 있다. 폰트를 설치하거나 --font 로 지정하라.')
        elif found[0] != chain[0]:
            warnings.append(f'{group} 폰트 {chain[0]}이(가) 없어 {found[0]}(으)로 대체한다.')
        if group == 'body':
            usable = found or chain
    return warnings, usable
