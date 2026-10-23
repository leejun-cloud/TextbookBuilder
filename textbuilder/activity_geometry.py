"""오려 붙이기 명세와 물리 치수. 조각과 빈자리는 하나의 정의만 공유한다."""
from __future__ import annotations

import copy
import json
import math
from pathlib import Path

from .model import PAGE_SIZES_MM
from .print_qc import sha256_file


class ActivityError(ValueError):
    pass


def number(value, name, minimum=0, *, positive=False):
    if (isinstance(value, bool) or not isinstance(value, (int, float)) or
            not math.isfinite(value) or value < minimum or (positive and value == 0)):
        raise ActivityError(f'{name}: {minimum} 이상의 유한한 수가 필요하다')
    return float(value)


def keys(value, allowed, name, required=()):
    if not isinstance(value, dict):
        raise ActivityError(f'{name}: 객체가 필요하다')
    unknown = set(value) - set(allowed)
    missing = set(required) - set(value)
    if unknown or missing:
        raise ActivityError(f'{name}: 알 수 없는 필드 {sorted(unknown)} / 누락 필드 {sorted(missing)}')


def _cross(a, b, c):
    return (b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0])


def _intersects(a, b, c, d):
    def on(p, q, r):
        return abs(_cross(p, q, r)) < 1e-10 and min(p[0], q[0]) <= r[0] <= max(p[0], q[0]) and min(p[1], q[1]) <= r[1] <= max(p[1], q[1])
    if any((on(a, b, c), on(a, b, d), on(c, d, a), on(c, d, b))):
        return True
    return (_cross(a,b,c)*_cross(a,b,d) < 0 and _cross(c,d,a)*_cross(c,d,b) < 0)


def outline(value):
    if isinstance(value, str) and value in ('rectangle', 'ellipse'):
        return value
    if not isinstance(value, list) or len(value) < 3:
        raise ActivityError('outline: rectangle/ellipse 또는 0~1 좌표의 다각형이 필요하다')
    points = []
    for p in value:
        if not isinstance(p, list) or len(p) != 2:
            raise ActivityError('outline: 각 점은 [x,y]여야 한다')
        points.append([number(p[0], 'outline.x'), number(p[1], 'outline.y')])
    if points[0] == points[-1]:
        points.pop()
    if len(points) < 3 or any(max(p) > 1 for p in points) or len({tuple(p) for p in points}) != len(points):
        raise ActivityError('outline: 범위를 벗어나거나 중복된 점이 있다')
    area = sum(p[0]*q[1]-q[0]*p[1] for p,q in zip(points, points[1:]+points[:1]))
    if abs(area) < 1e-10:
        raise ActivityError('outline: 면적이 0이다')
    n = len(points)
    for i in range(n):
        for j in range(i+1,n):
            if j == i+1 or (i == 0 and j == n-1):
                continue
            if _intersects(points[i],points[(i+1)%n],points[j],points[(j+1)%n]):
                raise ActivityError('outline: 윤곽이 자기 교차한다')
    return points


def compare_pair(target, piece):
    """동일 로컬 좌표에서 비교한다. 회전·크기·반전을 맞춰주는 보정은 하지 않는다."""
    errors = []
    for field in ('id', 'source_sha256', 'crop_px', 'outline'):
        if target.get(field) != piece.get(field):
            errors.append(f'{field} 불일치')
    for field in ('width_mm', 'height_mm'):
        a, b = target.get(field), piece.get(field)
        try:
            number(a, field, positive=True)
            number(b, field, positive=True)
            if abs(a-b) > 1e-7:
                errors.append(f'{field} 불일치: {a} / {b}')
        except ActivityError as exc:
            errors.append(str(exc))
    for obj in (target, piece):
        if obj.get('rotation', 0) != 0 or obj.get('flip', False) is not False:
            errors.append('회전·좌우반전 금지')
    return errors


