#!/usr/bin/env python3
"""Renderer 인터페이스 — 문서 편집(모델)과 출력 엔진을 분리한다.

    BookDocument ─→ Renderer ─→ RenderResult
                     ├── LegacyRenderer  (기존 scripts/*.py 호출. 동작 불변)
                     └── TypstRenderer   (templates/typst/* + typst CLI)

Renderer API는 실행 방식(CLI/WASM)에 의존하지 않는다. 나중에 typst.ts(WASM)로 바꿔도
이 인터페이스는 그대로 둔다.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .model import BookDocument


@dataclass
class RenderOptions:
    out_path: str = ''
    fmt: str = 'pdf'                 # pdf | png | docx
    pages: Optional[List[int]] = None    # 1-기준 페이지 선택(부분 프리뷰)
    ppi: int = 144                   # png 프리뷰 해상도
    keep_source: bool = False        # 생성된 .typ 등 중간 산출물 보존
    timeout_sec: int = 120
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RenderResult:
    ok: bool
    outputs: List[str] = field(default_factory=list)      # 만들어진 파일 경로
    errors: List[str] = field(default_factory=list)       # 사용자에게 보일 오류(정제됨)
    warnings: List[str] = field(default_factory=list)
    log: str = ''                                          # 엔진 원본 stderr/stdout
    source_path: str = ''                                  # 생성된 중간 소스(.typ 등)
    meta: Dict[str, Any] = field(default_factory=dict)     # pages, duration_ms 등

    def summary(self) -> str:
        if self.ok:
            s = f'성공 · 산출 {len(self.outputs)}개'
            if self.warnings:
                s += f' · 경고 {len(self.warnings)}건'
            return s
        return '실패: ' + ('; '.join(self.errors) if self.errors else '원인 불명')


class Renderer:
    """출력 엔진 인터페이스."""

    name = 'base'

    def available(self) -> tuple[bool, str]:
        """이 환경에서 쓸 수 있는가. (가능여부, 이유/버전)"""
        return True, ''

    def render(self, doc: BookDocument, options: RenderOptions) -> RenderResult:
        raise NotImplementedError

    def preview(self, doc: BookDocument, options: RenderOptions) -> RenderResult:
        """미리보기(기본은 PNG). 렌더러가 부분 렌더를 지원하면 options.pages를 쓴다."""
        opts = RenderOptions(**{**options.__dict__, 'fmt': 'png'})
        return self.render(doc, opts)

    def export(self, doc: BookDocument, options: RenderOptions) -> RenderResult:
        """최종 출력(기본은 PDF)."""
        opts = RenderOptions(**{**options.__dict__, 'fmt': options.fmt or 'pdf'})
        return self.render(doc, opts)


# ---------------------------------------------------------------- 레지스트리

_REGISTRY: Dict[str, Any] = {}


def register(name: str, factory) -> None:
    _REGISTRY[name] = factory


def get_renderer(name: str) -> Renderer:
    if name not in _REGISTRY:
        raise ValueError(f'모르는 렌더러: {name} (쓸 수 있는 것: {", ".join(sorted(_REGISTRY))})')
    return _REGISTRY[name]()


def available_renderers() -> Dict[str, tuple[bool, str]]:
    out = {}
    for name, factory in sorted(_REGISTRY.items()):
        try:
            out[name] = factory().available()
        except Exception as e:  # 렌더러 자체가 임포트 실패해도 목록은 보여 준다
            out[name] = (False, f'{type(e).__name__}: {e}')
    return out


def resolve_renderer(preferred: str, fallback: str = 'legacy') -> tuple[Renderer, List[str]]:
    """preferred를 쓰되 불가하면 fallback으로 내려간다. (렌더러, 경고목록)"""
    notes: List[str] = []
    r = get_renderer(preferred)
    ok, why = r.available()
    if ok:
        return r, notes
    notes.append(f'{preferred} 렌더러를 쓸 수 없다: {why}')
    if fallback and fallback != preferred:
        fb = get_renderer(fallback)
        ok2, why2 = fb.available()
        if ok2:
            notes.append(f'{fallback} 렌더러로 대체한다')
            return fb, notes
        notes.append(f'{fallback} 렌더러도 쓸 수 없다: {why2}')
    raise RuntimeError('; '.join(notes))


def _install_builtin():
    from .renderers.typst_cli import TypstRenderer
    from .renderers.legacy import LegacyRenderer
    register('typst', TypstRenderer)
    register('legacy', LegacyRenderer)


_install_builtin()
