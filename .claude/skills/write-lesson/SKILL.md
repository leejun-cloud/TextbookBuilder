---
name: write-lesson
description: 특정 과(課)의 교재 본문·활동지·교사용 자료를 작성한다. "N과 써줘", "/write-lesson N", "2과 작성" 등의 요청에 사용.
---

`/write-lesson N` 형태로 호출되며 N은 작성할 과 번호다. 다음 순서를 정확히 따른다.

## 0. 프로젝트 확인

`projects/` 아래에 프로젝트가 여러 개 있으면 사용자에게 어떤 프로젝트인지 묻는다. 하나뿐이거나 대화 맥락상 명확하면 그것으로 진행한다. 이하 `<project-id>`는 확정된 프로젝트, `NN`은 N을 두 자리 0-padding한 값(예: 2 → 02)이다.

## 1. 사전 조건 확인

다음 두 가지가 모두 있어야 진행할 수 있다.

- `projects/<project-id>/lessons/01/approved.md` (1과 승인본)
- `projects/<project-id>/style/style-rules.md` (스타일 규칙)

둘 중 하나라도 없으면 작업을 진행하지 말고, 사용자에게 먼저 `/design-lesson1`으로 1과를 완성하고 승인해야 한다고 안내한 뒤 중단한다.

## 2. 참고 자료 읽기

다음 파일을 모두 읽는다.

- `projects/<project-id>/project.md`
- `projects/<project-id>/style/style-rules.md`
- `projects/<project-id>/style/next-lesson-notes.md` (없으면 빈 것으로 간주)
- `projects/<project-id>/lessons/01/approved.md` (문체·구조 참조용 기준본)
- `projects/<project-id>/lessons/NN/input.md`
- `projects/<project-id>/project.md`의 "특수 지침" 섹션을 반드시 읽고 따른다.
- `projects/<project-id>/sources/자료목록.md`가 있으면 읽는다. input.md의 "원천 자료 범위"에 해당하는 `sources/` 파일들도 함께 읽는다.

`input.md`가 없으면 사용자에게 이 과의 주제와 핵심 내용 3가지를 물어보고, 답변을 받아 `projects/<project-id>/lessons/NN/input.md`로 저장한 뒤 이어서 진행한다.

## 3. lesson-writer 서브에이전트 실행

Agent 도구로 `subagent_type: lesson-writer`를 호출한다. 프롬프트에 아래 내용을 모두 포함시켜 자체 완결적으로 작성한다.

- project.md, style-rules.md, next-lesson-notes.md, 1과 approved.md 전체 내용 (또는 핵심 요약과 파일 경로)
- project.md의 "특수 지침" 섹션 내용
- 이번 과의 input.md 내용
- 원천 자료 범위에 해당하는 sources/ 파일 발췌본과, 자료목록.md에 명시된 해당 자료의 사용 지침
- 주 원천 자료가 지정된 경우: 본문은 원천 자료 내용의 재구성이며, 원천의 핵심 내용을 왜곡·누락하지 않고 원천에 없는 신학적/사실적 주장을 추가하지 않는다는 지시
- 요구사항: `projects/<project-id>/lessons/NN/draft.md`, `worksheet.md`, `teacher-notes.md`를 생성할 것. 1과 승인본의 문체·구조·질문 방식을 그대로 따르고, style-rules.md에 명시된 정량적 분량 기준(전체 및 섹션별 글자 수)을 맞출 것.
- 성경 인용은 별도 요청이 없는 한 개역개정만 사용할 것.

writer는 자기 결과물을 스스로 평가하지 않는다.

## 4. 즉시 평가 실행

draft가 나오면 바로 evaluate-lesson 흐름을 그대로 수행한다 (lesson-evaluator 실행 → 80점 규칙에 따라 필요시 lesson-updater로 수정 후 재평가, 최대 3회). evaluate-lesson SKILL.md의 절차를 따른다.

## 5. 사용자 승인 처리

사용자가 최종 승인하면:

1. `draft.md`를 `approved.md`로 복사한다.
2. `project.md`의 진행 현황표에 이번 과를 완료로 갱신한다.
3. 이번 과 작성/평가 과정에서 발견한 특이사항이나 주의할 점을 `style/next-lesson-notes.md`에 "다음 과에서 주의할 점"으로 추가한다.

## 6. 다음 액션 제안

작업 완료 후 사용자에게 `/export-docx N`과 `/write-lesson N+1`을 이어서 실행할지 제안한다.
