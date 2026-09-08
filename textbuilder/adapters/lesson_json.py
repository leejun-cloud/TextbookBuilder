#!/usr/bin/env python3
"""어댑터 (B): 콘텐츠 JSON → BookDocument.

두 스키마를 받는다.

1. `kids-lesson` (요청서 §7) — JSON 하나로 4페이지 어린이 교재가 나온다.
   grade / lesson / title / story / keywords / activities / memoryVerse / prayer / reflection / assets
2. `elem456` — 이미 저장소에서 쓰는 초등 3권 콘텐츠(`projects/elementary-456-v2/content/gN/NNN.json`).
   3페이지 구조. 기존 파일을 고치지 않고 읽는다.

스키마는 파일 안의 `schema` 필드 또는 키 모양으로 자동 판별한다.
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List

from ..model import BookDocument, Page, blk


def detect_schema(d: Dict[str, Any]) -> str:
    if d.get('schema'):
        return str(d['schema'])
    if 'q' in d and 'reading' in d and 'core' in d:
        return 'elem456'
    if 'story' in d and ('memoryVerse' in d or 'activities' in d or 'keywords' in d):
        return 'kids-lesson'
    raise ValueError('콘텐츠 JSON 스키마를 판별할 수 없다. "schema": "kids-lesson" 또는 "elem456"을 넣어라.')


def parse(path: str, *, theme: str = '', template: str = '',
          page_size: str = 'B5') -> BookDocument:
    with open(path, encoding='utf-8') as f:
        d = json.load(f)
    schema = detect_schema(d)
    if schema == 'kids-lesson':
        doc = _from_kids_lesson(d)
        default_template = 'workbook/junior'
        default_theme = 'kids-junior'
    elif schema == 'elem456':
        doc = _from_elem456(d)
        default_template = 'workbook/elementary'
        default_theme = 'kids-bright'
    else:
        raise ValueError(f'모르는 스키마: {schema}')
    doc.template = template or default_template
    doc.theme = theme or default_theme
    doc.page_setup.size = page_size
    doc.source = os.path.abspath(path)
    doc.assets_root = os.path.dirname(os.path.abspath(path))
    return doc


# ---------------------------------------------------------------- kids-lesson (4쪽)

def _img(a: Dict[str, Any], role: str, default_fit: str = 'contain'):
    """assets의 항목 → image 블록. 문자열이면 경로만 준 것으로 본다."""
    if isinstance(a, str):
        a = {'src': a}
    src = a.get('src', '')
    if not src:
        return None
    attrs = {'role': a.get('role', role), 'fit': a.get('fit', default_fit)}
    for k in ('position', 'caption', 'alt', 'bleed', 'crop', 'radius', 'width', 'height'):
        if k in a:
            attrs[k] = a[k]
    return blk('image', src=src, text=a.get('caption', ''), attrs=attrs)


def _from_kids_lesson(d: Dict[str, Any]) -> BookDocument:
    doc = BookDocument()
    doc.metadata.title = d.get('title', '')
    doc.metadata.grade = str(d.get('grade', ''))
    doc.metadata.lesson_no = d.get('lesson')
    doc.metadata.unit = d.get('unit', '')
    doc.metadata.department = d.get('department', '')
    doc.metadata.badge = d.get('badge', '') or (f"{d.get('grade','')} · {d.get('lesson','')}과".strip(' ·'))
    doc.metadata.kicker = d.get('kicker', '다음세대 교리교육')
    doc.metadata.footer = d.get('footer', '')
    assets = d.get('assets', {}) or {}
    story = d.get('story', {}) or {}
    if isinstance(story, str):
        story = {'body': [story]}

    # ---- 1쪽 · 시작하고 읽어요
    p1 = Page(layout='kids-story', title=d.get('page_titles', {}).get('p1', '시작하고 읽어요'))
    if story.get('title'):
        p1.blocks.append(blk('heading', text=story['title'], level=1, variant='story'))
    if d.get('opening') or story.get('opening'):
        p1.blocks.append(blk('question', text=d.get('opening') or story.get('opening'),
                             label='생각열기', variant='open'))
    body = story.get('body') or []
    if isinstance(body, str):
        body = [body]
    for para in body:
        p1.blocks.append(blk('text', text=para, variant='story'))
    hero = _img(assets.get('hero') or assets.get('main') or {}, 'hero', 'cover')
    if hero:
        p1.blocks.append(hero)
    words = d.get('words') or d.get('todayWords') or []
    if words:
        p1.blocks.append(blk('keywords', label='오늘의 낱말',
                             items=[_kv_line(w) for w in words], variant='words'))
    doc.pages.append(p1)

    # ---- 2쪽 · 찾고 생각해요
    p2 = Page(layout='kids-find', title=d.get('page_titles', {}).get('p2', '찾고 생각해요'))
    kws = d.get('keywords') or []
    if kws:
        p2.blocks.append(blk('keywords', label='키워드 찾기',
                             items=[_kv_line(k) for k in kws], variant='find'))
    if d.get('coreSentence') or d.get('core'):
        p2.blocks.append(blk('callout', label='핵심 문장',
                             text=d.get('coreSentence') or d.get('core'), variant='core'))
    for q in (d.get('findInWord') or d.get('questions') or []):
        p2.blocks.append(_question_block(q, '말씀에서 찾아요'))
    for q in (d.get('thinkDeeper') or []):
        p2.blocks.append(_question_block(q, '한 걸음 더 생각해요'))
    side = _img(assets.get('illustration') or {}, 'illustration')
    if side:
        p2.blocks.append(side)
    doc.pages.append(p2)

    # ---- 3쪽 · 오늘의 활동
    p3 = Page(layout='kids-activity', title=d.get('page_titles', {}).get('p3', '오늘의 활동'))
    for act in (d.get('activities') or []):
        if isinstance(act, str):
            p3.blocks.append(blk('activity', text=act))
            continue
        steps = act.get('steps') or []
        if isinstance(steps, str):
            steps = [steps]
        b = blk('activity', label=act.get('title', '활동'), text=act.get('intro', ''),
                items=list(steps), variant=act.get('type', ''),
                attrs={k: v for k, v in act.items()
                       if k in ('materials', 'note', 'time', 'answer')})
        p3.blocks.append(b)
        for im in (act.get('images') or []):
            sb = _img(im, 'step')
            if sb:
                p3.blocks.append(sb)
    for fb in (d.get('fillBlanks') or []):
        # 정답은 label(지면 제목)에 넣지 않는다 — 학생 지면에 인쇄되면 안 된다.
        # 정답은 attrs.answer로만 보관하고, 템플릿은 그것을 그리지 않는다.
        p3.blocks.append(blk('fill_blank',
                             text=fb if isinstance(fb, str) else fb.get('text', ''),
                             label='빈칸을 채워요',
                             attrs={} if isinstance(fb, str) or 'answer' not in fb
                                    else {'answer': fb['answer']}))
    doc.pages.append(p3)

    # ---- 4쪽 · 정리하고 고백해요
    p4 = Page(layout='kids-close', title=d.get('page_titles', {}).get('p4', '정리하고 고백해요'))
    if d.get('summary'):
        p4.blocks.append(blk('callout', label='한 문장으로 정리', text=d['summary'], variant='core'))
    if d.get('prayer'):
        p4.blocks.append(blk('prayer', label='오늘의 기도', text=d['prayer']))
    mv = d.get('memoryVerse') or {}
    if isinstance(mv, str):
        mv = {'text': mv}
    if mv.get('text'):
        p4.blocks.append(blk('memory', label='말씀 암송', text=mv['text'], ref=mv.get('ref', '')))
    if d.get('reflection'):
        p4.blocks.append(blk('reflection', label='나의 생각', text=d['reflection'],
                             count=int(d.get('reflectionLines', 3))))
    if d.get('confession'):
        p4.blocks.append(blk('callout', label='오늘의 고백', text=d['confession'], variant='confession'))
    deco = _img(assets.get('decoration') or {}, 'decoration')
    if deco:
        p4.blocks.append(deco)
    doc.pages.append(p4)

    for p in doc.pages:
        if not p.blocks:
            doc.warnings.append(f'{p.title or p.layout} 쪽에 내용이 없다')
    return doc


def _kv_line(x: Any) -> str:
    if isinstance(x, str):
        return x
    if isinstance(x, dict):
        w = x.get('word') or x.get('term') or ''
        m = x.get('meaning') or x.get('desc') or ''
        return f'{w} — {m}' if w and m else (w or m)
    return str(x)


def _question_block(q: Any, label: str):
    if isinstance(q, str):
        return blk('question', text=q, label=label)
    return blk('question', text=q.get('q') or q.get('text', ''), label=q.get('label', label),
               ref=q.get('ref', ''), count=int(q.get('lines', 1)),
               attrs={'answer': q['answer']} if 'answer' in q else {})


# ---------------------------------------------------------------- elem456 (3쪽)

def _from_elem456(d: Dict[str, Any]) -> BookDocument:
    """기존 초등 3권 콘텐츠를 그대로 읽어 3쪽 모델로 만든다(원본 무변경)."""
    doc = BookDocument()
    g, no = int(d['grade']), int(d['no'])
    offset = {4: 0, 5: 40, 6: 80}.get(g, 0)
    doc.metadata.title = d.get('title', '')
    doc.metadata.grade = f'{g}학년'
    doc.metadata.lesson_no = no
    doc.metadata.unit = d.get('unit', '')
    doc.metadata.kicker = '다음세대 교리교육 · 초등부 학생용 교재'
    doc.metadata.badge = (f'{no}과 · {g-3}년차 {no}과 · 초등부 {no+offset}과 · 공통 {d.get("common_no")}과'
                          + (' · ● 필수암송' if d.get('required_memory') else ''))
    doc.metadata.footer = f'{g}학년 · {no}과 · 공통 {d.get("common_no")}과'
    mode = {4: '관찰하고 관계 찾기', 5: '두 본문의 의미 묶기', 6: '주장-근거-이유로 판단'}.get(g, '')
    doc.metadata.extra['mode'] = mode

    p1 = Page(layout='elem-story', title='1 일상 스토리')
    p1.blocks.append(blk('callout', label='오늘의 한 문장', text=d.get('core', ''), variant='core'))
    p1.blocks.append(blk('text', text=d.get('story', ''), variant='story'))
    for lab in (d.get('story_lines') or []):
        p1.blocks.append(blk('writing', label=lab, count=1))
    p1.blocks.append(blk('heading', text='2 말씀 탐험', level=2, variant='banner'))
    p1.blocks.append(blk('text', text='성경을 직접 펴서 먼저 답을 찾아요. 확인구절은 답을 쓴 뒤 읽어요.',
                         variant='accent'))
    p1.blocks.append(blk('text', text=f'중심 본문 {d.get("center","")}', variant='strong'))
    qs = d.get('q') or []
    if qs:
        p1.blocks.extend(_elem_q(qs[0], 1))
    doc.pages.append(p1)

    p2 = Page(layout='elem-find', title='2 말씀 탐험 (계속)')
    if len(qs) > 1:
        p2.blocks.extend(_elem_q(qs[1], 2))
    p2.blocks.append(blk('text', text='도움 사다리  혼자 찾기 → 짝에게 절 위치 힌트 받기 → 교사에게 절 위치만 묻기',
                         variant='ladder'))
    p2.blocks.append(blk('heading', text='2단계 계속 · 성경에서 찾고 확인한 뒤 읽어요', level=3))
    read = blk('callout', label=d.get('reading_title', '말씀 이해 · 읽기'),
               text=(d.get('reading') or [''])[0], items=list((d.get('reading') or [])[1:]),
               variant='reading')
    p2.blocks.append(read)
    p2.blocks.append(blk('heading', text=f'{g}학년 사고활동', level=3))
    p2.blocks.append(blk('table', head=list(d.get('think_head') or []),
                         rows=[list(d.get('think_row') or [])], variant='head+tall'))
    p2.blocks.append(blk('writing', label=d.get('think_line_label', ''),
                         count=int(d.get('think_line_count', 1))))
    doc.pages.append(p2)

    p3 = Page(layout='elem-close', title='3 빈칸·미션 / 4 결단 액션 / 5 말씀 이어가기')
    p3.blocks.append(blk('heading', text='3 빈칸 · 미션', level=2, variant='banner'))
    p3.blocks.append(blk('fill_blank', label='빈칸은 딱 하나', text=d.get('blank', '')))
    p3.blocks.append(blk('text', text=d.get('mission', '')))
    p3.blocks.append(blk('writing', label=d.get('mission_line_label', '나의 미션'),
                         count=int(d.get('mission_line_count', 2))))
    p3.blocks.append(blk('heading', text='4 결단 액션', level=2, variant='banner'))
    p3.blocks.append(blk('text', text=d.get('decision', ''), variant='strong'))
    p3.blocks.append(blk('table', head=list(d.get('decision_cols') or ['언제', '어디서']),
                         rows=[[''] * len(d.get('decision_cols') or ['언제', '어디서'])],
                         variant='head+tall'))
    p3.blocks.append(blk('heading', text='5 말씀 이어가기', level=2, variant='banner'))
    p3.blocks.append(blk('text', text=d.get('share_intro', '')))
    p3.blocks.append(blk('checklist', items=['가족과', '믿을 만한 어른과', '교사와', '혼자 기록'],
                         label='네 방법은 모두 동등한 참여입니다.'))
    p3.blocks.append(blk('text', text=f'{d.get("share_label","나눌 말")}: {d.get("share_text","")}'))
    p3.blocks.append(blk('memory', label=f'암송 · {d.get("memory_ref","")}',
                         text=d.get('memory_text', ''), ref=d.get('memory_ref', '')))
    p3.blocks.append(blk('heading', text='오늘의 한 문장을 내 말로 말해요', level=3))
    p3.blocks.append(blk('writing', label='내 말', count=2))
    p3.blocks.append(blk('text', text='※ 활동 기록은 믿음을 점수로 표시하는 칸이 아닙니다.', variant='fine'))
    doc.pages.append(p3)

    if d.get('sensitivity'):
        doc.metadata.extra['sensitivity'] = d['sensitivity']
    return doc


def _elem_q(q: Dict[str, Any], idx: int) -> List[Any]:
    out = [blk('question', text=f'{"①②"[idx-1]} {q.get("label","")}', label='찾은 답', count=1)]
    out.append(blk('writing', label='찾은 답', count=1))
    label = '답을 쓴 뒤 맞추어 보기' + (f' · {q["ref"]}' if q.get('ref') else '')
    out.append(blk('verse' if not q.get('verse_is_fact') else 'callout',
                   label=label, text=q.get('verse', ''), ref=q.get('ref', ''), variant='check'))
    return out
