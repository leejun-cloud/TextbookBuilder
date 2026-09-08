// 초등 3쪽 워크북 템플릿 — 기존 elementary-456-v2 콘텐츠 JSON을 그대로 읽어 조판한다.
// (기존 scripts/elem456_build.py의 HTML 경로와 병행. 원본 콘텐츠는 고치지 않는다.)

#import "/templates/typst/shared/colors.typ": c, tint
#import "/templates/typst/shared/typography.typ": apply-typography, size-of, font-of
#import "/templates/typst/shared/page.typ": page-setup, header-line
#import "/templates/typst/shared/image.typ": get
#import "/templates/typst/shared/components.typ": (
  render-flow, lesson-badge, footer-bar,
)

#let head(doc, pg) = {
  let m = doc.metadata
  let theme = doc.theme
  let extra = if "extra" in m { m.extra } else { (:) }
  let mode = if type(extra) == dictionary and "mode" in extra { extra.mode } else { "" }
  block(width: 100%, below: 3mm, {
    header-line(theme, left-text: m.kicker, right-text: mode)
    v(1mm)
    grid(columns: (auto, 1fr), gutter: 3mm, align: (horizon, horizon),
      lesson-badge(theme, if m.grade != "" { m.grade } else { "초등부" }),
      text(size: size-of(theme, "cover_badge", 9.5), fill: c(theme, "accent"), weight: "bold", m.badge))
    v(1.5mm)
    text(font: font-of(theme, "heading"), size: size-of(theme, "cover_title", 20),
         fill: c(theme, "cover_title"), weight: "bold", m.title)
  })
}

#let render-book(doc) = {
  let theme = doc.theme
  set page(
    ..page-setup(doc.page),
    background: place(top + left, block(width: 100%, height: 4mm, fill: c(theme, "accent"))),
    footer: context {
      let m = doc.metadata
      block(width: 100%, {
        line(length: 100%, stroke: 0.4pt + c(theme, "rule").lighten(45%))
        v(1.2mm)
        grid(columns: (1fr, auto),
          text(size: size-of(theme, "footer", 8.5), fill: c(theme, "footer"), m.footer),
          text(size: size-of(theme, "footer", 8.5), fill: c(theme, "footer"),
               str(counter(page).get().first()) + " / " + str(counter(page).final().first())))
      })
    },
  )
  show: body => apply-typography(theme, body)

  let first = true
  for pg in doc.pages {
    if not first { pagebreak() }
    first = false
    head(doc, pg)
    render-flow(theme, pg.blocks)
  }
}
