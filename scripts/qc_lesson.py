#!/usr/bin/env python3
"""교리공과 과 원고를 기계적으로 점검한다. 에이전트가 아니라 코드로 잡을 수 있는 것만 본다.

  - 분량: 공백 제외 문자 수가 기준 ±10% 안인가
  - 스킴: 필수 블록·표 표시·금지 표시(`## `)·표 앞 [[TABLE:]] 누락
  - 원천 충실도: spec의 핵심 문장·대지·중심 본문·암송구절이 원고에 그대로 있는가
  - 금지 표현: AI 티 문구, 어투 위반(~입니다/~예요)
  - 확인요청 표시: 성경 인용을 미룬 곳
  - 과간 중복: 문장 단위로 다른 과와 겹치는 비율

사용법:
  python3 scripts/qc_lesson.py <lessons_dir> [--only 3,7,12] [--json out.json]
"""
import argparse, glob, json, os, re, sys
from collections import defaultdict

TARGET = {'draft.md': 3660, 'teacher-notes.md': 4140}
TOL = 0.10
WRITE_MIN, WRITE_MAX = 12, 18
CFG = {}  # lessons_dir 상위의 qc-config.json이 있으면 기준을 덮어쓴다
BANNED = ['할 수 있습니다', '살펴봅시다', '함께 알아봅시다', '중요합니다', '알아보겠습니다',
          '~에 대해 알아', '정리해 보자면', '다음과 같습니다', '첫째로,', '결론적으로']
POLITE = re.compile(r'(입니다|습니다|예요|이에요|해요)(?=[.\s,」)]|$)')
# 기도문·고백 인용은 경어체가 정상이므로 제외 구간
POLITE_OK = re.compile(r'(기도|아멘|하소서|하옵|고백|WSC|요리문답)')


def strip_marks(s):
    return re.sub(r'\[\[[^\]]*\]\]', '', s)


def drop_prayer(s):
    """기도문·고백 인용은 경어체가 정상이므로 어투 검사에서 뺀다."""
    return re.sub(r'\*\*기도.*?\[\[/BOX\]\]', '', s, flags=re.S)


def nchars(s):
    return len(re.sub(r'\s', '', strip_marks(s)))


def sentences(s):
    s = strip_marks(s)
    s = re.sub(r'\|[^\n]*\|', ' ', s)          # 표 제거
    s = re.sub(r'^#.*$', ' ', s, flags=re.M)   # 헤더 제거
    out = []
    for raw in re.split(r'(?<=[.?!다])\s+', s):
        t = ' '.join(raw.split())
        if len(t) >= 25 and not t.startswith(('「', '□', '→', '·', '-')):
            out.append(t)
    return out


def read_spec(d):
    p = os.path.join(d, 'spec.md')
    if not os.path.isfile(p):
        return {}
    s = open(p, encoding='utf-8').read()
    g = {}
    m = re.search(r'\*\*핵심 문장\*\*\s*(.+?)(?:\n\n|\n\*\*)', s, re.S)
    g['core'] = ' '.join(m.group(1).split()) if m else ''
    m = re.search(r'◆ 중심 본문\*\*\s*(.+)', s)
    g['main'] = m.group(1).strip() if m else ''
    m = re.search(r'필수암송 표시\(부록1 기준\): (◎|○|없음)(?: · 암송구절 (.+))?', s)
    g['mark'] = m.group(1) if m else '없음'
    g['memo'] = (m.group(2) or '').strip() if m else ''
    m = re.search(r'▣유의 등급: \((가|나)\)', s)
    g['caution'] = m.group(1) if m else ''
    m = re.search(r'진행유형: (\S+)', s)
    g['type'] = m.group(1) if m else ''
    m = re.search(r'◆ 주요 대지.*?\n(.*?)(?=\n\*\*◆|\n◆|\Z)', s, re.S)
    seg = m.group(1) if m else ''
    daeji = []
    for blk in re.split(r'\n\s*\n', seg):
        blk = ' '.join(blk.split())
        mm = re.match(r'^([①②③④])\s*(.+)$', blk)
        if mm:
            txt = re.split(r'[｜|]', mm.group(2))[0].strip()
            daeji.append((mm.group(1), txt))
    g['daeji'] = daeji[:4]
    return g


