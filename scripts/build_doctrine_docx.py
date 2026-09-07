#!/usr/bin/env python3
"""완성된 과를 하나씩 Word로 굽고 진행 원장을 갱신한다. 중간에 끊겨도 이미 구운 것은 남는다.

  python3 scripts/build_doctrine_docx.py                 # 새로 완성된 과만
  python3 scripts/build_doctrine_docx.py --only 3,4,5
  python3 scripts/build_doctrine_docx.py --force         # 전부 다시
  python3 scripts/build_doctrine_docx.py --combine 1-50 -o 1년차.docx
"""
import argparse, glob, json, os, re, subprocess, sys

ROOT = 'projects/doctrine-high-3stage'
LESSONS = os.path.join(ROOT, 'lessons')
STYLE = 'doctrine-stage3'
sys.path.insert(0, 'scripts')


def safe(t):
    return re.sub(r'[\\/:*?"<>|\s]+', '', t)


def index():
    return {e['num']: e for e in json.load(open(os.path.join(LESSONS, 'index.json'), encoding='utf-8'))}


def out_path(num, title):
    d = os.path.join(LESSONS, f'{num:03d}', 'exports')
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, f'고등부교리공과_{num:03d}과_{safe(title)}.docx')


def build_one(num, title):
    d = os.path.join(LESSONS, f'{num:03d}')
    files = [os.path.join(d, 'draft.md'), os.path.join(d, 'teacher-notes.md')]
    if not all(os.path.isfile(f) for f in files):
        return None
    out = out_path(num, title)
    r = subprocess.run([sys.executable, 'scripts/combine_lessons.py', '--files', *files,
                        '-o', out, '--style', STYLE], capture_output=True, text=True)
    if r.returncode:
        print(f'  {num:>3}과 변환 실패: {r.stderr.strip()[:200]}')
        return None
    return out


def ledger(idx):
    rows, done = [], 0
    for n in sorted(idx):
        e = idx[n]
        d = os.path.join(LESSONS, f'{n:03d}')
        has_md = os.path.isfile(os.path.join(d, 'draft.md')) and \
                 os.path.isfile(os.path.join(d, 'teacher-notes.md'))
        docx = os.path.isfile(out_path(n, e['title']))
        st = '완료' if (has_md and docx) else ('원고만' if has_md else '미착수')
        done += st == '완료'
        rows.append(f"| {n} | {e['title']} | {e['type']} | {e['year']} | "
                    f"{e['mark'] or '·'} | {'(' + e['caution'] + ')' if e['caution'] else '·'} | {st} |")
    with open(os.path.join(ROOT, 'PROGRESS.md'), 'w', encoding='utf-8') as f:
        f.write(f"# 진행 원장 — 고등부 교리공과 150과\n\n**완료 {done} / 150**  "
                f"(원고 2종 + Word 변환까지 끝난 과)\n\n"
                "이 파일은 `scripts/build_doctrine_docx.py`가 디스크 상태에서 다시 만든다. 직접 고치지 않는다.\n\n"
                "| 과 | 주제 | 유형 | 연차 | 암송 | ▣유의 | 상태 |\n|---|---|---|---|---|---|---|\n")
        f.write('\n'.join(rows) + '\n')
    return done


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--only', default=None)
    ap.add_argument('--force', action='store_true')
    ap.add_argument('--combine', default=None, help='예: 1-50')
    ap.add_argument('-o', '--out', default=None)
    ap.add_argument('--root', default=ROOT, help='프로젝트 루트 (기본: doctrine-high-3stage)')
    a = ap.parse_args()
    globals()['ROOT'] = a.root
    globals()['LESSONS'] = os.path.join(a.root, 'lessons')
    idx = index()

    if a.combine:
        lo, hi = (int(x) for x in a.combine.split('-'))
        files = []
        for n in range(lo, hi + 1):
            d = os.path.join(LESSONS, f'{n:03d}')
            f1, f2 = os.path.join(d, 'draft.md'), os.path.join(d, 'teacher-notes.md')
            if os.path.isfile(f1) and os.path.isfile(f2):
                files += [f1, f2]
        if not files:
            raise SystemExit('합칠 원고가 없다.')
        out = a.out or os.path.join(ROOT, 'exports', f'{lo}-{hi}과_합본.docx')
        os.makedirs(os.path.dirname(out), exist_ok=True)
        subprocess.run([sys.executable, 'scripts/combine_lessons.py', '--files', *files,
                        '-o', out, '--style', STYLE], check=True)
        print(f'합본: {out} ({len(files)//2}과)')
        return

    nums = sorted(idx)
    if a.only:
        keep = {int(x) for x in a.only.split(',')}
        nums = [n for n in nums if n in keep]
    made = 0
    for n in nums:
        e = idx[n]
        if not a.force and os.path.isfile(out_path(n, e['title'])):
            continue
        if build_one(n, e['title']):
            made += 1
            print(f'  {n:>3}과 → Word')
    done = ledger(idx)
    print(f'새로 구운 과 {made} · 완료 {done}/150')


if __name__ == '__main__':
    main()
