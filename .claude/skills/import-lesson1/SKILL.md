---
name: import-lesson1
description: 사용자가 이미 완성한 1과 샘플을 등록해 기준본으로 삼고 스타일 규칙을 추출한다. "1과 샘플 등록", "기준본 가져오기", "/import-lesson1" 등을 요청할 때 사용한다.
---

사용자가 1과를 처음부터 설계해 달라는 것이 아니라, 이미 완성된 1과 샘플(원고)을 제공하고 그것을 기준본으로 쓰고 싶어할 때 사용한다. `/design-lesson1`의 리서치·구조 3안 단계는 건너뛰고, 제공된 샘플을 그대로 기준본으로 확정한 뒤 스타일 규칙을 추출하는 데 집중한다. 아래 단계를 순서대로, 생략 없이 수행한다.

## 1. 샘플 파일 수신 및 변환

사용자가 제공한 1과 샘플 파일을 확인한다.

- HWP/HWPX 파일이면 `scripts/hwp_convert.py`로 마크다운 변환한다.
- DOCX 파일이면 pandoc으로 마크다운 변환한다.
- md/txt 파일이면 변환 없이 그대로 사용한다.

## 2. 승인본으로 저장

변환된 내용을 `projects/<project-id>/lessons/01/approved.md`로 저장한다.

- 샘플에 활동지(worksheet)와 교사용 해설(teacher-notes)이 구분되어 포함되어 있으면 각각 `lessons/01/worksheet.md`, `lessons/01/teacher-notes.md`로 분리해서 저장한다.
- 포함되어 있지 않으면, 이후 과 작성 시 활동지·교사용 해설도 함께 생성할지 사용자에게 확인한다.

## 3. 스타일 규칙 추출

`/design-lesson1`의 6단계와 동일한 방식으로 `lessons/01/approved.md`를 분석해 `style/style-rules.md`를 작성한다(`templates/style-rules.md` 양식을 채운다). 다음을 approved.md에서 실측하여 구체적으로 기록한다.

- 문체 (어미, 존댓말 여부)
- 제목/소제목 패턴
- 섹션 구성과 순서
- 섹션별 글자 수 (`wc -m`으로 실측 — 감으로 적지 않는다)
- 문단 길이
- 질문 유형과 개수
- 활동 형식
- 교사용 해설 톤
- 자주 쓴 표현
- 금지 표현

`/design-lesson1`으로 만든 기준본이든 `/import-lesson1`으로 등록한 샘플이든 결과는 동일한 형식의 `style-rules.md`로 수렴해야 한다 — 이후 과 작성은 두 경로를 구분하지 않고 똑같이 진행된다.

## 4. next-lesson-notes.md 작성

`style/next-lesson-notes.md`를 작성해 다음 과 집필 시 참고할 점(샘플에서 느껴지는 의도, 유지해야 할 뉘앙스 등)을 정리한다.

## 5. project.md 갱신

`project.md`의 과별 진행 현황표에서 1과 상태를 "승인"으로 갱신한다.

## 6. 안내

작업을 마치면 사용자에게 다음 단계는 `/write-lesson 2`(2과 집필)임을 안내한다.
