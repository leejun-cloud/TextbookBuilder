# 책과 오려 붙이기 제작·검증

## 준비와 바로 실행

```bash
python3 -m pip install -r requirements-print.txt
python3 scripts/qc_activity.py sample-projects/cut-paste/activity.json
python3 scripts/build_cut_paste.py sample-projects/cut-paste/activity.json -o build/demo/book.pdf
python3 scripts/qc_print.py build/demo/book.qc.json --verify-report --activity-spec sample-projects/cut-paste/activity.json
python3 scripts/test_print_qc.py -v
```

예제는 기하 도형으로 치수·조립 구조를 확인하는 샘플이다. 실제 교재의 성경 삽화를 대신하지 않는다. 기존 Typst 설치 없이 이 전용 경로를 실행할 수 있다. 한글 글자를 포함한 TrueType 폰트는 시스템에서 찾으며, 찾지 못하면 `--font /경로/NanumGothic.ttf`를 지정한다. 폰트 파일은 저장소에 넣지 않는다.

## 한 원본에서 생성

빈자리 없는 완성 장면 PNG/JPEG를 먼저 확정한다. EXIF 회전을 적용하여 저장한다. 각 조각의 원본 픽셀 좌표와 윤곽을 한 번 정한다. 같은 정의로 본문의 빈자리와 오리는 조각을 만들며, 조각은 위치만 옮긴다. 페이지에 들어가지 않아도 조각만 축소하거나 돌리지 않는다.

기존 AI 활동지가 한 장의 그림으로 합쳐져 있으면 정확한 조각 분리가 자동으로 보장되지 않는다. 완성 원본을 준비하거나 편집자가 조각 영역을 다시 정해야 한다. 불분명한 영역을 추측해 합격시키지 않는다.

```json
{
  "schema": "cut-paste/v1",
  "language": "ko",
  "page": {"size": "B5", "margin_mm": 14, "gutter_mm": 6, "min_dpi": 300, "min_piece_mm": 12},
  "activities": [{
    "id": "01",
    "title": "말씀을 잘 들어요",
    "instruction": "조각을 오려 같은 모양의 빈자리에 붙여요.",
    "scene": {"src": "scene.png", "x_mm": 20, "y_mm": 55, "width_mm": 142},
    "pieces": [{"id": "ear", "label": "귀", "crop_px": [180, 180, 320, 400], "outline": "ellipse"}]
  }]
}
```

- 위 좌표는 1800x1200px 예제 크기의 예시다. 실제 그림의 귀 위치를 측정하여 바꾼다.
- `crop_px`는 원본 이미지 왼쪽 위를 기준으로 한 정수 `[x,y,가로,세로]`다.
- `outline`은 `rectangle`, `ellipse` 또는 잘라낸 영역 내부의 0~1 좌표 다각형이다. 예: `[[0,0],[1,0],[0.8,1],[0,0.7]]`. 점 순서를 유지한다. 곡선은 충분히 촘촘한 점으로 표현한다.
- 장면의 가로 mm와 원본 비율로 높이 및 모든 조각의 실제 크기를 계산한다. 조각별 `width_mm`, `flip`, `rotation` 등 독립 변형 필드는 거부한다.
- 겹치는 조각 영역, 자기 교차 윤곽, 누락·중복 ID, 경계 밖 좌표, 작은 조각, 낮은 해상도를 차단한다. 경계 사각형이 겹치는 조각도 보수적으로 거부하므로 편집자가 영역을 정리한다.
- 양쪽 모두 제본 여백을 확보한다. 가위질 가능한 크기와 해상도는 교육 대상·인쇄소에 맞게 명세에서 설정한다. 기본값이 모든 연령에 적합하다는 뜻은 아니다.

## 생성되는 파일

`-o build/demo/book.pdf`를 지정하면 다음을 만든다.

| 파일 | 용도 |
|---|---|
| `book.pdf` | 활동면과 오리기 부록을 합친 책 |
| `book.activities.pdf` | 빈자리가 있는 활동면 |
| `book.cutouts.pdf` | 실제 크기 조각, 쪽 안내, 빈 뒷면, 50mm 확인선 |
| `book.assembled.pdf` | 같은 조각을 원래 위치에 얹은 교사용 조립본 |
| `book.qc.json` | 실제 PDF 검사, 원본·명세·산출물 SHA-256, 미확인 사항 |

