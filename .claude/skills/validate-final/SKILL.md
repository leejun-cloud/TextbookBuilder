---
name: validate-final
description: 최종 DOCX/PDF 등 결과물 생성 전에 해당 과가 원천 지침서·분량·스타일·학생용 출력 규칙을 모두 충족하는지 독립 검증한다. "/validate-final N", "최종 검증해줘", "출력 전 점검" 요청에 사용.
---

`/validate-final N` 형태로 호출한다. `<project-id>`는 현재 프로젝트, `NN`은 N을 두 자리 0-padding한 값이다.

## 1. 입력 확인

다음을 모두 읽는다.

- `projects/<project-id>/project.md`
- `projects/<project-id>/sources/자료목록.md`
- 해당 과의 주 원천 자료 범위
- `projects/<project-id>/style/style-rules.md`
- `projects/<project-id>/style/layout-spec.md` (있는 경우)
- `projects/<project-id>/lessons/01/approved.md` (N이 1이 아니면 스타일 기준)
- `projects/<project-id>/lessons/NN/approved.md` 또는 `draft.md`
- `projects/<project-id>/lessons/NN/worksheet.md` (있는 경우)
- 렌더/PDF가 있으면 실제 페이지 수·판형·오버플로·시각 스타일을 함께 확인한다.

원천 자료 범위를 찾지 못하면 검증을 추측으로 진행하지 말고 FAIL 처리한다.

## 2. final-validator 실행

Agent 도구로 `subagent_type: final-validator`를 호출한다. 원천 정합성 하드 게이트, 정량 분량 하드 게이트, 스타일 100점 평가를 모두 수행하게 한다.

결과는 `projects/<project-id>/lessons/NN/final-validation.md`에 저장한다.

## 3. 출력 잠금

`final-validation.md`의 마지막 판정이 `최종 출력 허용: YES`가 아니면 DOCX/PDF/인쇄용 결과물을 생성하지 않는다.

FAIL이면 사용자에게 다음만 보고한다.
- 차단 사유
- 수정 대상 파일·섹션
- 다시 `/validate-final N`을 실행해야 한다는 점

## 4. PASS 처리

PASS일 때만 최종 출력이 가능하다. PASS 결과는 출력 파일과 함께 보관하여 나중에 어떤 기준으로 승인되었는지 추적할 수 있게 한다.
