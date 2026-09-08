#!/usr/bin/env python3
"""TextBuilder 문서모델·Typst 렌더러 테스트 (표준 unittest, 외부 의존성 없음).

    python3 scripts/test_textbuilder.py            # 전부
    python3 scripts/test_textbuilder.py -k escape  # 골라서

느린 테스트(실제 typst 컴파일)는 typst가 없으면 skip된다.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

from textbuilder import load, BookDocument, Page, blk, RenderOptions, get_renderer  # noqa: E402
from textbuilder.model import Metadata  # noqa: E402
from textbuilder.typst_gen import generate, lit, q, resolve_asset, template_path, AssetError  # noqa: E402
from textbuilder.theme import to_typst_theme, load_profile  # noqa: E402
from textbuilder import renderer as renderer_mod  # noqa: E402

HAS_TYPST = shutil.which('typst') is not None
JUNIOR_JSON = os.path.join(REPO, 'sample-projects/typst-test/junior-lesson/lesson.json')
JUNIOR_MD = os.path.join(REPO, 'projects/doctrine-junior-120/lessons/01/draft.md')
ELEM_JSON = os.path.join(REPO, 'projects/elementary-456-v2/content/g4/001.json')
PICTURE_JSON = os.path.join(REPO, 'sample-projects/typst-test/picture-book/book.json')


def mini_doc(**kw) -> BookDocument:
    kw.setdefault('theme', 'doctrine-stage3')
    kw.setdefault('template', 'book/standard')
    d = BookDocument(**kw)
    d.metadata = Metadata(title='시험 문서')
    d.pages = [Page(layout='flow', blocks=[blk('text', text='한 줄')])]
    return d


# ---------------------------------------------------------------- 직렬화·이스케이프

class TestLiteral(unittest.TestCase):
    def test_string_escape(self):
        self.assertEqual(q('a"b'), '"a\\"b"')
        self.assertEqual(q('a\\b'), '"a\\\\b"')
        self.assertEqual(q('줄1\n줄2'), '"줄1\\n줄2"')

    def test_typst_syntax_is_neutralized(self):
        """사용자 텍스트에 Typst 문법이 들어와도 코드로 해석되지 않는다."""
        danger = '#set page(width: 1cm) $x^2$ *굵게* _기울임_ [블록] @참조 \\ "따옴표"'
        out = q(danger)
        self.assertTrue(out.startswith('"') and out.endswith('"'))
        # 리터럴 안에서 인용부호와 백슬래시만 이스케이프된다
        self.assertIn('\\"따옴표\\"', out)
        self.assertNotIn('\n', out)

    def test_dict_and_array(self):
        self.assertEqual(lit({}), '(:)')
        self.assertEqual(lit([]), '()')
        self.assertIn(',\n', lit(['하나']))          # 1-원소 배열은 후행 콤마
        self.assertIn('kind: "text"', lit({'kind': 'text'}))

    def test_bad_key_rejected(self):
        with self.assertRaises(ValueError):
            lit({'has space': 1})

    def test_numbers_and_bools(self):
        self.assertEqual(lit(True), 'true')
        self.assertEqual(lit(None), 'none')
        self.assertEqual(lit(3), '3')


# ---------------------------------------------------------------- 모델

class TestModel(unittest.TestCase):
    def test_unknown_kind_rejected(self):
        with self.assertRaises(ValueError):
            blk('nonexistent-kind')

    def test_roundtrip_json(self):
        d = mini_doc()
        again = BookDocument.from_dict(json.loads(d.to_json()))
        self.assertEqual(again.metadata.title, '시험 문서')
        self.assertEqual(again.pages[0].blocks[0].text, '한 줄')

    def test_page_sizes(self):
        d = mini_doc()
        d.page_setup.size = 'B5'
        self.assertEqual(d.dimensions_mm(), (182.0, 257.0))
        d.page_setup.size = 'custom'
        with self.assertRaises(ValueError):
            d.dimensions_mm()
        d.page_setup.width_mm, d.page_setup.height_mm = 100, 200
        self.assertEqual(d.dimensions_mm(), (100.0, 200.0))
        d.page_setup.size = '모르는판형'
        with self.assertRaises(ValueError):
            d.dimensions_mm()

    def test_validate_finds_problems(self):
        d = BookDocument()
        problems = d.validate()
        self.assertTrue(any('title' in p for p in problems))
        self.assertTrue(any('페이지가 없다' in p for p in problems))


# ---------------------------------------------------------------- 어댑터

class TestAdapters(unittest.TestCase):
    def test_kids_lesson_makes_four_pages(self):
        doc = load(JUNIOR_JSON)
        self.assertEqual(len(doc.pages), 4)
        self.assertEqual([p.layout for p in doc.pages],
                         ['kids-story', 'kids-find', 'kids-activity', 'kids-close'])
        self.assertEqual(doc.template, 'workbook/junior')

    def test_kids_lesson_answer_not_printed(self):
        """빈칸 정답이 지면에 인쇄되는 필드(label/text)로 새지 않는다."""
        doc = load(JUNIOR_JSON)
        for _p, b in doc.all_blocks():
            if b.kind == 'fill_blank':
                self.assertNotIn('왕', b.label)          # 정답 '왕'이 라벨에 없어야 한다
                self.assertEqual(b.attrs.get('answer'), '왕')
        src, _w = generate(doc)
        # 생성된 typst 소스에도 정답이 그려질 자리로 들어가지 않는다(attrs로만 존재)
        self.assertIn('answer: "왕"', src)
        self.assertNotIn('label: "왕"', src)

    def test_elem456_existing_content_reads(self):
        doc = load(ELEM_JSON)
        self.assertEqual(len(doc.pages), 3)
        self.assertIn('하나님 나라', doc.metadata.title)
        self.assertEqual(doc.metadata.grade, '4학년')

    def test_block_md_lossless_enough(self):
        doc = load(JUNIOR_MD)
        kinds = {b.kind for _p, b in doc.all_blocks()}
        self.assertIn('callout', kinds)
        self.assertIn('table', kinds)
        self.assertIn('checklist', kinds)
        self.assertEqual(doc.warnings, [], f'변환 경고: {doc.warnings}')
        self.assertTrue(doc.metadata.title)

    def test_unknown_marker_warns_not_crashes(self):
        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, 'draft.md')
            with open(p, 'w', encoding='utf-8') as f:
                f.write('# COVER\n큰제목: 시험\n\n# 1. 절\n[[ALIEN_MARK:x]]\n본문\n')
            doc = load(p)
            self.assertTrue(any('알 수 없는 블록 표시' in w for w in doc.warnings))
            self.assertTrue(any(b.kind == 'text' for _p, b in doc.all_blocks()))


# ---------------------------------------------------------------- 한글·테마·자산

class TestKoreanAndTheme(unittest.TestCase):
    def test_korean_survives_generation(self):
        doc = mini_doc()
        doc.pages[0].blocks = [
            blk('text', text='하나님 나라는 「만유」를 다스리세요 (엡 1:10) — 1·2·3 “인용” 100%'),
        ]
        src, _w = generate(doc)
        self.assertIn('하나님 나라는', src)
        self.assertIn('「만유」', src)
        self.assertIn('엡 1:10', src)

    def test_theme_maps_legacy_profile(self):
        theme = to_typst_theme(load_profile('doctrine-stage3'))
        self.assertTrue(theme['color']['accent'].startswith('#'))
        self.assertIsInstance(theme['fonts']['body'], list)
        self.assertGreater(len(theme['fonts']['body']), 1, '폰트 폴백 체인이 있어야 한다')
        self.assertIn('cover_panel', theme['flags'])

    def test_light_cover_title_flags_panel(self):
        self.assertTrue(to_typst_theme(load_profile('kids-junior'))['flags']['cover_panel'])
        self.assertFalse(to_typst_theme(load_profile('doctrine-stage3'))['flags']['cover_panel'])

    def test_asset_resolution(self):
        doc = load(JUNIOR_JSON)
        rel = resolve_asset(doc, 'assets/hero-crown.png')
        self.assertTrue(rel.startswith('/sample-projects/'), rel)
        with self.assertRaises(AssetError):
            resolve_asset(doc, 'assets/없는파일.png')
        with self.assertRaises(AssetError):
            resolve_asset(doc, '/etc/hosts')      # 저장소 밖

    def test_missing_image_degrades(self):
        doc = mini_doc()
        doc.source = JUNIOR_JSON
        doc.pages[0].blocks = [blk('image', src='없다.png', attrs={'alt': '대체 설명'})]
        src, warnings = generate(doc)
        self.assertTrue(any('이미지를 찾을 수 없다' in w for w in warnings))
        self.assertIn('missing: true', src)       # 템플릿이 placeholder를 그린다

    def test_template_selection(self):
        self.assertTrue(template_path('workbook/junior').endswith('/workbook/junior/main.typ'))
        with self.assertRaises(FileNotFoundError):
            template_path('없는/템플릿')


# ---------------------------------------------------------------- 렌더러

class TestRendererLayer(unittest.TestCase):
    def test_registry_has_both(self):
        names = set(renderer_mod.available_renderers())
        self.assertIn('typst', names)
        self.assertIn('legacy', names)

    def test_fallback_when_unavailable(self):
        class Dead(renderer_mod.Renderer):
            name = 'dead'

            def available(self):
                return False, '일부러 죽은 렌더러'

        renderer_mod.register('dead', Dead)
        r, notes = renderer_mod.resolve_renderer('dead', 'legacy')
        self.assertEqual(r.name, 'legacy')
        self.assertTrue(any('쓸 수 없다' in n for n in notes))

    def test_legacy_requires_source_file(self):
        r = get_renderer('legacy')
        res = r.render(mini_doc(), RenderOptions(fmt='docx'))
        self.assertFalse(res.ok)
        self.assertTrue(any('원본' in e for e in res.errors))

    def test_legacy_rejects_pdf(self):
        r = get_renderer('legacy')
        res = r.render(mini_doc(), RenderOptions(fmt='pdf'))
        self.assertFalse(res.ok)
        self.assertTrue(any('docx만' in e for e in res.errors))


@unittest.skipUnless(HAS_TYPST, 'typst 미설치')
class TestTypstCompile(unittest.TestCase):
    """실제 컴파일 — 골든 테스트(쪽수·성공 여부)."""

    def _render(self, path, template, theme, expect_pages, page_size=''):
        with tempfile.TemporaryDirectory(dir=os.path.join(REPO, 'build')) as td:
            out = os.path.join(td, 'out.pdf')
            kw = {'theme': theme, 'template': template}
            if page_size:
                kw['page_size'] = page_size
            doc = load(path, **kw)
            res = get_renderer('typst').render(doc, RenderOptions(out_path=out, fmt='pdf'))
            self.assertTrue(res.ok, f'실패: {res.errors}\n{res.log[-800:]}')
            self.assertTrue(os.path.isfile(out))
            self.assertEqual(res.meta['pages'], expect_pages)
            # 산출 PDF에 한글이 살아 있는지
            txt = subprocess.run(['pdftotext', out, '-'], capture_output=True, text=True).stdout
            self.assertNotIn('�', txt, '깨진 글자(U+FFFD)가 있다')
            return txt

    def test_junior_four_pages(self):
        txt = self._render(JUNIOR_JSON, 'workbook/junior', 'kids-junior', 4, page_size='B5')
        for must in ('시작하고 읽어요', '찾고 생각해요', '오늘의 활동', '정리하고 고백해요',
                     '하나님은 온 세상을 다스리시는 왕이세요', '왕관 만들기'):
            self.assertIn(must, txt.replace('\n', ' '), f'{must}가 PDF에 없다')

    def test_junior_answer_not_in_pdf(self):
        """빈칸 정답이 학생 지면 PDF에 인쇄되지 않는다."""
        txt = self._render(JUNIOR_JSON, 'workbook/junior', 'kids-junior', 4)
        flat = txt.replace('\n', ' ')
        self.assertIn('다스리시는 ______이세요', flat.replace('  ', ' '))
        # 정답만 홀로 찍힌 라벨이 없어야 한다(활동/본문 속 '왕' 언급은 정상)
        self.assertNotIn('빈칸을 채워요 왕 ', flat)

    def test_elem_three_pages(self):
        self._render(ELEM_JSON, 'workbook/elementary', 'kids-bright', 3)

    def test_book_from_legacy_md(self):
        self._render(JUNIOR_MD, 'book/standard', 'kids-junior', 1)

    def test_picture_book_layouts(self):
        self._render(PICTURE_JSON, 'picture-book/full-image', 'kids-bright', 6)

    def test_unknown_block_does_not_break_compile(self):
        """모르는 layout·variant가 와도 컴파일이 성공해야 한다(회색 안내 박스로 떨어짐)."""
        doc = mini_doc(template='workbook/junior')
        doc.pages = [Page(layout='이상한레이아웃', title='시험',
                          blocks=[blk('text', text='본문'), blk('spacer', count=2)])]
        with tempfile.TemporaryDirectory(dir=os.path.join(REPO, 'build')) as td:
            out = os.path.join(td, 'x.pdf')
            res = get_renderer('typst').render(doc, RenderOptions(out_path=out, fmt='pdf'))
            self.assertTrue(res.ok, f'실패: {res.errors}')

    def test_page_size_applies(self):
        """판형 설정이 실제 PDF 크기에 반영된다."""
        for size, expect_pt in (('B5', (516, 728)), ('A4', (595, 841))):
            with tempfile.TemporaryDirectory(dir=os.path.join(REPO, 'build')) as td:
                out = os.path.join(td, f'{size}.pdf')
                doc = load(JUNIOR_JSON, page_size=size)
                res = get_renderer('typst').render(doc, RenderOptions(out_path=out, fmt='pdf'))
                self.assertTrue(res.ok, f'{size} 실패: {res.errors}')
                info = subprocess.run(['pdfinfo', out], capture_output=True, text=True).stdout
                line = [l for l in info.splitlines() if l.startswith('Page size')]
                self.assertTrue(line, 'pdfinfo에서 판형을 읽지 못했다')
                w = float(line[0].split()[2])
                self.assertAlmostEqual(w, expect_pt[0], delta=2, msg=f'{size} 폭이 다르다: {line[0]}')

    def test_png_preview(self):
        with tempfile.TemporaryDirectory(dir=os.path.join(REPO, 'build')) as td:
            out = os.path.join(td, 'p.png')
            doc = load(JUNIOR_JSON)
            res = get_renderer('typst').preview(doc, RenderOptions(out_path=out, pages=[2], ppi=96))
            self.assertTrue(res.ok, f'미리보기 실패: {res.errors}')
            self.assertTrue(res.outputs and os.path.isfile(res.outputs[0]))


if __name__ == '__main__':
    unittest.main(verbosity=2)
