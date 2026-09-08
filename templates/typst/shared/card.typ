// 카드형 어린이 교재 부품 — 참조 지면(3학년 81과)의 구조를 컴포넌트로 옮긴 것.
// 둥근 카드 지면 · 학년/과 배지 · 아이콘 제목 · 손글씨 메모 · 번호 소제목 ·
// 점선 필기칸 · 인라인 빈칸 · 선택지 · 연결하기 · 그림 순서 패널 · 캐릭터 말풍선 · 낱말 칩

#import "colors.typ": c, tint, hex
#import "typography.typ": size-of, font-of, spacing-of
#import "image.typ": illustration, get

// 카드 지면 테두리(그라디언트). page의 배경으로 깐다.
#let card-frame(theme, radius: 7mm, thickness: 2.2pt) = place(
  top + left, dx: 3mm, dy: 3mm,
  block(width: 100% - 6mm, height: 100% - 6mm, radius: radius, fill: white,
        stroke: thickness + gradient.linear(
          c(theme, "accent"), tint(c(theme, "accent"), amount: 45%), angle: 35deg)),
)

// 학년/과 배지 — 두 줄(3학년 / 81과)
#let grade-badge(theme, top: "", bottom: "") = box(
  radius: 3mm, inset: (x: 3mm, y: 2mm), fill: c(theme, "accent"),
  align(center, {
    text(size: size-of(theme, "footer", 8.5), fill: white, weight: "bold", top)
    linebreak()
    text(size: size-of(theme, "cover_badge", 9.5) * 1.15, fill: white, weight: "bold", bottom)
  }),
)

// 아이콘 + 큰 제목 + (오른쪽) 손글씨 메모
#let icon-title(theme, title, icon: "", note: "") = block(width: 100%, below: 3mm, grid(
  columns: (auto, 1fr, auto), gutter: 3mm, align: (horizon, horizon, top),
  if icon != "" { text(size: size-of(theme, "cover_title", 20) * 0.9, icon) } else { [] },
  text(font: font-of(theme, "heading"), size: size-of(theme, "cover_title", 20) * 1.1,
       fill: c(theme, "heading"), weight: "bold", tracking: -0.2pt, title),
  if note != "" {
    block(width: 34mm, align(right, text(size: size-of(theme, "footer", 8.5) * 0.95,
                                          fill: c(theme, "accent"), style: "italic", note)))
  } else { [] },
))

// 오늘의 한 문장 — 왕관 + 굵은 문장(둥근 테두리 박스)
#let crown-box(theme, title, sentence, icon: "👑") = block(
  width: 100%, radius: 4mm, inset: (x: 4mm, y: 3mm), above: 1mm, below: 3mm,
  fill: white, stroke: 1.2pt + c(theme, "accent"),
  align(center, {
    text(size: size-of(theme, "subhead", 11.5) * 1.25, fill: c(theme, "heading"),
         weight: "bold", font: font-of(theme, "heading"), icon + " " + title)
    if sentence != "" {
      v(1.2mm)
      text(size: size-of(theme, "body", 10) * 1.02, sentence)
    }
  }),
)

// 번호 원 + 소제목 + 안내문 (2쪽·3쪽·4쪽의 1/2/3/4 항목)
#let num-heading(theme, n, title, hint: "", fill: none) = block(width: 100%, above: 3mm, below: 1.5mm,
  grid(columns: (auto, auto, 1fr), gutter: 2.2mm, align: (horizon, horizon, horizon),
    box(width: 5.6mm, height: 5.6mm, radius: 50%,
        fill: if fill == none { c(theme, "accent") } else { fill },
        align(center + horizon, text(size: size-of(theme, "footer", 8.5), fill: white,
                                     weight: "bold", str(n)))),
    text(font: font-of(theme, "heading"), size: size-of(theme, "subhead", 11.5),
         fill: c(theme, "heading"), weight: "bold", title),
    if hint != "" { text(size: size-of(theme, "quote_attr", 9), fill: c(theme, "footer"), hint) } else { [] }),
)

