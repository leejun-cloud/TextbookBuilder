---
name: make-ppt
description: 강의·교재 내용을 프리미엄 디자인의 PowerPoint(PPTX)로 만든다. 스타일 라이브러리(ppt-styles/)의 프로필을 골라 일관된 비주얼로 생성한다. 트리거 — "PPT 만들어줘", "강의 슬라이드", "/make-ppt"
---

# make-ppt — 강의 PPT 생성

`scripts/pptx_builder.py`로 spec JSON에서 PPTX를 생성한다. 레이아웃 구도는 빌더 코드에,
색·폰트·질감은 `ppt-styles/<이름>.json` 스타일 프로필에 분리되어 있다.

## 절차

### 1. 원본 내용 결정

- 과(課) 기반이면: `projects/<id>/lessons/NN/approved.md` 우선, 없으면 `draft.md`.
- 사용자가 파일이나 주제를 직접 주면 그것을 사용.
- 목표 장수를 물어본다 (미지정 시 기본 12–18장).

### 2. 스타일 선택

`ppt-styles/스타일목록.md`를 읽고 사용 가능한 스타일을 사용자에게 보여준 뒤 선택받는다.
내용 성격에 맞는 스타일을 추천해도 좋다 (예: 에너지 있는 교육 제안 → orange-gradient).
사용자가 고르지 않으면 기본값 `orange-gradient`.

### 3. 슬라이드 언어로 재작성

원문을 그대로 옮기지 말고 슬라이드 언어로 다시 쓴다:

- 슬라이드당 핵심 메시지 1개
- 항목은 3–5개, 긴 문단 금지
- 숫자·키워드를 강조 필드(kicker, stat, value)로 끌어올린다
- **사실 왜곡·통계 창작 금지** — 원문에 없는 숫자를 만들지 않는다

레이아웃은 내용 유형에 맞게 선택하고 다양하게 섞는다. **같은 레이아웃 연속 사용 금지.**
기본 흐름: `cover` → `toc` → (`section` 구분 + 내용 레이아웃들) → `thank_you`.

사용 가능한 레이아웃 19종과 필드는 `scripts/pptx_builder.py` 모듈 docstring 참조:
cover, toc, intro, overview, three_pillars, team, two_column, process, four_cards,
vision, gallery, kpi, report, bar_chart, full_image, testimonial, case_study,
section, thank_you.

### 4. spec JSON 저장

`lessons/NN/exports/ppt-spec.json`에 저장한다 (과 기반이 아니면 원본 파일 옆 `exports/`).
사용자에게 안내: **나중에 이 JSON만 고쳐서 다시 생성할 수 있다.**

### 5. 이미지

사용자가 사진 폴더를 주면 각 슬라이드의 `image` 필드에 경로를 배치한다.
없으면 그라데이션 플레이스홀더가 자동으로 그려진다고 안내한다 (어색한 가짜 사진 없음).

### 6. 생성 및 보고

```bash
python3 scripts/pptx_builder.py <spec경로> -o <exports>/<제목>.pptx --style <스타일이름>
```

완료 후 보고할 것:
- 출력 파일 경로
- 완전히 편집 가능한 PowerPoint 파일임 (모든 텍스트가 텍스트박스)
- 기본 폰트는 Pretendard — 미설치 환경에서는 시스템 대체 폰트로 열림
  (spec의 `"font"` 필드로 "Malgun Gothic", "Apple SD Gothic Neo" 등 지정 가능)