기존 본문을 앞에 붙이려면 다음처럼 실행한다. 원래 본문과 같은 판형이어야 한다. 기존 AI 활동지가 본문에 이미 있으면 편집 단계에서 교체할 면을 먼저 정리한다. 이 명령이 기존 본문의 활동지를 자동으로 찾아 제거하지는 않는다.

```bash
python3 scripts/build_cut_paste.py projects/my-book/activity.json \
  --body-pdf build/body.pdf --font /경로/NanumGothic.ttf -o build/book.pdf
```

부록은 오른쪽 면(홀수 쪽)에서 시작하며 필요하면 앞에 빈 면을 삽입한다. 오리기 면 뒤는 항상 비운다. 조각 라벨은 합본에서 붙일 활동면의 실제 페이지 번호를 사용한다. 실제 도서에 표지·간지 등을 추가하면 최종 순서로 다시 합쳐야 한다.

## 일반 Typst 교재의 최종 출력

```bash
python3 scripts/textbuilder_render.py input.json --final --page-size B5 \
  --min-image-dpi 300 -o build/final.pdf
python3 scripts/qc_print.py build/final.pdf --page-size B5 --expected-pages 24 \
  --min-image-dpi 300 --json build/final-check.json
```

`--final`은 모든 사전 경고를 차단한다. 편집 미리보기의 누락 그림 대체 기능은 유지한다. 후보 PDF는 임시 파일로 만들고 실제 쪽수·판형·해상도·사용 폰트 포함 여부 등을 다시 검사한 뒤에만 목적 파일로 교체한다. 최종 모드의 최소 해상도 기본값은 150dpi이며 인쇄소 기준에 맞춰 지정한다. 도련이 있는 Typst 문서는 도련을 포함한 출력 용지 크기를 검사한다. PDF/X·ICC·재단 상자 검증은 별도 인쇄소 preflight가 필요하다.

예상 쪽수는 기본적으로 모델의 페이지 수이며 `book/standard`의 별도 표지 1쪽은 포함한다. 흐름 조판이나 사용자 템플릿의 실제 예상 쪽수가 다르면 `--expected-pages 24`처럼 명시한다. 내용이 넘쳐 의도치 않게 늘어난 페이지를 자동으로 합격시키지 않는다.

이미지 `crop: [x,y,w,h]`는 비율 0~1로 입력하며 Python에서 실제 PNG로 잘라낸다. `width`/`height`는 숫자(mm) 또는 `25mm`, `2.5cm`, `1in`, `72pt`, `50%` 형식을 사용한다. 공통 이미지 캡션 배치 경로는 이 크기를 반영한다. 별도의 고정 레이아웃 템플릿은 자신의 배치 규칙을 가질 수 있으므로 조각에는 전용 제작 경로를 사용한다.

## 증거와 한계

- `machine_pass`는 실행된 기계 검사만 통과했다는 뜻이다. 교육 내용, 그림의 의미, 가위질 난이도, 이미지 속 글자 OCR 정확성, 실물 인쇄는 자동 승인하지 않는다.
- 출력 직후의 모든 페이지와 조립본을 눈으로 확인한다. 원본 자체의 잘못된 귀 방향·표정·본문 오류는 같은 원본을 복제해도 남는다.
- 최종 PDF 렌더링 비교 회귀검사는 조립된 패치가 원본을 복원하는지 확인한다. 실제 입력의 윤곽은 사용자가 정한 것이므로 임의 그림의 의미상 올바른 윤곽을 자동으로 찾아주는 기능이 아니다.
- 실제 크기 100%로 인쇄하여 50mm 확인선을 재고 대표 활동을 직접 잘라 붙인다. 화면·PDF 검사만으로 프린터의 배율과 재단 오차를 검증할 수 없다.
- 검사 후 PDF·명세·원본이 바뀌면 `--verify-report`가 실패한다. 보고서만 남기고 산출물이나 원본을 바꾸어 이전 합격을 재사용하지 않는다.
- 오류 시 새 책 PDF를 확정하지 않으며 기존 출력은 보존한다. 입력 검사에서 실패하면 새 보고서가 생기지 않을 수 있으므로 반드시 종료 코드를 확인한다.