// 라벨 + 안내 한 줄(번호 없는 소제목)
#let mini-heading(theme, icon: "", title: "", hint: "") = block(width: 100%, above: 2.5mm, below: 1.2mm,
  grid(columns: (auto, 1fr), gutter: 2mm, align: (horizon, horizon),
    text(size: size-of(theme, "subhead", 11.5), fill: c(theme, "accent"), weight: "bold",
         (if icon != "" { icon + " " } else { "" }) + title),
    if hint != "" { text(size: size-of(theme, "quote_attr", 9), fill: c(theme, "footer"), hint) } else { [] }),
)

// 점선 둥근 필기칸
#let dashed-write(theme, lines: 2, prompt: "", fill: none) = block(
  width: 100%, radius: 3mm, inset: 3mm, above: 1.5mm, below: 2.5mm,
  fill: if fill == none { white } else { fill },
  stroke: (paint: tint(c(theme, "accent"), amount: 40%), thickness: 0.8pt, dash: "dashed"),
  {
    if prompt != "" {
      text(size: size-of(theme, "quote_attr", 9), fill: c(theme, "footer"), prompt)
      v(1.2mm)
    }
    for i in range(calc.max(lines, 1)) {
      v(5.2mm)
      line(length: 100%, stroke: (paint: tint(c(theme, "rule"), amount: 45%),
                                   thickness: 0.35mm, dash: "densely-dotted"))
    }
  },
)

// 옅은 채움 본문 박스(키워드 찾기 본문 등)
#let soft-box(theme, body, fill: none, radius: 3.5mm) = block(
  width: 100%, radius: radius, inset: 3.5mm, above: 1.5mm, below: 2.5mm,
  fill: if fill == none { tint(c(theme, "accent"), amount: 92%) } else { fill },
  body,
)

// 문장 속 빈칸 — "성령님이 오셔서 사람들을 ___로 모으시고" 처럼 쓴다
#let inline-blank(theme, width: 30mm) = box(
  width: width, height: 6.4mm, radius: 2mm, baseline: 1.6mm,
  fill: white, stroke: (paint: tint(c(theme, "accent"), amount: 35%), thickness: 0.8pt, dash: "dashed"),
)

// 빈칸 문장 — parts: 문자열과 숫자(빈칸 너비 mm)를 섞은 배열
#let blank-sentence(theme, parts, size-mult: 1.15) = block(
  width: 100%, radius: 3.5mm, inset: 4mm, above: 1.5mm, below: 2.5mm,
  fill: tint(hex("#FDE68A"), amount: 72%),
  align(center, text(size: size-of(theme, "body", 10) * size-mult, weight: "bold", {
    for p in parts {
      if type(p) == str { p } else { inline-blank(theme, width: p * 1mm) }
    }
  })),
)

// 선택지 문항 — "제자들이 모여 ( 예배 / 기도 / 여행 ) 하고 있을 때"
#let choice-line(theme, n, before: "", options: (), after: "") = block(
  width: 100%, above: 1.2mm, below: 1.2mm,
  grid(columns: (auto, 1fr), gutter: 2mm, align: (horizon, horizon),
    box(width: 4.6mm, height: 4.6mm, radius: 50%, fill: tint(c(theme, "accent"), amount: 55%),
        align(center + horizon, text(size: 7pt, fill: white, weight: "bold", str(n)))),
    text(size: size-of(theme, "body", 10), {
      before
      " ( "
      for (i, o) in options.enumerate() {
        if i > 0 { text(fill: c(theme, "footer"), " / ") }
        text(fill: c(theme, "heading"), weight: "bold", o)
      }
      " ) "
      after
    })),
)

