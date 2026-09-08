#!/usr/bin/env python3
"""초등부 456 v2 — 원천(source-lessons120.json)에서 과 블록을 출력한다.

사용법: python3 scripts/elem456_spec.py --grade 4 --no 3 [--no 4 ...]
"""
import argparse, json

SRC = 'projects/elementary-456-v2/sources/source-lessons120.json'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--grade', type=int, required=True)
    ap.add_argument('--no', type=int, action='append', required=True)
    a = ap.parse_args()
    src = json.load(open(SRC, encoding='utf-8'))
    idx = {(x['year'] + 3, x['local_no']): x for x in src}
    for n in a.no:
        x = idx.get((a.grade, n))
        if not x:
            print(f'== {a.grade}학년 {n}과: 원천 없음 ==')
            continue
        print(f'\n===== {a.grade}학년 {n}과 · 공통 {x["common_no"]}과 · 단원 {x.get("unit")} '
              f'· 필수암송 {"●" if x.get("required_memory") else "없음"} '
              f'· 유의 {x.get("sensitivity") or "없음"} =====')
        for line in x.get('raw', []):
            print(line)


if __name__ == '__main__':
    main()
