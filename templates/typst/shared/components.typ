// 컴포넌트 라이브러리 — 모든 값은 theme에서 받는다(하드코딩 최소화).
// 각 컴포넌트는 (theme, ...) 형태이고, theme에 없는 키는 안전한 기본값으로 떨어진다.

#import "colors.typ": c, tint, banner-color, hex
#import "typography.typ": size-of, font-of, spacing-of, decor-of, head-text
#import "image.typ": illustration, illustration-with-caption, illustration-grid, get, has

#let radius-of(theme) = {
  let r = decor-of(theme, "radius_mm", 1.6)
  if type(r) == length { r } else { r * 1mm }
}
#let border-of(theme) = {
  let b = decor-of(theme, "border_pt", 0.7)
  if type(b) == length { b } else { b * 1pt }
}

// ---------------------------------------------------------------- 기본 조각

#let number-badge(theme, n, fill: none, size: 6.5mm) = box(
  width: size, height: size, radius: 50%,
  fill: if fill == none { c(theme, "accent") } else { fill },
  align(center + horizon, text(
    size: size-of(theme, "footer", 8.5), fill: c(theme, "banner_text"), weight: "bold", str(n),
  )),
)

#let lesson-badge(theme, s, fill: none) = box(
  radius: 2.4mm, inset: (x: 3mm, y: 1.6mm),
  fill: if fill == none { c(theme, "accent") } else { fill },
  text(size: size-of(theme, "cover_badge", 9.5), fill: c(theme, "banner_text"), weight: "bold", s),
)

#let page-title(theme, s, sub: "") = block(below: 4mm, {
  text(font: font-of(theme, "heading"), size: size-of(theme, "cover_title", 20),
       fill: c(theme, "cover_title"), weight: "bold", s)
  if sub != "" {
    v(1.5mm)
    text(size: size-of(theme, "cover_sub", 10), fill: c(theme, "cover_sub"), sub)
  }
})

// 번호 배너(레거시 '# N. 제목'과 같은 자리)
#let section-title(theme, s, index: 0, num: "") = block(
  width: 100%, above: spacing-of(theme, "section_gap_pt", 8) * 1pt, below: 2.5mm,
  fill: banner-color(theme, index), radius: radius-of(theme), inset: (x: 4mm, y: 2.2mm),
  text(font: font-of(theme, "heading"), size: size-of(theme, "banner", 12.5),
       fill: c(theme, "banner_text"), weight: "bold",
       if num != "" { num + [  ] + s } else { s }),
)

// 번호 없는 소제목
#let sub-title(theme, s) = block(above: 3.5mm, below: 2mm,
  head-text(theme, s, size: size-of(theme, "subhead", 11.5)))

#let footer-bar(theme, s) = block(width: 100%, {
  line(length: 100%, stroke: 0.4pt + c(theme, "rule").lighten(40%))
  v(1.4mm)
  text(size: size-of(theme, "footer", 8.5), fill: c(theme, "footer"), s)
})

#let page-number(theme) = context text(
  size: size-of(theme, "footer", 8.5), fill: c(theme, "footer"),
  str(counter(page).get().first()),
)

// ---------------------------------------------------------------- 박스류

#let base-box(theme, body, fill: none, border: none, label: "", label-color: none,
              inset: 4mm, radius: none, width: 100%) = block(
  width: width, breakable: false,
  fill: if fill == none { c(theme, "box_fill") } else { fill },
  stroke: if border == none { none } else { border },
  radius: if radius == none { radius-of(theme) } else { radius },
  inset: inset, above: 2.5mm, below: 3mm,
  {
    if label != "" {
      text(font: font-of(theme, "heading"), size: size-of(theme, "footer", 8.5), weight: "bold",
           fill: if label-color == none { c(theme, "heading") } else { label-color }, label)
      v(1.2mm)
    }
    body
  },
)

#let callout-box(theme, body, label: "", variant: "box") = {
  if variant == "note" {
    base-box(theme, body, label: label, fill: c(theme, "note_fill"),
             border: border-of(theme) + c(theme, "note_border"))
  } else if variant == "core" or variant == "confession" {
    base-box(theme, text(weight: "bold", size: size-of(theme, "subhead", 11.5), body),
             label: label, fill: tint(c(theme, "accent"), amount: 90%),
             border: (left: 3pt + c(theme, "accent")))
  } else if variant == "aside" {
    block(width: 100%, inset: (left: 3mm), above: 2mm, below: 2mm,
      stroke: (left: 2pt + c(theme, "rule").lighten(30%)),
      text(size: size-of(theme, "quote_attr", 9), fill: c(theme, "footer"), body))
  } else {
    base-box(theme, body, label: label, border: border-of(theme) + c(theme, "box_border"))
  }
}