// 연결하기 — 열마다 머리 칩 + 항목들, 사이에 점
#let match-columns(theme, heads: (), cols: (), colors: ()) = {
  let ncol = cols.len()
  let pal = if colors.len() == ncol { colors } else {
    (c(theme, "accent"), hex("#F472B6"), hex("#34D399")).slice(0, ncol)
  }
  let nrow = calc.max(..cols.map(x => x.len()))
  block(width: 100%, above: 1.5mm, below: 2mm, {
    // 머리 칩
    grid(columns: (1fr, auto) * ncol, gutter: 0mm, align: horizon,
      ..cols.enumerate().map(((i, _)) => (
        block(width: 100%, radius: 2mm, inset: (y: 1.2mm), fill: tint(pal.at(i), amount: 60%),
              align(center, text(size: size-of(theme, "footer", 8.5), weight: "bold",
                                 fill: c(theme, "ink"), heads.at(i, default: "")))),
        if i < ncol - 1 { h(6mm) } else { [] },
      )).flatten())
    v(1.5mm)
    // 항목 행
    for r in range(nrow) {
      grid(columns: (1fr, auto) * ncol, gutter: 0mm, align: horizon,
        ..cols.enumerate().map(((i, col)) => (
          block(width: 100%, inset: (y: 1mm), text(size: size-of(theme, "body", 10) - 0.6pt,
                                                    col.at(r, default: ""))),
          if i < ncol - 1 { box(width: 6mm, align(center, text(fill: c(theme, "footer"), "·"))) } else { [] },
        )).flatten())
    }
  })
}

// 그림 순서 패널 — 컷마다 번호 동그라미(빈 칸: 아이가 쓴다) + 그림 + 설명
#let panel-sequence(theme, items, cols: 4, numbered: true) = grid(
  columns: (1fr,) * cols, gutter: 3mm,
  ..items.map(it => block(width: 100%, breakable: false, {
    if numbered {
      align(center, box(width: 5.6mm, height: 5.6mm, radius: 50%, fill: white,
                        stroke: 1pt + c(theme, "accent")))
      v(1mm)
    }
    illustration(theme, it, width: 100%, height: 26mm, radius: 2.5mm)
    v(1.2mm)
    align(center, text(size: size-of(theme, "quote_attr", 9) * 0.95,
                       get(it, "caption", get(it, "text", ""))))
  })),
)

// 캐릭터 + 말풍선 (오른쪽 여백에 두는 도우미)
#let character-bubble(theme, said, character: none, width: 34mm, flip: false) = block(
  width: width, breakable: false,
  {
    block(width: 100%, radius: 3mm, inset: 2.6mm, fill: white,
          stroke: 0.9pt + tint(c(theme, "accent"), amount: 30%),
          text(size: size-of(theme, "quote_attr", 9) * 0.95, fill: c(theme, "heading"), said))
    if character != none {
      v(1mm)
      align(center, illustration(theme, character, width: 68%, height: 24mm))
    }
  },
)

// 낱말 칩 줄 — 오늘의 낱말 | 성령님 · 교회 · 예루살렘 · 시작
#let word-chips(theme, label: "오늘의 낱말", items: (), icon: "📖") = block(
  width: 100%, radius: 3mm, inset: (x: 3.5mm, y: 2.4mm), above: 2mm, below: 1mm,
  fill: tint(c(theme, "accent"), amount: 90%),
  grid(columns: (auto, auto, 1fr), gutter: 2.5mm, align: horizon,
    text(size: size-of(theme, "footer", 8.5), fill: c(theme, "accent"), weight: "bold",
         icon + " " + label),
    text(fill: tint(c(theme, "accent"), amount: 30%), "|"),
    text(size: size-of(theme, "body", 10) - 0.5pt, weight: "bold",
         items.join(text(fill: c(theme, "footer"), "  ·  ")))),
)

// 쪽 번호 — 오른쪽 아래 작은 숫자
#let corner-page-number(theme) = place(bottom + right, dx: -1mm, dy: -1mm,
  text(size: size-of(theme, "footer", 8.5) * 1.1, fill: c(theme, "accent"), weight: "bold",
       context str(counter(page).get().first())))

// 강조 띠 — 오늘의 고백
#let confession-bar(theme, label, body, icon: "👑") = block(
  width: 100%, radius: 3.5mm, inset: (x: 4mm, y: 3mm), above: 2mm,
  fill: tint(hex("#FDE68A"), amount: 62%),
  grid(columns: (auto, 1fr), gutter: 3mm, align: (horizon, horizon),
    text(size: size-of(theme, "subhead", 11.5), fill: c(theme, "heading"), weight: "bold",
         icon + " " + label),
    text(size: size-of(theme, "body", 10), body)),
)
