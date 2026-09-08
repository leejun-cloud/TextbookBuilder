// 일반 단행본 템플릿 — 표지 + 흐름 조판. 레거시 블록 스킴 md의 회귀 비교용 기준이기도 하다.

#import "/templates/typst/shared/colors.typ": c
#import "/templates/typst/shared/typography.typ": apply-typography, size-of, font-of
#import "/templates/typst/shared/page.typ": page-setup
#import "/templates/typst/shared/components.typ": render-flow, page-title, lesson-badge

#let cover(doc) = {
  let m = doc.metadata
  let theme = doc.theme
  // 밝은 제목색을 쓰는 테마(레거시 docx가 색 배경 표지를 쓰던 프로필)는 색 패널을 깐다.
  let panel = if "flags" in theme and "cover_panel" in theme.flags { theme.flags.cover_panel } else { false }
  let inner = block(width: 100%, {
    if m.kicker != "" {
      text(size: size-of(theme, "cover_kicker", 9),
           fill: if panel { c(theme, "banner_text") } else { c(theme, "cover_kicker") }, m.kicker)
      v(3mm)
    }
    text(font: font-of(theme, "heading"), size: size-of(theme, "cover_title", 20) * 1.4,
         fill: c(theme, "cover_title"), weight: "bold", m.title)
    if m.subtitle != "" {
      v(4mm)
      text(size: size-of(theme, "cover_sub", 10) * 1.2, fill: c(theme, "cover_sub"), m.subtitle)
    }
  })
  if panel {
    block(width: 100%, fill: c(theme, "heading"), inset: (x: 10mm, y: 18mm), radius: 0pt, inner)
    if m.badge != "" { v(8mm); lesson-badge(theme, m.badge) }
  } else {
    align(left + horizon, block(width: 100%, {
      inner
      if m.badge != "" { v(8mm); lesson-badge(theme, m.badge) }
    }))
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
  show: body => apply-typography(theme, justify: true, body)

  if doc.metadata.title != "" {
    cover(doc)
    pagebreak()
  }
  let first = true
  for pg in doc.pages {
    if not first { pagebreak() }
    first = false
    if pg.title != "" { page-title(theme, pg.title) }
    render-flow(theme, pg.blocks)
  }
}
