# Typst 렌더러 사용법

Typst는 **내부 출판 렌더러**다. 교재를 만드는 사람은 Typst 문법을 몰라도 된다.
콘텐츠(md/json)를 쓰고 아래 명령으로 PDF를 뽑는다.

## 설치

```bash
brew install typst          # 0.14 이상
typst --version
python3 scripts/textbuilder_render.py --list   # 렌더러·템플릿·테마 확인
```

폰트는 **저장소에 넣지 않는다.** 테마가 요구하는 폰트가 없으면 폴백 체인
(Apple SD Gothic Neo → NanumGothic → Noto Sans KR → …)으로 내려가고 경고를 남긴다.

## 자주 쓰는 명령

```bash
# 유년부 4쪽 교재 (JSON 하나 → 4쪽 PDF)
python3 scripts/textbuilder_render.py sample-projects/typst-test/junior-lesson/lesson.json \
    --template workbook/junior --theme kids-junior --page-size B5 -o build/유년부_1과.pdf

# 기존 초등 3권 콘텐츠를 Typst로 (원본 JSON 수정 없음)
python3 scripts/textbuilder_render.py projects/elementary-456-v2/content/g4/001.json \
    --template workbook/elementary --theme kids-bright -o build/초등4_1과.pdf

# 레거시 블록 스킴 md → 단행본
python3 scripts/textbuilder_render.py projects/doctrine-junior-120/lessons/01/draft.md \
    --template book/standard --theme kids-junior -o build/유년부_단행본.pdf

# 그림 동화책 (레이아웃 8종)
python3 scripts/textbuilder_render.py sample-projects/typst-test/picture-book/book.json \
    -o build/그림책.pdf

# 미리보기 PNG (2쪽만)
python3 scripts/textbuilder_render.py <입력> --preview --pages 2 -o build/preview.png

# 레거시(docx) 경로 — 기존 스크립트를 그대로 호출한다
python3 scripts/textbuilder_render.py <draft.md> --renderer legacy -o out.docx

# 디버깅: 정규화 모델과 생성된 Typst 소스를 꺼내 본다
python3 scripts/textbuilder_render.py <입력> --dump-model /tmp/m.json --dump-typst /tmp/d.typ
```

## 판형·테마·템플릿

| 옵션 | 값 |
|---|---|
| `--page-size` | A4 · A5 · B5(JIS) · B5-ISO · 210x210 · 6x9in (모델에서 custom 지정 가능) |
| `--theme` | `doc-styles/*.json` 프로필 (기존 11종 그대로 재사용) |
| `--template` | `workbook/junior` · `workbook/elementary` · `book/standard` · `picture-book/full-image` |
| `--renderer` | `typst`(기본) · `legacy` |
| `--fallback` | 주 렌더러 불가 시 대체 (예: `--renderer typst --fallback legacy`) |

## 새 디자인을 만들 때

**Typst 파일을 고치지 않는다.** `doc-styles/`에 JSON 프로필을 추가하고 `--theme`으로 고른다
(CLAUDE.md 고정 규칙과 같다). 색·폰트·크기·여백·둥근모서리가 전부 프로필에서 온다.

레이아웃 자체를 바꾸려면 `templates/typst/<종류>/<이름>/main.typ`를 새로 만든다.
`render-book(doc)` 하나만 export하면 CLI가 자동으로 인식한다(`--list`로 확인).

## 어린이 교재 JSON (요청서 §7 구조)

`sample-projects/typst-test/junior-lesson/lesson.json`이 기준 예다. 최소 형태:

```json
{
  "schema": "kids-lesson",
  "grade": "유년부 1년차", "lesson": 1, "title": "…",
  "opening": "생각열기 질문",
  "story": { "title": "…", "body": ["문단1", "문단2"] },
  "words": [{ "word": "왕", "meaning": "…" }],
  "keywords": [{ "word": "…", "meaning": "…" }],
  "coreSentence": "…",
  "findInWord": [{ "q": "…", "ref": "엡 1:10", "lines": 1 }],
  "activities": [{ "title": "…", "materials": "…", "steps": ["1", "2"], "images": [{ "src": "assets/x.png" }] }],
  "fillBlanks": [{ "text": "… ______이세요.", "answer": "왕" }],
  "summary": "…", "prayer": "…",
  "memoryVerse": { "ref": "에베소서 1:10", "text": "…" },
  "reflection": "…", "confession": "…",
  "assets": { "hero": { "src": "assets/hero.png", "fit": "cover", "alt": "…" } }
}
```

- `fillBlanks[].answer`는 **학생 지면에 인쇄되지 않는다**(모델의 attrs로만 보관). 테스트가 이를 지킨다.
- 이미지가 없으면 컴파일이 실패하지 않고 «그림 없음 + alt» placeholder가 그려지며 경고가 뜬다.

## 테스트

```bash
python3 scripts/test_textbuilder.py        # 32개 (typst 없으면 컴파일 테스트만 skip)
```

무엇을 지키는지: 문서→typst 변환 · Typst 문법 무력화(이스케이프) · 한글 보존 · 자산 해결 ·
누락 이미지 degrade · 템플릿 선택 · 테마 매핑 · 실제 PDF 컴파일(쪽수·판형·한글) ·
빈칸 정답 미인쇄 · 렌더러 폴백 · 레거시 계약.
