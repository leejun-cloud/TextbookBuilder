// 그림 동화책 템플릿 — 페이지 레이아웃 8종 (요청서 §9)
//
//   full-image                전면 그림
//   image-top-text-bottom     그림 70 / 글 30
//   text-top-image-bottom     글 30 / 그림 70
//   image-left                그림 왼쪽 / 글 오른쪽
//   image-right               글 왼쪽 / 그림 오른쪽
//   full-spread               전면(펼침면 취급 — 재단선까지)
//   background-overlay        배경 그림 + 글 오버레이
//   multi-illustration        여러 삽화 격자
//
// layout이 없거나 모르는 이름이면 image-top-text-bottom으로 떨어진다.

#import "/templates/typst/shared/colors.typ": c
#import "/templates/typst/shared/typography.typ": apply-typography, size-of, font-of
#import "/templates/typst/shared/page.typ": page-setup
#import "/templates/typst/shared/image.typ": (
  illustration, illustration-with-caption, illustration-grid, background-overlay, get,
)
#import "/templates/typst/shared/components.typ": render-flow, pick, drop, first-of, speech-bubble

#let story-text(theme, blocks, size-mult: 1.25) = {
  set par(leading: 0.9em)
  for b in blocks {
    let k = get(b, "kind", "")
    if k == "text" {
      block(above: 2mm, below: 2mm, text(size: size-of(theme, "body", 10) * size-mult,
                                          get(b, "text", "")))
    } else if k == "speech" {
      speech-bubble(theme, text(size: size-of(theme, "body", 10) * size-mult, get(b, "text", "")),
                    speaker: get(b, "label", ""))
    } else {
      render-flow(theme, (b,))
    }
  }
}

#let render-page(doc, pg) = {
  let theme = doc.theme
  let layout = if pg.layout == "" { "image-top-text-bottom" } else { pg.layout }
  let imgs = pick(pg.blocks, ("image",))
  let rest = drop(pg.blocks, ("image",))
  let img = if imgs.len() > 0 { imgs.at(0) } else { none }

  if layout == "full-image" or layout == "full-spread" {
    // 전면 그림. bleed가 설정돼 있으면 재단선까지 채운다.
    block(width: 100%, height: 100%, illustration(theme, img, width: 100%, height: 100%))
  } else if layout == "background-overlay" {
    background-overlay(theme, img, story-text(theme, rest), height: 100%)
  } else if layout == "multi-illustration" {
    if pg.title != "" {
      text(font: font-of(theme, "heading"), size: size-of(theme, "cover_title", 20) * 0.7,
           fill: c(theme, "heading"), weight: "bold", pg.title)
      v(3mm)
    }
    illustration-grid(theme, imgs, cols: if imgs.len() > 4 { 3 } else { 2 })
    v(3mm)
    story-text(theme, rest, size-mult: 1.0)
  } else if layout == "image-left" or layout == "image-right" {
    let img-col = block(width: 100%, height: 100%, illustration(theme, img, width: 100%, height: 100%))
    let txt-col = align(horizon, story-text(theme, rest))
    grid(
      columns: (1fr, 1fr), gutter: 6mm, rows: (100%,),
      ..if layout == "image-left" { (img-col, txt-col) } else { (txt-col, img-col) },
    )
  } else if layout == "text-top-image-bottom" {
    grid(
      rows: (30%, 70%), gutter: 5mm, columns: (100%,),
      align(horizon, story-text(theme, rest)),
      block(width: 100%, height: 100%, illustration(theme, img, width: 100%, height: 100%)),
    )
  } else {
    // image-top-text-bottom (기본)
    grid(
      rows: (68%, 1fr), gutter: 5mm, columns: (100%,),
      block(width: 100%, height: 100%, illustration(theme, img, width: 100%, height: 100%)),
      align(top, story-text(theme, rest)),
    )
  }
}

#let render-book(doc) = {
  let theme = doc.theme
  set page(
    ..page-setup(doc.page),
    footer: context if doc.page.page_numbers {
      align(center, text(size: size-of(theme, "footer", 8.5), fill: c(theme, "footer"),
                         str(counter(page).get().first())))
    } else { [] },
  )
  show: body => apply-typography(theme, body)

  let first = true
  for pg in doc.pages {
    if not first { pagebreak() }
    first = false
    render-page(doc, pg)
  }
}
