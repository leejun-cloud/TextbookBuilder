#!/usr/bin/env python3
"""v3 전환 원고의 성경 인용(낫표 「」)이 버전 2 원고에 있던 인용 그대로인지 대조한다.

v3 규칙: 인용은 v2에서 글자 그대로 복사하고 새 인용을 추가하지 않는다. 이 스크립트는
v3의 모든 인용을 뽑아 같은 과의 v2 인용 집합(공백 정규화)에 있는지 확인하고,
없는 것을 NEW로 보고한다. NEW는 사람이(또는 검증 에이전트가) 개역개정과 대조해야 한다.

사용법: python3 scripts/verse_carryover.py <v3_lessons_dir> <v2_lessons_dir> [--only 3,7]
"""
import argparse, glob, os, re, sys

QUOTE = re.compile(r'「(.+?)」', re.S)
MINLEN = 15  # 낫표는 「찾기」·「너희 가운데」 같은 용어에도 쓰인다 — 성경 인용만 보도록 짧은 것은 거른다


def quotes(path):
    out = []
    for fn in ('draft.md', 'teacher-notes.md'):
        p = os.path.join(path, fn)
        if os.path.isfile(p):
            for q in QUOTE.findall(open(p, encoding='utf-8').read()):
                q = ' '.join(q.split())
                if len(q) >= MINLEN:
                    out.append(q)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('v3_dir')
    ap.add_argument('v2_dir')
    ap.add_argument('--only', default=None)
    a = ap.parse_args()

    keep = {int(x) for x in a.only.split(',')} if a.only else None
    n_new = n_lessons = 0
    for d in sorted(glob.glob(os.path.join(a.v3_dir, '[0-9][0-9][0-9]'))):
        num = int(os.path.basename(d))
        if keep and num not in keep:
            continue
        if not os.path.isfile(os.path.join(d, 'draft.md')):
            continue
        n_lessons += 1
        v2 = set(quotes(os.path.join(a.v2_dir, os.path.basename(d))))
        news = [q for q in quotes(d) if q not in v2]
        if news:
            print(f'\n{num:>3}과 — v2에 없는 인용 {len(news)}건')
            for q in news:
                print(f'   NEW  「{q[:60]}{"…" if len(q) > 60 else ""}」')
            n_new += len(news)
    print(f'\n{"─" * 60}\n대조 {n_lessons}과 · NEW {n_new}건')
    return 1 if n_new else 0


if __name__ == '__main__':
    sys.exit(main())
