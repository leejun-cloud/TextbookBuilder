---
name: evaluate-lesson
description: 특정 과의 draft를 100점 만점 루브릭으로 평가하고 80점 규칙에 따라 수정 루프를 돌린다. "N과 평가해줘", "/evaluate-lesson N", "이 draft 점수 매겨줘" 등에 사용. write-lesson과 design-lesson1에서도 내부적으로 호출된다.
---

`/evaluate-lesson N`으로 단독 호출되거나, write-lesson·design-lesson1 흐름 안에서 호출된다. N을 두 자리로 0-padding한 값을 `NN`이라 한다. `<project-id>`는 확정된 프로젝트다.

## 1. 스타일 기준 확인

`projects/<project-id>/style/style-rules.md`를 읽는다.

- 있으면 아래 루브릭을 그대로 사용한다.
- 없으면(1과 승인 전 최초 평가인 경우) "스타일 일치도" 항목은 style-rules.md/1과 승인본 대신 `project.md`에 명시된 요구사항과 대조하고, 해당 배점을 나머지 항목에 비례 배분해 재조정한다.

## 2. 분량 정량 측정

evaluator를 호출하기 전에 Bash로 직접 글자 수를 측정한다. 예: `wc -m projects/<project-id>/lessons/NN/draft.md`. 가능하면 섹션 단위로도 나누어 측정한다(본문/활동지 구분, 소제목별 등). style-rules.md에 있는 기준 분량(전체 및 섹션별)과 비교할 수 있도록 측정값을 정리해 evaluator에게 넘긴다. 이 측정은 evaluator의 주관적 판단이 아니라 Claude가 직접 계산한 수치여야 한다.

## 3. lesson-evaluator 서브에이전트 실행

Agent 도구로 `subagent_type: lesson-evaluator`를 호출한다. 프롬프트에 다음을 모두 포함한다.

- 아래 루브릭 전문
- `style-rules.md` 내용 (없으면 `project.md`의 관련 요구사항)
- 1과 `approved.md` 내용 (스타일 비교 기준)
- 이번 과의 `draft.md`, `worksheet.md`, `teacher-notes.md`, `input.md`
- 2단계에서 측정한 글자 수 데이터

evaluator에게 요구하는 출력 형식: 항목별 점수 및 근거, 총점, 잘된 점, 수정 필요 사항(구체적으로 어느 문단·문장·섹션인지 명시), 누락된 요소, 다음 과 작성 시 참고할 점.

### 평가 루브릭 (100점)

- **스타일 일치도 (25점)**: style-rules.md 및 1과 승인본과 문체·구조·질문 방식이 일치하는가.
- **분량 유지 (20점)**: draft.md의 실측 글자 수(2단계 측정값)를 style-rules.md의 기준 분량과 비교. 기준 대비 ±10% 이내 20점, ±20% 이내 15점, ±30% 이내 8점, 그 이상 벗어나면 0점. 섹션별 분량도 기준과 대조해 근거에 명시한다. (1과는 3000자인데 2과가 1000자로 줄어드는 식의 축소를 반드시 잡아내야 한다.)
- **핵심내용 반영 (20점)**: input.md에 명시된 핵심 내용 3가지가 본문에 충실히 전개되었는가.
- **질문·활동 품질 (15점)**: 질문이 구체적이고 적용형(단순 확인형이 아닌)인가, 활동이 본문 내용과 실제로 연결되는가.
- **문장 자연스러움 (10점)**: "~하는 것이 중요합니다" 류의 반복, 과도한 목록화 등 AI 티 나는 표현을 감점한다.
- **성경 인용 정확성 (10점)**: 개역개정 본문과 일치하는가, 장절 표기가 올바른가.

## 4. 결과 저장

evaluator의 보고서를 `projects/<project-id>/lessons/NN/evaluation.md`로 저장한다(재평가 시 덮어쓰거나 회차를 구분해 추가한다).

## 5. 80점 규칙 적용

- **총점 < 80점**: `subagent_type: lesson-updater`를 호출해 evaluation.md의 수정 필요 사항을 반영하여 draft.md/worksheet.md/teacher-notes.md를 수정하게 한다. 수정 후 2~3단계를 다시 수행해 재평가한다. 이 사이클은 최대 3회까지만 반복한다. 3회 후에도 80점 미만이면 더 이상 자동 반복하지 말고, 현재 점수와 남은 문제점을 있는 그대로 사용자에게 보고하고 지시를 기다린다.
- **총점 ≥ 80점**: 자동으로 draft를 수정하지 않는다. 점수 요약과 evaluator가 제안한 개선 사항을 번호를 매긴 리스트로 사용자에게 제시하고, 어떤 항목을 적용할지 또는 이대로 승인할지 사용자의 지시를 기다린다.
