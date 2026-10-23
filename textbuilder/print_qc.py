"""최종 PDF를 다시 열어 검사한다. 기계 검증과 실물/내용 검토를 구분한다."""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as stream:
        for part in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(part)
    return digest.hexdigest()


def write_report(path, report):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.tmp')
    temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    temporary.replace(path)


def audit_cutout_geometry(activities_pdf, cutouts_pdf, plan, sheets):
    """PDF에 실제로 기록된 점선 윤곽을 읽어 위치만 제거한 뒤 1:1로 비교한다."""
    import fitz
    mm=72/25.4
    errors=[]; targets={}

    def dashed(page):
        return [p for p in page.get_drawings() if p.get('dashes') not in (None,'','[] 0')]

    def signature(path,x,y):
        def normalize(value):
            if isinstance(value,fitz.Point):
                return [value.x-x*mm,value.y-y*mm]
            if isinstance(value,fitz.Rect):
                return [value.x0-x*mm,value.y0-y*mm,value.x1-x*mm,value.y1-y*mm]
            return value
        return [[normalize(v) for v in item] for item in path['items']]

    def equal(a,b):
        if isinstance(a,list) and isinstance(b,list):
            return len(a)==len(b) and all(equal(x,y) for x,y in zip(a,b))
        if isinstance(a,(int,float)) and isinstance(b,(int,float)):
            return abs(a-b)<.005
        return a==b

    def bounded(path,piece,x,y,label):
        shape=piece['outline']
        points=shape if isinstance(shape,list) else [[0,0],[1,1]]
        xs=[p[0] for p in points]; ys=[p[1] for p in points]
        expected=fitz.Rect((x+min(xs)*piece['width_mm'])*mm,
                           (y+min(ys)*piece['height_mm'])*mm,
                           (x+max(xs)*piece['width_mm'])*mm,
                           (y+max(ys)*piece['height_mm'])*mm)
        if any(abs(a-b)>.01 for a,b in zip(path['rect'],expected)):
            errors.append(f'{label}: 실제 PDF 윤곽 크기·위치가 원래 영역과 다르다')

    with fitz.open(activities_pdf) as pdf:
        for ai,activity in enumerate(plan['activities']):
            paths=dashed(pdf[ai]); pieces=activity['pieces']
            if len(paths)!=len(pieces):
                errors.append(f'{activity["id"]}: 빈자리 점선 수 불일치'); continue
            sx,sy,sw,sh=activity['scene_mm']; iw,ih=activity['pixels']
            for path,piece in zip(paths,pieces):
                cx,cy,_,_=piece['crop_px']; x,y=sx+cx*sw/iw,sy+cy*sh/ih
                bounded(path,piece,x,y,f'{activity["id"]}/{piece["id"]}')
                targets[(ai,piece['id'])]=signature(path,x,y)
    with fitz.open(cutouts_pdf) as pdf:
        for si,sheet in enumerate(sheets):
            paths=dashed(pdf[si*2])
            if len(paths)!=len(sheet):
                errors.append(f'오리기 {si+1}면: 점선 수 불일치'); continue
            for path,piece in zip(paths,sheet):
                x,y=piece['x_mm'],piece['y_mm']; key=(piece['activity_index'],piece['id'])
                bounded(path,piece,x,y,f'조각 {piece["id"]}')
                if key not in targets or not equal(signature(path,x,y),targets[key]):
                    errors.append(f'조각 {piece["id"]}: 실제 PDF 빈자리와 윤곽·방향 불일치')
    return errors


