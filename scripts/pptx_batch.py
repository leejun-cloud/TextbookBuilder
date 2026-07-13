#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pptx_batch.py — TextbookBuilder 여러 PPT 일괄 수정 도구

여러 개의 .pptx 파일에 같은 작업(폰트 크기 조정, 폰트 통일, 문구 치환/제거, 색상 치환,
내용 추출)을 한 번에 적용한다. 원본을 실수로 덮어쓰지 않도록 출력 방식을 항상 명시해야
한다 (--out-dir 또는 --in-place).

사용법:
    python3 scripts/pptx_batch.py list 강의자료/*.pptx
    python3 scripts/pptx_batch.py scale-font --factor 1.2 강의자료/*.pptx --out-dir 수정본/
    python3 scripts/pptx_batch.py min-font --size 16 강의자료/ --out-dir 수정본/
    python3 scripts/pptx_batch.py set-font --name "Pretendard" 강의자료/*.pptx --out-dir 수정본/
    python3 scripts/pptx_batch.py replace-text --find "OLD" --replace "NEW" 강의자료/*.pptx --out-dir 수정본/
    python3 scripts/pptx_batch.py replace-map --map pairs.json 강의자료/*.pptx --out-dir 수정본/
    python3 scripts/pptx_batch.py remove-text --find "워터마크" --whole-shape 강의자료/*.pptx --out-dir 수정본/
    python3 scripts/pptx_batch.py replace-color --from FF0000 --to 0000FF 강의자료/*.pptx --out-dir 수정본/
    python3 scripts/pptx_batch.py extract --format md 강의자료/*.pptx --out-dir 추출본/
    python3 scripts/pptx_batch.py scale-font --factor 1.2 강의자료/*.pptx --dry-run
    python3 scripts/pptx_batch.py min-font --size 16 강의자료/*.pptx --in-place

replace-map 의 --map 파일 형식 (JSON 배열, {"find","replace"} 또는 {"찾기","바꾸기"} 키 사용):
    [
      {"find": "OLD1", "replace": "NEW1"},
      {"find": "OLD2", "replace": "NEW2"}
    ]

출력 안전 규칙:
    - 기본은 --out-dir DIR 이 필수다 (원본과 같은 이름으로 DIR 에 새로 저장).
    - --in-place 는 원본을 덮어쓰지만, 저장 직전에 같은 폴더의 백업_YYYYMMDD/ 에
      원본을 자동 백업한다.
    - --dry-run 은 무엇이 바뀔지만 보고하고 아무 파일도 쓰지 않는다.
"""

import argparse
import copy
import glob
import json
import re
import shutil
import sys
import time
from collections import Counter
from pathlib import Path

from pptx import Presentation
from pptx.util import Pt
from pptx.enum.shapes import MSO_SHAPE_TYPE
from pptx.enum.dml import MSO_COLOR_TYPE
from pptx.oxml.ns import qn
from lxml import etree


# ---------------------------------------------------------------- 파일 수집

def collect_files(patterns):
    """경로/글롭 목록을 .pptx 파일 목록으로 확장한다. 락 파일(~$)은 제외."""
    files = []
    for pat in patterns:
        p = Path(pat)
        if p.is_dir():
            files.extend(sorted(p.glob("*.pptx")))
            continue
        matched = sorted(glob.glob(pat))
        if matched:
            files.extend(Path(m) for m in matched)
        elif p.exists():
            files.append(p)
        else:
            print(f"[경고] 일치하는 파일이 없습니다: {pat}")

    seen = set()
    result = []
    for f in files:
        if f.name.startswith("~$"):
            continue
        if not f.is_file():
            continue
        key = f.resolve()
        if key in seen:
            continue
        seen.add(key)
        result.append(f)
    return result


# ---------------------------------------------------------------- 도형/텍스트 순회

def iter_leaf_shapes(shapes):
    """그룹을 재귀적으로 펼쳐 그룹이 아닌 실제 도형만 순서대로 낸다."""
    for shape in shapes:
        try:
            is_group = shape.shape_type == MSO_SHAPE_TYPE.GROUP
        except Exception:
            is_group = False
        if is_group:
            yield from iter_leaf_shapes(shape.shapes)
        else:
            yield shape


def iter_text_frames(slide, include_notes=False):
    """슬라이드 내 모든 텍스트 프레임(도형, 그룹 내부, 표 셀, 선택적으로 노트)을 낸다."""
    for shape in iter_leaf_shapes(slide.shapes):
        try:
            if shape.has_text_frame:
                yield shape.text_frame
        except Exception:
            pass
        try:
            if shape.has_table:
                table = shape.table
                for row in table.rows:
                    for cell in row.cells:
                        yield cell.text_frame
        except Exception:
            pass
    if include_notes:
        try:
            if slide.has_notes_slide:
                yield slide.notes_slide.notes_text_frame
        except Exception:
            pass


def iter_runs(tf):
    for para in tf.paragraphs:
        for run in para.runs:
            yield run


# ---------------------------------------------------------------- op: list (읽기 전용 인벤토리)

def op_list(prs, args):
    slide_count = len(prs.slides)
    total_runs = 0
    sizes = Counter()
    fonts = set()
    colors = set()
    for slide in prs.slides:
        for tf in iter_text_frames(slide, include_notes=args.include_notes):
            for run in iter_runs(tf):
                total_runs += 1
                try:
                    if run.font.size is not None:
                        sizes[run.font.size.pt] += 1
                except Exception:
                    pass
                try:
                    if run.font.name:
                        fonts.add(run.font.name)
                except Exception:
                    pass
                try:
                    if run.font.color and run.font.color.type == MSO_COLOR_TYPE.RGB:
                        colors.add(str(run.font.color.rgb))
                except Exception:
                    pass

    print(f"  - 슬라이드 수: {slide_count}")
    print(f"  - 전체 텍스트 런: {total_runs}")
    top5 = sizes.most_common(5)
    hist = ", ".join(f"{sz:g}pt×{cnt}" for sz, cnt in top5) or "(없음)"
    print(f"  - 폰트 크기 상위 5: {hist}")
    print(f"  - 사용된 폰트: {', '.join(sorted(fonts)) or '(없음)'}")
    print(f"  - 텍스트 색상 종류 수: {len(colors)}")
    return {"changed": total_runs, "note": "읽기 전용"}


# ---------------------------------------------------------------- op: scale-font / min-font

def op_scale_font(prs, args):
    changed = 0
    skipped = 0
    for slide in prs.slides:
        for tf in iter_text_frames(slide, include_notes=args.include_notes):
            for run in iter_runs(tf):
                sz = run.font.size
                if sz is None:
                    skipped += 1
                    continue
                new_pt = sz.pt * args.factor
                if args.min is not None:
                    new_pt = max(new_pt, args.min)
                if args.max is not None:
                    new_pt = min(new_pt, args.max)
                run.font.size = Pt(new_pt)
                changed += 1
    note = f"상속 크기 런 {skipped}건은 건너뜀 (레이아웃 상속)" if skipped else None
    return {"changed": changed, "note": note}


def op_min_font(prs, args):
    changed = 0
    skipped = 0
    for slide in prs.slides:
        for tf in iter_text_frames(slide, include_notes=args.include_notes):
            for run in iter_runs(tf):
                sz = run.font.size
                if sz is None:
                    skipped += 1
                    continue
                if sz.pt < args.size:
                    run.font.size = Pt(args.size)
                    changed += 1
    note = f"상속 크기 런 {skipped}건은 건너뜀 (레이아웃 상속)" if skipped else None
    return {"changed": changed, "note": note}


# ---------------------------------------------------------------- op: set-font

def op_set_font(prs, args):
    changed = 0
    for slide in prs.slides:
        for tf in iter_text_frames(slide, include_notes=args.include_notes):
            for run in iter_runs(tf):
                if not args.east_asian_only:
                    run.font.name = args.name
                rPr = run._r.get_or_add_rPr()
                ea = rPr.find(qn("a:ea"))
                if ea is None:
                    ea = etree.SubElement(rPr, qn("a:ea"))
                ea.set("typeface", args.name)
                changed += 1
    return {"changed": changed}


# ---------------------------------------------------------------- op: replace-text / remove-text

def _find_occurrences(hay, needle):
    idxs = []
    start = 0
    while True:
        i = hay.find(needle, start)
        if i == -1:
            break
        idxs.append(i)
        start = i + len(needle)
    return idxs


def _replace_in_paragraph(para, find, replace, ignore_case):
    """문단 내 run 을 넘나드는 문구도 치환한다. (변경건수, 서식병합여부) 반환."""
    runs = list(para.runs)
    if not runs:
        return 0, False
    texts = [r.text for r in runs]
    joined = "".join(texts)
    hay = joined.lower() if ignore_case else joined
    needle = find.lower() if ignore_case else find
    if not needle:
        return 0, False
    idxs = _find_occurrences(hay, needle)
    if not idxs:
        return 0, False

    bounds = []
    pos = 0
    for t in texts:
        bounds.append((pos, pos + len(t)))
        pos += len(t)

    def contained_in_single_run(start, end):
        for a, b in bounds:
            if a <= start and end <= b:
                return True
        return False

    all_single = all(contained_in_single_run(i, i + len(needle)) for i in idxs)

    if all_single:
        changed = 0
        flags = re.IGNORECASE if ignore_case else 0
        pattern = re.compile(re.escape(find), flags)
        for run in runs:
            new_text, n = pattern.subn(lambda m: replace, run.text)
            if n:
                changed += n
                run.text = new_text
        return changed, False
    else:
        flags = re.IGNORECASE if ignore_case else 0
        pattern = re.compile(re.escape(find), flags)
        new_joined, n = pattern.subn(lambda m: replace, joined)
        runs[0].text = new_joined
        for r in runs[1:]:
            r.text = ""
        return n, True


def _replace_pairs_in_deck(prs, pairs, ignore_case, include_notes):
    """(find, replace) 쌍 목록을 덱 전체에 한 번씩 훑으며 적용한다.
    pair 별 히트수, 총 변경건수, 서식 병합건수를 반환한다."""
    hits = [0] * len(pairs)
    merged = 0
    for slide in prs.slides:
        for tf in iter_text_frames(slide, include_notes=include_notes):
            for para in tf.paragraphs:
                for i, (find, replace) in enumerate(pairs):
                    n, was_merged = _replace_in_paragraph(para, find, replace, ignore_case)
                    hits[i] += n
                    if was_merged:
                        merged += 1
    return hits, merged


def op_replace_text(prs, args):
    changed = 0
    merged = 0
    for slide in prs.slides:
        for tf in iter_text_frames(slide, include_notes=args.include_notes):
            for para in tf.paragraphs:
                n, was_merged = _replace_in_paragraph(para, args.find, args.replace, args.ignore_case)
                changed += n
                if was_merged:
                    merged += 1
    note = f"서식 병합됨 {merged}건 (run 경계를 넘는 치환)" if merged else None
    return {"changed": changed, "note": note}


def _load_pairs(map_path):
    """pairs.json 을 읽어 (find, replace) 튜플 목록으로 변환.
    find-길이 내림차순으로 정렬해 긴 문구가 짧은 부분문자열보다 먼저 적용되게 한다."""
    data = json.loads(Path(map_path).read_text(encoding="utf-8"))
    if not isinstance(data, list):
        sys.exit(f"[오류] --map 파일은 JSON 배열이어야 합니다: {map_path}")
    pairs = []
    for item in data:
        find = item.get("find", item.get("찾기", ""))
        replace = item.get("replace", item.get("바꾸기", ""))
        if not find:
            continue
        pairs.append((find, replace))
    pairs.sort(key=lambda p: len(p[0]), reverse=True)
    return pairs


def op_replace_map(prs, args):
    pair_hits, merged = _replace_pairs_in_deck(prs, args._pairs, args.ignore_case, args.include_notes)
    changed = sum(pair_hits)

    print("  - 항목별 치환 건수:")
    for (find, replace), n in zip(args._pairs, pair_hits):
        if n == 0:
            print(f"      '{find}' → '{replace}': 0건 (미발견)")
        else:
            print(f"      '{find}' → '{replace}': {n}건")

    note_parts = []
    if merged:
        note_parts.append(f"서식 병합됨 {merged}건 (run 경계를 넘는 치환)")
    note = " / ".join(note_parts) if note_parts else None
    return {"changed": changed, "note": note}


def op_remove_text(prs, args):
    if args.whole_shape:
        changed = 0
        for slide in prs.slides:
            candidates = []
            for shape in iter_leaf_shapes(slide.shapes):
                try:
                    if shape.has_text_frame:
                        candidates.append(shape.text_frame)
                except Exception:
                    pass
                try:
                    if shape.has_table:
                        for row in shape.table.rows:
                            for cell in row.cells:
                                candidates.append(cell.text_frame)
                except Exception:
                    pass
            if args.include_notes:
                try:
                    if slide.has_notes_slide:
                        candidates.append(slide.notes_slide.notes_text_frame)
                except Exception:
                    pass
            for tf in candidates:
                text = tf.text.strip()
                hay = text.lower() if args.ignore_case else text
                needle = args.find.lower() if args.ignore_case else args.find
                if needle and needle in hay:
                    tf.clear()
                    changed += 1
        return {"changed": changed}
    else:
        fake_args = argparse.Namespace(find=args.find, replace="", ignore_case=args.ignore_case,
                                        include_notes=args.include_notes)
        return op_replace_text(prs, fake_args)


# ---------------------------------------------------------------- op: replace-color

def _replace_color_in_element(el, from_hex, to_hex, include_gradients):
    count = 0
    for srgb in el.iter(qn("a:srgbClr")):
        parent = srgb.getparent()
        if not include_gradients and parent is not None and parent.tag == qn("a:gs"):
            continue
        val = srgb.get("val", "")
        if val.upper() == from_hex:
            srgb.set("val", to_hex)
            count += 1
    return count


def op_replace_color(prs, args):
    from_hex = args.from_.lstrip("#").upper()
    to_hex = args.to.lstrip("#").upper()
    changed = 0
    for slide in prs.slides:
        for shape in iter_leaf_shapes(slide.shapes):
            try:
                changed += _replace_color_in_element(shape._element, from_hex, to_hex, args.include_gradients)
            except Exception:
                pass
    return {"changed": changed}


# ---------------------------------------------------------------- op: extract

def _extract_shape_content(shape):
    items = []
    try:
        is_group = shape.shape_type == MSO_SHAPE_TYPE.GROUP
    except Exception:
        is_group = False
    if is_group:
        for sub in shape.shapes:
            items.extend(_extract_shape_content(sub))
        return items
    try:
        if shape.has_table:
            rows = []
            for row in shape.table.rows:
                rows.append([cell.text_frame.text for cell in row.cells])
            items.append({"type": "table", "rows": rows})
            return items
    except Exception:
        pass
    try:
        if shape.has_text_frame:
            t = shape.text_frame.text
            if t.strip():
                items.append({"type": "text", "text": t})
    except Exception:
        pass
    return items


def _extract_deck(prs, include_notes=True):
    slides_data = []
    for idx, slide in enumerate(prs.slides, 1):
        content = []
        for shape in slide.shapes:
            content.extend(_extract_shape_content(shape))
        notes = ""
        try:
            if slide.has_notes_slide:
                notes = slide.notes_slide.notes_text_frame.text
        except Exception:
            pass
        slides_data.append({"slide": idx, "content": content, "notes": notes})
    return slides_data


def _deck_to_markdown(name, slides_data):
    lines = [f"# {name}", ""]
    for sl in slides_data:
        lines.append(f"## 슬라이드 {sl['slide']}")
        for item in sl["content"]:
            if item["type"] == "text":
                lines.append(item["text"])
                lines.append("")
            elif item["type"] == "table":
                rows = item["rows"]
                if rows:
                    lines.append("| " + " | ".join(rows[0]) + " |")
                    lines.append("|" + "---|" * len(rows[0]))
                    for r in rows[1:]:
                        lines.append("| " + " | ".join(r) + " |")
                    lines.append("")
        if sl["notes"].strip():
            lines.append(f"**발표자 노트:** {sl['notes']}")
            lines.append("")
    return "\n".join(lines)


def op_extract(prs, args, name, out_path):
    slides_data = _extract_deck(prs, include_notes=True)
    char_count = 0
    for sl in slides_data:
        for item in sl["content"]:
            if item["type"] == "text":
                char_count += len(item["text"])
            else:
                char_count += sum(len(c) for row in item["rows"] for c in row)
        char_count += len(sl["notes"])

    if not args.dry_run:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        if args.format == "json":
            out_path.write_text(json.dumps(slides_data, ensure_ascii=False, indent=2), encoding="utf-8")
        else:
            out_path.write_text(_deck_to_markdown(name, slides_data), encoding="utf-8")
    return {"changed": char_count, "note": f"글자 수 {char_count}"}


# ---------------------------------------------------------------- 출력 경로/백업

def backup_original(path, backup_dirname):
    backup_dir = path.parent / backup_dirname
    backup_dir.mkdir(parents=True, exist_ok=True)
    dest = backup_dir / path.name
    if not dest.exists():
        shutil.copy2(path, dest)
    return dest


# ---------------------------------------------------------------- CLI

OPS = ["list", "scale-font", "min-font", "set-font", "replace-text", "replace-map",
       "remove-text", "replace-color", "extract"]


def build_parser():
    ap = argparse.ArgumentParser(
        prog="pptx_batch.py",
        description="TextbookBuilder 여러 PPT 일괄 수정 도구",
        epilog=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = ap.add_subparsers(dest="op", required=True)

    def add_common(p, needs_output=True):
        p.add_argument("files", nargs="+", help="파일/폴더/글롭 패턴 (예: 강의자료/*.pptx)")
        if needs_output:
            p.add_argument("--out-dir", help="결과를 저장할 폴더 (원본은 보존)")
            p.add_argument("--in-place", action="store_true",
                           help="원본을 덮어씀 (저장 전 자동 백업 폴더 생성)")
            p.add_argument("--dry-run", action="store_true", help="변경사항만 보고, 저장하지 않음")
        p.add_argument("--include-notes", action="store_true", help="발표자 노트도 포함")

    p_list = sub.add_parser("list", help="덱 인벤토리 (읽기 전용)")
    add_common(p_list, needs_output=False)

    p_scale = sub.add_parser("scale-font", help="모든 명시적 폰트 크기를 비율로 조정")
    add_common(p_scale)
    p_scale.add_argument("--factor", type=float, required=True, help="곱할 배율 (예: 1.2)")
    p_scale.add_argument("--min", type=float, default=None, help="최소 크기(pt)")
    p_scale.add_argument("--max", type=float, default=None, help="최대 크기(pt)")

    p_min = sub.add_parser("min-font", help="지정 크기보다 작은 폰트를 지정 크기로 올림")
    add_common(p_min)
    p_min.add_argument("--size", type=float, required=True, help="최소 보장 크기(pt)")

    p_setf = sub.add_parser("set-font", help="폰트 이름(및 한글 서체)을 통일")
    add_common(p_setf)
    p_setf.add_argument("--name", required=True, help="설정할 폰트 이름")
    p_setf.add_argument("--east-asian-only", action="store_true",
                         help="한글(East Asian) 서체만 설정하고 라틴 폰트명은 건드리지 않음")

    p_rep = sub.add_parser("replace-text", help="문구 치환 (run 경계를 넘어도 처리)")
    add_common(p_rep)
    p_rep.add_argument("--find", required=True, help="찾을 문구")
    p_rep.add_argument("--replace", required=True, help="바꿀 문구")
    p_rep.add_argument("--ignore-case", action="store_true", help="대소문자 무시")

    p_repmap = sub.add_parser("replace-map", help="여러 문구를 pairs.json 으로 한 번에 치환")
    add_common(p_repmap)
    p_repmap.add_argument("--map", required=True, help="{find, replace} 쌍 목록 JSON 파일 경로")
    p_repmap.add_argument("--ignore-case", action="store_true", help="대소문자 무시")

    p_rm = sub.add_parser("remove-text", help="문구 제거 (워터마크/회사명 등)")
    add_common(p_rm)
    p_rm.add_argument("--find", required=True, help="제거할 문구")
    p_rm.add_argument("--ignore-case", action="store_true", help="대소문자 무시")
    p_rm.add_argument("--whole-shape", action="store_true",
                       help="문구가 포함된 도형이면 전체 텍스트를 비움 (도형 자체는 삭제하지 않음)")

    p_col = sub.add_parser("replace-color", help="채우기/폰트/선 색상 치환")
    add_common(p_col)
    p_col.add_argument("--from", dest="from_", required=True, help="바꿀 원본 색상(HEX)")
    p_col.add_argument("--to", required=True, help="새 색상(HEX)")
    p_col.add_argument("--include-gradients", action="store_true",
                        help="그라데이션 stop 색상도 함께 치환")

    p_ext = sub.add_parser("extract", help="덱 내용을 md/json 으로 추출")
    add_common(p_ext)
    p_ext.add_argument("--format", choices=["md", "json"], default="md", help="추출 형식")

    return ap


def validate_output_flags(args):
    if args.op == "list":
        return
    if args.dry_run:
        return
    if bool(args.out_dir) == bool(args.in_place):
        # 둘 다 없거나 둘 다 있으면 오류
        if args.out_dir and args.in_place:
            sys.exit("[오류] --out-dir 와 --in-place 는 동시에 사용할 수 없습니다.")
        sys.exit("[오류] 출력 방식을 지정해야 합니다: --out-dir DIR (새 폴더에 저장) "
                  "또는 --in-place (원본 덮어쓰기, 자동 백업 생성). "
                  "미리 확인만 하려면 --dry-run 을 사용하세요.")


OP_FUNCS = {
    "list": op_list,
    "scale-font": op_scale_font,
    "min-font": op_min_font,
    "set-font": op_set_font,
    "replace-text": op_replace_text,
    "replace-map": op_replace_map,
    "remove-text": op_remove_text,
    "replace-color": op_replace_color,
}


def run(args):
    files = collect_files(args.files)
    if not files:
        sys.exit("[오류] 처리할 .pptx 파일을 찾지 못했습니다.")

    if args.op == "replace-map":
        args._pairs = _load_pairs(args.map)
        if not args._pairs:
            sys.exit(f"[오류] --map 파일에 유효한 항목이 없습니다: {args.map}")

    backup_dirname = f"백업_{time.strftime('%Y%m%d')}"
    out_dir = Path(args.out_dir) if getattr(args, "out_dir", None) else None
    in_place = getattr(args, "in_place", False)
    dry_run = getattr(args, "dry_run", False)

    report_rows = []
    any_failed = False

    for f in files:
        name = f.name
        print(f"\n[처리 중] {name}")
        try:
            prs = Presentation(str(f))

            if args.op == "extract":
                ext = "json" if args.format == "json" else "md"
                if out_dir is not None:
                    out_path = out_dir / f"{f.stem}.{ext}"
                else:
                    out_path = f.parent / f"{f.stem}.{ext}"
                result = op_extract(prs, args, f.stem, out_path)
            else:
                result = OP_FUNCS[args.op](prs, args)

                if args.op != "list" and not dry_run:
                    if out_dir is not None:
                        out_dir.mkdir(parents=True, exist_ok=True)
                        out_path = out_dir / f.name
                    else:
                        if in_place:
                            backup_original(f, backup_dirname)
                        out_path = f
                    prs.save(str(out_path))

            changed = result.get("changed", 0)
            note = result.get("note")
            status = "완료(미리보기)" if dry_run and args.op != "list" else "완료"
            if note:
                print(f"  - {note}")
            report_rows.append((name, changed, status))
        except Exception as e:
            print(f"  [오류] {e}")
            report_rows.append((name, "-", f"실패: {e}"))
            any_failed = True

    print("\n=== 요약 ===")
    print(f"{'파일명':30} | {'변경 건수':>10} | 결과")
    print("-" * 60)
    for name, changed, status in report_rows:
        print(f"{name:30} | {str(changed):>10} | {status}")

    return 1 if any_failed else 0


def main():
    parser = build_parser()
    args = parser.parse_args()
    validate_output_flags(args)
    sys.exit(run(args))


if __name__ == "__main__":
    main()
