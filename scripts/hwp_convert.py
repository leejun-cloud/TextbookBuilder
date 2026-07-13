#!/usr/bin/env python3
"""HWP/HWPX -> Markdown 변환기.

사용법:
    python3 scripts/hwp_convert.py <input> [-o output.md] [--split-by-heading DIR]

- .hwpx : 순수 stdlib (zipfile + xml.etree.ElementTree)로 직접 파싱한다.
- .hwp  : 바이너리(구) 포맷이라 자체 파싱 대신 pyhwp의 hwp5txt를 호출한다.
          hwp5txt가 없으면 설치 안내를 출력하고 종료 코드 1로 종료한다.

제목(heading) 판별은 header.xml의 문단 스타일 정의를 신뢰하지 않는다(버전별로
구조가 크게 달라 파싱이 취약해지기 때문). 대신 아래의 단순한 휴리스틱을 쓴다:

    문단 길이가 40자 미만이고, '다'/'요'/'.'로 끝나지 않으며,
    바로 다음 문단이 더 길면 -> 소제목(##)으로 취급한다.

이 휴리스틱은 표 안의 텍스트에는 적용하지 않는다.
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import zipfile
import xml.etree.ElementTree as ET

HEADING_MAX_LEN = 40
HEADING_EXCLUDE_ENDINGS = ("다", "요", ".")


# ---------------------------------------------------------------------------
# 공통 유틸
# ---------------------------------------------------------------------------

def localname(tag: str) -> str:
    """네임스페이스 접두사({ns}tag)를 제거하고 태그 이름만 반환한다."""
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def error_exit(message: str) -> None:
    print(f"오류: {message}", file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# .hwpx 파싱
# ---------------------------------------------------------------------------

def extract_para_text(p_elem: ET.Element) -> str:
    """hp:p 문단 안의 모든 hp:t 텍스트를 순서대로 이어 붙인다."""
    parts = []
    for elem in p_elem.iter():
        if localname(elem.tag) == "t":
            parts.append(elem.text or "")
    return "".join(parts)


def extract_cell_text(tc_elem: ET.Element) -> str:
    """hp:tc(표 셀) 안의 문단들을 <br>로 이어 붙인다."""
    paras = []
    for elem in tc_elem.iter():
        if localname(elem.tag) == "p":
            text = extract_para_text(elem)
            if text.strip():
                paras.append(text)
    return "<br>".join(paras)


def extract_table(tbl_elem: ET.Element) -> list[list[str]]:
    """hp:tbl -> 2차원 문자열 리스트(행 x 셀)."""
    rows_elems = [c for c in tbl_elem if localname(c.tag) == "tr"]
    if not rows_elems:
        rows_elems = [e for e in tbl_elem.iter() if localname(e.tag) == "tr"]

    rows: list[list[str]] = []
    for tr in rows_elems:
        cells_elems = [c for c in tr if localname(c.tag) == "tc"]
        if not cells_elems:
            cells_elems = [e for e in tr.iter() if localname(e.tag) == "tc"]
        rows.append([extract_cell_text(tc) for tc in cells_elems])
    return rows


def walk_blocks(elem: ET.Element) -> list[tuple[str, object]]:
    """문서 순서대로 ('para', text) / ('table', rows) 블록 리스트를 만든다.

    hp:tbl을 만나면 그 내부는 표 전용 로직으로만 처리하고 더 이상 재귀하지
    않는다(표 셀 안의 hp:p가 본문 문단으로 중복 추출되는 것을 막기 위함).
    """
    blocks: list[tuple[str, object]] = []
    for child in elem:
        tag = localname(child.tag)
        if tag == "tbl":
            blocks.append(("table", extract_table(child)))
        elif tag == "p":
            text = extract_para_text(child)
            if text.strip():
                blocks.append(("para", text))
        else:
            blocks.extend(walk_blocks(child))
    return blocks


def section_files(zf: zipfile.ZipFile) -> list[str]:
    pattern = re.compile(r"Contents/section(\d+)\.xml$")
    matches = []
    for name in zf.namelist():
        m = pattern.search(name)
        if m:
            matches.append((int(m.group(1)), name))
    matches.sort(key=lambda pair: pair[0])
    return [name for _, name in matches]


def extract_hwpx(path: str) -> list[tuple[str, object]]:
    try:
        zf = zipfile.ZipFile(path)
    except zipfile.BadZipFile:
        error_exit(f"'{path}'가 올바른 .hwpx(zip) 파일이 아닙니다. 파일이 손상되었을 수 있습니다.")

    with zf:
        names = section_files(zf)
        if not names:
            error_exit("Contents/section*.xml을 찾을 수 없습니다. 올바른 .hwpx 파일인지 확인하세요.")

        blocks: list[tuple[str, object]] = []
        for name in names:
            try:
                data = zf.read(name)
                root = ET.fromstring(data)
            except ET.ParseError as e:
                error_exit(f"{name} 파싱 실패: {e}")
            blocks.extend(walk_blocks(root))
        return blocks


# ---------------------------------------------------------------------------
# .hwp (구 바이너리 포맷) 처리 - hwp5txt 위임
# ---------------------------------------------------------------------------

def find_hwp5txt() -> list[str] | None:
    """hwp5txt 실행 커맨드를 찾는다. 못 찾으면 None."""
    exe = shutil.which("hwp5txt")
    if exe:
        return [exe]

    for candidate in (
        os.path.expanduser("~/.local/bin/hwp5txt"),
        "/usr/local/bin/hwp5txt",
        "/opt/homebrew/bin/hwp5txt",
    ):
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return [candidate]

    # python -m hwp5.hwp5txt 로 모듈이 설치되어 있는지 확인
    probe = subprocess.run(
        [sys.executable, "-m", "hwp5.hwp5txt", "--help"],
        capture_output=True,
    )
    if probe.returncode == 0:
        return [sys.executable, "-m", "hwp5.hwp5txt"]

    return None


HWP5TXT_MISSING_MESSAGE = """.hwp(구 바이너리 포맷) 파일을 변환하려면 pyhwp의 hwp5txt가 필요합니다.

