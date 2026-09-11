---
name: write-lesson
description: 특정 과(課)의 교재 본문·활동지·교사용 자료를 작성한다. "N과 써줘", "/write-lesson N", "2과 작성" 등의 요청에 사용. 선택적으로 --style <style-id>, --student-pages <N>을 받아 학생용 시각 스타일 프리셋을 적용한다.
---

기본 호출은 `/write-lesson N`이다. 학생용 시각 스타일을 명시하려면 `/write-lesson N --style <style-id> --student-pages <N>` 형식도 허용한다. N은 작성할 과 번호이며, 이하 `<project-id>`는 확정된 프로젝트, `NN`은 N을 두 자리 0-padding한 값(예: 2 → 02)이다.

## 0. 프로젝트 확인

`projects/` 아래에 프로젝트가 여러 개 있으면 사용자에게 어떤 프로젝트인지 묻는다. 하나뿐이거나 대화 맥락상 명확하면 그것으로 진행한다.

## 1. 사전 조건 확인

다음 두 가지가 모두 있어야 진행할 수 있다.

- `projects/<project-id>/lessons/01/approved.md` (1과 승인본)
- `projects/<project-id>/style/style-rules.md` (스타일 규칙)

둘 중 하나라도 없으면 작업을 진행하지 말고, 사용자에게 먼저 `/design-lesson1` 또는 `/import-lesson1`으로 1과를 기준본으로 확정해야 한다고 안내한 뒤 중단한다.

## 2. 학생용 시각 스타일 해석

학생용 시각 스타일은 선택 사항이며 다음 우선순위로 결정한다.

1. 호출 인자의 `--style <style-id>`
2. `projects/<project-id>/project.md`의 `학생용 시각 스타일 > 시각 스타일 ID`
3. `projects/<project-id>/style/style-rules.md`의 `학생용 시각 스타일 > 시각 스타일 ID`
4. 모두 없거나 `없음`이면 시각 스타일 미적용

시각 스타일 ID가 정해졌다면 반드시 `doc-styles/<style-id>.json`을 읽는다. 파일이 없으면 임의의 비슷한 스타일로 대체하지 말고 스타일 ID 오류를 보고한다.

학생용 페이지 수는 다음 우선순위로 결정한다.

1. `--student-pages <N>`
2. `project.md`의 `학생용 페이지 수`
3. 시각 스타일 JSON의 `page.student_pages_per_lesson`
4. 없으면 기존 프로젝트 기본값

### `preschool-bible-seomun26` 특별 계약

`preschool-bible-seomun26`이 선택된 경우 다음을 절대 기준으로 한다.

- B5 세로형
- 학생용 3페이지 고정
- 1과는 구조 기준본, 2과 승인본/참조 이미지가 있으면 변형 기준본으로 함께 참조
- 1p = 핵심 고백, 2p = 말씀 이야기 3장면, 3p = 참여 활동
- 밝은 파스텔 어린이 성경동화 화풍, 둥근 카드형 박스, 큰 둥근 제목, 낮은 정보 밀도
- 한 장면에 핵심 사건 하나만 표현
- 학생용 페이지에는 교리 해설·본문 경계·흔한 오해·관찰평가·민감도·음악 사용 기록 등 교사용 필드를 노출하지 않음
- 핵심 고백을 세 페이지 전체에서 반복 회수
- 페이지 2의 질문은 2개 이하
- 페이지 3의 선택 활동은 핵심 활동에 맞는 4개를 기본으로 구성
- 기존 찬송가/노래 가사를 복제하지 않고 비선율 말리듬으로 구성
- 이전 승인 이미지가 있으면 이후 이미지 생성 시 reference image로 우선 사용하도록 프롬프트에 기록

## 3. 참고 자료 읽기

다음 파일을 모두 읽는다.

- `projects/<project-id>/project.md`
- `projects/<project-id>/style/style-rules.md`
- `projects/<project-id>/style/next-lesson-notes.md` (없으면 빈 것으로 간주)
- `projects/<project-id>/lessons/01/approved.md` (문체·구조 참조용 기준본)
- `projects/<project-id>/lessons/02/approved.md` (있으면 변형 패턴 참조용; 특히 preschool-bible-seomun26에서는 우선 참조)
- `projects/<project-id>/lessons/NN/input.md`
- `projects/<project-id>/project.md`의 "특수 지침" 섹션
- 시각 스타일이 지정된 경우 `doc-styles/<style-id>.json`
- `projects/<project-id>/sources/자료목록.md`가 있으면 읽는다. input.md의 "원천 자료 범위"에 해당하는 `sources/` 파일들도 함께 읽는다.

`input.md`가 없으면 사용자에게 이 과의 주제와 핵심 내용 3가지를 물어보고, 답변을 받아 `projects/<project-id>/lessons/NN/input.md`로 저장한 뒤 이어서 진행한다.

## 4. lesson-writer 서브에이전트 실행

Agent 도구로 `subagent_type: lesson-writer`를 호출한다. 프롬프트에 아래 내용을 모두 포함시켜 자체 완결적으로 작성한다.

