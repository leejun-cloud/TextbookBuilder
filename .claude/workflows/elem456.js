export const meta = {
  name: 'elem456',
  description: '초등부 4·5·6학년 120과 콘텐츠(JSON)를 배치 집필하고 학년별로 교리·인용을 교차 검수한다',
  whenToUse: 'projects/elementary-456-v2 콘텐츠 배치 집필 때',
  phases: [
    { title: '집필', detail: '4과 묶음마다 집필 에이전트 1명 — content JSON 작성, qc ERROR 0까지 스스로 고친다' },
    { title: '학년 검수', detail: '학년마다 1명 — 읽기 본문의 교리 정확성·오해 교정·수준·중복을 검수하고 직접 고친다' },
  ],
}

const ROOT = 'projects/elementary-456-v2'
const A = typeof args === 'string' ? JSON.parse(args) : (args || {})
const PLAN = A.plan || { 4: [3, 40], 5: [2, 40], 6: [2, 40] }  // 학년: [시작, 끝] (fixture 제외)
const pad = n => String(n).padStart(3, '0')

const WROTE = {
  type: 'object',
  required: ['grade', 'nums', 'ok', 'notes'],
  properties: {
    grade: { type: 'integer' },
    nums: { type: 'array', items: { type: 'integer' } },
    ok: { type: 'boolean', description: 'qc가 ERROR 0으로 통과했는가' },
    verse_todo: { type: 'array', items: { type: 'string' }, description: '확인구절을 찾지 못해 미확정으로 남긴 곳' },
    notes: { type: 'string', description: '판단이 필요했던 곳 2문장 이내' },
  },
}

const REVIEWED = {
  type: 'object',
  required: ['grade', 'fixed', 'flagged'],
  properties: {
    grade: { type: 'integer' },
    fixed: { type: 'array', items: { type: 'string' }, description: '고친 것 — "N과: 요지"' },
    flagged: { type: 'array', items: { type: 'string' }, description: '사람 확인 필요 — 교리적으로 애매한 곳' },
  },
}

const WRITE_PROMPT = (g, ns) => `너는 전주서문교회 초등부 교리교재 집필자다. ${g}학년 ${ns.join('·')}과의 콘텐츠 JSON을 쓴다.
작업 디렉터리: /Users/ichangjun/Documents/GitHub/test/TextbookBuilder

## 먼저 읽어라 (순서대로, 전부)
1. \`${ROOT}/project.md\` — 특수 지침 6개가 최우선이다.
2. \`${ROOT}/content/SCHEMA.md\` — 출력 스키마와 고정 문구, 학년별 사고활동 유형.
3. 기준본(fixture) — \`${ROOT}/content/g4/001.json\` 과 \`${ROOT}/content/g${g}/001.json\`. 읽기 본문의 문체·전개·분량 감을 여기서 익힌다.
4. 이 과들의 원천: \`python3 scripts/elem456_spec.py --grade ${g} ${ns.map(n => `--no ${n}`).join(' ')}\`

## 쓸 파일
${ns.map(n => `- \`${ROOT}/content/g${g}/${pad(n)}.json\``).join('\n')}

## 규칙
- **원천 그대로**: title(물음표 추가만 허용)·core·center·blank·질문 라벨 2개·암송(memory_ref+memory_text)·common_no·required_memory·unit. 원천 미션·결단·이어가기는 뜻을 바꾸지 않고 학생에게 말하는 꼴(~보세요)로만 다듬는다.
- **확인구절(q[].verse)은 절대 지어내지 않는다.** 다음 순서로 찾는다:
  1) 같은 공통 과의 고등부 원고: \`grep -h "「" projects/doctrine-high-3stage/lessons/<공통번호 3자리>/draft.md projects/doctrine-high-3stage/lessons/<공통번호 3자리>/teacher-notes.md\`
  2) 저장소 전체에서 장절로 검색: \`grep -rn "<장절>" projects/doctrine-high-3stage projects/doctrine-mid-150 projects/wsc-youth-catechism | grep 「\`
  찾은 낫표 인용에서 **필요한 구절 부분을 글자 그대로** 잘라 쓴다(중간 생략은 \` … \`). 어디에서도 못 찾으면 \`"verse": ""\` + \`"verse_todo": true\`로 남긴다. 기억으로 쓰는 것은 금지다.
- 질문에 장절이 없는 **사실 확인 질문**(예: "성경은 몇 권인가요?")은 \`"ref": ""\` + 사실 답 문장을 verse에 + \`"verse_is_fact": true\`.
- **읽기(reading)**: ${g}학년 ${g === 4 ? '2문단 300–430자' : g === 5 ? '2문단 420–560자' : '3문단 540–720자'}(공백 포함). 학생이 확인구절에서 본 낱말에서 출발해 교리를 풀고, 원천 교사 메모의 「흔한 오해」를 본문 안에서 자연스럽게 교정하고 「바꿔 말할 낱말」을 지킨다. 어투 ~예요/~해요. 새 성경 인용 추가 금지. 기준본 4편(1과들)과 도입 문장·비유가 겹치지 않게 그 과 고유의 자리에서 시작한다.
- **사고활동**: ${g === 4 ? '4학년 관계 잇기 — 본문에서 찾은 말(그 과 확인구절의 실제 낱말 2~3개) / 이어지는 뜻 / 내 하루, 한 문장 ×1' : g === 5 ? '5학년 두 본문 묶기 — 1열·2열은 두 확인구절 요약(2~4어), 3열은 오늘의 한 문장을 빈칸 2개로 만든 묶기 문장, 내 문장 ×1' : '6학년 주장-근거-이유 — 1열은 그 과 교리에 반대되는 세상의 주장 한 문장, 2열은 두 확인구절 장절, 3열 "이 주장이 맞는지 판단해요.", 나의 답과 이유 ×2'}.
- **유의 과**(원천에 표시가 있으면): sensitivity에 원천 문구를 담고, 학생 지면 문구(미션 라벨·이어가기)를 그 배려에 맞게 바꾼다(예: "나만 보는 기록", "발표하거나 제출하지 않아요"). 아픈 장면·지옥 묘사를 자세히 쓰지 않는다.
- decision_cols는 결단 내용에 맞게 2~3열(기본 언제/어디서, 필요시 어떻게·몇 절부터 등).

## 끝내기 전에 반드시
\`\`\`
python3 scripts/elem456_qc.py --grade ${g} --only ${ns.join(',')}
\`\`\`
ERROR 0이 될 때까지 고친다. 인용미확정(VERSE)은 정말 못 찾은 경우에만 남긴다.

보고: 과별 읽기 자수 · verse_todo 목록 · 판단 필요했던 곳 2문장.`

