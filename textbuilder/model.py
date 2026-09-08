#!/usr/bin/env python3
"""TextBuilder 정규화 문서 모델 (Normalized Document Model).

이 모델은 **의미**만 담는다. Typst 문법도, docx 서식도, HTML도 들어오지 않는다.
블록 스킴 마크다운(레거시)과 콘텐츠 JSON(신규)이 각자 어댑터를 통해 이 모델로 들어오고,
렌더러들이 이 모델만 보고 출력한다.

    (A) 블록 스킴 md ─┐
                      ├─→ BookDocument ─→ Renderer(Legacy | Typst)
    (B) 콘텐츠 JSON ─┘

스키마 문서: docs/document-model.md · TS 타입: schema/book-document.d.ts
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

SCHEMA_VERSION = 1

# ---------------------------------------------------------------- 블록

# kind 목록. 렌더러/템플릿은 이 문자열로 디스패치한다.
BLOCK_KINDS = (
    'heading',     # 소제목·섹션 제목
    'text',        # 문단
    'image',       # 그림
    'verse',       # 성경 인용
    'question',    # 질문(답 쓰는 자리 포함 가능)
    'activity',    # 활동(준비물 + 단계)
    'callout',     # 강조/주의 박스
    'table',       # 표
    'fill_blank',  # 빈칸 채우기
    'writing',     # 필기 줄
    'checklist',   # 체크 항목
    'memory',      # 암송 구절
    'prayer',      # 기도문
    'reflection',  # 생각 쓰기
    'speech',      # 말풍선
    'keywords',    # 낱말/키워드 묶음
    'spacer',      # 여백
)


@dataclass
class Block:
    """모든 블록의 공통 형태 — kind로 구분되는 판별 유니온.

    kind별로 쓰는 필드만 채운다(나머지는 None/빈값). TS 쪽에서는 kind별 인터페이스로 좁혀진다.
    """
    kind: str
    text: str = ''                       # 본문/제목/한 줄 문구
    label: str = ''                      # 박스 제목·항목 라벨·화자 이름
    items: List[str] = field(default_factory=list)      # 목록·단계·체크 항목·키워드
    rows: List[List[str]] = field(default_factory=list)  # 표 본문
    head: List[str] = field(default_factory=list)        # 표 머리행
    src: str = ''                        # 이미지 경로(문서 기준 상대경로)
    ref: str = ''                        # 성경 장절 등 출처
    level: int = 2                       # heading 단계 (1=페이지 제목, 2=섹션, 3=소항목)
    count: int = 1                       # writing 줄 수 · spacer 배수
    variant: str = ''                    # 템플릿이 아는 변형 이름(예: 'story', 'note')
    attrs: Dict[str, Any] = field(default_factory=dict)  # 이미지 role/fit/crop 등 부가 속성

    def __post_init__(self):
        if self.kind not in BLOCK_KINDS:
            raise ValueError(f'알 수 없는 블록 kind: {self.kind!r} (허용: {", ".join(BLOCK_KINDS)})')

    # 이미지 편의 접근자 (요청서 §8)
    @property
    def role(self) -> str:
        return str(self.attrs.get('role', 'illustration'))

    @property
    def fit(self) -> str:
        return str(self.attrs.get('fit', 'contain'))


def blk(kind: str, **kw) -> Block:
    return Block(kind=kind, **kw)


# ---------------------------------------------------------------- 페이지

@dataclass
class Page:
    """한 페이지. layout은 템플릿이 아는 레이아웃 이름이며, 없으면 템플릿 기본 흐름을 쓴다.

    페이지 나눔의 최종 결정권은 렌더러/템플릿에 있다(레거시 md 계열은 페이지 개념이 없다).
    layout이 지정된 문서는 '페이지가 의미를 갖는' 문서(그림책·워크북)다.
    """
    layout: str = 'flow'
    title: str = ''
    blocks: List[Block] = field(default_factory=list)
    attrs: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------- 문서

@dataclass
class Metadata:
    title: str = ''
    subtitle: str = ''
    kicker: str = ''            # 머리글 작은 글씨
    badge: str = ''             # 배지(단원·과번호 등)
    footer: str = ''
    grade: str = ''
    lesson_no: Optional[int] = None
    unit: str = ''
    department: str = ''
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PageSetup:
    """출판 설정 (요청서 §14). 첫 버전은 size/margins/bleed만 렌더러가 쓴다."""
    size: str = 'B5'            # A4 | A5 | B5 | 210x210 | 6x9in | custom
    width_mm: Optional[float] = None    # size == 'custom'일 때
    height_mm: Optional[float] = None
    margin_top_mm: float = 19.0
    margin_bottom_mm: float = 16.0
    margin_inside_mm: float = 20.0
    margin_outside_mm: float = 20.0
    gutter_mm: float = 0.0
    bleed_mm: float = 0.0
    facing_pages: bool = False
    page_numbers: bool = True


PAGE_SIZES_MM = {
    'A4': (210.0, 297.0),
    'A5': (148.0, 210.0),
    'B5': (182.0, 257.0),        # JIS B5
    'B5-ISO': (176.0, 250.0),
    '210x210': (210.0, 210.0),
    '6x9in': (152.4, 228.6),
}


@dataclass
class BookDocument:
    """렌더러가 받는 최종 입력."""
    metadata: Metadata = field(default_factory=Metadata)
    page_setup: PageSetup = field(default_factory=PageSetup)
    theme: str = 'doctrine-stage3'          # doc-styles/<이름>.json
    template: str = 'workbook/junior'       # templates/typst/<template>/main.typ
    pages: List[Page] = field(default_factory=list)
    assets_root: str = ''                    # 이미지 상대경로의 기준 디렉터리
    source: str = ''                         # 어디서 왔는지(디버깅용 경로)
    schema_version: int = SCHEMA_VERSION
    warnings: List[str] = field(default_factory=list)   # 어댑터가 남기는 손실 경고

    # ---- 직렬화

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self, indent: int = 1) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> 'BookDocument':
        doc = BookDocument()
        doc.metadata = Metadata(**d.get('metadata', {}))
        doc.page_setup = PageSetup(**d.get('page_setup', {}))
        for k in ('theme', 'template', 'assets_root', 'source'):
            if k in d:
                setattr(doc, k, d[k])
        doc.schema_version = int(d.get('schema_version', SCHEMA_VERSION))
        doc.warnings = list(d.get('warnings', []))
        for p in d.get('pages', []):
            page = Page(layout=p.get('layout', 'flow'), title=p.get('title', ''),
                        attrs=p.get('attrs', {}) or {})
            page.blocks = [Block(**b) for b in p.get('blocks', [])]
            doc.pages.append(page)
        return doc

    @staticmethod
    def from_json_file(path: str) -> 'BookDocument':
        with open(path, encoding='utf-8') as f:
            return BookDocument.from_dict(json.load(f))

    # ---- 조회

    def all_blocks(self):
        for page in self.pages:
            for b in page.blocks:
                yield page, b

    def dimensions_mm(self):
        if self.page_setup.size == 'custom':
            w, h = self.page_setup.width_mm, self.page_setup.height_mm
            if not w or not h:
                raise ValueError('page_setup.size가 custom이면 width_mm/height_mm가 필요하다')
            return float(w), float(h)
        if self.page_setup.size not in PAGE_SIZES_MM:
            raise ValueError(f'모르는 판형: {self.page_setup.size} '
                             f'(허용: {", ".join(PAGE_SIZES_MM)}, custom)')
        return PAGE_SIZES_MM[self.page_setup.size]

    def validate(self) -> List[str]:
        """치명적이지 않은 문제 목록을 돌려준다(렌더 전에 사람이 보게)."""
        problems = []
        if not self.metadata.title:
            problems.append('metadata.title이 비었다')
        if not self.pages:
            problems.append('페이지가 없다')
        try:
            self.dimensions_mm()
        except ValueError as e:
            problems.append(str(e))
        for i, page in enumerate(self.pages, 1):
            if not page.blocks:
                problems.append(f'{i}쪽에 블록이 없다')
            for b in page.blocks:
                if b.kind == 'image' and not b.src:
                    problems.append(f'{i}쪽 image 블록에 src가 없다')
                if b.kind == 'table' and not (b.head or b.rows):
                    problems.append(f'{i}쪽 table 블록이 비었다')
        return problems
