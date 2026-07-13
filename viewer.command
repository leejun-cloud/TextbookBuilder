#!/bin/bash
# TextbookBuilder 뷰어 더블클릭 실행기 (macOS)
cd "$(dirname "$0")"
exec python3 viewer/server.py
