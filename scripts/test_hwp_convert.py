#!/usr/bin/env python3
"""hwp_convert.py에 대한 자체 실행 테스트.

실행: python3 scripts/test_hwp_convert.py
"""
import os
import subprocess
import sys
import tempfile
import zipfile

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONVERTER = os.path.join(SCRIPT_DIR, "hwp_convert.py")

NS = "http://www.hancom.co.kr/hwpml/2011/paragraph"

SECTION0_XML = f"""<?xml version="1.0" encoding="UTF-8"?>
<hp:sec xmlns:hp="{NS}">
  <hp:p>
    <hp:run>
      <hp:t>제1문</hp:t>
    </hp:run>
  </hp:p>
  <hp:p>
    <hp:run>
      <hp:t>사람의 제일 되는 목적은 하나님을 영화롭게 하고 영원토록 그를 즐거워하는 것입니다.</hp:t>
    </hp:run>
  </hp:p>
  <hp:p>
    <hp:run>
      <hp:t>이것은 소요리문답의 첫 번째 문답으로서 인간 존재의 궁극적인 목적을 다룬다.</hp:t>
    </hp:run>
  </hp:p>
  <hp:tbl>
    <hp:tr>
      <hp:tc><hp:subList><hp:p><hp:run><hp:t>구분</hp:t></hp:run></hp:p></hp:subList></hp:tc>
      <hp:tc><hp:subList><hp:p><hp:run><hp:t>내용</hp:t></hp:run></hp:p></hp:subList></hp:tc>
    </hp:tr>
    <hp:tr>
      <hp:tc><hp:subList><hp:p><hp:run><hp:t>목적</hp:t></hp:run></hp:p></hp:subList></hp:tc>
      <hp:tc><hp:subList><hp:p><hp:run><hp:t>하나님 영화</hp:t></hp:run></hp:p></hp:subList></hp:tc>
    </hp:tr>
  </hp:tbl>
</hp:sec>
"""


def build_sample_hwpx(path: str) -> None:
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("mimetype", "application/hwp+zip")
        zf.writestr("Contents/section0.xml", SECTION0_XML)


def run_converter(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, CONVERTER] + args,
        capture_output=True,
        text=True,
    )


def test_hwpx_conversion() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        hwpx_path = os.path.join(tmpdir, "sample.hwpx")
        build_sample_hwpx(hwpx_path)

        result = run_converter([hwpx_path])
        assert result.returncode == 0, f"변환 실패: {result.stderr}"

        md_path = os.path.join(tmpdir, "sample.md")
        assert os.path.isfile(md_path), "출력 마크다운 파일이 생성되지 않았습니다"

        with open(md_path, encoding="utf-8") as f:
            markdown = f.read()

        # 짧은 문단("제1문")은 다/요/.으로 끝나지 않고 다음 문단이 더 기니 헤딩이어야 한다
        assert "## 제1문" in markdown, f"헤딩 마커가 없습니다:\n{markdown}"

        # 본문 텍스트가 그대로 들어있는지 확인
        assert "사람의 제일 되는 목적은 하나님을 영화롭게 하고 영원토록 그를 즐거워하는 것입니다." in markdown
        assert "이것은 소요리문답의 첫 번째 문답으로서 인간 존재의 궁극적인 목적을 다룬다." in markdown

        # 표가 파이프 마크다운 테이블로 변환되었는지 확인
        assert "| 구분 | 내용 |" in markdown
        assert "| --- | --- |" in markdown
        assert "| 목적 | 하나님 영화 |" in markdown

        # 요약 출력 확인
        assert "문단 수:" in result.stdout
        assert "표 수: 1" in result.stdout
        assert "추출 글자 수:" in result.stdout

        print("PASS: test_hwpx_conversion")


def test_hwpx_split_by_heading() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        hwpx_path = os.path.join(tmpdir, "sample.hwpx")
        build_sample_hwpx(hwpx_path)
        split_dir = os.path.join(tmpdir, "split")

        result = run_converter([hwpx_path, "--split-by-heading", split_dir])
        assert result.returncode == 0, f"변환 실패: {result.stderr}"

        files = sorted(os.listdir(split_dir))
        assert len(files) >= 1, "분할된 파일이 없습니다"
        assert any(f.startswith("01_") for f in files), f"01_ 접두 파일이 없습니다: {files}"

        print("PASS: test_hwpx_split_by_heading")


def test_missing_file_errors() -> None:
    result = run_converter(["/no/such/file.hwpx"])
    assert result.returncode == 1, "존재하지 않는 파일에 대해 종료 코드 1이어야 합니다"
    assert "오류" in result.stderr, f"에러 메시지가 없습니다: {result.stderr}"
    print("PASS: test_missing_file_errors")


def test_unsupported_extension_errors() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "sample.docx")
        with open(path, "w", encoding="utf-8") as f:
            f.write("dummy")

        result = run_converter([path])
        assert result.returncode == 1, "지원하지 않는 확장자에 대해 종료 코드 1이어야 합니다"
        assert "오류" in result.stderr
        print("PASS: test_unsupported_extension_errors")


if __name__ == "__main__":
    test_hwpx_conversion()
    test_hwpx_split_by_heading()
    test_missing_file_errors()
    test_unsupported_extension_errors()
    print("모든 테스트 통과")
