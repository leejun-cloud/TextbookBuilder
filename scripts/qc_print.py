#!/usr/bin/env python3
"""최종 PDF 사후검사 또는 오려 붙이기 출력 묶음의 변경 여부 검사."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))


def verify_bundle(report_path, manifest):
    from textbuilder.activity_geometry import load_plan
    from textbuilder.print_qc import sha256_file
    path=Path(report_path).resolve(); report=json.loads(path.read_text(encoding='utf-8'))
    errors=[]
    if report.get('status')!='machine_pass' or report.get('errors'):
        errors.append('기계 검증을 통과한 보고서가 아니다')
    if not report.get('files'):
        errors.append('출력 파일 식별값이 없다')
    for item in report.get('files',{}).values():
        name=item.get('name','')
        if not name or Path(name).name!=name:
            errors.append('잘못된 산출물 경로')
            continue
        candidate=path.parent/name
        if not candidate.is_file() or sha256_file(candidate)!=item.get('sha256'):
            errors.append(f'출력 후 변경되었거나 누락된 파일: {name}')
    plan=load_plan(manifest)
    if plan['manifest_sha256']!=report.get('manifest_sha256'):
        errors.append('조각 명세가 검사 후 변경되었다')
    current=[{'activity':a['id'],'sha256':a['source_sha256']} for a in plan['activities']]
    if current!=report.get('sources'):
        errors.append('원본 이미지가 검사 후 변경되었다')
    return errors


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input',help='PDF 또는 --verify-report일 때 qc.json')
    parser.add_argument('--page-size',default='B5')
    parser.add_argument('--expected-pages',type=int)
    parser.add_argument('--blank-pages',default='',help='빈 뒷면의 1기준 쪽번호: 4,6,8')
    parser.add_argument('--min-image-dpi',type=float,default=300)
    parser.add_argument('--json')
    parser.add_argument('--verify-report',action='store_true')
    parser.add_argument('--activity-spec',help='출력 당시 조각 명세')
    args=parser.parse_args()
    from textbuilder.print_qc import audit_pdf,write_report
    try:
        if args.verify_report:
            if not args.activity_spec:
                parser.error('--verify-report에는 --activity-spec이 필요하다')
            errors=verify_bundle(args.input,args.activity_spec)
            report={'status':'blocked' if errors else 'machine_pass','errors':errors,
                    'unverified':['교육 내용과 실물 조립은 별도 확인']}
        else:
            from textbuilder.model import PAGE_SIZES_MM
            if args.page_size not in PAGE_SIZES_MM:
                parser.error('지원하지 않는 판형')
            blanks=[int(v) for v in args.blank_pages.split(',') if v.strip()]
            report=audit_pdf(args.input,expected_size_mm=PAGE_SIZES_MM[args.page_size],
                             expected_pages=args.expected_pages,blank_pages=blanks,
                             min_image_dpi=args.min_image_dpi)
        if args.json:
            write_report(args.json,report)
    except (ValueError,RuntimeError,OSError,ImportError) as exc:
        print(f'검사 실패: {exc}',file=sys.stderr)
        return 1
    print(json.dumps(report,ensure_ascii=False,indent=2))
    return 0 if report['status']=='machine_pass' else 1


if __name__=='__main__':
    sys.exit(main())
