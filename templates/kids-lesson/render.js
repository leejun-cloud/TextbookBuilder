/*
 * kids-lesson 렌더러 — 읽기 중심 초등부 교재용 (기존 실제 출판 교재 v3.6 형식을 틀로 채택).
 * 섹션 수·이름은 과마다 step.title로 자유롭게 정한다 (도입/성경이야기탐험/성경속이야기/실천/
 * 창조적표현/정리 등).
 *
 * 사용법: print.html에서 kids-print.css → 이 파일 → data.js(window.LESSON) 순서로 로드하고
 * <div id="app"></div>가 있으면 된다. window.LESSON 스키마는 이 파일 끝 주석 참조.
 *
 * 설계 원칙: 활동(스티커·게임)이 아니라 "아이가 읽는 글"이 중심이다.
 * 이야기(story)·발견 설명(discoveries[].explain)은 반드시 채운다 — 빈 채로 두면
 * 아이가 혼자 읽어도 이해할 수 없는 활동지가 된다.
 */
(function () {
  function el(tag, opts) {
    var e = document.createElement(tag);
    opts = opts || {};
    if (opts.cls) e.className = opts.cls;
    if (opts.html !== undefined) e.innerHTML = opts.html;
    if (opts.text !== undefined) e.textContent = opts.text;
    return e;
  }

  function writeLine(n) {
    var frag = document.createDocumentFragment();
    for (var i = 0; i < (n || 1); i++) frag.appendChild(el('div', { cls: 'write-line' }));
    return frag;
  }

  function renderFigure(img, defaultFloat) {
    if (!img) return null;
    var fig = el('figure', { cls: 'framed' + (img.float ? ' float-' + img.float : (defaultFloat ? ' float-' + defaultFloat : '')) });
    if (img.width) fig.style.width = img.width;
    var im = el('img'); im.src = img.src; im.alt = img.alt || img.caption || '';
    fig.appendChild(im);
    if (img.caption) fig.appendChild(el('figcaption', { text: img.caption }));
    return fig;
  }

  function renderStory(story) {
    var box = el('div', { cls: 'story' });
    box.appendChild(el('span', { cls: 'story-label', text: story.label || '이야기' }));
    box.appendChild(el('br'));
    (story.paragraphs || []).forEach(function (p) {
      box.appendChild(el('p', { text: p }));
    });
    if (story.say) box.appendChild(el('p', { cls: 'say', text: story.say }));
    return box;
  }

  function renderVerse(ref, text) {
    var v = el('div', { cls: 'verse' });
    v.appendChild(el('span', { cls: 'ref', text: ref }));
    v.appendChild(document.createTextNode('「' + text + '」'));
    return v;
  }

  function renderDiscovery(d, idx) {
    var box = el('div', { cls: 'discovery' });
    var label = el('div', { cls: 'discovery-label' });
    label.appendChild(el('span', { cls: 'discovery-badge', text: String(idx) }));
    label.appendChild(document.createTextNode(d.title || d.q));
    box.appendChild(label);
    if (d.analogy) box.appendChild(el('p', { html: '<b>그림으로 생각하면</b> ' + d.analogy }));
    if (d.q && d.title) box.appendChild(el('p', { html: '<b>' + d.q + '</b>' }));
    if (d.verseRef) box.appendChild(renderVerse(d.verseRef, d.verse));
    if (d.explain) box.appendChild(el('p', { text: d.explain }));
    return box;
  }

  function renderBibleStory(s) {
    var box = el('div', { cls: 'story' });
    box.appendChild(el('span', { cls: 'story-label', text: s.label || '성경 속 이야기' }));
    if (s.title) { box.appendChild(el('br')); box.appendChild(el('b', { text: s.title })); }
    box.appendChild(el('br'));
    (s.paragraphs || []).forEach(function (p) { box.appendChild(el('p', { text: p })); });
    return box;
  }

  function renderPractice(items) {
    var wrap = el('div');
    items.forEach(function (cat) {
      var row = el('div');
      row.style.cssText = 'margin:2mm 0';
      var tag = el('span', { cls: 'where', text: cat.where });
      row.appendChild(tag);
      var ul = el('ul', { cls: 'repeat-list' });
      (cat.items || []).forEach(function (t) { ul.appendChild(el('li', { text: t })); });
      row.appendChild(ul);
      wrap.appendChild(row);
    });
    return wrap;
  }

  function renderScenarios(scenarios) {
    var ul = el('ul', { cls: 'scenario-list' });
    scenarios.forEach(function (s) {
      var li = el('li');
      var where = el('span', { cls: 'where', text: s.where });
      li.appendChild(where);
      li.appendChild(document.createTextNode(s.when + ' → '));
      li.appendChild(el('span', { cls: 'then', text: s.then }));
      ul.appendChild(li);
    });
    return ul;
  }

  function renderChecklist(items, cls) {
    var ul = el('ul', { cls: cls || 'checklist' });
    items.forEach(function (t) { ul.appendChild(el('li', { text: t })); });
    return ul;
  }

  function renderStep(step) {
    var section = el('section', { cls: 'step' });
    var head = el('div', { cls: 'step-head' });
    head.appendChild(el('span', { cls: 'chip', text: String(step.num) }));
    head.appendChild(document.createTextNode(step.title));
    if (step.minutes) head.appendChild(el('span', { cls: 'step-min', text: step.minutes + '분' }));
    section.appendChild(head);

    if (step.image) section.appendChild(renderFigure(step.image, 'right'));
    if (step.goal) section.appendChild(el('div', { cls: 'goal', html: '<b style="white-space:nowrap">오늘 이 시간에</b> ' + step.goal }));

    if (step.story) section.appendChild(renderStory(step.story));

    if (step.think && step.think.length) {
      var p = el('p');
      p.innerHTML = step.think.join('<br>');
      section.appendChild(p);
    }

    if (step.intro) section.appendChild(el('p', { html: '<b>' + step.intro + '</b>' }));

    if (step.discoveries) {
      step.discoveries.forEach(function (d, i) {
        section.appendChild(renderDiscovery(d, i + 1));
        if (d.answerLabel) section.appendChild(el('p', { cls: 'answer-label', text: d.answerLabel }));
        if (d.writeLines) section.appendChild(writeLine(d.writeLines));
      });
    }

    if (step.bigPicture) {
      section.appendChild(el('div', { cls: 'note', html: '<span class="box-label">생각해보기</span><br>' + step.bigPicture }));
    }

    if (step.blank) {
      var blankBox = el('div', { cls: 'box' });
      blankBox.appendChild(el('span', { cls: 'box-label', text: '빈칸 채우기' }));
      blankBox.appendChild(el('br'));
      blankBox.appendChild(document.createTextNode(step.blank.before + ' '));
      var span = el('span'); span.style.cssText = 'display:inline-block;width:70px;border-bottom:2.5px solid var(--teal)';
      blankBox.appendChild(span);
      blankBox.appendChild(document.createTextNode(' ' + step.blank.after));
      section.appendChild(blankBox);
    }

    if (step.mission) {
      section.appendChild(el('div', {
        cls: 'note',
        html: '<span class="box-label">' + (step.mission.label || '미션') + '</span><br>' + step.mission.text
      }));
    }

    if (step.scenarios) {
      if (step.pickNote) section.appendChild(el('p', { text: step.pickNote }));
      section.appendChild(renderScenarios(step.scenarios));
    }

    if (step.bibleStory) section.appendChild(renderBibleStory(step.bibleStory));

    if (step.practice) section.appendChild(renderPractice(step.practice));

    if (step.creativeActivity) {
      section.appendChild(el('div', {
        cls: 'note',
        html: '<span class="box-label">' + (step.creativeActivity.label || '창조적으로 표현하기') + '</span><br>' + step.creativeActivity.text
      }));
    }

    if (step.options) {
      var optBox = el('div', {
        cls: 'note',
        html: '<span class="box-label">' + (step.optionsLabel || '하나를 골라요') + '</span>'
      });
      optBox.appendChild(renderChecklist(step.options));
      section.appendChild(optBox);
    }

    if (step.answerLabel) section.appendChild(el('p', { cls: 'answer-label', text: step.answerLabel }));
    if (step.writeLines) section.appendChild(writeLine(step.writeLines));

    return section;
  }

  function renderField(label, valueHtml) {
    var box = el('div', { cls: 'field' });
    box.appendChild(el('span', { cls: 'field-label', text: label }));
    var span = el('span', { html: valueHtml });
    box.appendChild(span);
    return box;
  }

  function renderTeacherPage(t) {
    var page = el('div', { cls: 'teacher-page' });
    var header = el('div', { cls: 'lesson-header' });
    header.appendChild(el('div', { cls: 'lesson-num', html: (t.num || '') + '<small>과</small>' }));
    header.appendChild(el('div', { cls: 'lesson-title', text: '교사 안내 · ' + (t.title || '') }));
    page.appendChild(header);
    page.appendChild(el('p', { cls: 'delete-note', text: '학생 배부본에서는 이 면을 삭제합니다.' }));

    if (t.goal) page.appendChild(renderField('이 과의 목표', t.goal));

    if (t.materials || (t.prep && t.prep.length)) {
      var prepBox = el('div', { cls: 'field' });
      prepBox.appendChild(el('span', { cls: 'field-label', text: '준비물과 수업 전 준비' }));
      if (t.materials) prepBox.appendChild(el('p', { html: '<b>준비물</b> ' + t.materials }));
      if (t.prep && t.prep.length) {
        var ul = el('ul', { cls: 'plain' });
        t.prep.forEach(function (p) { ul.appendChild(el('li', { text: p })); });
        prepBox.appendChild(ul);
      }
      page.appendChild(prepBox);
    }

    if (t.rules && t.rules.length) {
      var rulesBox = el('div', { cls: 'field' });
      rulesBox.appendChild(el('span', { cls: 'field-label', text: '이 과에서 지킬 것' }));
      var ol = el('ol', { cls: 'plain' });
      t.rules.forEach(function (r) { ol.appendChild(el('li', { text: r })); });
      rulesBox.appendChild(ol);
      page.appendChild(rulesBox);
    }

    if (t.notes) {
      var notesBox = el('div', { cls: 'field' });
      notesBox.appendChild(el('span', { cls: 'field-label', text: '교사 메모' }));
      var rows = [
        ['빈칸 정답', t.notes.blankAnswer],
        ['흔한 오해', t.notes.misconception],
        ['바꿔 말할 낱말', t.notes.rewordings],
        ['신앙고백 (교사용)', t.notes.confession],
        ['중등부 연결', t.notes.nextLevel]
      ];
      rows.forEach(function (r) {
        if (!r[1]) return;
        notesBox.appendChild(el('p', { html: '<b>' + r[0] + '</b> ' + r[1] }));
      });
      page.appendChild(notesBox);
      if (t.notes.caveat) page.appendChild(el('p', { cls: 'answer-label', text: t.notes.caveat }));
    }

    if (t.record) {
      var recBox = el('div', { cls: 'field' });
      recBox.appendChild(el('span', { cls: 'field-label', text: '수업 기록 (교사용)' }));
      var table = el('table', { cls: 'record-table' });
      var thead = el('tr');
      (t.record.columns || []).forEach(function (c) { thead.appendChild(el('th', { text: c })); });
      table.appendChild(thead);
      for (var i = 0; i < (t.record.rows || 3); i++) {
        var tr = el('tr');
        (t.record.columns || []).forEach(function () { tr.appendChild(el('td', { html: '&nbsp;' })); });
        table.appendChild(tr);
      }
      recBox.appendChild(table);
      page.appendChild(recBox);
    }

    if (t.footer) page.appendChild(el('div', { cls: 'page-footer', text: t.footer }));
    return page;
  }

  function render(data) {
    var app = document.getElementById('app');
    if (!app) return;

    var header = el('div', { cls: 'lesson-header' });
    header.appendChild(el('div', { cls: 'lesson-num', html: data.num + '<small>과</small>' }));
    header.appendChild(el('div', { cls: 'lesson-title', text: data.title }));
    app.appendChild(header);

    if (data.tagline || data.meta) {
      app.appendChild(el('p', { cls: 'lesson-tagline', text: [data.tagline, data.meta].filter(Boolean).join(' | ') }));
    }

    if (data.goal) {
      app.appendChild(el('div', { cls: 'goal', html: '<b style="white-space:nowrap">학습 목표</b> ' + data.goal }));
    }

    var lead = el('div', { cls: 'lead' });
    var leadText = el('div', { cls: 'lead-text' });
    var hero = el('div', { cls: 'hero' });
    hero.appendChild(el('span', { cls: 'hero-label', text: '오늘의 한 문장' }));
    hero.appendChild(el('div', { cls: 'hero-sentence', html: data.hero.replace(/\n/g, '<br>') }));
    leadText.appendChild(hero);
    if (data.centralText) {
      leadText.appendChild(el('p', { html: '<b>중심 본문</b> ' + data.centralText }));
    }
    if (data.heroVerseRef) {
      var vbox = renderVerse(data.heroVerseRef, data.heroVerse);
      if (data.heroNote) {
        vbox.appendChild(el('br'));
        var noteSpan = el('span', { text: data.heroNote });
        noteSpan.style.cssText = 'font-size:8.5pt;color:var(--sub)';
        vbox.appendChild(noteSpan);
      }
      leadText.appendChild(vbox);
    }
    if (data.heroBlank) {
      var blankBox = el('div', { cls: 'box' });
      blankBox.appendChild(el('span', { cls: 'box-label', text: '빈칸 채우기' }));
      blankBox.appendChild(el('br'));
      blankBox.appendChild(document.createTextNode(data.heroBlank.before + ' '));
      var blankLine = el('span'); blankLine.style.cssText = 'display:inline-block;width:60px;border-bottom:2.5px solid var(--teal)';
      blankBox.appendChild(blankLine);
      blankBox.appendChild(document.createTextNode(' ' + data.heroBlank.after));
      leadText.appendChild(blankBox);
    }
    lead.appendChild(leadText);

    if (data.leadImage) {
      var leadArt = el('div', { cls: 'lead-art' });
      leadArt.appendChild(renderFigure(data.leadImage));
      if (data.leadImage.bubble) {
        var wrap = el('div'); wrap.style.textAlign = 'center';
        wrap.appendChild(el('span', { cls: 'bubble', text: data.leadImage.bubble }));
        leadArt.appendChild(wrap);
      }
      lead.appendChild(leadArt);
    }
    app.appendChild(lead);

    (data.steps || []).forEach(function (step) { app.appendChild(renderStep(step)); });

    if (data.verseRecap) {
      var recap = el('div', { cls: 'verse' });
      recap.style.textAlign = 'center'; recap.style.fontWeight = '700';
      recap.appendChild(el('span', { cls: 'ref', text: '오늘의 암송 · ' + data.verseRecap.ref }));
      recap.appendChild(el('br'));
      recap.appendChild(document.createTextNode('「' + data.verseRecap.text + '」'));
      app.appendChild(recap);
    }

    if (data.prayer) {
      var prayerBox = el('div', { cls: 'prayer' });
      prayerBox.appendChild(el('span', { cls: 'prayer-label', text: '마음을 담은 기도' }));
      prayerBox.appendChild(el('br'));
      prayerBox.appendChild(document.createTextNode(data.prayer.text));
      if (data.prayer.blank) {
        prayerBox.appendChild(el('br')); prayerBox.appendChild(el('br'));
        prayerBox.appendChild(document.createTextNode(data.prayer.blank));
      }
      if (data.prayer.closing) {
        prayerBox.appendChild(el('br')); prayerBox.appendChild(el('br'));
        prayerBox.appendChild(document.createTextNode(data.prayer.closing));
      }
      app.appendChild(prayerBox);
    }

    if (data.summary) {
      app.appendChild(el('div', {
        cls: 'summary',
        html: '<span class="summary-label">한 줄 정리</span>' + data.summary
      }));
    }

    if (data.checklist) {
      var checkBox = el('div', { cls: 'box' });
      checkBox.appendChild(el('span', { cls: 'box-label', text: '나의 확인' }));
      checkBox.appendChild(renderChecklist(data.checklist));
      app.appendChild(checkBox);
    }

    if (data.footer) app.appendChild(el('div', { cls: 'page-footer', text: data.footer }));

    if (data.teacher) {
      var teacherData = Object.assign({ num: data.num, title: data.title, footer: data.footer }, data.teacher);
      app.appendChild(renderTeacherPage(teacherData));
    }

    if (document.title !== undefined && data.title) {
      document.title = data.num + '과 ' + data.title + ' · 초등부';
    }
  }

  render(window.LESSON);
})();

