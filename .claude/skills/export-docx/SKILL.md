---
name: export-docx
description: 승인된 과의 본문·활동지·교사용 자료를 워드(.docx) 파일로 변환한다. "N과 워드로 내보내줘", "/export-docx N", "/export-docx all"(전체 통합본) 등에 사용.
---

`/export-docx N` 또는 `/export-docx all` 형태로 호출된다. N을 두 자리로 0-padding한 값을 `NN`이라 한다. `<project-id>`는 확정된 프로젝트다. pandoc은 `/opt/homebrew/bin/pandoc`에 설치되어 있다.

## 1. 교재 제목 확인

`projects/<project-id>/project.md`에서 교재 제목을 확인한다.

## 2. 단일 과 변환 (`/export-docx N`)

`projects/<project-id>/lessons/NN/approved.md`를 사용한다. 없으면 `draft.md`를 대신 사용하되, 승인되지 않은 초안임을 사용자에게 경고 문구로 알린다.

다음 세 파일을 `projects/<project-id>/lessons/NN/exports/`에 생성한다. 파일명의 `<교재제목>`은 project.md에서 읽은 제목으로 치환한다.

- `<교재제목>_N과_본문.docx` ← approved.md(또는 draft.md)
- `<교재제목>_N과_활동지.docx` ← worksheet.md
- `<교재제목>_N과_교사용.docx` ← teacher-notes.md

기본 명령 형태:

```
pandoc input.md -o output.docx
```

`templates/reference.docx`(저장소 루트 기준)가 존재하면 워드 스타일 일관성을 위해 `--reference-doc=templates/reference.docx` 옵션을 추가한다.

## 3. 전체 통합본 (`/export-docx all`)

승인된(=approved.md가 존재하는) 과를 번호 순서대로 모두 찾아 하나의 워드 파일로 합친다. pandoc은 여러 마크다운 파일을 이어 붙일 때 파일 사이에 아무 구분이 없으면 섹션이 그냥 이어지므로, 각 과 사이에 페이지 나누기를 넣어야 한다. 마크다운에서 raw OpenXML 페이지 나누기를 삽입하는 구분자를 각 과 파일 사이에 끼워 넣은 임시 결합 파일을 만든 뒤 pandoc으로 변환하거나, 각 과를 개별 변환해 두었다가 필요시 안내한다. 결과물은 `projects/<project-id>/exports/<교재제목>_전체.docx`로 저장한다. reference.docx가 있으면 동일하게 적용한다.

## 4. 결과 보고

생성된 파일들의 경로를 모두 알려주고, 워드에서 바로 열어 확인할 수 있음을 안내한다.