설치 방법:
    pip3 install pyhwp
    (또는) pipx install pyhwp

설치가 어렵다면 한컴오피스/한글Viewer에서 파일을 .hwpx 또는 .txt로
다시 저장한 뒤 이 도구를 다시 실행해 주세요."""


def extract_hwp(path: str) -> list[tuple[str, object]]:
    cmd = find_hwp5txt()
    if cmd is None:
        error_exit(HWP5TXT_MISSING_MESSAGE)

    result = subprocess.run(cmd + [path], capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        error_exit(f"hwp5txt 실행 실패:\n{result.stderr.strip()}")

    blocks: list[tuple[str, object]] = []
    for line in result.stdout.splitlines():
        line = line.strip()
        if line:
            blocks.append(("para", line))
    return blocks


# ---------------------------------------------------------------------------
# 제목 판별 + 마크다운 조립
# ---------------------------------------------------------------------------

def detect_headings(paragraphs: list[str]) -> list[bool]:
    flags = []
    for i, text in enumerate(paragraphs):
        is_short = len(text) < HEADING_MAX_LEN
        ends_excluded = text.endswith(HEADING_EXCLUDE_ENDINGS)
        followed_by_longer = i + 1 < len(paragraphs) and len(paragraphs[i + 1]) > len(text)
        flags.append(is_short and not ends_excluded and followed_by_longer)
    return flags


def render_table(rows: list[list[str]]) -> list[str]:
    if not rows:
        return []
    lines = []
    header = rows[0]
    lines.append("| " + " | ".join(cell.replace("|", "\\|") for cell in header) + " |")
    lines.append("| " + " | ".join("---" for _ in header) + " |")
    for row in rows[1:]:
        lines.append("| " + " | ".join(cell.replace("|", "\\|") for cell in row) + " |")
    return lines


def build_markdown(blocks: list[tuple[str, object]]) -> tuple[str, dict]:
    paragraphs_only = [text for kind, text in blocks if kind == "para"]
    heading_flags = detect_headings(paragraphs_only)

    lines: list[str] = []
    para_idx = 0
    n_paragraphs = 0
    n_tables = 0
    n_chars = 0

    for kind, payload in blocks:
        if kind == "para":
            text = payload
            n_paragraphs += 1
            n_chars += len(text)
            if heading_flags[para_idx]:
                lines.append(f"## {text}")
            else:
                lines.append(text)
            para_idx += 1
            lines.append("")
        else:  # table
            rows = payload
            n_tables += 1
            for row in rows:
                for cell in row:
                    n_chars += len(cell)
            lines.extend(render_table(rows))
            lines.append("")

    markdown = "\n".join(lines).rstrip() + "\n"
    stats = {"paragraphs": n_paragraphs, "tables": n_tables, "chars": n_chars}
    return markdown, stats


# ---------------------------------------------------------------------------
# 헤딩별 분할 저장
# ---------------------------------------------------------------------------

def slugify(text: str) -> str:
    text = text.strip()
    text = re.sub(r"[^\w가-힣]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    return text or "untitled"


def split_by_heading(markdown: str, out_dir: str) -> list[str]:
    os.makedirs(out_dir, exist_ok=True)
    lines = markdown.split("\n")

    sections: list[tuple[str, list[str]]] = []  # (heading_text, lines)
    preamble: list[str] = []
    current_heading = None
    current_lines: list[str] = []

    for line in lines:
        if line.startswith("## "):
            if current_heading is None:
                preamble = current_lines
            else:
                sections.append((current_heading, current_lines))
            current_heading = line[3:].strip()
            current_lines = [line]
        else:
            current_lines.append(line)
    if current_heading is not None:
        sections.append((current_heading, current_lines))
    elif not sections:
        preamble = current_lines

    written = []
    idx = 1
    if any(l.strip() for l in preamble):
        path = os.path.join(out_dir, "00_머리말.md")
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(preamble).strip() + "\n")
        written.append(path)

    for heading, sec_lines in sections:
        filename = f"{idx:02d}_{slugify(heading)}.md"
        path = os.path.join(out_dir, filename)
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(sec_lines).strip() + "\n")
        written.append(path)
        idx += 1

    return written


# ---------------------------------------------------------------------------
# 메인
# ---------------------------------------------------------------------------

def convert(input_path: str) -> tuple[str, dict]:
    if not os.path.isfile(input_path):
        error_exit(f"파일을 찾을 수 없습니다: {input_path}")

    ext = os.path.splitext(input_path)[1].lower()
    if ext == ".hwpx":
        blocks = extract_hwpx(input_path)
    elif ext == ".hwp":
        blocks = extract_hwp(input_path)
    else:
        error_exit(f"지원하지 않는 파일 형식입니다: '{ext}' (지원 형식: .hwp, .hwpx)")

    return build_markdown(blocks)


def main() -> None:
    parser = argparse.ArgumentParser(description="HWP/HWPX 문서를 마크다운으로 변환한다.")
    parser.add_argument("input", help="입력 .hwp 또는 .hwpx 파일 경로")
    parser.add_argument("-o", "--output", help="출력 마크다운 파일 경로 (기본: 입력 파일명.md)")
    parser.add_argument(
        "--split-by-heading",
        metavar="DIR",
        help="최상위 소제목(##) 기준으로 여러 파일로 나눠 DIR에 저장",
    )
    args = parser.parse_args()

    markdown, stats = convert(args.input)

    output_path = args.output or os.path.splitext(args.input)[0] + ".md"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(markdown)

    print(f"문단 수: {stats['paragraphs']}")
    print(f"표 수: {stats['tables']}")
    print(f"추출 글자 수: {stats['chars']}")
    print(f"출력 파일: {output_path}")

    if args.split_by_heading:
        written = split_by_heading(markdown, args.split_by_heading)
        print(f"분할 저장 ({len(written)}개 파일) -> {args.split_by_heading}")
        for path in written:
            print(f"  - {path}")


if __name__ == "__main__":
    main()
