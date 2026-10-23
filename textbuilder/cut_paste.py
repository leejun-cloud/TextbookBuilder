"""한 원본에서 활동면·조각 부록·조립본을 만들고 양면 책 PDF로 합친다."""
from __future__ import annotations

import os
from pathlib import Path
import tempfile

from .activity_geometry import ActivityError, load_plan, pack_cutouts
from .print_qc import audit_pdf, audit_cutout_geometry, sha256_file, write_report


WORDS = {
    'ko': {'appendix':'오려 붙이기 부록', 'guide':'조각의 크기를 바꾸지 말고 점선을 따라 오려요.',
           'footer':'실제 크기 100%로 인쇄해요. 조각은 책 뒤 부록에 있어요.', 'proof':'교사용 조립 확인',
           'page':'쪽', 'scale':'50mm 크기 확인선'},
    'en': {'appendix':'Cut-out appendix', 'guide':'Cut on the dotted lines. Keep the original size.',
           'footer':'Print at 100%. Find the pieces in the appendix.', 'proof':'Assembly proof',
           'page':'p.', 'scale':'50 mm calibration line'},
}


def _font(path, texts):
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    candidates = [path] if path else [
        str(Path.home()/'Library/Fonts/NanumGothic.ttf'),
        '/Library/Fonts/NanumGothic.ttf',
        '/System/Library/Fonts/AppleSDGothicNeo.ttc',
        '/usr/share/fonts/truetype/nanum/NanumGothic.ttf',
        '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
        'C:/Windows/Fonts/malgun.ttf',
    ]
    required={ord(ch) for t in texts for ch in t if not ch.isspace()}
    for candidate in candidates:
        if not candidate or not Path(candidate).is_file():
            continue
        try:
            name='TextbookPrint'+sha256_file(candidate)[:12]
            face=TTFont(name,candidate)
            if required-set(face.face.charToGlyph):
                continue
            pdfmetrics.registerFont(face)
            return name
        except Exception:
            continue
    raise ActivityError('모든 글자를 포함한 TrueType 폰트가 필요하다. --font /경로/NanumGothic.ttf 를 지정하라')


def _text(c, text, x, top, width, font, size=12, minimum=9):
    from reportlab.pdfbase.pdfmetrics import stringWidth
    from reportlab.lib.units import mm
    if '\n' in text or '\r' in text:
        raise ActivityError('제목·조각 라벨에는 줄바꿈을 사용할 수 없다')
    while stringWidth(text,font,size)>width*mm and size>minimum:
        size-=0.25
    if stringWidth(text,font,size)>width*mm:
        raise ActivityError(f'문장이 지정 영역보다 길다: {text[:35]}')
    c.setFillColorRGB(.12,.17,.22)
    c.setFont(font,size)
    c.drawString(x*mm,c._pagesize[1]-top*mm,text)


def _wrapped(c,text,x,top,width,font,size=10):
    from reportlab.pdfbase.pdfmetrics import stringWidth
    from reportlab.lib.units import mm
    lines=['']
    for char in text:
        if char=='\n' or stringWidth(lines[-1]+char,font,size)>width*mm:
            lines.append('' if char=='\n' else char)
        else:
            lines[-1]+=char
    if len(lines)>3:
        raise ActivityError('활동 안내는 3줄 이내로 줄여라')
    for i,line in enumerate(lines):
        _text(c,line,x,top+i*4.5,width,font,size,minimum=size)


def _outline(c,piece,x,y):
    from reportlab.lib.units import mm
    w,h=piece['width_mm']*mm,piece['height_mm']*mm
    x,y=x*mm,c._pagesize[1]-y*mm
    p=c.beginPath()
    shape=piece['outline']
    if shape=='rectangle':
        p.rect(x,y-h,w,h)
    elif shape=='ellipse':
        p.ellipse(x,y-h,w,h)
    else:
        p.moveTo(x+shape[0][0]*w,y-shape[0][1]*h)
        for px,py in shape[1:]:
            p.lineTo(x+px*w,y-py*h)
        p.close()
    return p


def _patch(c,image,piece,x,y):
    from reportlab.lib.units import mm
    from reportlab.lib.utils import ImageReader
    cx,cy,cw,ch=piece['crop_px']
    patch=image.crop((cx,cy,cx+cw,cy+ch))
    c.saveState()
    c.clipPath(_outline(c,piece,x,y),stroke=0,fill=0)
    c.drawImage(ImageReader(patch),x*mm,c._pagesize[1]-(y+piece['height_mm'])*mm,
                width=piece['width_mm']*mm,height=piece['height_mm']*mm,mask='auto')
    c.restoreState()


