# TextbookBuilder

Claude Code 안에서 동작하는 다과(多課) 교재 제작 시스템이다. 성경공부 교재, 청소년 수업안,
워크북, 독서교재, 특강자료, 기업교육 자료 등 최대 약 50과 분량의 교재를 만든다.
API 비용 없이 사용자의 Claude 구독 안에서 전 과정을 처리한다.

## 핵심 워크플로우

1과를 기준본(master lesson)으로 정교하게 완성하고 사용자 승인을 받은 뒤, 그 기준본에서
스타일 규칙(정량적 분량 기준 포함)을 추출한다. 이후 과들은 한 과씩 순차 작성하며, 과마다
별도 평가 에이전트가 채점한다.

1. `/new-textbook` — 새 교재 프로젝트 시작, `projects/<id>/project.md` 생성
2. `/import-source` — 원천 자료(해설집 등)를 HWP/HWPX/DOCX/PDF에서 변환해 `sources/`에 등록
3. `/design-lesson1` — 1과 기준본 제작: 웹 리서치 → 구조 3안 제시 및 선택 → 집필 → 평가 →
   승인 → `style-rules.md` 추출
4. `/import-lesson1` — 사용자가 이미 완성한 1과 샘플을 등록해 기준본으로 확정하고
   `style-rules.md` 추출 (`/design-lesson1`의 대체 경로)
5. `/write-lesson N` — N과 작성: 스타일 규칙 + 1과 승인본 참조 → 집필 → 자동 평가
6. `/evaluate-lesson N` — N과 평가 (100점 채점표)
7. `/export-docx N` — Word(DOCX) 변환 (pandoc 사용). `/export-docx all`은 전체 합본
8. `/make-ppt` — 강의 PPT 생성: 과 내용을 슬라이드 언어로 재구성 → spec JSON →
   `scripts/pptx_builder.py`로 PPTX 생성. 스타일은 `ppt-styles/`에서 선택하며
   새 스타일은 `/import-ppt-style`로 등록
9. `/batch-ppt` — 여러 PPT 파일을 한 번에 수정: 폰트 크기 조정, 폰트 통일, 문구 치환/제거,
   색상 치환, 내용 추출. `scripts/pptx_batch.py` 사용
10. `/sync-ppt` — 교재(정본)와 PPT를 대조해 어긋난 질문/인용/핵심문장을 확인받고 일괄 반영
11. `/validate-print` — 책·최종 PDF 검증. 오려 붙이기는 공통 원본과 윤곽으로 제작하고
    조립본·오리기 부록의 빈 뒷면·최종 PDF·파일 변경 여부를 검사한다.

## 고정 규칙

- 성경 인용은 반드시 개역개정을 사용한다. 사용자가 명시적으로 다른 번역을 요청한 경우에만 예외로 한다.
- 평가 점수가 80점 미만이면 `lesson-updater`가 자동으로 수정한 뒤 재평가한다. 최대 3회 반복한다.
  80점 이상이면 자동 수정하지 않고, 개선 제안을 번호 목록으로 제시한 뒤 사용자 지시를 기다린다.
- 분량은 정량적으로 관리한다. 기본 기준은 과당 A4 2–3장(약 2,500–4,000자)이며, 평가 시 글자 수를
  실측하여 기준 대비 ±10% 이내면 만점을 준다.
- 한 번에 한 과만 작업한다. 사용자 승인 없이 다음 과로 임의로 넘어가지 않는다.
- 산출물의 1순위는 Word(DOCX)다. `/export-docx`로 변환한다.
- 집필과 평가는 분리한다. `lesson-writer`가 쓰고, `lesson-evaluator`가 채점하며, 같은 에이전트가
  자기 글을 스스로 평가하지 않는다.
- `project.md`의 특수 지침 섹션은 모든 작업에서 최우선으로 따른다. 주 원천 자료가 있는 교재는
  창작이 아니라 원천 재구성으로 작업한다.

## 평가 기준 (100점 만점)

책 출판·최종 인쇄 요청에는 `.claude/skills/validate-print/SKILL.md`를 적용한다.
원고 평가 점수와 실제 활동의 조립 가능성은 별개다. 기계 검사는 `machine_pass`로 보고하고,
교육 내용·모든 페이지 시각 검토·실물 조립 중 하지 않은 검사는 완료로 보고하지 않는다.
오려 붙이기와 퍼즐의 빈자리·조각을 각각 AI로 생성하지 않는다. 완성 장면 한 장과 공유
윤곽에서 생성한다. 자세한 명세와 실행법은 `docs/print-validation.md`에 있다.

- 스타일 일치도 25
- 분량 유지 20 (글자 수 실측, 기준 대비 ±10% 만점)
- 핵심내용 반영 20
- 질문·활동 품질 15
- 문장 자연스러움(AI 티 여부) 10
- 성경 인용 정확성 10

## Subagents (.claude/agents/)

- `lesson-writer` — 과 집필
- `lesson-evaluator` — 과 평가
- `lesson-updater` — 80점 미만 시 자동 수정

## 디렉터리 구조

```
projects/<project-id>/
├── project.md              # 교재 개요 + 과별 진행 현황표 (참고 자료 / 특수 지침 포함)
├── sources/                # 원천 자료 (해설집 등, HWP/HWPX/DOCX/PDF에서 변환)
│   ├── 자료목록.md          # 각 자료의 역할 (주 원천 자료 / 보조 참고 / 스타일 참조)
│   └── ...                 # 변환된 원천 자료 md 파일들
├── style/
│   ├── style-rules.md      # 1과 승인 후 추출되는 스타일 규칙 (정량 분량 포함)
│   └── next-lesson-notes.md # 다음 과 작성 시 참고사항 (누적)
└── lessons/NN/             # 01, 02, ... (zero-padded)
    ├── input.md            # 사용자 제공: 주제 + 핵심내용 3가지 (+ 원천 자료 범위)
    ├── draft.md            # 학생용 본문
    ├── worksheet.md        # 활동지
    ├── teacher-notes.md    # 교사용 해설
    ├── evaluation.md       # 평가 결과
    ├── feedback.md         # 뷰어에서 남긴 수정 요청 (있는 경우)
    ├── approved.md         # 승인본
    └── exports/            # docx 출력
```

사용자가 "N과 피드백 반영해줘"라고 하면 `lessons/NN/feedback.md`를 읽어 `lesson-updater`로
해당 지적만 반영한다.

