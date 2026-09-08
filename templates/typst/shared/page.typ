// 판형·여백·머리글/바닥글·페이지 번호.
// 출판 설정(요청서 §14) 중 이 버전이 실제로 반영하는 것:
//   page size / margins(inside·outside 구분) / gutter / bleed / facing pages / page numbers
// 아직 반영하지 않는 것(모델은 이미 담고 있어 나중에 템플릿만 고치면 된다):
//   imposition, spine, blank page 삽입, chapter start 규칙

#import "colors.typ": c
#import "typography.typ": size-of, font-of

#let mm-of(d, name, fallback) = {
  let v = if type(d) == dictionary and name in d { d.at(name) } else { fallback }
  if type(v) == length { v } else { v * 1mm }
}

// doc.page → #set page(...) 인자
#let page-setup(pg) = {
  let bleed = mm-of(pg, "bleed_mm", 0)
  let facing = if type(pg) == dictionary and "facing_pages" in pg { pg.facing_pages } else { false }
  let inside = mm-of(pg, "margin_inside_mm", 20)
  let outside = mm-of(pg, "margin_outside_mm", 20)
  let gutter = mm-of(pg, "gutter_mm", 0)
  (
    width: mm-of(pg, "width_mm", 182) + bleed * 2,
    height: mm-of(pg, "height_mm", 257) + bleed * 2,
    margin: (
      top: mm-of(pg, "margin_top_mm", 19) + bleed,
      bottom: mm-of(pg, "margin_bottom_mm", 16) + bleed,
      inside: inside + gutter + bleed,
      outside: outside + bleed,
    ),
    binding: if facing { left } else { left },
  )
}

// 상단 색 띠 (어린이 교재용)
#let top-band(theme, col: none, height: 4mm) = place(
  top + left,
  dx: -100%,  // 여백 밖까지 채우기 위해 넉넉히 잡고 clip은 페이지가 한다
  block(width: 400%, height: height, fill: if col == none { c(theme, "accent") } else { col }),
)

// 머리글 한 줄: 왼쪽 작은 회색 + 오른쪽 강조
#let header-line(theme, left-text: "", right-text: "") = block(
  width: 100%,
  below: 3mm,
  grid(
    columns: (1fr, auto),
    align: (left + bottom, right + bottom),
    text(size: size-of(theme, "cover_kicker", 9), fill: c(theme, "cover_kicker"), left-text),
    text(size: size-of(theme, "cover_kicker", 9), fill: c(theme, "accent"), weight: "bold", right-text),
  ),
)

// 바닥글: 얇은 선 + 작은 회색 글씨
#let footer-line(theme, s) = {
  set align(bottom)
  block(width: 100%, {
    line(length: 100%, stroke: 0.4pt + c(theme, "rule").lighten(40%))
    v(1.5mm)
    text(size: size-of(theme, "footer", 8.5), fill: c(theme, "footer"), s)
  })
}