def audit_pdf(path, *, expected_size_mm=None, expected_pages=None,
              blank_pages=(), min_image_dpi=0, require_embedded_fonts=True):
    """페이지 번호는 1부터. 빈 뒷면은 렌더링 결과까지 확인한다.

    결과가 machine_pass여도 교육 내용·OCR·인쇄물 조립을 승인한 것은 아니다.
    """
    try:
        import fitz
    except ImportError as exc:
        raise RuntimeError('PDF 검수에는 PyMuPDF가 필요하다: pip install -r requirements-print.txt') from exc
    if (isinstance(min_image_dpi, bool) or not isinstance(min_image_dpi, (int, float))
            or not math.isfinite(min_image_dpi) or min_image_dpi < 0):
        raise ValueError('min_image_dpi는 0 이상의 유한한 수여야 한다')
    if expected_pages is not None and (type(expected_pages) is not int or expected_pages < 1):
        raise ValueError('expected_pages는 1 이상의 정수여야 한다')
    errors, pages = [], []
    report = {'status': 'blocked', 'pdf_sha256': '', 'errors': errors, 'pages': pages,
              'unverified': ['교육 내용과 그림의 의미', '실제 인쇄물의 재단·오려 붙이기']}
    try:
        report['pdf_sha256'] = sha256_file(path)
        pdf = fitz.open(path)
        if not pdf.is_pdf or pdf.needs_pass or len(pdf) == 0:
            pdf.close()
            raise ValueError('열 수 있는 비암호화 PDF가 아니다')
    except Exception as exc:
        errors.append(f'PDF를 읽지 못했다: {exc}')
        return report
    with pdf:
        report['page_count'] = len(pdf)
        if expected_pages is not None and len(pdf) != expected_pages:
            errors.append(f'실제 {len(pdf)}쪽 / 예상 {expected_pages}쪽')
        blanks = set(blank_pages)
        if any(isinstance(p, bool) or not isinstance(p, int) or p < 1 or p > len(pdf) for p in blanks):
            errors.append('빈 뒷면 페이지 번호가 PDF 범위를 벗어났다')
        for number, page in enumerate(pdf, 1):
            size = [page.rect.width * 25.4 / 72, page.rect.height * 25.4 / 72]
            item = {'page': number, 'size_mm': [round(v, 3) for v in size], 'images': []}
            pages.append(item)
            if expected_size_mm and any(abs(a-b) > 0.1 for a, b in zip(size, expected_size_mm)):
                errors.append(f'{number}쪽 판형 {item["size_mm"]}mm / 예상 {list(expected_size_mm)}mm')
            if page.rotation:
                errors.append(f'{number}쪽 회전값 {page.rotation}도: 물리 판형과 방향 확인 필요')
            text_dict = page.get_text('dict')
            used_fonts = set()
            for block in text_dict['blocks']:
                for line in block.get('lines', []):
                    for span in line.get('spans', []):
                        if not span['text'].strip():
                            continue
                        used_fonts.add(span['font'].replace(' ', ''))
                        if '\ufffd' in span['text'] or '\x00' in span['text']:
                            errors.append(f'{number}쪽 문자 추출에 깨진 글자가 있다')
                        x0, y0, x1, y1 = span['bbox']
                        if x0 < -0.5 or y0 < -0.5 or x1 > page.rect.width + 0.5 or y1 > page.rect.height + 0.5:
                            errors.append(f'{number}쪽 글자가 페이지 경계를 벗어났다: {span["text"][:30]}')
            if require_embedded_fonts:
                for font in page.get_fonts(full=True):
                    xref, extension, kind, name = font[:4]
                    short = name.split('+')[-1].replace(' ', '')
                    if short in used_fonts and kind != 'Type3' and not pdf.extract_font(xref)[3]:
                        errors.append(f'{number}쪽 사용 폰트가 포함되지 않았다: {name}')
            for info in page.get_image_info():
                x0, y0, x1, y1 = info['bbox']
                if x1 <= x0 or y1 <= y0:
                    continue
                dpi = min(info['width'] * 72 / (x1-x0), info['height'] * 72 / (y1-y0))
                item['images'].append({'dpi': round(dpi, 2), 'pixels': [info['width'], info['height']]})
                if dpi + 0.1 < min_image_dpi:
                    errors.append(f'{number}쪽 이미지 {dpi:.1f}dpi / 최소 {min_image_dpi}dpi')
            if number in blanks:
                pix = page.get_pixmap(dpi=36, colorspace=fitz.csGRAY, alpha=False)
                # 뒷면에는 쪽번호·옅은 장식·주석도 허용하지 않는다.
                item['blank'] = all(value >= 254 for value in pix.samples)
                if not item['blank'] or page.get_text().strip() or next(page.annots(), None) is not None:
                    errors.append(f'{number}쪽 오리기 뒷면이 비어 있지 않다')
        report['status'] = 'blocked' if errors else 'machine_pass'
    return report
