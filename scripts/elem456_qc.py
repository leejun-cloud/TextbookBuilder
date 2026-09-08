#!/usr/bin/env python3
"""초등부 456 v2 콘텐츠 JSON을 기계 점검한다.

  - 원천 일치: 오늘의 한 문장·빈칸·중심 본문·질문 라벨·암송이 source-lessons120.json 그대로인가
  - 읽기 분량: 학년 밴드 (4: 300–420 / 5: 430–560 / 6: 570–720, 공백 제외) + 문단 수 (2/2/3)
  - 인용 안전: q[].verse 가 저장소의 검증된 낫표 인용(또는 승인 구절 파일)의 부분문자열인가
  - 어투: JSON 문자열에 ~습니다/~입니다 금지 (해요체)
  - 과간 중복: 읽기 문장이 다른 과와 겹치는가

사용법: python3 scripts/elem456_qc.py [--grade 4] [--only 1,2] [--corpus-refresh]
"""
import argparse, glob, json, os, re, sys
from collections import defaultdict

ROOT = 'projects/elementary-456-v2'
SRC = os.path.join(ROOT, 'sources/source-lessons120.json')
CORPUS_CACHE = os.path.join(ROOT, 'sources/.verse-corpus.txt')
APPROVED = os.path.join(ROOT, 'sources/verses-approved.txt')

READ_BAND = {4: (300, 430, 2), 5: (420, 560, 2), 6: (540, 720, 3)}  # 공백 포함
POLITE = re.compile(r'(습니다|입니다)(?=[.\s"”」)]|$)')
# 담임목사 표준안(승인본)이 원천 문구를 미세 수정한 곳 — 라벨 정확 대조를 건너뛴다
APPROVED_LABEL_SKIP = {(6, 1)}


def norm(s):
    return re.sub(r'\s+', '', s or '')


# 저장소 옛 원고에 남아 있는 잘못된 인용 — 코퍼스에서 배제한다 (사람이 확인해 등재)
BLOCKLIST = [
    '다른 사람의 피를 흘리면 그 사람의 피도 흘릴 것이니',  # 창 9:6 오인용, 정본은 「무릇 사람의 피를 흘리면 사람이 그 피를 …」
]


def build_corpus():
    """저장소의 모든 낫표 인용(길이 10+)을 모은다. 시간이 걸리므로 캐시한다."""
    quotes = set()
    for base in glob.glob('projects/*/lessons'):
        for path in glob.glob(os.path.join(base, '**', '*.md'), recursive=True):
            try:
                s = open(path, encoding='utf-8').read()
            except Exception:
                continue
            for q in re.findall(r'「(.+?)」', s, re.S):
                q = norm(q)
                if len(q) >= 10 and not any(norm(b) in q for b in BLOCKLIST):
                    quotes.add(q)
    if os.path.isfile(APPROVED):
        # 승인 파일은 사람이 확인한 목록이므로 짧은 구절도 받는다 (예: 창 3:9)
        for line in open(APPROVED, encoding='utf-8'):
            if line.lstrip().startswith('#'):
                continue
            line = norm(line)
            if len(line) >= 5:
                quotes.add(line)
    with open(CORPUS_CACHE, 'w', encoding='utf-8') as f:
        f.write('\n'.join(sorted(quotes)))
    return quotes


def load_corpus(refresh):
    if refresh or not os.path.isfile(CORPUS_CACHE):
        return build_corpus()
    return set(open(CORPUS_CACHE, encoding='utf-8').read().split('\n'))


def load_source():
    src = json.load(open(SRC, encoding='utf-8'))
    return {(x['year'] + 3, x['local_no']): x for x in src}


