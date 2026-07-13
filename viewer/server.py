#!/usr/bin/env python3
"""TextbookBuilder 로컬 웹 뷰어 서버.

Python 3 표준 라이브러리만 사용 (http.server). 외부 의존성 없음.

실행:
    python3 viewer/server.py [--root DIR] [--port PORT]

기본 포트는 3737이며 $TEXTBOOK_VIEWER_PORT 환경변수로 재정의 가능.
"""
import argparse
import json
import os
import re
import sys
import threading
import webbrowser
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX_HTML_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "index.html")

STATUS_ORDER = ["승인", "평가됨", "초안", "입력만", "미시작"]


def read_text(path):
    if not path or not os.path.isfile(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def project_title(project_md_text, fallback):
    if not project_md_text:
        return fallback
    for line in project_md_text.splitlines():
        line = line.strip()
        if line.startswith("#"):
            return line.lstrip("#").strip()
    return fallback


def lesson_status(lesson_dir):
    if os.path.isfile(os.path.join(lesson_dir, "approved.md")):
        return "승인"
    if os.path.isfile(os.path.join(lesson_dir, "evaluation.md")):
        return "평가됨"
    if os.path.isfile(os.path.join(lesson_dir, "draft.md")):
        return "초안"
    if os.path.isfile(os.path.join(lesson_dir, "input.md")):
        return "입력만"
    return "미시작"


def parse_score(evaluation_text):
    """evaluation.md에서 가장 최근(마지막) 총점 숫자를 파싱."""
    if not evaluation_text:
        return None
    # "총점**: 87", "총점: 87", "87/100", "총점 87점" 등 관대하게 매칭
    patterns = [
        r"총점[^\d]{0,10}(\d{1,3})\s*/\s*100",
        r"총점[^\d]{0,10}(\d{1,3})\s*점",
        r"총점[^\d]{0,10}(\d{1,3})\b",
        r"(\d{1,3})\s*/\s*100",
    ]
    last_match = None
    for pat in patterns:
        matches = re.findall(pat, evaluation_text)
        if matches:
            last_match = matches[-1]
    if last_match is None:
        return None
    try:
        val = int(last_match)
        if 0 <= val <= 100:
            return val
    except ValueError:
        pass
    return None


def parse_target_chars(style_text):
    if not style_text:
        return None
    m = re.findall(r"전체\s*글자\s*수[^\d]{0,20}(\d[\d,]*)\s*자", style_text)
    if not m:
        return None
    try:
        return int(m[-1].replace(",", ""))
    except ValueError:
        return None


def list_projects_dir(root):
    projects_dir = os.path.join(root, "projects")
    if not os.path.isdir(projects_dir):
        return []
    return sorted(
        d for d in os.listdir(projects_dir)
        if os.path.isdir(os.path.join(projects_dir, d)) and not d.startswith(".")
    )


def project_dir_for(root, project_id):
    return os.path.join(root, "projects", project_id)


def build_project_summary(root, project_id):
    pdir = project_dir_for(root, project_id)
    project_md = read_text(os.path.join(pdir, "project.md"))
    title = project_title(project_md, project_id)
    lessons_dir = os.path.join(pdir, "lessons")
    lessons = []
    if os.path.isdir(lessons_dir):
        for nn in sorted(
            d for d in os.listdir(lessons_dir)
            if os.path.isdir(os.path.join(lessons_dir, d)) and not d.startswith(".")
        ):
            ldir = os.path.join(lessons_dir, nn)
            status = lesson_status(ldir)
            score = parse_score(read_text(os.path.join(ldir, "evaluation.md")))
            lessons.append({"nn": nn, "status": status, "score": score})
    return {
        "id": project_id,
        "title": title,
        "lessonCount": len(lessons),
        "lessons": lessons,
    }


def safe_join_sources(pdir, rel_path):
    """sources/ 하위로만 접근 가능하도록 경로 검증 (경로 순회 방지)."""
    sources_root = os.path.realpath(os.path.join(pdir, "sources"))
    candidate = os.path.realpath(os.path.join(sources_root, rel_path))
    if candidate != sources_root and not candidate.startswith(sources_root + os.sep):
        return None
    return candidate


def collapse_len(text):
    if text is None:
        return 0
    return len(text)


class Handler(BaseHTTPRequestHandler):
    server_version = "TextbookViewer/1.0"

    def log_message(self, fmt, *args):
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def _send_json(self, obj, status=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, path):
        try:
            with open(path, "rb") as f:
                body = f.read()
        except OSError:
            self._send_json({"error": "index.html not found"}, 404)
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    @property
    def root(self):
        return self.server.textbook_root

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        qs = parse_qs(parsed.query)

        try:
            if path == "/" or path == "/index.html":
                self._send_html(INDEX_HTML_PATH)
            elif path == "/api/projects":
                self.handle_projects()
            elif path == "/api/lesson":
                self.handle_lesson(qs)
            elif path == "/api/sources":
                self.handle_sources(qs)
            elif path == "/api/source":
                self.handle_source(qs)
            elif path == "/api/poll":
                self.handle_poll(qs)
            else:
                self._send_json({"error": "not found"}, 404)
        except Exception as e:  # pragma: no cover - safety net
            self._send_json({"error": str(e)}, 500)

    def do_POST(self):
        parsed = urlparse(self.path)
        try:
            if parsed.path == "/api/feedback":
                self.handle_feedback_post()
            else:
                self._send_json({"error": "not found"}, 404)
        except Exception as e:  # pragma: no cover - safety net
            self._send_json({"error": str(e)}, 500)

    # ---- handlers ----

    def handle_projects(self):
        root = self.root
        ids = list_projects_dir(root)
        result = [build_project_summary(root, pid) for pid in ids]
        self._send_json(result)

    def handle_lesson(self, qs):
        project = (qs.get("project") or [None])[0]
        nn = (qs.get("nn") or [None])[0]
        if not project or not nn:
            self._send_json({"error": "project, nn 파라미터가 필요합니다"}, 400)
            return
        pdir = project_dir_for(self.root, project)
        ldir = os.path.join(pdir, "lessons", nn)
        if not os.path.isdir(ldir):
            self._send_json({"error": "해당 과를 찾을 수 없습니다"}, 404)
            return

        def p(name):
            return os.path.join(ldir, name)

        files = {
            "draft": read_text(p("draft.md")),
            "worksheet": read_text(p("worksheet.md")),
            "teacherNotes": read_text(p("teacher-notes.md")),
            "input": read_text(p("input.md")),
            "evaluation": read_text(p("evaluation.md")),
            "approved": read_text(p("approved.md")),
            "feedback": read_text(p("feedback.md")),
        }
        char_counts = {
            "draft": collapse_len(files["draft"]),
            "worksheet": collapse_len(files["worksheet"]),
            "teacherNotes": collapse_len(files["teacherNotes"]),
        }
        style_text = read_text(os.path.join(pdir, "style", "style-rules.md"))
        target = parse_target_chars(style_text)

        mtimes = {}
        for name in ["draft.md", "worksheet.md", "teacher-notes.md", "input.md",
                     "evaluation.md", "approved.md", "feedback.md"]:
            fp = p(name)
            mtimes[name] = os.path.getmtime(fp) if os.path.isfile(fp) else None

        self._send_json({
            "files": files,
            "charCounts": char_counts,
            "target": target,
            "mtimes": mtimes,
        })

    def handle_sources(self, qs):
        project = (qs.get("project") or [None])[0]
        if not project:
            self._send_json({"error": "project 파라미터가 필요합니다"}, 400)
            return
        pdir = project_dir_for(self.root, project)
        sources_dir = os.path.join(pdir, "sources")
        if not os.path.isdir(sources_dir):
            self._send_json({"files": []})
            return
        files = []
        for dirpath, _dirnames, filenames in os.walk(sources_dir):
            for fn in filenames:
                if fn.startswith("."):
                    continue
                full = os.path.join(dirpath, fn)
                rel = os.path.relpath(full, sources_dir)
                files.append(rel.replace(os.sep, "/"))
        files.sort()
        self._send_json({"files": files})

    def handle_source(self, qs):
        project = (qs.get("project") or [None])[0]
        rel_path = (qs.get("path") or [None])[0]
        if not project or rel_path is None:
            self._send_json({"error": "project, path 파라미터가 필요합니다"}, 400)
            return
        pdir = project_dir_for(self.root, project)
        real_path = safe_join_sources(pdir, rel_path)
        if real_path is None:
            self._send_json({"error": "잘못된 경로입니다"}, 400)
            return
        if not os.path.isfile(real_path):
            self._send_json({"error": "파일을 찾을 수 없습니다"}, 404)
            return
        self._send_json({"content": read_text(real_path)})

    def handle_poll(self, qs):
        project = (qs.get("project") or [None])[0]
        nn = (qs.get("nn") or [None])[0]
        if not project:
            self._send_json({"error": "project 파라미터가 필요합니다"}, 400)
            return
        pdir = project_dir_for(self.root, project)
        candidates = [os.path.join(pdir, "project.md")]
        if nn:
            ldir = os.path.join(pdir, "lessons", nn)
            if os.path.isdir(ldir):
                for fn in os.listdir(ldir):
                    candidates.append(os.path.join(ldir, fn))
        max_mtime = 0
        for c in candidates:
            if os.path.isfile(c):
                max_mtime = max(max_mtime, os.path.getmtime(c))
        self._send_json({"mtime": max_mtime})

    def handle_feedback_post(self):
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b""
        try:
            data = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            self._send_json({"error": "잘못된 JSON 요청입니다"}, 400)
            return

        project = data.get("project")
        nn = data.get("nn")
        selection = data.get("selection", "")
        comment = data.get("comment", "")
        if not project or not nn:
            self._send_json({"error": "project, nn 값이 필요합니다"}, 400)
            return

        ldir = os.path.join(project_dir_for(self.root, project), "lessons", nn)
        if not os.path.isdir(ldir):
            self._send_json({"error": "해당 과를 찾을 수 없습니다"}, 404)
            return

        feedback_path = os.path.join(ldir, "feedback.md")
        is_new = not os.path.isfile(feedback_path)
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        entry = f"## [{now}] 수정 요청\n> 대상 문장: {selection}\n요청: {comment}\n\n"
        with open(feedback_path, "a", encoding="utf-8") as f:
            if is_new:
                f.write(f"# {nn}과 수정 요청 — Claude Code에서 '{nn}과 피드백 반영해줘'로 반영\n\n")
            f.write(entry)

        self._send_json({"ok": True})


def main():
    parser = argparse.ArgumentParser(description="TextbookBuilder 로컬 뷰어")
    parser.add_argument("--root", default=REPO_ROOT, help="교재 프로젝트 루트 (projects/ 상위 디렉터리)")
    parser.add_argument("--port", type=int, default=None, help="서버 포트")
    parser.add_argument("--no-browser", action="store_true", help="자동으로 브라우저를 열지 않음")
    args = parser.parse_args()

    port = args.port or int(os.environ.get("TEXTBOOK_VIEWER_PORT", "3737"))
    root = os.path.abspath(args.root)

    server = ThreadingHTTPServer(("localhost", port), Handler)
    server.textbook_root = root

    url = f"http://localhost:{port}"
    print(f"TextbookBuilder 뷰어 실행 중: {url}")
    print(f"프로젝트 루트: {root}")

    if not args.no_browser:
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n서버를 종료합니다.")
        server.shutdown()


if __name__ == "__main__":
    main()
