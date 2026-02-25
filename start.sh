#!/usr/bin/env bash
set -e

if ! command -v python3 &> /dev/null; then
    echo "Python 3 is required. Install it from https://python.org"
    exit 1
fi

echo ""
echo "  Starting Octobot..."
echo ""

python3 -c "import anthropic, flask, httpx, rich" 2>/dev/null || {
    echo "  Installing dependencies..."
    pip install . --quiet
    python3 -m playwright install chromium --quiet 2>/dev/null || true
}

python3 main.py
