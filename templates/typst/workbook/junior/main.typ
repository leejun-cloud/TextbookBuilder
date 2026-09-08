// 유년부 4쪽 교재 템플릿 (저학년 · 요청서 §7)
//
//   1쪽 시작하고 읽어요   배지·제목·이야기·생각열기·삽화·오늘의 낱말
//   2쪽 찾고 생각해요     키워드·핵심문장·말씀에서 찾아요·한 걸음 더
//   3쪽 오늘의 활동       활동(준비물+단계)·삽화·빈칸
//   4쪽 정리하고 고백해요 한 문장 정리·기도·암송·나의 생각·오늘의 고백
//
// 저학년이므로 글자를 키우고 여백을 넉넉히 준다. 콘텐츠는 doc가 주고, 배치만 여기서 한다.

#import "/templates/typst/shared/colors.typ": c, tint
#import "/templates/typst/shared/typography.typ": apply-typography, size-of, font-of, spacing-of
#import "/templates/typst/shared/page.typ": page-setup, header-line, footer-line
#import "/templates/typst/shared/image.typ": illustration, illustration-with-caption, get
#import "/templates/typst/shared/components.typ": (
  lesson-badge, page-title, sub-title, render-block, render-flow, pick, drop, first-of,
  keyword-box, callout-box, story-box, activity-box, fill-blank, memory-verse, prayer-box,
  reflection-box, question-box, speech-bubble, character-tip, step-image, footer-bar, page-number,
)

#let page-header(doc, page-title-text) = {
  let m = doc.metadata
  let theme = doc.theme
  block(width: 100%, below: 3mm, {
    header-line(theme,
      left-text: if m.kicker != "" { m.kicker } else { "다음세대 교리교육" },
      right-text: page-title-text)
    v(1mm)
    grid(columns: (auto, 1fr), gutter: 3mm, align: (horizon, horizon),
      lesson-badge(theme, if m.grade != "" { m.grade } else { "유년부" }),
      text(size: size-of(theme, "cover_badge", 9.5), fill: c(theme, "accent"), weight: "bold", m.badge))
    v(1.5mm)
    text(font: font-of(theme, "heading"), size: size-of(theme, "cover_title", 20),
         fill: c(theme, "cover_title"), weight: "bold", m.title)
  })
}

// ---- 쪽별 레이아웃

#let page-story(doc, pg) = {
  let theme = doc.theme
  let blocks = pg.blocks
  let hero = first-of(blocks, ("image",))
  let story-title = first-of(pick(blocks, ("heading",)), ("heading",))
  let opening = first-of(blocks, ("question",))
  let texts = pick(blocks, ("text",))
  let words = first-of(blocks, ("keywords",))

  page-header(doc, pg.title)
  if story-title != none { sub-title(theme, get(story-title, "text", "")) }
  if opening != none {
    callout-box(theme, text(weight: "bold", get(opening, "text", "")),
                label: get(opening, "label", "생각열기"), variant: "note")
  }
  if texts.len() > 0 { story-box(theme, texts.map(t => get(t, "text", "")), big: true) }
  if hero != none { illustration-with-caption(theme, hero, width: 100%, height: 58mm, radius: 3mm) }
  if words != none {
    keyword-box(theme, get(words, "items", ()), label: get(words, "label", "오늘의 낱말"),
                cols: if get(words, "items", ()).len() > 2 { 2 } else { 1 })
  }
}

#let page-find(doc, pg) = {
  let theme = doc.theme
  let blocks = pg.blocks
  let kws = first-of(blocks, ("keywords",))
  let core = first-of(blocks, ("callout",))
  let qs = pick(blocks, ("question",))
  let img = first-of(blocks, ("image",))

  page-header(doc, pg.title)
  if kws != none {
    keyword-box(theme, get(kws, "items", ()), label: get(kws, "label", "키워드 찾기"),
                cols: if get(kws, "items", ()).len() > 2 { 2 } else { 1 })
  }
  if core != none {
    callout-box(theme, get(core, "text", ""), label: get(core, "label", "핵심 문장"), variant: "core")
  }
  let cur = ""
  for q in qs {
    let lab = get(q, "label", "")
    if lab != cur {
      sub-title(theme, if lab == "" { "생각해 보아요" } else { lab })
      cur = lab
    }
    question-box(theme, get(q, "text", ""), label: "", lines: get(q, "count", 1), ref: get(q, "ref", ""))
  }
  if img != none {
    illustration-with-caption(theme, img, width: 100%, height: 40mm, radius: 3mm)
  }
}

#let page-activity(doc, pg) = {
  let theme = doc.theme
  let blocks = pg.blocks
  page-header(doc, pg.title)
  let n = 1
  for b in blocks {
    let k = get(b, "kind", "")
    if k == "activity" {
      render-block(theme, b)
    } else if k == "image" {
      step-image(theme, b, n: n)
      n += 1
    } else {
      render-block(theme, b)
    }
  }
}

#let page-close(doc, pg) = {
  let theme = doc.theme
  let blocks = pg.blocks
  page-header(doc, pg.title)
  for b in blocks {
    let k = get(b, "kind", "")
    let v = get(b, "variant", "")
    if k == "image" {
      // 마무리 쪽 장식 이미지는 작게, 가운데
      align(center, illustration(theme, b, width: 45%, height: 22mm, radius: 2mm))
    } else if k == "callout" and v == "confession" {
      // 오늘의 고백은 말풍선으로 (아이가 소리 내어 말하는 자리)
      speech-bubble(theme, text(size: size-of(theme, "subhead", 11.5), weight: "bold",
                                get(b, "text", "")),
                    speaker: get(b, "label", "오늘의 고백"))
    } else {
      render-block(theme, b)
    }
  }
}

#let LAYOUTS = (
  "kids-story": page-story,
  "kids-find": page-find,
  "kids-activity": page-activity,
  "kids-close": page-close,
)

// ---- 진입점

#let render-book(doc) = {
  let theme = doc.theme
  set page(
    ..page-setup(doc.page),
    footer: context {
      let m = doc.metadata
      let s = if m.footer != "" { m.footer } else { m.title }
      block(width: 100%, {
        line(length: 100%, stroke: 0.4pt + c(theme, "rule").lighten(45%))
        v(1.2mm)
        grid(columns: (1fr, auto),
          text(size: size-of(theme, "footer", 8.5), fill: c(theme, "footer"), s),
          if doc.page.page_numbers {
            text(size: size-of(theme, "footer", 8.5), fill: c(theme, "footer"),
                 str(counter(page).get().first()) + " / " + str(counter(page).final().first()))
          } else { [] })
      })
    },
  )
  show: body => apply-typography(theme, body)

  // 상단 색 띠
  set page(background: place(top + left, block(width: 100%, height: 4mm, fill: c(theme, "accent"))))

  let first = true
  for pg in doc.pages {
    if not first { pagebreak() }
    first = false
    let fn = if pg.layout in LAYOUTS { LAYOUTS.at(pg.layout) } else { none }
    if fn != none {
      fn(doc, pg)
    } else {
      // 모르는 레이아웃은 흐름으로 그린다(죽지 않는다)
      page-header(doc, pg.title)
      render-flow(theme, pg.blocks, big-text: true)
    }
  }
}