def _opaque(image):
    """투명 장면을 흰 종이 위에 합성한다. 알파를 버려 검게 만들지 않는다."""
    from PIL import Image
    if image.mode=='RGBA' or 'transparency' in image.info:
        layer=image.convert('RGBA')
        paper=Image.new('RGBA',image.size,'white')
        return Image.alpha_composite(paper,layer).convert('RGB')
    return image.convert('RGB')


def _dotted(c,piece,x,y):
    c.saveState()
    c.setStrokeColorRGB(.18,.23,.27); c.setLineWidth(.7); c.setDash(2,2)
    c.drawPath(_outline(c,piece,x,y),stroke=1,fill=0)
    c.restoreState()


def _activity_pages(plan,path,font,page_offset,assembled=False):
    from PIL import Image
    from reportlab.pdfgen.canvas import Canvas
    from reportlab.lib.units import mm
    from reportlab.lib.utils import ImageReader
    page=plan['page']; words=WORDS[plan['language']]
    c=Canvas(str(path),pagesize=(page['width_mm']*mm,page['height_mm']*mm))
    c.setTitle(words['proof'] if assembled else 'Textbook activities')
    left=page['margin_mm']+page['gutter_mm']; width=page['width_mm']-left-page['margin_mm']
    for index,activity in enumerate(plan['activities']):
        _text(c,activity['title'],left,22,width,font,19,14)
        _wrapped(c,activity['instruction'],left,32,width,font)
        sx,sy,sw,sh=activity['scene_mm']
        with Image.open(activity['source']) as raw:
            image=_opaque(raw)
            c.drawImage(ImageReader(image),sx*mm,(page['height_mm']-sy-sh)*mm,width=sw*mm,height=sh*mm)
            iw,ih=activity['pixels']
            for piece in activity['pieces']:
                cx,cy,cw,ch=piece['crop_px']
                tx,ty=sx+cx*sw/iw,sy+cy*sh/ih
                c.saveState(); c.setFillColorRGB(1,.985,.94)
                c.drawPath(_outline(c,piece,tx,ty),stroke=0,fill=1); c.restoreState()
                if assembled:
                    _patch(c,image,piece,tx,ty)
                else:
                    _dotted(c,piece,tx,ty)
        _text(c,words['proof'] if assembled else words['footer'],left,page['height_mm']-16,width,font,9)
        _text(c,f'{words["page"]} {page_offset+index+1}',left,page['height_mm']-10,width,font,9)
        c.showPage()
    c.save()


def _cutout_pages(plan,sheets,path,font,page_offset):
    from PIL import Image
    from reportlab.pdfgen.canvas import Canvas
    from reportlab.lib.units import mm
    page=plan['page']; words=WORDS[plan['language']]
    left=page['margin_mm']+page['gutter_mm']; width=page['width_mm']-left-page['margin_mm']
    c=Canvas(str(path),pagesize=(page['width_mm']*mm,page['height_mm']*mm))
    for sheet in sheets:
        _text(c,words['appendix'],left,22,width,font,19)
        _text(c,words['guide'],left,32,width,font,10)
        for piece in sheet:
            activity=plan['activities'][piece['activity_index']]
            label=f'{words["page"]} {page_offset+piece["activity_index"]+1} / {activity["id"]} / {piece["label"]}'
            _text(c,label,piece['x_mm'],piece['y_mm']-2,piece['width_mm'],font,9,7)
            with Image.open(activity['source']) as raw:
                _patch(c,_opaque(raw),piece,piece['x_mm'],piece['y_mm'])
            _dotted(c,piece,piece['x_mm'],piece['y_mm'])
        y=18
        c.line(left*mm,y*mm,(left+50)*mm,y*mm)
        _text(c,words['scale'],left,page['height_mm']-12,width,font,8)
        c.showPage()
        # 빈 뒷면에 페이지 번호나 장식을 넣지 않는다.
        c.showPage()
    c.save()