/*
 * ── window.LESSON 스키마 ──────────────────────────────────────
 * {
 *   num, title, tagline, meta, goal,
 *   hero, heroVerseRef, heroVerse, heroNote,
 *   leadImage: {src, caption, bubble, width?, float?},
 *   steps: [{
 *     num, title, minutes,
 *     image?: {src, caption, width?, float?},
 *     goal?,                          // 이 단계에서 확인할 것 한 줄
 *     story?: {label?, paragraphs:[...], say?},   // 1단계용 읽는 이야기
 *     think?: [...],                  // 이야기 뒤 생각할 질문 (문장 배열)
 *     intro?,                         // 굵게 강조되는 안내 한 줄
 *     discoveries?: [{title, analogy?, verseRef, verse, explain, writeLines?}],  // 발견 카드
 *     bigPicture?,                    // 그리스도 중심 질문 한 줄
 *     bibleStory?: {label?, title?, paragraphs:[...]},  // 성경 속 하나님 나라 이야기
 *     blank?: {before, after},        // 빈칸 (한 과에 하나만)
 *     mission?: {label?, text},
 *     scenarios?: [{where, when, then}],  // 구체 상황 카드 (한 줄형)
 *     practice?: [{where, items:[...]}],  // 실천해요 (가정/학교/개인적으로 각각 여러 줄)
 *     creativeActivity?: {label?, text},  // 창조적으로 표현하기
 *     pickNote?, options?: [...], optionsLabel?,  // 선택지
 *     writeLines?: N
 *   }],
 *   verseRecap?: {ref, text},
 *   prayer?: {text, blank?, closing?},
 *   summary?,
 *   checklist?: [...],
 *   footer?,
 *   teacher?: {                     // 있으면 학생 지면 뒤에 교사 안내면(새 페이지)을 덧붙인다
 *     goal,                         // 이 과의 목표 (한 문장, 측정 가능하게)
 *     materials, prep: [...],       // 준비물과 수업 전 준비
 *     rules: [...],                 // 이 과에서 지킬 것
 *     notes: { blankAnswer, misconception, rewordings, confession, nextLevel, caveat? },
 *     record: { columns:[...], rows?: N },  // 수업 기록표 (기본 3행)
 *     footer?                       // 없으면 data.footer 재사용
 *   }
 * }
 * ──────────────────────────────────────────────────────────
 */
