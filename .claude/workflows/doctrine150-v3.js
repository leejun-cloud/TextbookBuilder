export const meta = {
  name: 'doctrine150-v3',
  description: '고등부 교리공과 버전 2 원고를 버전 3(1과 축약 개정판) 형식으로 배치 전환하고 인용 이월·기계 점검을 교차 검증한다',
  whenToUse: 'doctrine-high-v3 전환 집필을 배치로 실행할 때',
  phases: [
    { title: '전환', detail: '과마다 전환 에이전트 1명 — v2 원고 + spec → v3 draft/teacher-notes. lint·qc ERROR 0까지 스스로 고친다' },
    { title: '검증', detail: '6과 묶음마다 1명 — 인용 이월 대조(verse_carryover) + qc 재확인, 어긋난 인용을 v2 원문으로 되돌린다' },
  ],
}

const V3 = 'projects/doctrine-high-v3'
const V2 = 'projects/doctrine-high-3stage'
const A = typeof args === 'string' ? JSON.parse(args) : (args || {})
const LO = A.lo || 3
const HI = A.hi || 150
const SKIP = new Set(A.skip || [1, 2, 5, 14])

const nums = []
for (let n = LO; n <= HI; n++) if (!SKIP.has(n)) nums.push(n)
const pad = n => String(n).padStart(3, '0')

const WROTE = {
  type: 'object',
  required: ['num', 'ok', 'chars_draft', 'chars_teacher', 'writing_lines', 'notes'],
  properties: {
    num: { type: 'integer' },
    ok: { type: 'boolean', description: 'lint와 qc가 ERROR 0으로 통과했는가' },
    chars_draft: { type: 'integer' },
    chars_teacher: { type: 'integer' },
    writing_lines: { type: 'integer' },
    opening_q: { type: 'string', description: '여는 질문 문구' },
    notes: { type: 'string', description: '판단이 필요했던 곳 2문장 이내' },
  },
}

const CHECK = {
  type: 'object',
  required: ['chunk', 'new_quotes_fixed', 'flagged', 'qc_errors'],
  properties: {
    chunk: { type: 'string' },
    new_quotes_fixed: { type: 'array', items: { type: 'string' }, description: 'v2 원문으로 되돌린 인용 — "N과: 요지"' },
    flagged: { type: 'array', items: { type: 'string' }, description: '사람 확인이 필요한 곳' },
    qc_errors: { type: 'integer', description: '재점검 후 남은 ERROR 수 (0이어야 함)' },
  },
}

const TYPE_NOTE = `**유형 반영법(스타일 규칙 §2와 동일):** 지면 구조는 150과 공통이다. spec의 진행유형은 두 곳에서만 드러난다.
- 서사형 — 여는 질문: 나의 실제 자리를 스스로 진단 / 한 걸음: 물어볼 순간 정하기
- 논쟁형 — 여는 질문: 세상의 주장 하나에 대한 배우기 전의 내 생각을 먼저 적기 (선택지 3개는 서로 다른 실제 입장, 정답 없음. v2의 쟁점·반론에서 가져온다. 반론 대응 내용은 교사면 예상 오답·해설로) / 한 걸음: 그 주장을 만날 자리에서 할 한 마디 준비
- 적용형 — 여는 질문: 지난 한 주를 행동 사실 하나로 진단 (신앙 상태 자가진단 금지) / 한 걸음: spec 「고등부 적용」의 실천 하나와 시점
타임라인·쟁점 두 축 표·진단 표·평가 체크·교사 기록 표는 만들지 않는다.`