def load_plan(path):
    """일반 삽화가 아닌 완성 장면에서 잘라낼 crop_px를 명시한다."""
    try:
        from PIL import Image
    except ImportError as exc:
        raise ActivityError('pip install -r requirements-print.txt 를 먼저 실행하라') from exc
    path = Path(path).resolve()
    data = json.loads(path.read_text(encoding='utf-8'))
    keys(data, ('schema','language','page','activities'), 'manifest', ('schema','activities'))
    if data['schema'] != 'cut-paste/v1':
        raise ActivityError('schema는 cut-paste/v1이어야 한다')
    if data.get('language','ko') not in ('ko','en'):
        raise ActivityError('language는 ko 또는 en이어야 한다')
    keys(data.get('page', {}), ('size','margin_mm','gutter_mm','min_dpi','min_piece_mm'), 'page')
    page = dict(data.get('page', {}))
    size = page.get('size', 'B5')
    if size not in PAGE_SIZES_MM:
        raise ActivityError(f'지원하지 않는 판형: {size}')
    w, h = PAGE_SIZES_MM[size]
    settings = {'size': size, 'width_mm':w, 'height_mm':h}
    for k, default in [('margin_mm',14),('gutter_mm',6),('min_dpi',300),('min_piece_mm',12)]:
        settings[k] = number(page.get(k, default), 'page.'+k, positive=True)
    margin, gutter = settings['margin_mm'],settings['gutter_mm']
    if margin*2+gutter >= w or margin*2+50 >= h:
        raise ActivityError('여백·제본 여백이 페이지보다 크다')
    activities = data['activities']
    if not isinstance(activities,list) or not activities:
        raise ActivityError('activities가 비었다')
    seen_activities, result = set(), []
    for activity in activities:
        keys(activity, ('id','title','instruction','scene','pieces'), 'activity', ('id','title','scene','pieces'))
        for k in ('id','title'):
            if not isinstance(activity[k],str) or not activity[k].strip():
                raise ActivityError(f'activity.{k}: 빈 문자열을 쓸 수 없다')
        aid = activity['id']
        if aid in seen_activities:
            raise ActivityError(f'중복 activity.id: {aid}')
        seen_activities.add(aid)
        instruction = activity.get('instruction', '조각을 오려 같은 모양의 빈자리에 붙여요.' if data.get('language','ko')=='ko' else 'Cut out the pieces and paste them in the matching spaces.')
        if not isinstance(instruction,str):
            raise ActivityError('instruction은 문자열이어야 한다')
        scene=activity['scene']
        keys(scene, ('src','x_mm','y_mm','width_mm'), 'scene', ('src','x_mm','y_mm','width_mm'))
        if not isinstance(scene['src'],str) or not scene['src']:
            raise ActivityError('scene.src: 완성 장면 파일을 지정하라')
        source=(path.parent/scene['src']).resolve()
        try:
            with Image.open(source) as image:
                if image.format not in ('PNG','JPEG') or image.getexif().get(274,1) != 1:
                    raise ActivityError('완성 장면은 EXIF 회전이 없는 PNG/JPEG로 저장하라')
                iw, ih=image.size
                image.load()
        except (OSError, ValueError) as exc:
            raise ActivityError(f'장면 이미지를 읽을 수 없다: {source.name}') from exc
        sw=number(scene['width_mm'],'scene.width_mm',positive=True)
        sh=sw*ih/iw
        sx,sy=number(scene['x_mm'],'scene.x_mm'),number(scene['y_mm'],'scene.y_mm')
        if sx < margin+gutter or sy < 48 or sx+sw > w-margin-gutter or sy+sh > h-margin-12:
            raise ActivityError(f'{aid}: 장면이 제목·본문·제본 안전 영역을 벗어났다')
        dpi=iw/sw*25.4
        if dpi+0.1 < settings['min_dpi']:
            raise ActivityError(f'{aid}: 장면 {dpi:.1f}dpi / 최소 {settings["min_dpi"]}dpi')
        pieces=activity['pieces']
        if not isinstance(pieces,list) or not pieces:
            raise ActivityError(f'{aid}: pieces가 비었다')
        seen, normalized = set(),[]
        digest=sha256_file(source)
        for piece in pieces:
            keys(piece, ('id','label','crop_px','outline'), 'piece', ('id','crop_px','outline'))
            pid=piece['id']
            if not isinstance(pid,str) or not pid.strip() or pid in seen:
                raise ActivityError(f'{aid}: 비었거나 중복된 piece.id')
            seen.add(pid)
            label=piece.get('label',pid)
            if not isinstance(label,str):
                raise ActivityError('piece.label은 문자열이어야 한다')
            crop=piece['crop_px']
            if not isinstance(crop,list) or len(crop)!=4 or any(type(v) is not int for v in crop):
                raise ActivityError('crop_px는 정수 픽셀 [x,y,w,h]여야 한다')
            x,y,cw,ch=crop
            if min(x,y)<0 or min(cw,ch)<=0 or x+cw>iw or y+ch>ih:
                raise ActivityError(f'{aid}/{pid}: crop_px가 원본을 벗어났다')
            pw,ph=cw*sw/iw,ch*sw/iw
            if min(pw,ph)<settings['min_piece_mm']:
                raise ActivityError(f'{aid}/{pid}: 조각 {pw:.1f}x{ph:.1f}mm가 최소 크기보다 작다. 완성 장면을 크게 설계하라')
            geom={'id':pid,'label':label,'source_sha256':digest,'crop_px':crop,
                  'outline':outline(piece['outline']),'width_mm':pw,'height_mm':ph}
            # 윤곽을 포함한 사각 영역이 겹치면 보수적으로 수동 조정하도록 한다.
            for other in normalized:
                ox,oy,ow,oh=other['crop_px']
                if x<ox+ow and x+cw>ox and y<oy+oh and y+ch>oy:
                    raise ActivityError(f'{aid}: 조각 영역이 겹친다: {pid}/{other["id"]}')
            normalized.append(geom)
        result.append({'id':aid,'title':activity['title'],'instruction':instruction,
                       'source':str(source),'source_sha256':digest,'pixels':[iw,ih],
                       'scene_mm':[sx,sy,sw,sh],'pieces':normalized})
    return {'schema':'cut-paste/v1','language':data.get('language','ko'),'manifest_sha256':sha256_file(path),
            'manifest':str(path),'page':settings,'activities':result}


