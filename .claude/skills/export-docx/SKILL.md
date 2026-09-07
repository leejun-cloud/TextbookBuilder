---
name: export-docx
description: 승인되고 최종 검증을 통과한 과를 워드(.docx) 파일로 변환한다. "N과 워드로 내보내줘", "/export-docx N", "/export-docx all" 등에 사용.
---

`/export-docx N` 또는 `/export-docx all` 형태로 호출된다. N을 두 자리로 0-padding한 값을 `NN`이라 한다. `<project-id>`는 확정된 프로젝트다. pandoc은 `/opt/homebrew/bin/pandoc`에 설치되어 있다.

## 1. 프로젝트와 출력 프로필 확인

`projects/<project-id>/project.md`에서 다음을 확인한다.

- 교재 제목
- 출력 프로필: `student-only`인지 일반 본문+활동지+교사용인지
- 최종 검증 필수 여부
- 판형/스타일 관련 특수 지침

## 2. 최종 검증 게이트 — 반드시 먼저

최종 파일을 만들기 전에 `projects/<project-id>/lessons/NN/final-validation.md`를 확인한다.

- 파일이 없으면 `/validate-final N`을 먼저 실행한다.
- 마지막 판정이 `최종 출력 허용: YES`가 아니면 **내보내기를 중단한다.**
- FAIL 상태에서 초안 경고만 붙여 임의로 출력하지 않는다.

`/export-docx all`의 경우 포함할 모든 과가 각각 `최종 출력 허용: YES`여야 한다. 하나라도 미통과면 전체 합본을 만들지 않고 미통과 과 번호를 보고한다.

## 3. 단일 과 변환 (`/export-docx N`)

기본 원본은 `projects/<project-id>/lessons/NN/approved.md`다. 승인본이 없으면 최종 출력하지 않는다.

### student-only 프로젝트

학생용 전용 프로젝트는 교사용 파일을 생성하지 않는다. `approved.md`와 필요한 학생 활동 내용을 합쳐 다음 한 파일만 생성한다.

- `<교재제목>_N과_학생용.docx`

`teacher-notes.md`가 존재하더라도 최종 학생용 결과물에는 포함하지 않는다.

### 일반 프로젝트

기존 구조를 유지한다.

- `<교재제목>_N과_본문.docx`
- `<교재제목>_N과_활동지.docx`
- `<교재제목>_N과_교사용.docx`

기본 명령 형태:

```
pandoc input.md -o output.docx
```

`templates/reference.docx`가 존재하면 `--reference-doc=templates/reference.docx`를 사용한다. 프로젝트 전용 reference.docx가 지정되어 있으면 프로젝트 전용 파일을 우선한다.

## 4. 전체 통합본 (`/export-docx all`)

최종 검증 PASS + 승인본 존재 조건을 모두 만족한 과만 번호 순서대로 합친다.

- student-only 프로젝트: 학생용 승인본만 합쳐 `projects/<project-id>/exports/<교재제목>_학생용_전체.docx`
- 일반 프로젝트: 기존 통합 규칙을 사용한다.

각 과 사이에는 페이지 나누기를 넣는다.

## 5. 결과 보고

생성 파일 경로와 함께, 해당 결과물이 어떤 `final-validation.md` PASS를 근거로 출력되었는지 과 번호별로 알려준다.
