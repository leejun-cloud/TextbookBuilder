#!/bin/zsh -l
# TextbookBuilder 통합 실행기
# 더블클릭 한 번으로: ① 브라우저 뷰어가 열리고 ② 이 터미널 창에서 Claude Code가 시작된다.
# Claude Code를 종료(/exit 또는 Ctrl+C 두 번)하면 뷰어도 함께 꺼진다.

cd "$(dirname "$0")"

echo "📖 TextbookBuilder 시작"
echo ""

# 1) 뷰어 서버를 백그라운드로 실행 (브라우저 자동 오픈)
python3 viewer/server.py &
VIEWER_PID=$!
trap "kill $VIEWER_PID 2>/dev/null" EXIT

sleep 1
echo ""
echo "✅ 뷰어: http://localhost:3737 (브라우저 창)"
echo "✅ 아래에서 Claude Code가 시작됩니다. 여기에 명령을 입력하세요."
echo "   예: /import-source, /import-lesson1, /write-lesson 2"
echo ""

# 2) 같은 창에서 Claude Code 실행
if command -v claude >/dev/null 2>&1; then
  claude
else
  echo "⚠️  claude 명령을 찾지 못했습니다. Claude Code가 설치되어 있는지 확인하세요."
  echo "   설치: npm install -g @anthropic-ai/claude-code"
  read -k 1 "?아무 키나 누르면 닫힙니다..."
fi
