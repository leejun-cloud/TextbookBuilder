/**
 * TextBuilder 정규화 문서 모델 — TypeScript 타입.
 *
 * 파이썬 구현: textbuilder/model.py (판별 유니온을 하나의 Block dataclass로 구현)
 * 여기서는 kind별 인터페이스로 좁혀 두어, 에디터/툴이 필드를 정확히 알 수 있게 한다.
 *
 * 원칙: 이 모델에는 **Typst 문법도, docx 서식도, HTML도 들어오지 않는다.** 의미만 담는다.
 */

export type BlockKind =
  | 'heading' | 'text' | 'image' | 'verse' | 'question' | 'activity' | 'callout'
  | 'table' | 'fill_blank' | 'writing' | 'checklist' | 'memory' | 'prayer'
  | 'reflection' | 'speech' | 'keywords' | 'spacer';

/** 이미지 역할 — 템플릿이 배치 규칙을 고르는 근거 (요청서 §8) */
export type ImageRole =
  | 'hero' | 'illustration' | 'character' | 'step' | 'background' | 'decoration' | 'cover';

export type ImageFit = 'contain' | 'cover' | 'fill';

export interface BlockBase {
  kind: BlockKind;
  /** 템플릿이 아는 변형 이름. 모르면 무시한다 (예: 'story', 'note', 'core', 'banner') */
  variant?: string;
  /** 템플릿이 모르는 부가 속성은 여기로 */
  attrs?: Record<string, unknown>;
}

export interface HeadingBlock extends BlockBase {
  kind: 'heading';
  text: string;
  /** 1 = 페이지 제목, 2 = 섹션(배너), 3 = 소항목 */
  level?: 1 | 2 | 3;
  /** 섹션 번호 등 */
  label?: string;
}

export interface TextBlock extends BlockBase {
  kind: 'text';
  text: string;
}

export interface ImageBlock extends BlockBase {
  kind: 'image';
  /** 문서 기준 상대경로. 렌더 시 --root 기준 절대경로로 해결된다 */
  src: string;
  role?: ImageRole;
  fit?: ImageFit;
  /** 캡션(=text로도 받음) */
  text?: string;
  attrs?: {
    role?: ImageRole;
    fit?: ImageFit;
    alt?: string;
    caption?: string;
    /** 재단선까지 넘겨 그리기 */
    bleed?: boolean;
    /** [x, y, w, h] 비율(0~1) */
    crop?: [number, number, number, number];
    position?: 'left' | 'right' | 'top' | 'bottom' | 'center' | 'full';
    radius?: number;
    width?: string | number;
    height?: string | number;
    [k: string]: unknown;
  };
}

export interface VerseBlock extends BlockBase {
  kind: 'verse';
  /** 성경 본문 (개역개정) */
  text: string;
  /** 장절 */
  ref?: string;
  /** 박스 제목 (예: '답을 쓴 뒤 맞추어 보기 · 시 103:19') */
  label?: string;
  items?: string[];
}

export interface QuestionBlock extends BlockBase {
  kind: 'question';
  text: string;
  /** 라벨(예: '말씀에서 찾아요') 또는 예시 답 */
  label?: string;
  ref?: string;
  /** 답 쓰는 줄 수 */
  count?: number;
}

export interface ActivityBlock extends BlockBase {
  kind: 'activity';
  /** 활동 이름 */
  label?: string;
  /** 활동 소개 */
  text?: string;
  /** 단계 */
  items?: string[];
  attrs?: { materials?: string; note?: string; time?: string; answer?: string; [k: string]: unknown };
}

export interface CalloutBlock extends BlockBase {
  kind: 'callout';
  label?: string;
  text: string;
  items?: string[];
}

export interface TableBlock extends BlockBase {
  kind: 'table';
  head?: string[];
  rows?: string[][];
}

