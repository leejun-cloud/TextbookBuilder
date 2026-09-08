// 이미지 — role/fit/crop/bleed/rounded/caption/overlay/누락 placeholder (요청서 §8)
//
// 누락 이미지는 **컴파일을 실패시키지 않는다.** 회색 placeholder + alt 텍스트로 그려서
// 편집 중에도 전체 미리보기가 계속 나오게 한다(어댑터가 경고를 따로 올린다).

#import "colors.typ": c, tint
#import "typography.typ": size-of, font-of

#let has(b, k) = type(b) == dictionary and k in b
#let get(b, k, fb) = if has(b, k) { b.at(k) } else { fb }

// fit 문자열 → typst image fit
#let fit-of(b) = {
  let f = get(b, "fit", "contain")
  if f == "cover" { "cover" } else if f == "fill" { "stretch" } else { "contain" }
}

#let placeholder(theme, b, width: 100%, height: 40mm) = block(
  width: width, height: height,
  fill: tint(c(theme, "rule"), amount: 90%),
  stroke: (paint: c(theme, "rule"), thickness: 0.6pt, dash: "dashed"),
  radius: 2mm,
  inset: 4mm,
  align(center + horizon, text(
    size: size-of(theme, "footer", 8.5), fill: c(theme, "footer"),
    [그림 없음] + if get(b, "alt", "") != "" { linebreak() + get(b, "alt", "") } else { [] },
  )),
)

// 핵심: 이미지 한 장
#let illustration(theme, b, width: 100%, height: auto, radius: none) = {
  let r = if radius != none { radius } else {
    let rr = get(b, "radius", 0)
    if type(rr) == length { rr } else { rr * 1mm }
  }
  if get(b, "missing", false) or get(b, "src", "") == "" {
    placeholder(theme, b, width: width, height: if height == auto { 40mm } else { height })
  } else {
    let img = image(b.src, width: 100%, height: if height == auto { auto } else { 100% }, fit: fit-of(b))
    let boxed = if r != 0pt and r != 0 {
      block(width: width, height: height, radius: r, clip: true, img)
    } else {
      block(width: width, height: height, img)
    }
    boxed
  }
}

// 캡션이 있으면 아래에 붙인다
#let illustration-with-caption(theme, b, width: 100%, height: auto, radius: none) = {
  let cap = get(b, "caption", get(b, "text", ""))
  block(width: width, breakable: false, {
    illustration(theme, b, width: 100%, height: height, radius: radius)
    if cap != "" {
      v(1.2mm)
      align(center, text(size: size-of(theme, "quote_attr", 9), fill: c(theme, "footer"), cap))
    }
  })
}

// 배경 이미지 + 텍스트 오버레이 (그림책 07)
#let background-overlay(theme, b, body, height: 100%) = block(
  width: 100%, height: height, clip: true, radius: 0pt,
  {
    place(top + left, illustration(theme, b, width: 100%, height: height))
    place(bottom + left, block(
      width: 100%, inset: 8mm,
      fill: color.mix((white, 78%), (c(theme, "ink"), 22%)),
      body,
    ))
  },
)

// 여러 삽화 격자 (그림책 08)
#let illustration-grid(theme, blocks, cols: 2, gap: 4mm) = grid(
  columns: (1fr,) * cols,
  gutter: gap,
  ..blocks.map(b => illustration-with-caption(theme, b, width: 100%, height: 45mm, radius: 2mm)),
)