def norm(t):
    return re.sub(r'[^가-힣A-Za-z0-9]', '', t)


def qc_one(d, spec):
    num = int(os.path.basename(d))
    issues = []
    files = {}
    for fn in ('draft.md', 'teacher-notes.md'):
        p = os.path.join(d, fn)
        if not os.path.isfile(p):
            issues.append(('ERROR', f'{fn} 없음'))
            continue
        files[fn] = open(p, encoding='utf-8').read()
    if len(files) < 2:
        return dict(num=num, issues=issues, chars={}, write=0, sents=[])

    for fn, s in files.items():
        n = nchars(s)
        lo, hi = int(TARGET[fn] * (1 - TOL)), int(TARGET[fn] * (1 + TOL))
        if not lo <= n <= hi:
            issues.append(('WARN' if abs(n - TARGET[fn]) < TARGET[fn] * .25 else 'ERROR',
                           f'{fn} 분량 {n}자 (기준 {lo}~{hi})'))
        if '## ' in s:
            issues.append(('ERROR', f'{fn} 금지 표시 "## " 사용 — 렌더러가 문답으로 오독한다'))
        if '# COVER' not in s:
            issues.append(('ERROR', f'{fn} COVER 없음'))
        if '# FOOTER' not in s:
            issues.append(('WARN', f'{fn} FOOTER 없음'))
        if '|---' in s:
            issues.append(('ERROR', f'{fn} 마크다운 구분선 행 사용 금지'))
        # 표 앞 [[TABLE:]] 누락
        lines = s.split('\n')
        for i, ln in enumerate(lines):
            if ln.strip().startswith('|') and not (i and lines[i-1].strip().startswith(('[[TABLE:', '|'))):
                issues.append(('WARN', f'{fn} {i+1}행 표 앞 [[TABLE:...]] 누락'))
        for b in BANNED:
            if b in s:
                issues.append(('WARN', f'{fn} 금지 표현 "{b}"'))
        cleaned = strip_marks(drop_prayer(s))
        for m in POLITE.finditer(cleaned):
            ctx = cleaned[max(0, m.start()-80):m.end()+20]
            if not POLITE_OK.search(ctx):
                issues.append(('WARN', f'{fn} 어투 위반(경어체): …{ctx[-45:]}'))
                break
        for m in re.finditer(r'<!--\s*확인요청:\s*(.+?)\s*-->', s):
            issues.append(('VERSE', f'{fn} 인용 미확정: {m.group(1)}'))

    dr = files['draft.md']; tn = files['teacher-notes.md']
    w = sum(int(x) for x in re.findall(r'\[\[WRITING_BOX:(\d+)\]\]', dr))
    if not WRITE_MIN <= w <= WRITE_MAX:
        issues.append(('ERROR' if w > WRITE_MAX else 'WARN', f'필기 줄 {w} (기준 {WRITE_MIN}~{WRITE_MAX})'))

    if spec:
        if num in CFG.get('skip_core', []):
            spec = dict(spec, core='')
        if spec['core'] and norm(spec['core']) not in norm(dr):
            issues.append(('ERROR', '핵심 문장이 draft에 원문 그대로 없다'))
        for k, v in spec['daeji']:
            if norm(v)[:24] and norm(v)[:24] not in norm(tn):
                issues.append(('ERROR', f'대지 {k}가 teacher-notes에 원문 그대로 없다'))
        if spec['mark'] == '없음' and re.search(r'◎|필수암송', dr):
            issues.append(('ERROR', '필수암송 과가 아닌데 ◎/필수암송 표시가 있다'))
        if spec['mark'] in '◎○' and spec['mark'] not in dr:
            issues.append(('WARN', f'필수암송 {spec["mark"]} 표시가 지면에 없다'))
        if spec['caution'] == '나' and ('평가 체크' in dr or '교사 기록' in dr):
            issues.append(('ERROR', '▣유의(나) 과인데 평가 체크/교사 기록이 있다'))
        st = {'서사형': '읽고 이야기의 자리에 놓기', '논쟁형': '쟁점', '적용형': '진단'}
        if CFG.get('type_check', True) and spec['type'] in st and st[spec['type']] not in dr:
            issues.append(('WARN', f'{spec["type"]} 1단계 변주 장치가 보이지 않는다'))
    return dict(num=num, issues=issues,
                chars={k: nchars(v) for k, v in files.items()}, write=w,
                sents=sentences(dr))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('lessons_dir')
    ap.add_argument('--only', default=None)
    ap.add_argument('--json', default=None)
    a = ap.parse_args()

    cfgp = os.path.join(a.lessons_dir, os.pardir, 'qc-config.json')
    if os.path.isfile(cfgp):
        CFG.update(json.load(open(cfgp, encoding='utf-8')))
        TARGET.update({k: int(v) for k, v in CFG.get('target', {}).items()})
        globals()['WRITE_MIN'] = int(CFG.get('write_min', WRITE_MIN))
        globals()['WRITE_MAX'] = int(CFG.get('write_max', WRITE_MAX))

    dirs = sorted(d for d in glob.glob(os.path.join(a.lessons_dir, '[0-9][0-9][0-9]'))
                  if os.path.isdir(d))
    if a.only:
        keep = {int(x) for x in a.only.split(',')}
        dirs = [d for d in dirs if int(os.path.basename(d)) in keep]

    results = []
    for d in dirs:
        if not os.path.isfile(os.path.join(d, 'draft.md')):
            continue
        results.append(qc_one(d, read_spec(d)))

    # 과간 중복 — 기준본 1·2과에 함께 나오는 문장은 설계상 공통 골격이므로 제외한다
    tmpl = set()
    by_num = {r['num']: r for r in results}
    if 1 in by_num and 2 in by_num:
        a1 = {norm(x) for x in by_num[1]['sents']}
        a2 = {norm(x) for x in by_num[2]['sents']}
        tmpl = a1 & a2
    INSTR = re.compile(r'(적으라|쓰라|말하라|읽으라|고르라|표시하라|보라)[.\s]*$')
    seen = defaultdict(list)
    for r in results:
        for raw in set(r['sents']):
            k = norm(raw)
            if len(k) >= 22 and k not in tmpl and not INSTR.search(raw):
                seen[k].append(r['num'])
    dup = defaultdict(list)
    for k, nums in seen.items():
        if len(nums) > 1:
            for n in nums:
                dup[n].append((sorted(nums), k[:40]))
    for r in results:
        for nums, frag in dup.get(r['num'], [])[:6]:
            r['issues'].append(('DUP', f'{nums} 과와 같은 문장: {frag}…'))

    nerr = nwarn = ndup = nverse = 0
    for r in results:
        lv = [i[0] for i in r['issues']]
        nerr += lv.count('ERROR'); nwarn += lv.count('WARN')
        ndup += lv.count('DUP'); nverse += lv.count('VERSE')
        if r['issues']:
            print(f"\n{r['num']:>3}과  draft {r['chars'].get('draft.md','-')} / "
                  f"teacher {r['chars'].get('teacher-notes.md','-')} / 필기 {r['write']}")
            for lvl, msg in r['issues']:
                print(f"   {lvl:<6} {msg}")
    print('\n' + '─' * 60)
    print(f"점검 {len(results)}과 · ERROR {nerr} · WARN {nwarn} · DUP {ndup} · 인용미확정 {nverse}")
    if a.json:
        json.dump(results, open(a.json, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    return 1 if nerr else 0


if __name__ == '__main__':
    sys.exit(main())
