---
name: validate-print
description: 교재를 책으로 출판하거나 최종 PDF를 검수할 때 사용한다. 오려 붙이기·퍼즐·스티커의 실제 치수와 양면 배치, 최종 PDF, 검사 증거와 미확인 항목을 확인한다. 원고 점수와 별개로 수행하며 검증 명령 실패·누락·오래된 결과를 합격으로 처리하지 않는다.
---

# 교재 인쇄 검증

저장소 루트에서 실행한다. 명령 실행 결과와 실제 산출물을 확인한다. 설명이나 프롬프트만 읽고 완성된 교재를 승인하지 않는다.

## 입력 확인

- 교재의 최종 PDF, 판형, 예상 페이지 수, 최소 해상도 기준을 확인한다.
- 오려 붙이기는 `cut-paste/v1` 명세와 빈자리 없는 완성 장면을 사용한다. 자세한 명세는 `docs/print-validation.md`와 `sample-projects/cut-paste/activity.json`을 읽는다.
- 기존 한 장짜리 AI 활동지는 크기·방향을 추측해 승인하지 않는다. 원본 장면과 조각별 좌표·윤곽을 먼저 정한다. 없는 정보는 확인 불가로 기록한다.

## 실행 순서

1. 의존성이 없으면 `python3 -m pip install -r requirements-print.txt`로 준비한다.
2. `python3 scripts/qc_activity.py <activity.json> --json build/activity-check.json`으로 명세를 검사한다. 실패하면 후속 합격 판정을 중단하고 명세를 수정한다.
3. `python3 scripts/build_cut_paste.py <activity.json> -o build/book.pdf`로 활동면·오리기 부록·조립본·책을 만든다. 기존 본문을 합칠 때 `--body-pdf <body.pdf>`를 지정한다. 한글 폰트가 없으면 `--font <font.ttf>`를 지정한다. 조각만 별도로 축소하거나 회전하지 않는다.
4. `python3 scripts/qc_print.py build/book.qc.json --verify-report --activity-spec <activity.json>`으로 원본·명세·모든 산출물의 변경 여부를 확인한다.
5. 일반 Typst 교재는 `python3 scripts/textbuilder_render.py <input> --final --page-size B5 -o build/final.pdf`로 출력한다. 인쇄 기준이 300dpi면 `--min-image-dpi 300`을 지정한다. 미리보기·부분 출력·렌더러 fallback을 최종 출력으로 쓰지 않는다.
6. 최종 PDF와 조립본을 페이지 이미지로 렌더링하여 모든 비어 있지 않은 면을 확인한다. 글자 잘림·누락·그림의 의미·어색한 신체 부위·활동 안내를 직접 검토한다. PDF의 빈 뒷면 목록도 보고서와 대조한다.
7. 변경한 검수 코드가 있으면 `python3 scripts/test_print_qc.py -v`를 실행하고 실패·건너뜀을 그대로 보고한다. 테스트 자체의 합격과 이번 교재의 합격을 혼동하지 않는다.

## 합격과 증거

- 보고서 `machine_pass`는 실행한 기계 검사만 통과했다는 뜻이다. 교육 내용·OCR 정확성·실제 인쇄물 조립의 승인을 뜻하지 않는다.
- 실패·확인 불가·미실행 항목이 있는 상태에서 ‘출판 검증 완료’라고 보고하지 않는다. 원고 평가 80점 이상도 이를 대신하지 않는다.
- 조립본에 조각을 얹을 때 위치만 옮긴다. 크기·회전·좌우반전을 맞춰주는 보정으로 오류를 숨기지 않는다.
- 명세·원본·PDF를 수정하면 다시 출력하고 검사한다. 이전 보고서의 SHA-256이 맞지 않으면 이전 합격을 재사용하지 않는다.
- 실제 크기 100%로 인쇄하여 50mm 확인선과 조각을 확인해야 할 때는 사용자 확인이 남았다고 명시한다. 실제로 하지 않은 오리기·인쇄 검사를 했다고 주장하지 않는다.
- 결과에는 검사한 파일, 실행 명령, 오류, 증거 파일 경로, 남은 확인 사항을 간결하게 보고한다.
