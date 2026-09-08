// 카드형 어린이 교재 4쪽 — 참조 지면(3학년 81과) 구조.
//
//   1쪽 시작하고 읽어요   배지·아이콘 제목·손글씨 메모 / 왕관 한 문장 / 생각 열기+필기칸 /
//                        본문(왼쪽) + 큰 삽화(오른쪽) / 오늘의 낱말 칩
//   2쪽 찾고 생각해요     ①키워드 찾기(본문 박스) ②핵심 문장 완성(빈칸) ③말씀에서 찾아요(선택지)
//                        + 오른쪽 곁박스 「한 걸음 더 생각해요」 + 캐릭터 말풍선
//   3쪽 오늘의 활동       ①순서대로 정리(그림 4컷+번호) ②이어 보아요(연결하기) + 함께 생각해요
//   4쪽 정리하고 고백해요 ①한 문장 정리 ②오늘의 기도 ③말씀을 기억해요 ④내가 생각하는 …
//                        + 오늘의 고백 띠
//
// 콘텐츠는 doc가 주고 배치만 여기서 한다. 그림은 자리만 잡아 두고 다른 도구로 채운다.

#import "/templates/typst/shared/colors.typ": c, tint
#import "/templates/typst/shared/typography.typ": apply-typography, size-of, font-of
#import "/templates/typst/shared/page.typ": page-setup
#import "/templates/typst/shared/image.typ": illustration, illustration-with-caption, get
#import "/templates/typst/shared/components.typ": render-block, render-flow, pick, first-of
#import "/templates/typst/shared/card.typ": (
  card-frame, grade-badge, icon-title, crown-box, num-heading, mini-heading, dashed-write,
  soft-box, blank-sentence, choice-line, match-columns, panel-sequence, character-bubble,
  word-chips, corner-page-number, confession-bar, inline-blank,
)

#let A(d, k, fb) = if type(d) == dictionary and k in d { d.at(k) } else { fb }

#let page-top(doc, pg) = {
  let m = doc.metadata
  let theme = doc.theme
  let a = A(pg, "attrs", (:))
  block(width: 100%, below: 1mm, grid(
    columns: (auto, 1fr), gutter: 3.5mm, align: (top, horizon),
    grade-badge(theme, top: m.grade, bottom: if m.lesson_no != none { str(m.lesson_no) + "과" } else { "" }),
    icon-title(theme, pg.title, icon: A(a, "icon", ""), note: A(a, "note", "")),
  ))
}

// ---- 1쪽

#let p-story(doc, pg) = {
  let theme = doc.theme
  let a = A(pg, "attrs", (:))
  let bs = pg.blocks
  page-top(doc, pg)

  let core = first-of(bs, ("callout",))
  if core != none {
    crown-box(theme, get(core, "label", ""), get(core, "text", ""))
  }

  let open-q = first-of(bs, ("question",))
  if open-q != none {
    mini-heading(theme, icon: "💡", title: "생각 열기", hint: get(open-q, "label", ""))
  }
  let texts = pick(bs, ("text",))
  let hero = first-of(bs, ("image",))

  grid(columns: (1fr, 1.05fr), gutter: 4mm, align: (top, top),
    {
      if open-q != none {
        dashed-write(theme, lines: get(open-q, "count", 2), prompt: get(open-q, "text", ""))
      }
      for t in texts {
        block(above: 1.2mm, below: 1.2mm,
          text(size: size-of(theme, "body", 10) * 1.02, get(t, "text", "")))
      }
    },
    if hero != none { illustration(theme, hero, width: 100%, height: 92mm, radius: 4mm) } else { [] })

  let words = first-of(bs, ("keywords",))
  if words != none {
    place(bottom + left, dy: -2mm,
      word-chips(theme, label: get(words, "label", "오늘의 낱말"), items: get(words, "items", ())))
  }
  corner-page-number(theme)
}

// ---- 2쪽

