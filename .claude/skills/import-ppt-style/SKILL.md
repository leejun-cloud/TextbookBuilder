---
name: import-ppt-style
description: 사용자가 준 PPTX 파일의 디자인(색·폰트·그라데이션·그림자·모티프)을 분석해 ppt-styles/에 새 스타일 프로필로 등록한다. 트리거 — "이 PPT 스타일 등록", "스타일 추가", "/import-ppt-style"
---

# import-ppt-style — PPT 스타일 등록

사용자가 마음에 들어하는 `.pptx`를 분석해 `ppt-styles/<slug>.json` 프로필을 만든다.
**레이아웃 구도(geometry)는 빌더가 공유하고, 스타일은 색·폰트·질감만 담는다.**

## 절차

### 1. 덱 분석 (python-pptx 덤프)

스크래치 디렉터리에 일회용 스크립트를 작성해 슬라이드별로 덤프한다:

- shape 타입 / autoshape 종류(MSO_SHAPE), 위치·크기
- fill 종류 (solid 색 / gradient stop 색과 위치, `<a:lin ang>` 각도)
- 텍스트 run별 폰트 이름·크기·bold·색
- `<a:effectLst><a:outerShdw>` 그림자 파라미터 (blurRad, dist, dir, alpha)
- ROUNDED_RECTANGLE의 adjustment 값 (모서리 반경)
- 반복해서 등장하는 모티프 도형 (링/원/웨이브 — 도형인지, 미리 렌더된 PNG인지 확인:
  PNG라면 `unzip`으로 `ppt/media/`를 열어 Read 도구로 직접 보고 색·형태를 파악)

팔레트는 **빈도 기준**으로 추출한다: 가장 많이 쓰인 강조색 → primary, 본문 텍스트색 →
charcoal/gray 역할, 배경·카드·구분선 색 등 역할별로 매핑한다.

### 2. 스타일 프로필 작성

`ppt-styles/orange-gradient.json`을 스키마 참고본으로 삼아 같은 구조로 작성한다.
키를 다 채울 필요는 없다 — 빌더가 빠진 키는 기본값으로 채운다. 필수 항목:

- `name`, `description`(한국어 — 어떤 분위기, 언제 쓰면 좋은지), `source`(원본 파일명)
- `palette` (역할별: primary/bright/accent/charcoal/gray/light/white/divider ...)
- `gradient` (main/diagonal/vertical/soft/dark — colors 배열 + angle)
- `font` (main + fallback + latin)
- 추출 가능하면: `type_scale`, `shadow`, `corner_radius`, `motif` 파라미터

### 3. 스타일 목록 등록

`ppt-styles/스타일목록.md`에 항목을 추가한다: 이름, 설명, 어울리는 용도, 원본 파일.

분석 중 기존 19종 레이아웃에 없는 **진짜 새로운 구도**를 발견했다면, 그 목록 항목에
"추가 레이아웃 후보"로 짧게 메모만 남긴다 (구현은 사용자가 요청할 때).

### 4. 검증

새 스타일로 데모를 한 번 빌드해 열리는지 확인한다:

```bash
python3 scripts/pptx_builder.py scripts/demo_deck.json -o /tmp/style-test.pptx --style <slug>
python3 -c "from pptx import Presentation; Presentation('/tmp/style-test.pptx')"
```

완료 후 사용자에게: 등록된 스타일 이름과 `/make-ppt`에서 선택 가능함을 안내한다.