def qc_one(path, src, corpus):
    x = json.load(open(path, encoding='utf-8'))
    g, n = x['grade'], x['no']
    issues = []
    s = src.get((g, n))
    if not s:
        return [('ERROR', f'원천에 {g}학년 {n}과가 없다')], x

    # 원천 일치
    for field, sfield, name in [('core', 'core', '오늘의 한 문장'), ('blank', 'blank', '빈칸'),
                                ('center', 'center', '중심 본문'), ('title', 'title', '제목')]:
        a_, b_ = norm(x.get(field)), norm(s.get(sfield))
        if field == 'title':  # 표준안이 의문형 제목에 ?를 붙인다 — 물음표 차이는 허용
            a_, b_ = a_.rstrip('?'), b_.rstrip('?')
        if a_ != b_:
            issues.append(('ERROR', f'{name}이 원천과 다르다: {str(x.get(field))[:40]}'))
    if x.get('common_no') != s['common_no']:
        issues.append(('ERROR', f'공통 과번호 불일치 {x.get("common_no")} != {s["common_no"]}'))
    if bool(x.get('required_memory')) != bool(s.get('required_memory')):
        issues.append(('ERROR', '필수암송 표시가 원천과 다르다'))
    # 암송: 원천 memory = "장절 본문" 형태
    mem = norm(s.get('memory', ''))
    if norm(x.get('memory_ref', '') + x.get('memory_text', '')) != mem:
        issues.append(('ERROR', f'암송이 원천과 다르다: {x.get("memory_ref")} {str(x.get("memory_text"))[:25]}'))
    # 질문 2개 라벨
    sq = s.get('questions', [])
    xq = x.get('q', [])
    if len(xq) != 2:
        issues.append(('ERROR', f'질문이 {len(xq)}개 (2개여야 함)'))
    for i, q in enumerate(xq):
        if (g, n) not in APPROVED_LABEL_SKIP and i < len(sq) and norm(q.get('label')) != norm(sq[i]):
            issues.append(('ERROR', f'질문 {i+1} 라벨이 원천과 다르다'))
        # 라벨에 괄호 장절이 있으면 ref와 일치해야 한다. 후속 질문(괄호 없음)은 ref를 자유롭게 둔다.
        ref = q.get('ref', '')
        m_label = re.search(r'\(([^)]+)\)\s*$', q.get('label', ''))
        if m_label and norm(m_label.group(1)) != norm(ref):
            issues.append(('WARN', f'질문 {i+1} 라벨 괄호({m_label.group(1)})와 ref({ref})가 다르다'))
        # 인용 안전 (verse_is_fact = 장절 없는 사실 확인 답 — 성경 인용 검증 제외)
        if q.get('verse_is_fact'):
            if not norm(q.get('verse', '')):
                issues.append(('ERROR', f'질문 {i+1} 사실 확인 답이 비었다'))
        elif q.get('verse_todo'):
            issues.append(('VERSE', f'질문 {i+1} 확인구절 미확정 ({ref})'))
        else:
            v = norm(q.get('verse', ''))
            parts = [norm(p) for p in re.split(r'…|\.\.\.', q.get('verse', '')) if norm(p)]
            if not v:
                issues.append(('ERROR', f'질문 {i+1} 확인구절이 비었다'))
            elif not all(any(p in c for c in corpus) for p in parts):
                # 짧은 구절은 코퍼스에 실려 있으면 통과한다 (예: 창 3:9 「네가 어디 있느냐」)
                issues.append(('ERROR', f'질문 {i+1} 확인구절({ref})이 검증된 인용에 없다 — 지어냈거나 오타'))

    # 읽기 분량
    lo, hi, paras = READ_BAND[g]
    reading = x.get('reading', [])
    total = sum(len(' '.join(p.split())) for p in reading)
    if len(reading) != paras:
        issues.append(('ERROR', f'읽기 문단 {len(reading)}개 (기준 {paras}개)'))
    if not lo <= total <= hi:
        lvl = 'WARN' if lo * 0.9 <= total <= hi * 1.1 else 'ERROR'
        issues.append((lvl, f'읽기 분량 {total}자 (기준 {lo}–{hi})'))

    # 어투 (sensitivity는 운영 문구라 제외)
    blob = json.dumps({k: v for k, v in x.items() if k != 'sensitivity'}, ensure_ascii=False)
    m = POLITE.search(blob)
    if m and '아닙니다' not in blob[max(0, m.start()-6):m.end()]:
        issues.append(('WARN', f'경어체(~습니다) 사용: …{blob[max(0,m.start()-20):m.end()]}'))

    # 구조
    if len(x.get('think_head', [])) != 3 or len(x.get('think_row', [])) != 3:
        issues.append(('ERROR', '사고활동 표는 3열이어야 한다'))
    if '______' not in x.get('blank', ''):
        issues.append(('ERROR', '빈칸 문장에 ______ 가 없다'))
    if not 1 <= len(x.get('story_lines', [])) <= 2:
        issues.append(('ERROR', '일상 스토리 필기 줄은 1~2개'))
    if s.get('sensitivity') and not x.get('sensitivity'):
        issues.append(('ERROR', '유의 과인데 sensitivity가 비어 있다'))
    return issues, x


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--grade', type=int, default=None)
    ap.add_argument('--only', default=None)
    ap.add_argument('--corpus-refresh', action='store_true')
    a = ap.parse_args()

    corpus = load_corpus(a.corpus_refresh)
    src = load_source()
    grades = [a.grade] if a.grade else [4, 5, 6]
    keep = {int(x) for x in a.only.split(',')} if a.only else None

    nerr = nwarn = nverse = 0
    readings = defaultdict(list)
    n_files = 0
    for g in grades:
        for path in sorted(glob.glob(os.path.join(ROOT, f'content/g{g}', '[0-9][0-9][0-9].json'))):
            n = int(os.path.basename(path)[:3])
            if keep and n not in keep:
                continue
            n_files += 1
            issues, x = qc_one(path, src, corpus)
            for p in x.get('reading', []):
                for sent in re.split(r'(?<=[.?!])\s+', p):
                    k = norm(sent)
                    if len(k) >= 25:
                        readings[k].append(f'{g}-{x["no"]}')
            lv = [i[0] for i in issues]
            nerr += lv.count('ERROR'); nwarn += lv.count('WARN'); nverse += lv.count('VERSE')
            if issues:
                print(f'\n{g}학년 {x.get("no", "?"):>2}과 ({os.path.basename(path)})')
                for lvl, msg in issues:
                    print(f'   {lvl:<6} {msg}')

    ndup = 0
    for k, where in readings.items():
        if len(set(where)) > 1:
            ndup += 1
            print(f'   DUP    {sorted(set(where))} 읽기 문장 겹침: {k[:36]}…')

    print('\n' + '─' * 60)
    print(f'점검 {n_files}과 · ERROR {nerr} · WARN {nwarn} · 인용미확정 {nverse} · DUP {ndup}')
    return 1 if nerr else 0


if __name__ == '__main__':
    sys.exit(main())