#let story-box(theme, paragraphs, big: false) = base-box(
  theme,
  {
    let first = true
    for p in paragraphs {
      if not first { v(spacing-of(theme, "para_gap_pt", 5) * 1pt) }
      first = false
      text(size: if big { size-of(theme, "body", 10) * 1.15 } else { size-of(theme, "body", 10) }, p)
    }
  },
  fill: c(theme, "note_fill"), border: none, inset: 4.5mm,
)

#let verse-box(theme, body, label: "", ref: "") = base-box(
  theme,
  {
    text(fill: c(theme, "quote_text"), style: "italic", body)
    if ref != "" {
      v(1mm)
      align(right, text(size: size-of(theme, "quote_attr", 9), fill: c(theme, "quote_attr"),
                        weight: "bold", "— " + ref))
    }
  },
  label: label, fill: c(theme, "quote_fill"), border: none,
)

#let memory-verse(theme, body, ref: "", label: "말씀 암송") = base-box(
  theme,
  {
    if ref != "" {
      text(size: size-of(theme, "footer", 8.5), fill: c(theme, "accent"), weight: "bold", ref)
      v(1mm)
    }
    text(size: size-of(theme, "subhead", 11.5), fill: c(theme, "quote_text"), body)
  },
  label: label, fill: tint(c(theme, "accent"), amount: 92%),
  border: border-of(theme) + c(theme, "box_border"),
)

#let prayer-box(theme, body, label: "오늘의 기도", lines: ()) = base-box(
  theme,
  {
    body
    for l in lines { v(1.2mm); l }
  },
  label: label, fill: c(theme, "note_fill"),
  border: border-of(theme) + c(theme, "note_border"),
)

// ---------------------------------------------------------------- 필기·질문·활동

#let writing-lines(theme, count: 1, label: "", gap: none) = {
  let h = decor-of(theme, "writing_line_mm", 7.0)
  let hh = if type(h) == length { h } else { h * 1mm }
  block(width: 100%, above: 2mm, below: 2.5mm, {
    if label != "" {
      text(weight: "bold", size: size-of(theme, "body", 10), label)
      v(1mm)
    }
    for i in range(calc.max(count, 1)) {
      v(if gap == none { hh } else { gap })
      line(length: 100%, stroke: 0.35mm + c(theme, "rule").lighten(35%))
    }
  })
}

#let question-box(theme, q, label: "", lines: 1, ref: "") = block(
  width: 100%, above: 2.5mm, below: 2mm, breakable: false,
  {
    if label != "" {
      text(size: size-of(theme, "footer", 8.5), fill: c(theme, "accent"), weight: "bold", label)
      v(1mm)
    }
    grid(
      columns: (auto, 1fr), gutter: 2.5mm, align: (top, top),
      number-badge(theme, "?", size: 5.5mm),
      {
        text(weight: "bold", q)
        if ref != "" { text(size: size-of(theme, "quote_attr", 9), fill: c(theme, "footer"), " (" + ref + ")") }
      },
    )
    if lines > 0 { writing-lines(theme, count: lines) }
  },
)

#let activity-box(theme, steps, label: "오늘의 활동", intro: "", materials: "", note: "") = base-box(
  theme,
  {
    if intro != "" { intro; v(2mm) }
    if materials != "" {
      block(width: 100%, fill: white, radius: radius-of(theme), inset: 2.5mm, below: 2.5mm,
        text(size: size-of(theme, "quote_attr", 9),
             [*준비물* ] + materials))
    }
    let i = 1
    for s in steps {
      grid(columns: (auto, 1fr), gutter: 2.5mm, align: (top, top),
           number-badge(theme, i), s)
      v(1.6mm)
      i += 1
    }
    if note != "" {
      v(0.5mm)
      text(size: size-of(theme, "quote_attr", 9), fill: c(theme, "footer"), "안내 — " + note)
    }
  },
  label: label, fill: tint(c(theme, "accent"), amount: 93%),
  border: border-of(theme) + c(theme, "box_border"),
)

#let keyword-box(theme, items, label: "오늘의 낱말", cols: 1) = base-box(
  theme,
  grid(
    columns: (1fr,) * calc.max(cols, 1), gutter: 2.5mm,
    ..items.map(it => block(width: 100%, {
      text(weight: "bold", fill: c(theme, "accent"), "● ")
      text(it)
    })),
  ),
  label: label, fill: c(theme, "box_fill"), border: none,
)

#let fill-blank(theme, sentence, label: "빈칸을 채워요") = base-box(
  theme,
  text(size: size-of(theme, "subhead", 11.5), weight: "bold", sentence),
  label: label, fill: c(theme, "note_fill"),
  border: border-of(theme) + c(theme, "note_border"),
)