#let p-find(doc, pg) = {
  let theme = doc.theme
  let bs = pg.blocks
  page-top(doc, pg)
  let side = bs.filter(b => get(b, "variant", "") == "side")
  let helper = first-of(bs, ("speech",))
  // 캐릭터 그림은 곁단(말풍선 아래)에서만 쓴다 — 본문 흐름에 또 그리면 쪽이 밀린다
  let character = bs.filter(b => get(b, "kind", "") == "image"
                                 and get(b, "role", "") == "character")
  let main = bs.filter(b => get(b, "variant", "") != "side"
                            and get(b, "kind", "") != "speech"
                            and not (get(b, "kind", "") == "image" and get(b, "role", "") == "character"))

  grid(columns: (1fr, 36mm), gutter: 4mm, align: (top, top),
    {
      let n = 1
      let i = 0
      while i < main.len() {
        let b = main.at(i)
        let k = get(b, "kind", "")
        if k == "keywords" {
          num-heading(theme, n, get(b, "label", "키워드를 찾아 표시해요"),
                      hint: get(b, "ref", ""))
          soft-box(theme, text(size: size-of(theme, "body", 10),
                               get(b, "items", ()).join(linebreak())))
          n += 1
        } else if k == "fill_blank" {
          num-heading(theme, n, get(b, "label", "핵심 문장을 완성해요"), hint: get(b, "ref", ""))
          // parts: 문자열/숫자(빈칸 너비) 배열
          blank-sentence(theme, get(b, "items", (get(b, "text", ""),)).map(x =>
            if type(x) == str and x.starts-with("__") { int(x.slice(2)) } else { x }))
          n += 1
        } else if k == "choice" {
          num-heading(theme, n, get(b, "label", "말씀에서 찾아요"), hint: get(b, "ref", ""))
          let rows = get(b, "rows", ())
          for (j, r) in rows.enumerate() {
            choice-line(theme, j + 1, before: r.at(0, default: ""),
                        options: r.slice(1, calc.max(r.len() - 1, 1)),
                        after: r.at(r.len() - 1, default: ""))
          }
          n += 1
        } else {
          render-block(theme, b)
        }
        i += 1
      }
    },
    {
      if helper != none {
        character-bubble(theme, get(helper, "text", ""),
                         character: if character.len() > 0 { character.at(0) } else { none },
                         width: 36mm)
      }
      for s in side {
        block(width: 100%, radius: 3.5mm, inset: 3mm, above: 2mm,
              fill: tint(c(theme, "accent"), amount: 88%), {
          text(size: size-of(theme, "footer", 8.5), fill: c(theme, "heading"), weight: "bold",
               "📖 " + get(s, "label", "한 걸음 더 생각해요"))
          v(1.2mm)
          text(size: size-of(theme, "quote_attr", 9), get(s, "text", ""))
        })
      }
    })
  corner-page-number(theme)
}

// ---- 3쪽

#let p-activity(doc, pg) = {
  let theme = doc.theme
  let bs = pg.blocks
  page-top(doc, pg)
  let n = 1
  for b in bs {
    let k = get(b, "kind", "")
    if k == "panels" {
      num-heading(theme, n, get(b, "label", "순서대로 정리해요"), hint: get(b, "ref", ""))
      panel-sequence(theme, get(b, "attrs", (:)).at("panels", default: ()), cols: 4)
      n += 1
    } else if k == "match" {
      num-heading(theme, n, get(b, "label", "이어 보아요"), hint: get(b, "ref", ""))
      match-columns(theme, heads: get(b, "head", ()),
                    cols: get(b, "rows", ()))
      n += 1
    } else if k == "speech" {
      block(width: 100%, radius: 3.5mm, inset: 3mm, above: 3mm,
            fill: tint(c(theme, "accent"), amount: 90%),
        grid(columns: (auto, 1fr), gutter: 3mm, align: (horizon, horizon),
          text(size: size-of(theme, "subhead", 11.5), fill: c(theme, "heading"), weight: "bold",
               "✋ " + get(b, "label", "함께 생각해요")),
          text(size: size-of(theme, "body", 10) - 0.5pt, get(b, "text", ""))))
    } else {
      render-block(theme, b)
    }
  }
  corner-page-number(theme)
}

