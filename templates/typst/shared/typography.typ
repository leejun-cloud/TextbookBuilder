// 타이포그래피 — 한글 조판 기본값과 크기 스케일.
//
// 한글 처리 요지:
//  - lang: "ko" 를 켜서 Typst의 한국어 줄바꿈 규칙을 쓴다(조사·문장부호가 줄머리에 오지 않게).
//  - 폰트는 배열(폴백 체인)로 넘긴다. 앞의 것이 없으면 Typst가 다음 것을 쓴다.
//  - 한글은 라틴보다 자모가 촘촘해 보이므로 행간을 넉넉히(기본 1.55) 준다.
//  - 양끝맞춤(justify)은 한글 장문에서 어색한 공백을 만들 수 있어 기본 off로 두고,
//    단행본 템플릿에서만 켠다.

#import "colors.typ": c

#let size-of(theme, name, fallback) = {
  let s = if type(theme) == dictionary and "size" in theme { theme.size } else { (:) }
  let v = if name in s { s.at(name) } else { fallback }
  if type(v) == length { v } else { v * 1pt }
}

#let font-of(theme, group) = {
  let f = if type(theme) == dictionary and "fonts" in theme { theme.fonts } else { (:) }
  if group in f and f.at(group).len() > 0 { f.at(group) }
  else { ("Apple SD Gothic Neo", "NanumGothic", "Noto Sans KR") }
}

#let spacing-of(theme, name, fallback) = {
  let s = if type(theme) == dictionary and "spacing" in theme { theme.spacing } else { (:) }
  if name in s { s.at(name) } else { fallback }
}

#let decor-of(theme, name, fallback) = {
  let d = if type(theme) == dictionary and "decor" in theme { theme.decor } else { (:) }
  if name in d { d.at(name) } else { fallback }
}

// 문서 전체 기본 텍스트 설정
#let apply-typography(theme, justify: false, body) = {
  let lh = spacing-of(theme, "line_height", 1.55)
  set text(
    font: font-of(theme, "body"),
    size: size-of(theme, "body", 10),
    fill: c(theme, "ink"),
    lang: "ko",
    region: "kr",
  )
  set par(leading: (lh - 1.0) * 1em, justify: justify, spacing: spacing-of(theme, "para_gap_pt", 5) * 1pt)
  set heading(numbering: none)
  show heading: it => block(
    above: spacing-of(theme, "section_gap_pt", 8) * 1pt,
    below: spacing-of(theme, "para_gap_pt", 5) * 1pt,
    text(font: font-of(theme, "heading"), weight: "bold", fill: c(theme, "heading"), it.body),
  )
  body
}

// 제목용 텍스트
#let head-text(theme, s, size: none, fill: none, weight: "bold", tracking: 0pt) = text(
  font: font-of(theme, "heading"),
  size: if size == none { size-of(theme, "subhead", 11.5) } else { size },
  fill: if fill == none { c(theme, "heading") } else { fill },
  weight: weight,
  tracking: tracking,
  s,
)
