#!/usr/bin/env python3
"""완성 그림 + 조각 명세 → 검증된 활동면/부록/조립본/책 PDF."""
import argparse
import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest',help='cut-paste/v1 JSON')
    parser.add_argument('-o','--out',required=True,help='최종 책 PDF')
    parser.add_argument('--body-pdf',help='앞에 붙일 기존 본문 PDF (같은 판형)')
    parser.add_argument('--font',help='한글을 지원하는 TrueType 폰트 파일')
    args=parser.parse_args()
    try:
        from textbuilder.cut_paste import build_book
        files,report=build_book(args.manifest,args.out,body_pdf=args.body_pdf,font_path=args.font)
    except (ValueError,RuntimeError,OSError,ImportError) as exc:
        print(f'출력 차단: {exc}',file=sys.stderr)
        return 1
    print(f'기계 검증 통과: {report["page_count"]}쪽 / 조각 {len(report["pairs"])}개')
    for key,path in files.items():
        print(f'{key}: {path}')
    print('최종 확인 필요: 교육 내용·모든 페이지 시각 검토·실제 크기로 오려 붙이기')
    return 0


if __name__=='__main__':
    sys.exit(main())