const REVIEW_PROMPT = g => `너는 개혁주의 교리 검수자다. 집필자와 다른 사람이다. ${g}학년 40과의 콘텐츠를 검수한다.
작업 디렉터리: /Users/ichangjun/Documents/GitHub/test/TextbookBuilder

## 대상
\`${ROOT}/content/g${g}/\`의 모든 JSON (001은 사용자 승인 기준본 — **읽고 기준으로만 삼고 수정 금지**${g === 4 ? ', 002도 승인본이라 수정 금지' : ''}).

## 볼 것 (reading·reading_title·think_row·share_text 중심)
1. **교리 정확성** — 개혁주의 표준(WSC·하이델베르크)과 어긋나는 표현, 과장·오해 소지(예: 번영신학 뉘앙스, 신인혼합, 행위구원 뉘앙스, "착한 일 하면 복 받아요"류). 원천 교사 메모의 「흔한 오해」가 본문에서 실제로 교정되는지.
2. **학년 수준** — ${g}학년이 모르는 추상어를 풀지 않고 쓴 곳. 「바꿔 말할 낱말」 위반.
3. **중복** — 과들 사이 도입 문장·비유·마무리 문장이 겹치는 곳. \`python3 scripts/elem456_qc.py --grade ${g}\`의 DUP도 확인.
4. **어투** — ~예요/~해요 일관, 학생을 채점·정죄하는 문장 금지.

## 할 일
문제를 **직접 고친다** (Edit). 단: 원천 고정 필드(core·blank·질문 라벨·암송·center)와 q[].verse(성경 인용)는 건드리지 않는다 — 인용이 의심되면 고치지 말고 flagged에 담는다. 고친 뒤 \`python3 scripts/elem456_qc.py --grade ${g}\` ERROR 0 확인.`

phase('집필')
const jobs = []
for (const [gs, range] of Object.entries(PLAN)) {
  const g = Number(gs)
  const [lo, hi] = range
  const nums = []
  for (let n = lo; n <= hi; n++) nums.push(n)
  for (let i = 0; i < nums.length; i += 4) jobs.push({ g, ns: nums.slice(i, i + 4) })
}
log(`집필 ${jobs.length}묶음 (4과/명) — 이후 학년별 교리 검수 3명`)

const wrote = await parallel(jobs.map(j => () =>
  agent(WRITE_PROMPT(j.g, j.ns), { label: `집필 g${j.g} ${j.ns[0]}-${j.ns[j.ns.length - 1]}`, phase: '집필', schema: WROTE })))

const okJobs = wrote.filter(Boolean)
log(`집필 완료 ${okJobs.length}/${jobs.length}묶음 — 학년 검수 시작`)

let reviews = []
if (A.review !== false) {
  phase('학년 검수')
  reviews = await parallel([4, 5, 6].map(g => () =>
    agent(REVIEW_PROMPT(g), { label: `검수 ${g}학년`, phase: '학년 검수', schema: REVIEWED })))
}

return {
  written: okJobs.map(w => ({ g: w.grade, nums: w.nums, ok: w.ok, verse_todo: w.verse_todo || [] })),
  verse_todo: okJobs.flatMap(w => (w.verse_todo || []).map(v => `g${w.grade}: ${v}`)),
  reviews: reviews.filter(Boolean),
}
