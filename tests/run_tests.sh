#!/usr/bin/env bash
# CoatMenu test suite.
#
# Every test_*.py under tests/ runs in its own process. Uses 3DCoat's bundled
# Python when present (it is the exact interpreter + PySide6 the extension runs
# against); falls back to whatever `python` is on PATH.
#
# Note: MSYS paths must be handed to the native Windows interpreter in the
# "C:/x/y" form (cygpath -m) - "//h/Dev/..." would be misread as H:\h\Dev\...
set -u

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(dirname "$HERE")"

find_python() {
    local cand
    for cand in \
        "$HOME/Documents/3DCoat/python-3.11.9/python.exe" \
        "$(cygpath -u "${USERPROFILE:-$HOME}" 2>/dev/null)/Documents/3DCoat/python-3.11.9/python.exe"; do
        if [ -n "$cand" ] && [ -x "$cand" ]; then
            echo "$cand"
            return 0
        fi
    done
    command -v python || command -v python3
}

PY="$(find_python)"
if [ -z "$PY" ]; then
    echo "no python found"
    exit 2
fi
echo "python: $PY"

failed=0
for test in "$HERE"/test_*.py; do
    name="$(basename "$test")"
    echo
    echo "=== $name ==="
    if ! QT_QPA_PLATFORM=offscreen "$PY" "$(cygpath -m "$test" 2>/dev/null || echo "$test")"; then
        failed=$((failed + 1))
    fi
done

echo
if [ "$failed" -gt 0 ]; then
    echo "SUITE FAILED: $failed file(s)"
    exit 1
fi
echo "SUITE PASSED"