export interface FillBlankBlock extends BlockBase {
  kind: 'fill_blank';
  /** '______'를 포함한 문장 */
  text: string;
  /** 정답(학생 지면에 인쇄하지 않는다) */
  label?: string;
}

export interface WritingBlock extends BlockBase {
  kind: 'writing';
  /** 줄 수 */
  count?: number;
  label?: string;
}

export interface ChecklistBlock extends BlockBase {
  kind: 'checklist';
  items: string[];
  /** 목록 아래 안내 한 줄 */
  label?: string;
}

export interface MemoryVerseBlock extends BlockBase {
  kind: 'memory';
  text: string;
  ref?: string;
  label?: string;
}

export interface PrayerBlock extends BlockBase {
  kind: 'prayer';
  text: string;
  label?: string;
  items?: string[];
}

export interface ReflectionBlock extends BlockBase {
  kind: 'reflection';
  text?: string;
  label?: string;
  /** 필기 줄 수 */
  count?: number;
}

export interface SpeechBlock extends BlockBase {
  kind: 'speech';
  text: string;
  /** 화자 */
  label?: string;
}

export interface KeywordsBlock extends BlockBase {
  kind: 'keywords';
  /** '낱말 — 뜻' 형태의 줄들 */
  items: string[];
  label?: string;
}

export interface SpacerBlock extends BlockBase {
  kind: 'spacer';
  /** 기본 간격의 배수 */
  count?: number;
}

export type Block =
  | HeadingBlock | TextBlock | ImageBlock | VerseBlock | QuestionBlock | ActivityBlock
  | CalloutBlock | TableBlock | FillBlankBlock | WritingBlock | ChecklistBlock
  | MemoryVerseBlock | PrayerBlock | ReflectionBlock | SpeechBlock | KeywordsBlock | SpacerBlock;

export interface Page {
  /**
   * 템플릿이 아는 레이아웃 이름. 'flow'면 템플릿 기본 흐름.
   * 어린이 교재: 'kids-story' | 'kids-find' | 'kids-activity' | 'kids-close'
   * 초등 3쪽:   'elem-story' | 'elem-find' | 'elem-close'
   * 그림책:     'full-image' | 'image-top-text-bottom' | 'text-top-image-bottom'
   *             | 'image-left' | 'image-right' | 'full-spread' | 'background-overlay' | 'multi-illustration'
   */
  layout?: string;
  title?: string;
  blocks: Block[];
  attrs?: Record<string, unknown>;
}

export interface Metadata {
  title: string;
  subtitle?: string;
  /** 머리글 작은 글씨 */
  kicker?: string;
  /** 배지(단원·과번호 등) */
  badge?: string;
  footer?: string;
  grade?: string;
  lesson_no?: number | null;
  unit?: string;
  department?: string;
  extra?: Record<string, unknown>;
}

export type PageSize = 'A4' | 'A5' | 'B5' | 'B5-ISO' | '210x210' | '6x9in' | 'custom';

/** 출판 설정 (요청서 §14). 첫 버전은 size/margins/bleed/page_numbers를 렌더러가 쓴다. */
export interface PageSetup {
  size: PageSize;
  width_mm?: number | null;
  height_mm?: number | null;
  margin_top_mm?: number;
  margin_bottom_mm?: number;
  margin_inside_mm?: number;
  margin_outside_mm?: number;
  gutter_mm?: number;
  bleed_mm?: number;
  facing_pages?: boolean;
  page_numbers?: boolean;
}

export interface BookDocument {
  metadata: Metadata;
  page_setup: PageSetup;
  /** doc-styles/<이름>.json — 기존 디자인 프로필을 그대로 쓴다 */
  theme: string;
  /** templates/typst/<template>/main.typ */
  template: string;
  pages: Page[];
  /** 이미지 상대경로의 기준 디렉터리 */
  assets_root?: string;
  /** 어디서 왔는지(디버깅용) */
  source?: string;
  schema_version: number;
  /** 어댑터가 남긴 손실·주의 경고 */
  warnings?: string[];
}
