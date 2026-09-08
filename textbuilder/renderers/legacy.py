#!/usr/bin/env python3
"""LegacyRenderer — 기존 파이프라인을 감싸기만 한다. 기존 스크립트를 고치지 않는다.

블록 스킴 md → `scripts/lesson_docx.py` (프로필 적용 docx)가 현재 주력 경로다.
정규화 모델에서 다시 docx를 그리는 대신, **원본 파일이 있으면 그 파일로 기존 스크립트를 호출**한다.
회귀 위험 0이 목표이므로, 원본이 없는(모델만 있는) 문서는 지원하지 않고 그 사실을 명확히 알린다.
"""
from __future__ import annotations

import os
import subprocess
import sys
import time

from ..model import BookDocument
from ..renderer import Renderer, RenderOptions, RenderResult

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class LegacyRenderer(Renderer):
    name = 'legacy'

    def available(self):
        script = os.path.join(REPO_ROOT, 'scripts', 'lesson_docx.py')
        if not os.path.isfile(script):
            return False, 'scripts/lesson_docx.py가 없다'
        try:
            import docx  # noqa: F401
        except Exception:
            return False, 'python-docx가 설치되지 않았다 (pip3 install python-docx)'
        return True, 'scripts/lesson_docx.py'

    def render(self, doc: BookDocument, options: RenderOptions) -> RenderResult:
        t0 = time.time()
        ok, why = self.available()
        if not ok:
            return RenderResult(ok=False, errors=[why])

        fmt = (options.fmt or 'docx').lower()
        if fmt != 'docx':
            return RenderResult(ok=False, errors=[
                f'레거시 렌더러는 docx만 만든다(요청: {fmt}). '
                f'PDF는 Word/LibreOffice로 변환하거나 --renderer typst 를 쓰라.'])

        src = doc.source
        if not src or not os.path.isfile(src):
            return RenderResult(ok=False, errors=[
                '레거시 렌더러는 원본 블록 스킴 md 파일이 필요하다(회귀 방지를 위해 기존 스크립트를 '
                '그대로 호출한다). doc.source가 비었거나 파일이 없다. '
                'Typst 렌더러는 모델만으로 렌더할 수 있다.'])

        out_path = options.out_path or os.path.splitext(src)[0] + '.docx'
        os.makedirs(os.path.dirname(os.path.abspath(out_path)) or '.', exist_ok=True)
        cmd = [sys.executable, os.path.join(REPO_ROOT, 'scripts', 'lesson_docx.py'),
               src, '-o', out_path, '--style', doc.theme]
        try:
            r = subprocess.run(cmd, capture_output=True, text=True,
                               timeout=options.timeout_sec, cwd=REPO_ROOT)
        except subprocess.TimeoutExpired:
            return RenderResult(ok=False, errors=[f'lesson_docx.py가 {options.timeout_sec}초를 넘겼다'])
        log = (r.stdout or '') + (r.stderr or '')
        if r.returncode != 0 or not os.path.isfile(out_path):
            tail = '\n'.join(log.strip().splitlines()[-6:])
            return RenderResult(ok=False, log=log, errors=[f'lesson_docx.py 실패:\n{tail}'])
        return RenderResult(ok=True, outputs=[out_path], log=log,
                            meta={'duration_ms': int((time.time() - t0) * 1000),
                                  'theme': doc.theme, 'format': 'docx',
                                  'via': 'scripts/lesson_docx.py'})

    def preview(self, doc: BookDocument, options: RenderOptions) -> RenderResult:
        return RenderResult(ok=False, errors=[
            '레거시 렌더러는 미리보기를 지원하지 않는다(docx만 만든다). '
            '미리보기는 --renderer typst 를 쓰라.'])
