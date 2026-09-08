# Typst 통합 분석 (PHASE 1)

작성 2026-09-08. 실측 기준 커밋 `0d058db`.

## 0. 요약 — 요청서 전제와 실제 구조의 차이

요청서는 TextBuilder를 **Electron/웹 앱 + XML 문서 모델 + GUI 편집기(undo/redo, live preview)**로 전제했다.
실측 결과 이 저장소는 그런 애플리케이션이 **아니다.**

| 요청서 전제 | 실제 |
|---|---|
| Electron 또는 웹앱 | **아님.** Claude Code 스킬 + 파이썬 CLI 스크립트 모음 |
| frontend/backend 분리 | 없음. `viewer/`가 stdlib `http.server` 단일 파일(읽기 전용 뷰어) |
| XML 문서 모델 | **XML 없음.** 마크다운 블록 스킴 + JSON 두 계열 |
| GUI 편집기 · undo/redo | 없음. 편집은 사람/에이전트가 md·json 파일을 직접 고치고, 이력은 git |
| live preview | 없음. `viewer/`가 파일을 읽어 목록·본문을 브라우저에 보여 주는 수준 |
| 렌더링 엔진 | python-docx(DOCX), 헤드리스 크롬(HTML→PDF), python-pptx(PPTX) |

**결론:** "Renderer 추상화 + Typst 백엔드 추가"는 그대로 유효하지만, 그 대상은 *편집기 앱*이 아니라
*파이썬 렌더 스크립트 계층*이다. UI 항목(템플릿 셀렉터, 테마 에디터, 라이브 프리뷰)은 지금 저장소에
대응 화면이 없으므로 **CLI 옵션 + 스킬 인자 + 뷰어 표시**로 매핑한다(§7).

## 1. 현재 프로젝트 구조 (실측)

```
CLAUDE.md · 매뉴얼.md · 빠른시작.md   운영 문서(시스템의 실질적 "명세")
.claude/
  skills/        슬래시 명령(=사용자 진입점): new-textbook, write-lesson, export-docx,
                 evaluate-lesson, make-ppt, kids-print, doctrine150 …
  agents/        lesson-writer / lesson-evaluator / lesson-updater
  workflows/     doctrine150.js, doctrine150-v3.js, elem456.js (배치 오케스트레이션)
scripts/         6,011줄 파이썬 — 렌더러·QC·변환기 (아래 §5)
templates/       project.md / style-rules.md / lesson-input.md / evaluation-rubric.md
                 kids-lesson/render.js (HTML 조판)
doc-styles/      *.json 디자인 프로필 11종  ← 테마의 실질적 소재지
ppt-styles/      PPT 프로필
print-styles/    kids-print.css
viewer/          server.py(383줄) + index.html(600줄) — 로컬 읽기 전용 뷰어
projects/<id>/   교재 프로젝트 (원고·산출물). 15개 프로젝트, md 1,639개
```

의존성 선언 파일(package.json / requirements.txt / tsconfig.json)이 **없다.** 파이썬 의존성은
`python-docx`, `python-pptx`가 문서(매뉴얼.md)로만 요구된다. 나머지는 stdlib.

## 2. 현재 문서 모델 — 두 계열이 공존

### (A) 마크다운 블록 스킴 (레거시 주류, 대부분의 프로젝트)

`scripts/catechism_lesson_docx.py:133 parse_blocks()`가 `# 헤더` 단위로 자르고,
본문 줄에서 인라인 표시를 정규식으로 해석한다. 실질 문법:

| 표시 | 의미 |
|---|---|
| `# COVER` + `키: 값` 줄 | 표지 (parse_kv) |
| `# N. 제목` | 번호 섹션(배너). 색이 `banner_cycle` 순번에 묶임 |
| `# 제목` | 번호 없는 소제목 |
| `[[BOX:제목]] … [[/BOX]]` | 강조 박스 |
| `[[NOTE:제목]] … [[/NOTE]]` | 크림색 주의 박스 |
| `[[WRITING_BOX:N]]` | 필기 줄 N개 |
| `[[TABLE:label\|head+label\|head+tall\|…]]` | 다음 표의 렌더 변형 |
| `**굵게**` · `> 콜아웃` · `□ 항목` · `→ 강조줄` · `① ②` | 인라인 |
| `문)` / `답)` · `## 소제목` 뒤 Q&A 쌍 | 문답 (catechism 모드 전용) |
| `# FOOTER` | 바닥글 |

- **파서와 렌더러가 분리되어 있지 않다.** `lesson_docx.py`가 줄을 읽으며 즉시 docx를 그린다
  (중간 표현 없음). 그래서 "같은 문서를 다른 엔진으로" 낼 수 없다 → 이번 작업의 핵심 병목.
- 스킴을 어긴 줄은 **조용히 버려진다.** 그래서 `scripts/lint_lesson.py`(359줄)가 변환 전
  게이트로 존재한다(CLAUDE.md 고정 규칙).

### (B) 타입 있는 JSON (신규, `elementary-456-v2`)

