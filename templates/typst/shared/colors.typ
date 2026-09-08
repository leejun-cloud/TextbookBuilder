// 색 — theme.color 딕트("#RRGGBB" 문자열)에서 안전하게 꺼낸다.
// theme에 없는 키를 요구해도 죽지 않고 기본값을 쓴다(템플릿은 콘텐츠 때문에 실패하지 않아야 한다).

#let DEFAULTS = (
  ink: "#3A3A3A",
  heading: "#1F3864",
  accent: "#2E6DA4",
  banner_text: "#FFFFFF",
  box_fill: "#EAF1FA",
  box_border: "#9FBEDD",
  note_fill: "#FDF6E3",
  note_border: "#E0C97F",
  quote_fill: "#F4F7FB",
  quote_text: "#2A4A6B",
  quote_attr: "#1F3864",
  table_head_fill: "#1F3864",
  table_head_text: "#FFFFFF",
  rule: "#9AA5B1",
  footer: "#8A929B",
  cover_kicker: "#7A8899",
  cover_title: "#1F3864",
  cover_sub: "#6B7684",
  cover_badge: "#2E6DA4",
)

#let hex(s) = {
  let t = if type(s) == str { s } else { "#000000" }
  if not t.starts-with("#") { t = "#" + t }
  rgb(t)
}

// theme에서 색 하나. c(theme, "accent")
#let c(theme, name, fallback: none) = {
  let pal = if type(theme) == dictionary and "color" in theme { theme.color } else { (:) }
  if name in pal { hex(pal.at(name)) }
  else if fallback != none { hex(fallback) }
  else if name in DEFAULTS { hex(DEFAULTS.at(name)) }
  else { hex(DEFAULTS.ink) }
}

// 배너 색 순환 — 섹션 순번에 따라 색이 돌아간다(레거시 doc-styles의 banner_cycle과 같은 규칙)
#let banner-color(theme, idx) = {
  let cyc = if type(theme) == dictionary and "banner_cycle" in theme { theme.banner_cycle } else { () }
  if cyc.len() == 0 { c(theme, "heading") } else { hex(cyc.at(calc.rem(idx, cyc.len()))) }
}

// 흰 배경 위에 옅게 깐 색 (연한 채움을 만들 때)
#let tint(col, amount: 88%) = color.mix((col, 100% - amount), (white, amount))