- project.md, style-rules.md, next-lesson-notes.md, 1과 approved.md 전체 내용 (또는 핵심 요약과 파일 경로)
- 2과 approved.md가 있으면 그 내용과 "1과는 구조 기준, 2과는 변형 기준"이라는 역할 구분
- project.md의 "특수 지침" 섹션 내용
- 이번 과의 input.md 내용
- 원천 자료 범위에 해당하는 sources/ 파일 발췌본과, 자료목록.md에 명시된 해당 자료의 사용 지침
- 주 원천 자료가 지정된 경우: 본문은 원천 자료 내용의 재구성이며, 원천의 핵심 내용을 왜곡·누락하지 않고 원천에 없는 신학적/사실적 주장을 추가하지 않는다는 지시
- 요구사항: `projects/<project-id>/lessons/NN/draft.md`, `worksheet.md`, `teacher-notes.md`를 생성할 것. 1과 승인본의 문체·구조·질문 방식을 따르고, style-rules.md에 명시된 정량적 분량 기준을 맞출 것.
- 성경 인용은 별도 요청이 없는 한 개역개정만 사용할 것.

시각 스타일이 지정된 경우에는 추가로 다음을 프롬프트에 포함한다.

- `doc-styles/<style-id>.json` 전체 내용
- 학생용 페이지 수
- 스타일 JSON의 `visual_contract`, `page_templates`, `content_rules`, `image_prompt_base`, `evaluation`
- 학생용 시각 스타일을 원고 내용보다 후순위 장식으로 취급하지 말고, 학생용 페이지 설계의 구조적 계약으로 취급할 것
- `projects/<project-id>/lessons/NN/student-pages.md`를 추가 생성할 것
- `student-pages.md`는 페이지별로 `PAGE 1`, `PAGE 2`, ...를 명시하고, 각 페이지에 들어갈 정확한 학생용 문구·섹션·장면 설명·레이아웃 의도를 기록할 것
- `projects/<project-id>/lessons/NN/image-prompts.md`를 추가 생성할 것
- `image-prompts.md`에는 페이지별 이미지 생성 프롬프트를 작성하되, 스타일 JSON의 `image_prompt_base`를 공통 프리픽스로 사용하고 해당 과의 성경 장면·활동만 변경할 것
- 이전 승인 이미지 경로가 확인되면 reference image로 사용할 것을 프롬프트에 명시할 것

### preschool-bible-seomun26의 student-pages.md 고정 구조

**PAGE 1 — 핵심 고백**
- 과 번호/과 제목
- 1년차 · 해당 활동 유형
- 아이의 핵심 고백
- 중심 성경
- 오늘의 이야기: 3문장 이내
- 메인 성경 삽화: 페이지 아래 약 40~50%
- 하단 핵심문장 1개

**PAGE 2 — 말씀 이야기**
- 제목 `말씀 이야기`
- 이야기 부제
- 장면 1: 짧은 소제목 + 1~2문장 + 한 사건 그림
- 장면 2: 짧은 소제목 + 1~2문장 + 한 사건 그림
- 장면 3: 짧은 소제목 + 1~2문장 + 한 사건 그림
- `이야기해 보아요`: 질문 2개 이하
- 하단 이야기 핵심문장

**PAGE 3 — 참여 활동**
- 핵심 활동에 맞는 참여형 제목 (`함께 따라 해요`, `함께 만들어 봐요`, `함께 찾아봐요`, `함께 움직여요`, `함께 표현해요` 등)
- 말리듬 챈트: 교사/아이 메아리 응답
- `나는 이렇게 표현해요`: 적합한 선택 활동 4개
- 마침기도: 1~2문장
- 말씀 이어가기: 가정 행동 1개
- 유아들이 해당 활동을 하는 메인 삽화
- 하단 핵심 고백 반복

writer는 자기 결과물을 스스로 평가하지 않는다.

## 5. 즉시 평가 실행

draft가 나오면 바로 evaluate-lesson 흐름을 그대로 수행한다 (lesson-evaluator 실행 → 80점 규칙에 따라 필요시 lesson-updater로 수정 후 재평가, 최대 3회). 시각 스타일이 지정되었다면 `student-pages.md`, `image-prompts.md`, `doc-styles/<style-id>.json`도 평가 입력에 포함한다. evaluate-lesson SKILL.md의 절차를 따른다.

## 6. 사용자 승인 처리

사용자가 최종 승인하면:

1. `draft.md`를 `approved.md`로 복사한다.
2. `project.md`의 진행 현황표에 이번 과를 완료로 갱신한다.
3. 이번 과 작성/평가 과정에서 발견한 특이사항이나 주의할 점을 `style/next-lesson-notes.md`에 "다음 과에서 주의할 점"으로 추가한다.
4. 시각 스타일이 적용된 경우 다음 과에서 일관성 기준으로 삼을 수 있도록 승인된 `student-pages.md`와 이미지 프롬프트/생성 이미지 경로를 유지한다.

## 7. 다음 액션 제안

작업 완료 후 사용자에게 `/export-docx N`과 `/write-lesson N+1`을 이어서 실행할지 제안한다. 시각 스타일이 적용된 프로젝트에서는 다음 과 호출 시 같은 `--style`을 유지한다. project.md에 시각 스타일 ID가 이미 저장되어 있다면 이후 호출에서 `--style` 생략을 허용한다.