`projects/elementary-456-v2/content/g4/001.json` + `content/SCHEMA.md`. 이미 **의미 중심 모델**이다:
`grade/no/common_no/unit/title/core/center/story/story_lines/q[]/reading[]/think_head/think_row/
blank/mission/decision/decision_cols/share_*/memory_*/sensitivity`.
`scripts/elem456_build.py`(587줄)가 이 JSON → HTML → PDF로 조판한다.

요청서 §7의 "JSON 하나로 4페이지 교재 자동 생성"은 **이미 이 계열로 동작 중**이다(120과, 3권).
따라서 정규화 모델은 (B)를 일반화하는 방향이 자연스럽고, (A)는 어댑터로 흡수한다.

## 3. 페이지/블록 데이터 구조

- (A) 계열: **페이지 개념이 없다.** 블록의 흐름만 있고 페이지 나눔은 렌더러/브라우저가 결정.
  `lesson_docx.py`는 문서 흐름 + 개별 `add_page_break` 판단, `elem456_build.py`는
  `.page { height: 257mm }` div로 **명시적 페이지**를 만든다.
- (B) 계열: 한 JSON = 한 과 = 고정 3쪽. 쪽 배치는 빌더 코드에 하드코딩(`page_content_strings` 유사).
- 즉 **"페이지"는 지금 렌더러의 소유물이다.** Typst 도입 시 페이지는 템플릿이 결정하게 두고,
  모델에는 `page_hint`(강제 나눔·레이아웃 힌트)만 두는 것이 안전하다.

## 4. 테마/스타일 — 이미 분리돼 있다 (재사용 가능)

`doc-styles/<이름>.json` 프로필 11종. 키: `font{main,heading,fallback}`, `type_scale{cover_title,
banner,body,quote,footer,…}`, `palette{ink,heading,accent,box_fill,box_border,note_fill,
table_head_fill,rule,footer,…}`, `banner_cycle[]`, `page{margins_cm}`, `box`, `spacing`, `decor`.

CLAUDE.md 고정 규칙: **"문서 디자인은 코드에 박지 않는다. 새 디자인은 JSON을 추가해 만들고
렌더러는 고치지 않는다."** → 요청서 §10 테마 시스템과 철학이 이미 일치한다.
**Typst 테마는 이 프로필을 그대로 읽어 쓰는 것이 정답이다**(새 테마 포맷을 만들면 11종이 고아가 된다).

## 5. 현재 렌더링·출력 경로

| 경로 | 스크립트 | 출력 |
|---|---|---|
| 블록md → DOCX (범용, 프로필 적용) | `lesson_docx.py` 772줄 | .docx |
| 블록md → DOCX (구버전, 디자인 하드코딩) | `catechism_lesson_docx.py` 500줄 | .docx |
| 과 합본 | `combine_lessons.py`, `combine_book_docx.py` | .docx |
| 초등 JSON → HTML → PDF | `elem456_build.py` 587줄 | .html, .pdf |
| 어린이 삽화 교재 HTML → PDF | `templates/kids-lesson/render.js` + `print-styles/kids-print.css` | .pdf |
| HTML → PDF 실행기 | `print_pdf.sh` (gstack browse = 헤드리스 크로미움) | .pdf |
| PPT | `pptx_builder.py` 900줄, `pptx_batch.py` 696줄 | .pptx |
| HWP/HWPX → md | `hwp_convert.py` 360줄 | .md |
| 점검 | `lint_lesson.py`, `qc_lesson.py`, `elem456_qc.py`, `verify_docx.py`, `dup_scan.py`, `verse_carryover.py` | 리포트 |

**PDF 생성 방식 2종:** (1) DOCX → 사람이 Word/LibreOffice로, (2) HTML → 헤드리스 크롬.
전자는 조판 품질이 Word에 종속되고, 후자는 브라우저 페이지 나눔에 종속된다.
→ **Typst가 실제로 해결하는 문제:** 페이지 나눔·조판을 우리가 통제하는 결정적(deterministic) 출력.

- **이미지:** `illustrated_docx.py`(159줄)와 kids-print 경로에서 파일 경로 문자열로만 다룬다.
  role/fit/crop/bleed 개념 없음 → 요청서 §8은 **신규 설계**가 맞다.
- **폰트:** 프로필의 폰트명을 docx run에 문자열로 지정. 설치 여부 검사 없음(없으면 조용히 대체).
  실측: Typst가 `Apple SD Gothic Neo`, `NanumGothic`, `NanumMyeongjo` 등 인식 → **폰트 파일 커밋 불필요.**
- **저장/불러오기:** 파일 시스템이 곧 문서. `projects/<id>/lessons/NNN/*.md|json`.
- **undo/redo:** 없음(git). `PROGRESS.md`·`index.json`이 진행 원장.
- **preview:** `viewer/server.py` — 프로젝트·과 목록, 상태(승인/평가됨/초안), 점수 파싱, 본문 표시.
- **테스트:** `scripts/test_hwp_convert.py`(136줄), `scripts/test_pptx_batch.py`(373줄) 2종뿐.
  렌더러·문서모델 테스트 없음 → 요청서 §19 골든 테스트는 신규.

