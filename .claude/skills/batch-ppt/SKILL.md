---
name: batch-ppt
description: 여러 개의 PPTX 파일에 같은 작업(폰트 크기 조정, 폰트 통일, 문구 치환/제거, 색상 치환, 내용 추출)을 한 번에 적용한다. `scripts/pptx_batch.py`를 사용. 트리거 — "PPT 일괄 수정", "여러 PPT 한꺼번에", "PPT 대량 작업", "/batch-ppt"
---

# batch-ppt — 여러 PPT 일괄 수정

`scripts/pptx_batch.py`로 여러 `.pptx` 파일에 같은 작업을 한 번에 적용한다.
원본을 항상 보존하는 것이 원칙이며, 실행 전에 반드시 미리보기를 보여준다.

## 1. 수집: 대상과 작업 파악

사용자에게 다음을 확인한다:
- 대상 파일들 (폴더 경로 또는 파일 목록/글롭 패턴)
- 원하는 작업

사용자의 표현을 아래처럼 작업으로 매핑한다:

| 사용자 표현 | 작업(op) | 비고 |
|---|---|---|
| "글씨 크게 해줘" | `scale-font` 또는 `min-font` | 아래 참고 — 반드시 방식을 확인 |
| "문구 빼줘 / 워터마크 지워줘" | `remove-text` | 정확한 문자열을 확인하고, 먼저 `list`/`--dry-run`으로 확인 |
| "여러 문구를 한 번에 바꿔줘" | `replace-map` | `--map pairs.json`으로 여러 {find, replace} 쌍을 한 파일에 한 번에 적용. 교재 기준으로 PPT를 대조·수정하는 경우는 `/sync-ppt` 참고 |
| "폰트 통일해줘" | `set-font` | 한글은 기본으로 East Asian 서체도 함께 설정됨 |
| "색 바꿔줘" | `replace-color` | HEX 코드 확인 (모르면 `list`로 색상 개수만 먼저 확인) |
| "여러 PPT를 하나의 스타일로 통일" | `extract` → 서브에이전트 변환 → `pptx_builder.py` | 3번 참고 |

**"글씨 크게"의 두 가지 의미**를 반드시 사용자에게 구분해서 물어본다:
- **전부 비율로 키우기** (`scale-font --factor`): 이미 있는 크기 차이(제목/본문 등)를 유지한 채
  전체적으로 확대. 배율을 정확히 지정해야 함.
- **최소 크기 보장** (`min-font --size`): "너무 작은 글씨만" 읽기 좋은 크기로 올림. 큰 글씨는
  그대로 둠. **가독성 문제 해결이 목적이면 이쪽을 권장한다.**

## 2. 안전 프로토콜 (반드시 지킬 것)

**첫 실행에서 `--in-place`를 쓰지 않는다.**

항상 이 순서로 진행한다:

① 먼저 `--dry-run`으로 실행해 파일별 변경 건수를 사용자에게 보여준다.

```bash
python3 scripts/pptx_batch.py <op> [옵션] <파일/글롭...> --out-dir <임시경로> --dry-run
```

② 사용자가 확인하면 `--out-dir <원본폴더>/일괄수정_YYYYMMDD/` (또는 사용자가 원하는 경로)로
실제 실행한다.

```bash
python3 scripts/pptx_batch.py <op> [옵션] <파일/글롭...> --out-dir <원본폴더>/일괄수정_YYYYMMDD/
```

③ 사용자에게 **원본은 전혀 손대지 않았음**을 알린다.

사용자가 명시적으로 원본 덮어쓰기를 요청하는 경우에만 `--in-place`를 사용한다. 이 경우에도
`pptx_batch.py`가 저장 직전 같은 폴더에 `백업_YYYYMMDD/` 폴더를 만들어 원본을 자동 백업한다는
점을 미리 안내한다.

## 3. 공통 포맷 재조판 (여러 PPT를 하나의 스타일로 통일)

여러 덱의 내용은 그대로 두고 디자인만 통일하고 싶을 때:

① `extract --format md`로 각 덱의 내용을 텍스트로 추출한다.

```bash
python3 scripts/pptx_batch.py extract --format md <파일들...> --out-dir <추출경로>/
```

② 덱마다 (lesson-writer가 아니라) **general-purpose 서브에이전트**를 Agent 도구로 실행해,
추출된 md 내용을 `pptx_builder.py`용 spec JSON으로 변환하게 한다. 레이아웃은 내용 성격에
맞게 다양하게 고르고, 슬라이드당 3–5항목을 넘지 않게 한다. 사용 가능한 레이아웃과 필드는
`scripts/pptx_builder.py` 모듈 docstring을 참조하도록 서브에이전트에게 안내한다.

③ 각 spec을 다음과 같이 생성한다:

```bash
python3 scripts/pptx_builder.py <spec.json> --style <선택한 스타일> -o <출력.pptx>
```

④ 결과 경로 목록을 보고하고, 원본 pptx들은 전혀 수정되지 않았음을 안내한다.

**덱이 5개 이상이면** 서브에이전트를 병렬로 나눠 처리한다 (Agent 도구 호출을 한 메시지에
여러 개 담아 동시 실행).

## 4. 결과 보고

작업 완료 후 항상 다음을 보고한다:
- 파일별 변경 건수 표 (스크립트가 표준출력에 자동으로 찍어주는 요약 표 활용)
- 출력 폴더 경로
- 확인 방법: 이 저장소의 뷰어는 PPTX를 지원하지 않으므로, PowerPoint 또는 Keynote에서
  직접 열어 확인해야 한다고 안내한다.