def pack_cutouts(plan):
    """크기를 줄이거나 돌리지 않고 선반 방식으로 배치. 좌표는 왼쪽 위 기준 mm."""
    page=plan['page']; margin=page['margin_mm']; gap=7.0; label=9.0
    left=margin+page['gutter_mm']; right=page['width_mm']-margin-page['gutter_mm']
    bottom=page['height_mm']-margin-12
    x,y,row_height=left,43.0,0.0
    sheets=[[]]
    for ai,activity in enumerate(plan['activities']):
        for canonical in activity['pieces']:
            piece=copy.deepcopy(canonical)
            w,h=piece['width_mm'],piece['height_mm']
            if w>right-left or h+label>bottom-43:
                raise ActivityError(f'{activity["id"]}/{piece["id"]}: 오리기 면에 원래 크기로 들어가지 않는다')
            if x+w>right+1e-8:
                x,y,row_height=left,y+row_height+gap,0.0
            if y+label+h>bottom+1e-8:
                sheets.append([]); x,y,row_height=left,43.0,0.0
            piece.update(activity_index=ai,x_mm=x,y_mm=y+label)
            if compare_pair(canonical,piece):
                raise ActivityError('조각 배치에서 원본과 불일치가 발생했다')
            sheets[-1].append(piece)
            x+=w+gap; row_height=max(row_height,h+label)
    return sheets