// ---- 4쪽

#let p-close(doc, pg) = {
  let theme = doc.theme
  let bs = pg.blocks
  page-top(doc, pg)
  let n = 1
  let confession = bs.filter(b => get(b, "variant", "") == "confession")
  let main = bs.filter(b => get(b, "variant", "") != "confession")

  let i = 0
  while i < main.len() {
    let b = main.at(i)
    let k = get(b, "kind", "")
    if k == "reflection" {
      num-heading(theme, n, get(b, "label", "한 문장으로 정리해요"), hint: get(b, "text", ""))
      dashed-write(theme, lines: get(b, "count", 2))
      n += 1
      i += 1
    } else if k == "prayer" {
      // 기도 + 암송을 나란히 (참조 지면의 2·3 항목)
      let mem = if i + 1 < main.len() and get(main.at(i + 1), "kind", "") == "memory" {
        main.at(i + 1)
      } else { none }
      grid(columns: (1fr, 1fr), gutter: 4mm, align: (top, top),
        {
          num-heading(theme, n, get(b, "label", "오늘의 기도"), fill: rgb("#F472B6"))
          block(width: 100%, radius: 3.5mm, inset: 3mm, fill: tint(rgb("#F472B6"), amount: 90%), {
            text(size: size-of(theme, "body", 10) - 0.5pt, get(b, "text", ""))
            for l in get(b, "items", ()) {
              v(4.6mm)
              line(length: 100%, stroke: (paint: tint(c(theme, "rule"), amount: 45%),
                                          thickness: 0.3mm, dash: "densely-dotted"))
            }
            v(1.5mm)
            text(size: size-of(theme, "quote_attr", 9), fill: c(theme, "footer"),
                 "예수님의 이름으로 기도합니다. 아멘.")
          })
        },
        if mem != none {
          num-heading(theme, n + 1, get(mem, "label", "말씀을 기억해요"),
                      hint: get(mem, "ref", ""))
          block(width: 100%, radius: 3.5mm, inset: 3mm, fill: tint(c(theme, "accent"), amount: 90%), {
            align(center, text(size: size-of(theme, "subhead", 11.5), weight: "bold",
                               fill: c(theme, "heading"), "“" + get(mem, "text", "") + "”"))
            let im = get(mem, "attrs", (:)).at("image", default: none)
            if im != none { v(1.5mm); illustration(theme, im, width: 100%, height: 20mm, radius: 2mm) }
          })
        } else { [] })
      n += (if mem != none { 2 } else { 1 })
      i += (if mem != none { 2 } else { 1 })
    } else if k == "memory" {
      num-heading(theme, n, get(b, "label", "말씀을 기억해요"), hint: get(b, "ref", ""))
      render-block(theme, b)
      n += 1
      i += 1
    } else {
      render-block(theme, b)
      i += 1
    }
  }
  for cf in confession {
    confession-bar(theme, get(cf, "label", "오늘의 고백"), get(cf, "text", ""))
  }
  corner-page-number(theme)
}

#let LAYOUTS = (
  "kids-story": p-story, "kids-find": p-find,
  "kids-activity": p-activity, "kids-close": p-close,
)

#let render-book(doc) = {
  let theme = doc.theme
  set page(
    ..page-setup(doc.page),
    fill: tint(c(theme, "accent"), amount: 96%),
    background: card-frame(theme),
  )
  show: body => apply-typography(theme, body)

  let first = true
  for pg in doc.pages {
    if not first { pagebreak() }
    first = false
    let fn = if pg.layout in LAYOUTS { LAYOUTS.at(pg.layout) } else { none }
    if fn != none { fn(doc, pg) } else {
      page-top(doc, pg)
      render-flow(theme, pg.blocks)
      corner-page-number(theme)
    }
  }
}
