#!/usr/bin/env python3
"""TypstRenderer — typst CLI로 컴파일한다.

CLI를 고른 이유는 docs/typst-integration-analysis.md §6 참조(파이썬+subprocess가 이미 관용,
Node 런타임 없음, stderr 디버깅 용이). Renderer API는 실행 방식에 의존하지 않으므로
나중에 WASM(typst.ts)이나 embedded로 바꿀 때 이 파일만 교체하면 된다.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
import time
from typing import List

from ..model import BookDocument
from ..renderer import Renderer, RenderOptions, RenderResult
from ..typst_gen import generate, REPO_ROOT


class TypstRenderer(Renderer):
    name = 'typst'

    def __init__(self, exe: str = ''):
        self.exe = exe or shutil.which('typst') or ''

    # ---- 가용성

    def available(self):
        if not self.exe:
            return False, ('typst 실행 파일을 찾을 수 없다. 설치: brew install typst '
                           '(또는 cargo install --locked typst-cli)')
        try:
            r = subprocess.run([self.exe, '--version'], capture_output=True, text=True, timeout=15)
            return (r.returncode == 0), r.stdout.strip() or r.stderr.strip()
        except Exception as e:
            return False, f'typst 실행 실패: {e}'

    # ---- 렌더

    def render(self, doc: BookDocument, options: RenderOptions) -> RenderResult:
        t0 = time.time()
        if options.final and ((options.fmt or 'pdf').lower() != 'pdf' or options.pages):
            return RenderResult(ok=False, errors=['최종 출력은 전체 페이지 PDF만 허용한다'])
        ok_exe, why = self.available()
        if not ok_exe:
            return RenderResult(ok=False, errors=[why])

        problems = doc.validate()
        try:
            src, warnings = generate(doc)
        except Exception as e:
            return RenderResult(ok=False, errors=[f'{type(e).__name__}: {e}'], warnings=problems)
        warnings = list(warnings) + problems
        if options.final and warnings:
            return RenderResult(ok=False, errors=['최종 출력 사전검증 실패: ' + w for w in warnings])

        fmt = (options.fmt or 'pdf').lower()
        if fmt not in ('pdf', 'png', 'svg'):
            return RenderResult(ok=False, errors=[f'typst 렌더러가 모르는 형식: {fmt}'])

        out_path = options.out_path or os.path.join(
            REPO_ROOT, 'build', f'{(doc.metadata.title or "document")[:40]}.{fmt}')
        os.makedirs(os.path.dirname(os.path.abspath(out_path)) or '.', exist_ok=True)

        # 생성 소스는 산출물 옆(.typ) 또는 저장소 안 임시 디렉터리에 둔다.
        # typst는 `--root` 밖의 소스를 거부하므로(source file must be contained in project root)
        # 임시 파일도 반드시 REPO_ROOT 아래에 만든다.
        if options.keep_source:
            src_path = os.path.splitext(out_path)[0] + '.typ'
            tmpdir = None
        else:
            holder = os.path.join(REPO_ROOT, 'build', '.typst-tmp')
            os.makedirs(holder, exist_ok=True)
            tmpdir = tempfile.mkdtemp(prefix='render-', dir=holder)
            src_path = os.path.join(tmpdir, 'document.typ')
        with open(src_path, 'w', encoding='utf-8') as f:
            f.write(src)

        final_path = out_path
        final_tmp = tempfile.TemporaryDirectory(prefix='final-', dir=os.path.dirname(os.path.abspath(out_path))) if options.final else None
        if final_tmp:
            out_path = os.path.join(final_tmp.name, 'candidate.pdf')
        cmd = [self.exe, 'compile', '--root', REPO_ROOT, '--format', fmt]
        if fmt == 'png':
            cmd += ['--ppi', str(options.ppi)]
            if '{p}' not in out_path and '{n}' not in out_path:
                # 여러 쪽이면 typst가 {p}를 요구한다
                base, ext = os.path.splitext(out_path)
                out_path = f'{base}-{{p}}{ext}'
        if options.pages:
            cmd += ['--pages', ','.join(str(p) for p in options.pages)]
        cmd += [src_path, out_path]

        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=options.timeout_sec)
        except subprocess.TimeoutExpired:
            if final_tmp:
                final_tmp.cleanup()
            return RenderResult(ok=False, source_path=src_path, warnings=warnings,
                                errors=[f'typst 컴파일이 {options.timeout_sec}초를 넘겨 중단했다. '
                                        f'문서가 너무 크거나 템플릿이 무한 반복일 수 있다.'])
        except OSError as e:
            if final_tmp:
                final_tmp.cleanup()
            return RenderResult(ok=False, source_path=src_path, errors=[f'typst 실행 실패: {e}'])
        log = (r.stdout or '') + (r.stderr or '')

        if r.returncode != 0:
            if final_tmp:
                final_tmp.cleanup()
            return RenderResult(ok=False, source_path=src_path, log=log, warnings=warnings,
                                errors=_friendly_errors(log, src_path))

        outputs = _collect_outputs(out_path)
        if not outputs or any(os.path.getsize(p) == 0 for p in outputs):
            if final_tmp:
                final_tmp.cleanup()
            return RenderResult(ok=False, source_path=src_path, log=log, warnings=warnings,
                                errors=['typst가 성공했다고 보고했으나 비어 있거나 없는 산출 파일이다'])
        actual_pages = None
        if options.final:
            from ..print_qc import audit_pdf, write_report
            try:
                bleed = doc.page_setup.bleed_mm * 2
                expected_size = tuple(v + bleed for v in doc.dimensions_mm())
                expected_pages = options.extra.get('expected_pages')
                if expected_pages is None:
                    expected_pages = len(doc.pages) + int(doc.template == 'book/standard' and bool(doc.metadata.title))
                report = audit_pdf(outputs[0], expected_size_mm=expected_size,
                                   expected_pages=expected_pages,
                                   min_image_dpi=options.extra.get('min_image_dpi', 150))
                write_report(final_path + '.qc.json', report)
                if report['status'] != 'machine_pass':
                    final_tmp.cleanup()
                    return RenderResult(ok=False, errors=report['errors'], warnings=warnings,
                                        source_path=src_path, meta={'qc_report': final_path + '.qc.json'})
                actual_pages = report['page_count']
                os.replace(outputs[0], final_path)
                outputs = [final_path]
            except Exception as e:
                return RenderResult(ok=False, errors=[f'최종 PDF 검수 실패: {e}'], source_path=src_path)
            finally:
                final_tmp.cleanup()
        if tmpdir and not options.keep_source:
            shutil.rmtree(tmpdir, ignore_errors=True)
            src_path = ''
        return RenderResult(ok=True, outputs=outputs, warnings=warnings, log=log,
                            source_path=src_path,
                            meta={'pages': actual_pages if actual_pages is not None else len(doc.pages), 'duration_ms': int((time.time() - t0) * 1000),
                                  'template': doc.template, 'theme': doc.theme, 'format': fmt})


def _collect_outputs(out_path: str) -> List[str]:
    if '{p}' in out_path or '{n}' in out_path:
        base = re.escape(os.path.basename(out_path)).replace(r'\{p\}', r'(\d+)').replace(r'\{n\}', r'(\d+)')
        d = os.path.dirname(os.path.abspath(out_path)) or '.'
        pat = re.compile('^' + base + '$')
        return sorted(os.path.join(d, f) for f in os.listdir(d) if pat.match(f))
    return [out_path] if os.path.isfile(out_path) else []


def _friendly_errors(log: str, src_path: str) -> List[str]:
    """typst stderr를 TextBuilder 사용자가 읽을 수 있는 메시지로 바꾼다."""
    out: List[str] = []
    for m in re.finditer(r'error: (.+)', log):
        msg = m.group(1).strip()
        if 'file not found' in msg and ('.png' in msg or '.jpg' in msg or '.jpeg' in msg or '.svg' in msg):
            out.append(f'이미지 파일이 없다 — {msg}')
        elif 'unknown font family' in msg or 'font' in msg and 'not found' in msg:
            out.append(f'폰트를 찾을 수 없다 — {msg}. 테마의 폰트를 설치하거나 다른 테마를 쓰라.')
        elif 'file not found' in msg and '.typ' in msg:
            out.append(f'템플릿 파일이 없다 — {msg}')
        elif 'unexpected' in msg or 'expected' in msg:
            out.append(f'생성된 Typst 소스 문법 오류 — {msg} (소스: {src_path})')
        else:
            out.append(msg)
    if not out:
        tail = '\n'.join(log.strip().splitlines()[-6:])
        out.append(f'typst 컴파일 실패:\n{tail}')
    # 중복 제거(순서 유지)
    seen, uniq = set(), []
    for e in out:
        if e not in seen:
            seen.add(e)
            uniq.append(e)
    return uniq[:8]

