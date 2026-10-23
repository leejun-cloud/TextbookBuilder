#!/usr/bin/env python3
"""오려 붙이기 명세를 검사한다. 이미지/PDF 시각 검토를 대신하지 않는다."""
import argparse
import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest')
    parser.add_argument('--json',help='검사 결과 JSON')
    args=parser.parse_args()
    from textbuilder.print_qc import write_report
    try:
        from textbuilder.activity_geometry import load_plan,pack_cutouts
        plan=load_plan(args.manifest); sheets=pack_cutouts(plan)
        report={'status':'machine_pass','manifest_sha256':plan['manifest_sha256'],
                'activities':len(plan['activities']),'cut_sheets':len(sheets),
                'pieces':sum(len(a['pieces']) for a in plan['activities']),
                'unverified':['최종 PDF 렌더링','교육 내용','실물 조립']}
    except (ValueError,RuntimeError,OSError,ImportError) as exc:
        report={'status':'blocked','errors':[str(exc)]}
    if args.json:
        write_report(args.json,report)
    print(report)
    return 0 if report['status']=='machine_pass' else 1


if __name__=='__main__':
    sys.exit(main())