#let reflection-box(theme, prompt: "", label: "나의 생각", lines: 3) = base-box(
  theme,
  {
    if prompt != "" { text(size: size-of(theme, "quote_attr", 9), fill: c(theme, "footer"), prompt) }
    writing-lines(theme, count: lines)
  },
  label: label, fill: white, border: border-of(theme) + c(theme, "box_border"),
)

#let check-list(theme, items, note: "") = block(width: 100%, above: 2mm, below: 2.5mm, {
  for it in items {
    grid(columns: (auto, 1fr), gutter: 2mm, align: (top, top),
         text(fill: c(theme, "accent"), "☐"), it)
    v(1.2mm)
  }
  if note != "" { text(size: size-of(theme, "quote_attr", 9), fill: c(theme, "footer"), note) }
})

// ---------------------------------------------------------------- 말풍선·캐릭터

#let speech-bubble(theme, body, speaker: "", tail: bottom) = block(
  width: 100%, above: 2.5mm, below: 3mm, breakable: false,
  {
    block(width: 100%, fill: white, radius: 3mm, inset: 3.5mm,
      stroke: border-of(theme) + c(theme, "accent"),
      {
        if speaker != "" {
          text(size: size-of(theme, "footer", 8.5), fill: c(theme, "accent"), weight: "bold", speaker)
          v(1mm)
        }
        body
      })
    // 꼬리
    place(bottom + left, dx: 8mm, dy: 2.4mm,
      polygon(fill: white, stroke: border-of(theme) + c(theme, "accent"),
              (0mm, 0mm), (4mm, 0mm), (1.5mm, 2.6mm)))
  },
)

#let character-tip(theme, body, name: "선생님") = block(
  width: 100%, above: 2.5mm, below: 3mm,
  fill: tint(c(theme, "note_border"), amount: 90%), radius: 3mm, inset: 3.5mm,
  grid(columns: (auto, 1fr), gutter: 3mm, align: (top, top),
    box(width: 9mm, height: 9mm, radius: 50%, fill: c(theme, "note_border"),
        align(center + horizon, text(size: 11pt, "☺"))),
    { text(size: size-of(theme, "footer", 8.5), weight: "bold", fill: c(theme, "heading"), name); v(1mm); body }),
)

// 단계 그림 — 번호 배지를 그림 왼쪽 위에 얹는다(따로 떨어뜨리면 무엇의 번호인지 모른다)
#let step-image(theme, b, n: 1) = block(width: 100%, breakable: false, above: 2.5mm, below: 3mm, {
  align(center, block(width: 62%, {
    illustration-with-caption(theme, b, width: 100%, height: 34mm, radius: 2mm)
    place(top + left, dx: -2mm, dy: -2mm, number-badge(theme, n))
  }))
})

// ---------------------------------------------------------------- 표

#let data-table(theme, head: (), rows: (), variant: "plain") = {
  let ncols = if head.len() > 0 { head.len() } else if rows.len() > 0 { rows.at(0).len() } else { 0 }
  if ncols == 0 { return [] }
  let has-head = head.len() > 0 and variant.contains("head")
  let tall = variant.contains("tall")
  let label-col = variant.contains("label")
  block(width: 100%, above: 2.5mm, below: 3mm, table(
    columns: (1fr,) * ncols,
    stroke: 0.5pt + c(theme, "box_border"),
    inset: if tall { (x: 3mm, y: 4.5mm) } else { (x: 3mm, y: 2.2mm) },
    fill: (x, y) => {
      if has-head and y == 0 { c(theme, "table_head_fill") }
      else if label-col and x == 0 { tint(c(theme, "box_fill"), amount: 55%) }
      else { none }
    },
    ..if has-head {
      head.map(h => text(fill: c(theme, "table_head_text"), weight: "bold",
                         size: size-of(theme, "footer", 8.5), h))
    } else { () },
    ..rows.flatten().map(cell => text(size: size-of(theme, "body", 10) - 0.5pt, cell)),
  ))
}

// ---------------------------------------------------------------- 블록 디스패처

#let unknown-box(theme, b) = block(
  width: 100%, fill: tint(c(theme, "rule"), amount: 88%), radius: 1.5mm, inset: 3mm,
  above: 2mm, below: 2mm,
  text(size: size-of(theme, "quote_attr", 9), fill: c(theme, "footer"),
       [처리하지 못한 블록: ] + get(b, "kind", "?") + if get(b, "text", "") != "" { [ — ] + get(b, "text", "") } else { [] }),
)