const WRITE_PROMPT = n => `너는 전주서문교회 고등부 교리공과 전환 집필자다. 버전 2 원고를 버전 3(1과 축약 개정판) 형식으로 전환한다. 대상: **${n}과**.

## 먼저 읽어라 (순서대로, 전부)
1. \`${V3}/style/style-rules.md\` — 형식의 유일한 기준.
2. \`${V3}/lessons/001/draft.md\` 와 \`${V3}/lessons/001/teacher-notes.md\` — 사용자 승인 기준본. 블록 표시·고정 문구를 눈으로 익힌다.
3. \`${V3}/lessons/002/draft.md\` 와 \`${V3}/lessons/002/teacher-notes.md\` — 승인된 전환 예 (2과부터의 교사면 구조는 이쪽을 따른다).
4. \`${V3}/lessons/${pad(n)}/spec.md\` — 이 과의 원천.
5. \`${V2}/lessons/${pad(n)}/draft.md\` 와 \`${V2}/lessons/${pad(n)}/teacher-notes.md\` — **전환 원본(버전 2).** 내용(성경 인용·확인 해설·예상 오답·기도문·세계관 이슈·적용)은 여기서 가져온다.

## 쓸 파일 두 개
- \`${V3}/lessons/${pad(n)}/draft.md\` — 학생용. 공백 제외 2,529~3,091자
- \`${V3}/lessons/${pad(n)}/teacher-notes.md\` — 교사 안내면. 공백 제외 2,898~3,542자

## 절대 지킬 것
- 전환이다. 성경 인용(낫표 「」)은 버전 2에서 **글자 그대로 복사**한다. 기억으로 다시 쓰지 않고, 새 인용을 추가하지 않는다. v2의 \`<!-- 확인요청: … -->\`은 그대로 가져온다.
- **낫표 「」는 성경과 WSC 인용에만 쓴다.** 세상의 주장·대지 조각·용어 인용은 큰따옴표 \`"…"\`로 쓴다.
- spec의 핵심 문장은 원문 그대로 핵심 교리 문장 박스에(굵게). 주요 대지 ①~④는 교사면 「주요 대지 원문」에 문장 그대로.
- 버전 2의 3단계 ① 세계관 이슈 → 1단계 ① 여는 질문으로 앞당긴다. spec 「고등부 적용」 → 3단계 ② 이번 주 한 걸음.
- ${TYPE_NOTE}
- 버전 2 원고나 spec이 타임라인·쟁점 표·진단 표 등 폐지된 장치(자기 과 것이든 앞 과 것이든)를 참조하면, 그 참조를 새 구조(여는 질문·찾기·KQCI) 언어로 바꾼다.
- 1과 기준본의 고정 문구(도입 한 줄, 찾기 안내 문단, 손들기 줄, KQCI 항목 설명, 함께 나누기 문단, 돌아가기 안내, 기도 뒷문단 꼴, 나의 확인 꼴)는 그대로 재사용하고 과 고유 부분만 바꾼다.
- 필기 줄 총 12줄, 배치는 style-rules §1 고정. \`## \` 절대 금지. 표 앞 \`[[TABLE:...]]\` 필수. \`|---|\` 금지. \`[[NOTE:]]\` 학생 지면 금지.
- ▣유의 과라면 spec 등급 지침을 교리 전달보다 앞세운다. (나) 등급은 「나의 확인」에서 자기 상태 점검 항목을 빼고 수행 여부만 남긴다.

## 끝내기 전에 반드시 통과시켜라
\`\`\`
python3 scripts/lint_lesson.py ${V3}/lessons/${pad(n)}/draft.md ${V3}/lessons/${pad(n)}/teacher-notes.md
python3 scripts/qc_lesson.py ${V3}/lessons --only ${n}
python3 scripts/verse_carryover.py ${V3}/lessons ${V2}/lessons --only ${n}
\`\`\`
셋 다 ERROR/NEW 0이 될 때까지 고친다. WARN도 최대한 없앤다. 분량이 벗어나면 확인 해설·예상 오답을 줄이거나 늘려 맞춘다.

두 파일을 디스크에 쓴 뒤 결과를 보고하라.`

const CHECK_PROMPT = ns => `너는 전환 검증자다. 집필자와 다른 사람이다. 대상 과: ${ns.join(' · ')}

## 할 일 (순서대로)
1. \`python3 scripts/verse_carryover.py ${V3}/lessons ${V2}/lessons --only ${ns.join(',')}\` 를 돌린다.
   NEW로 나온 인용은 규칙 위반이다 — \`${V2}/lessons/NNN/\`의 같은 자리 인용을 찾아 **v2 원문 그대로** 되돌린다.
   v2에 대응 인용이 아예 없으면(전환 중 새로 추가된 인용) 그 인용을 지우거나 장절만 남기고, flagged에 담는다.
2. \`python3 scripts/qc_lesson.py ${V3}/lessons --only ${ns.join(',')}\` 를 돌려 ERROR를 확인한다.
   ERROR가 있으면 그 과의 파일을 열어 고친다 (분량·필기 줄·핵심 문장·대지 원문·표 표시).
3. 과마다 draft.md의 고정 골격을 눈으로 훑는다 — # 1./# 2./# 3. 배너 세 개, 찾기 ①②③에 각각 구절 박스·내 말 한 줄·확인 박스·손들기 줄, KQCI 4칸, 나의 확인 6항목. 빠진 것은 1과 기준본(\`${V3}/lessons/001/draft.md\`) 꼴로 채운다.
4. 고쳤으면 lint(\`python3 scripts/lint_lesson.py ${V3}/lessons/NNN/*.md\`)와 qc를 다시 돌려 ERROR 0을 확인한다.

내용을 다시 쓰지 마라. 성경 인용 복원·기계 점검 통과·골격 보정만 한다.`

phase('전환')
log(`${nums.length}과 전환 — 과마다 전환 1명, 6과 묶음 검증 1명 (건너뜀: ${[...SKIP].join(',')})`)

const CHUNK = 6
const chunks = []
for (let i = 0; i < nums.length; i += CHUNK) chunks.push(nums.slice(i, i + CHUNK))

const done = await pipeline(
  chunks,
  ch => parallel(ch.map(n => () =>
    agent(WRITE_PROMPT(n), { label: `전환 ${n}과`, phase: '전환', schema: WROTE, agentType: 'lesson-writer' }))),
  (ws, ch) => agent(CHECK_PROMPT(ch), {
    label: `검증 ${ch[0]}-${ch[ch.length - 1]}과`, phase: '검증', schema: CHECK,
  }).then(v => ({ chunk: ch, writes: (ws || []).filter(Boolean), check: v })),
)

const good = done.filter(Boolean)
const lessons = good.flatMap(g => g.writes)
log(`전환 완료 ${lessons.length}/${nums.length}과`)

return {
  range: `${LO}-${HI}`,
  converted: lessons.map(w => ({ num: w.num, ok: w.ok, chars: [w.chars_draft, w.chars_teacher], lines: w.writing_lines })),
  not_ok: lessons.filter(w => !w.ok).map(w => `${w.num}: ${w.notes}`),
  checks: good.map(g => ({
    chunk: `${g.chunk[0]}-${g.chunk[g.chunk.length - 1]}`,
    fixed: g.check ? g.check.new_quotes_fixed : [],
    flagged: g.check ? g.check.flagged : [],
    qc_errors: g.check && g.check.qc_errors,
  })),
}
