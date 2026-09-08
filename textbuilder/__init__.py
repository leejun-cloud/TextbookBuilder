"""TextBuilder 문서 모델 · 렌더러 계층.

기존 `scripts/*.py` 파이프라인은 그대로 두고, 그 옆에 얹는 계층이다.

    load(path) ─→ BookDocument ─→ get_renderer('typst'|'legacy').render(doc, options)
"""
from .model import BookDocument, Page, Block, Metadata, PageSetup, blk, PAGE_SIZES_MM  # noqa: F401
from .renderer import (Renderer, RenderOptions, RenderResult,  # noqa: F401
                       get_renderer, available_renderers, resolve_renderer)

__all__ = [
    'BookDocument', 'Page', 'Block', 'Metadata', 'PageSetup', 'blk', 'PAGE_SIZES_MM',
    'Renderer', 'RenderOptions', 'RenderResult',
    'get_renderer', 'available_renderers', 'resolve_renderer', 'load',
]


def load(path: str, **kw) -> BookDocument:
    """확장자로 어댑터를 골라 정규화 모델을 만든다.

    .md   → 레거시 블록 스킴
    .json → 콘텐츠 JSON (kids-lesson | elem456) 또는 모델 JSON(schema_version 있음)
    """
    import json
    import os
    ext = os.path.splitext(path)[1].lower()
    if ext in ('.md', '.markdown'):
        from .adapters.block_md import parse as parse_md
        return parse_md(path, **kw)
    if ext == '.json':
        with open(path, encoding='utf-8') as f:
            head = json.load(f)
        if 'schema_version' in head and 'pages' in head:
            doc = BookDocument.from_dict(head)
            doc.source = os.path.abspath(path)
            if not doc.assets_root:
                doc.assets_root = os.path.dirname(os.path.abspath(path))
            for k, v in kw.items():
                if v:
                    setattr(doc, k, v) if k in ('theme', 'template') else None
            return doc
        from .adapters.lesson_json import parse as parse_json
        return parse_json(path, **kw)
    raise ValueError(f'지원하지 않는 입력 형식: {ext} (.md 또는 .json)')