// 한 블록을 그린다. 템플릿이 특별히 다루지 않는 블록은 모두 여기로 온다.
#let render-block(theme, b, section-index: 0, big-text: false) = {
  let kind = get(b, "kind", "")
  let variant = get(b, "variant", "")
  let txt = get(b, "text", "")
  let label = get(b, "label", "")
  let items = get(b, "items", ())

  if kind == "heading" {
    let lv = get(b, "level", 2)
    if lv <= 1 { page-title(theme, txt) }
    else if variant == "banner" { section-title(theme, txt, index: section-index, num: label) }
    else { sub-title(theme, txt) }
  } else if kind == "text" {
    if variant == "accent" {
      block(above: 2mm, below: 2mm, text(fill: c(theme, "accent"), weight: "bold", txt))
    } else if variant == "strong" {
      block(above: 1.5mm, below: 1.5mm, text(weight: "bold", txt))
    } else if variant == "fine" or variant == "ladder" {
      block(above: 2mm, below: 2mm, width: 100%,
        fill: if variant == "ladder" { tint(c(theme, "accent"), amount: 94%) } else { none },
        inset: if variant == "ladder" { 2.5mm } else { 0mm }, radius: radius-of(theme),
        text(size: size-of(theme, "quote_attr", 9), fill: c(theme, "footer"), txt))
    } else {
      block(above: 1.5mm, below: 1.5mm,
        text(size: if big-text { size-of(theme, "body", 10) * 1.12 } else { size-of(theme, "body", 10) }, txt))
    }
  } else if kind == "image" {
    let role = get(b, "role", "illustration")
    let h = if role == "hero" { 62mm } else if role == "step" { 34mm } else if role == "decoration" { 24mm } else { 46mm }
    illustration-with-caption(theme, b, width: 100%, height: h, radius: 2.5mm)
  } else if kind == "verse" {
    verse-box(theme, txt, label: label, ref: get(b, "ref", ""))
  } else if kind == "question" {
    question-box(theme, txt, label: label, lines: get(b, "count", 1), ref: get(b, "ref", ""))
  } else if kind == "activity" {
    let attrs = get(b, "attrs", (:))
    activity-box(theme, items, label: if label == "" { "오늘의 활동" } else { label },
                 intro: txt,
                 materials: if type(attrs) == dictionary and "materials" in attrs { attrs.materials } else { "" },
                 note: if type(attrs) == dictionary and "note" in attrs { attrs.note } else { "" })
  } else if kind == "callout" {
    callout-box(theme, { txt; for it in items { v(1.5mm); it } }, label: label, variant: variant)
  } else if kind == "table" {
    data-table(theme, head: get(b, "head", ()), rows: get(b, "rows", ()),
               variant: if variant == "" { "plain" } else { variant })
  } else if kind == "fill_blank" {
    fill-blank(theme, txt, label: if label == "" { "빈칸을 채워요" } else { label })
  } else if kind == "writing" {
    writing-lines(theme, count: get(b, "count", 1), label: label)
  } else if kind == "checklist" {
    check-list(theme, items, note: label)
  } else if kind == "memory" {
    memory-verse(theme, txt, ref: get(b, "ref", ""), label: if label == "" { "말씀 암송" } else { label })
  } else if kind == "prayer" {
    prayer-box(theme, txt, label: if label == "" { "오늘의 기도" } else { label }, lines: items)
  } else if kind == "reflection" {
    reflection-box(theme, prompt: txt, label: if label == "" { "나의 생각" } else { label },
                   lines: get(b, "count", 3))
  } else if kind == "speech" {
    speech-bubble(theme, txt, speaker: label)
  } else if kind == "keywords" {
    keyword-box(theme, items, label: if label == "" { "낱말" } else { label },
                cols: if items.len() > 3 { 2 } else { 1 })
  } else if kind == "spacer" {
    v(get(b, "count", 1) * spacing-of(theme, "section_gap_pt", 8) * 1pt)
  } else {
    unknown-box(theme, b)
  }
}

// 블록 배열을 흐름으로 그린다(섹션 배너 색 순환 관리 포함)
#let render-flow(theme, blocks, big-text: false) = {
  let si = 0
  for b in blocks {
    render-block(theme, b, section-index: si, big-text: big-text)
    if get(b, "kind", "") == "heading" and get(b, "variant", "") == "banner" { si += 1 }
  }
}

// kind로 블록 골라내기 (레이아웃 템플릿이 쓴다)
#let pick(blocks, kinds) = blocks.filter(b => kinds.contains(get(b, "kind", "")))
#let drop(blocks, kinds) = blocks.filter(b => not kinds.contains(get(b, "kind", "")))
#let first-of(blocks, kinds) = {
  let f = pick(blocks, kinds)
  if f.len() > 0 { f.at(0) } else { none }
}