def build_book(manifest, output, *, body_pdf=None, font_path=None):
    """모든 검사 통과 후에만 산출물을 교체한다. 기존 본문은 그대로 앞에 붙인다."""
    try:
        from pypdf import PdfReader, PdfWriter
    except ImportError as exc:
        raise ActivityError('pip install -r requirements-print.txt 를 먼저 실행하라') from exc
    plan=load_plan(manifest); sheets=pack_cutouts(plan)
    output=Path(output).resolve()
    if output.suffix.lower()!='.pdf':
        raise ActivityError('출력 파일은 .pdf여야 한다')
    page=plan['page']; dims=(page['width_mm'],page['height_mm'])
    prefix_count=0; prefix_hash=None
    if body_pdf:
        body_pdf=Path(body_pdf).resolve()
        body_report=audit_pdf(body_pdf,expected_size_mm=dims,min_image_dpi=page['min_dpi'])
        if body_report['status']!='machine_pass':
            raise ActivityError('본문 PDF 검수 실패: '+'; '.join(body_report['errors']))
        prefix_count=body_report['page_count']; prefix_hash=body_report['pdf_sha256']
    words=WORDS[plan['language']]
    texts=list(words.values())+[str(i) for i in range(prefix_count+len(plan['activities'])+len(sheets)*2+3)]
    texts += [text for a in plan['activities'] for text in (a['id'],a['title'],a['instruction'])]
    texts += [p['label'] for a in plan['activities'] for p in a['pieces']]
    font=_font(font_path,texts+[' / '])
    output.parent.mkdir(parents=True,exist_ok=True)
    destinations={name:output.with_name(output.stem+'.'+suffix) for name,suffix in
                  [('activities','activities.pdf'),('cutouts','cutouts.pdf'),('assembled','assembled.pdf'),('report','qc.json')]}
    destinations['book']=output
    with tempfile.TemporaryDirectory(prefix='cut-paste-',dir=output.parent) as folder:
        staged={k:Path(folder)/v.name for k,v in destinations.items()}
        _activity_pages(plan,staged['activities'],font,prefix_count)
        _activity_pages(plan,staged['assembled'],font,prefix_count,True)
        _cutout_pages(plan,sheets,staged['cutouts'],font,prefix_count)
        writer=PdfWriter()
        if body_pdf:
            writer.append(str(body_pdf))
        writer.append(str(staged['activities']))
        before_appendix=len(writer.pages)
        if before_appendix%2:
            writer.add_blank_page(width=dims[0]*72/25.4,height=dims[1]*72/25.4)
        appendix_start=len(writer.pages)+1
        writer.append(str(staged['cutouts']))
        with staged['book'].open('wb') as stream:
            writer.write(stream)
        writer.close()
        blank_pages=list(range(appendix_start+1,appendix_start+len(sheets)*2,2))
        if before_appendix%2:
            blank_pages.insert(0,before_appendix+1)
        expected=appendix_start-1+len(sheets)*2
        report=audit_pdf(staged['book'],expected_size_mm=dims,expected_pages=expected,
                         blank_pages=blank_pages,min_image_dpi=page['min_dpi'])
        report['errors'].extend(audit_cutout_geometry(staged['activities'],staged['cutouts'],plan,sheets))
        report.update(manifest_sha256=plan['manifest_sha256'],body_sha256=prefix_hash,
                      sources=[{'activity':a['id'],'sha256':a['source_sha256']} for a in plan['activities']],
                      appendix_start=appendix_start,blank_pages=blank_pages,
                      pairs=[{'activity':a['id'],'id':p['id'],'width_mm':p['width_mm'],
                              'height_mm':p['height_mm'],'status':'pdf_contours_match'}
                             for a in plan['activities'] for p in a['pieces']])
        for name,count in [('activities',len(plan['activities'])),('assembled',len(plan['activities'])),('cutouts',len(sheets)*2)]:
            check=audit_pdf(staged[name],expected_size_mm=dims,expected_pages=count,
                            blank_pages=range(2,count+1,2) if name=='cutouts' else (),min_image_dpi=page['min_dpi'])
            report['errors'].extend(f'{name}: {e}' for e in check['errors'])
        # 검사 중 원본이 바뀌면 이전 근거를 재사용하지 않는다.
        if sha256_file(manifest)!=plan['manifest_sha256'] or any(sha256_file(a['source'])!=a['source_sha256'] for a in plan['activities']):
            report['errors'].append('검사 중 원고 또는 원본 이미지가 바뀌었다')
        if body_pdf and sha256_file(body_pdf)!=prefix_hash:
            report['errors'].append('검사 중 본문 PDF가 바뀌었다')
        if report['errors']:
            report['status']='blocked'
            write_report(destinations['report'],report)
            raise ActivityError('출력 차단: '+'; '.join(report['errors']))
        report['files']={k:{'name':destinations[k].name,'sha256':sha256_file(staged[k])}
                         for k in ('book','activities','cutouts','assembled')}
        write_report(staged['report'],report)
        for name in ('activities','cutouts','assembled','book','report'):
            os.replace(staged[name],destinations[name])
    return {k:str(v) for k,v in destinations.items()},report