## 6. Typst를 어디에 넣는 것이 가장 안전한가

**결론: 기존 스크립트를 건드리지 않고, 그 옆에 정규화 모델 + 렌더러 계층을 새로 얹는다.**

```
 (A) 블록 스킴 md ──┐
                    ├─→ [adapters] ─→ TextBuilder Document Model ─→ [Renderer]
 (B) 콘텐츠 JSON ──┘        (normalize)         (dataclass/JSON)      ├─ LegacyRenderer  (기존 스크립트 호출, 무변경)
                                                                      └─ TypstRenderer   (신규)
                                                                            ↓ TypstGenerator
                                                                          .typ  +  templates/typst/*
                                                                            ↓ typst compile (CLI)
                                                                          PDF / PNG preview
```

안전 근거:
1. **기존 진입점 불변.** `lesson_docx.py`·`elem456_build.py`·`export-docx` 스킬은 그대로 둔다.
   기존 문서·프로젝트 파일을 **마이그레이션하지 않는다**(어댑터가 읽기만 한다).
2. **레거시는 래핑만.** `LegacyRenderer`는 기존 스크립트를 subprocess/함수 호출로 감싸므로
   레거시 출력이 바뀔 위험이 0이다. 회귀 비교(legacy vs typst)가 가능해진다.
3. **테마 재사용.** `doc-styles/*.json`을 Typst 테마로 매핑 → 디자인 자산 11종이 즉시 살아난다.
4. **Typst 문법은 모델에 침입하지 않는다.** 변환은 `typst_gen.py` 한 곳에서만 일어난다(요청서 §3).

선택: **Typst CLI 방식.** 근거 — 이 저장소는 파이썬 + subprocess가 이미 관용(`print_pdf.sh`,
`combine_lessons.py`)이고, Node/Electron 런타임이 없어 WASM(typst.ts)을 얹으면 새 런타임·번들
체계를 도입해야 한다. CLI는 `typst 0.14.2`가 이미 설치돼 있어 즉시 검증 가능하고 stderr 디버깅이 쉽다.
Renderer API는 실행 방식에 의존하지 않게 두어(§2 인터페이스) 나중에 WASM/embedded로 교체 가능.

## 7. UI 요구(§21, §11-12)의 현실적 매핑

| 요청서 | 이 저장소에서의 실체 |
|---|---|
| 새 프로젝트 · 책 종류 선택 | `/new-textbook` 스킬 인터뷰 + `project.md`의 `renderer`·`template`·`theme` 필드 |
| 템플릿/판형/테마 드롭다운 | CLI 옵션 `--template`·`--page-size`·`--theme` + project.md 기본값 |
| 페이지 편집 버튼(텍스트/그림/질문/…) | 블록 타입 = 모델의 블록 종류. 작성은 md/json 편집(사람·AI) |
| 미리보기 | `typst compile --format png` 산출 + `viewer/`에 표시(후속) |
| PDF 만들기 | `scripts/textbuilder_render.py --renderer typst` |
| 테마 에디터 | `doc-styles/*.json` 편집(기존 규칙 그대로) |

즉 **"Typst 코드를 사용자가 보지 않는다"는 원칙은 유지**되고, 조작 표면만 GUI가 아니라
스킬/CLI다. 이는 이 저장소의 기존 UX와 일치한다.

## 8. 리스크와 방어

| 리스크 | 방어 |
|---|---|
| 레거시 출력 회귀 | LegacyRenderer는 기존 스크립트를 호출만. 골든 테스트로 산출물 해시 비교 |
| 블록 스킴 손실 변환 | 어댑터에 미지원 표시 경고 리포트. `lint_lesson.py`를 계속 게이트로 사용 |
| Typst 미설치 환경 | `TypstRenderer.available()` 검사 → 미설치 시 명확한 오류 + LegacyRenderer 폴백 |
| 한글 폰트 부재 | 테마 폰트 존재 검사(`typst fonts`) → fallback 체인(Apple SD Gothic Neo → NanumGothic → Noto Sans KR) + 경고 |
| 폰트 라이선스 | 폰트 **파일을 저장소에 넣지 않는다.** 이름만 참조 |
| 대규모 rewrite | 신규 코드는 `textbuilder/` 패키지에 격리. 기존 `scripts/*` 무변경(신규 CLI만 추가) |

## 9. 다음 단계 (PHASE 2~)

2. `textbuilder/model.py` 정규화 모델 + JSON Schema + TS 타입
3. `textbuilder/renderer.py` Renderer 인터페이스·레지스트리·RenderResult
4. `textbuilder/adapters/` 블록md·콘텐츠JSON → 모델
5. `textbuilder/typst_gen.py` 모델 → .typ (escape·asset 해결)
6. `templates/typst/` shared·book·picture-book·workbook + 컴포넌트 라이브러리
7. `sample-projects/typst-test/` 3종 + 골든 테스트 + legacy 비교
