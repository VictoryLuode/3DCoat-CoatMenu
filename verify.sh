#!/usr/bin/env bash
# verify.sh — 一条命令回答「这个仓现在可发布吗？」
#
#   ./verify.sh           全量：版本一致 + 语法 + 扩展测试 + 打包依赖
#   ./verify.sh --quick   快速：只做版本一致 + 语法（改文档、小改时用）
#
# 退出码：0 = 全绿可发布；1 = 有失败。
#
# 三条纪律（动这个文件之前先读）：
#   1. 每个 gate 都必须真的能变红。永远绿的 gate 比没有 gate 更糟——它是对
#      坏代码的 ✓ 背书。加 gate 时故意弄坏一次，确认它红了，再改回来。
#   2. 本脚本是验证的唯一入口：本地跑它、发版前跑它、将来 CI 也只调它。
#   3. 版本号的唯一真源是 git tag；文件里的字面量是它的投影，两者必须相等。
#
# 本仓版本的落点（两处必须相等）：
#   coat_side/coatmenu/__init__.py  ->  __version__
#   CHANGELOG.md                    ->  最靠前的 "vX.Y.Z" 标题
#
# ⚠️ __version__ 必须是**单行字符串字面量**：install/build_pack.py 用
#    `line.startswith("__version__")` 逐行扫它。改成计算式会让打包直接失败。
set -uo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO"

QUICK=0
for a in "$@"; do
  case "$a" in
    --quick) QUICK=1 ;;
    -h|--help) sed -n '2,4p' "$0"; exit 0 ;;
    *) echo "unknown option: $a" >&2; exit 2 ;;
  esac
done

failed=0
step() { printf '\n== %s\n' "$1"; }
pass() { printf '   ok   %s\n' "$1"; }
fail() { printf '   FAIL %s\n' "$1"; failed=1; }

PY="$(command -v python || command -v python3 || true)"
ADDON="coat_side/coatmenu/__init__.py"

# --------------------------------------------------------- 1. 版本一致性
step "1. version consistency"

code_version=""
if [ -z "$PY" ]; then
  fail "no python on PATH — cannot read __version__"
else
  code_version="$("$PY" - "$ADDON" <<'PYEOF' 2>&1
import ast, pathlib, sys
for node in ast.parse(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8")).body:
    if isinstance(node, ast.Assign) and any(getattr(t, "id", "") == "__version__" for t in node.targets):
        try:
            v = ast.literal_eval(node.value)
        except ValueError:
            sys.exit("not-a-literal")
        print(v if isinstance(v, str) else "")
        break
PYEOF
)"
  case "$code_version" in
    not-a-literal) fail "__version__ must be a plain string literal"; code_version="" ;;
    "") fail "no __version__ in $ADDON" ;;
    *) pass "__version__ = $code_version" ;;
  esac
fi

# build_pack.py 的文本扫描必须能读到它（这是打包的硬前提）
if grep -qE '^__version__ *= *"[0-9]+\.[0-9]+\.[0-9]+"' "$ADDON"; then
  pass "__version__ is a single-line literal (install/build_pack.py can scan it)"
else
  fail "install/build_pack.py scans for 'line.startswith(\"__version__\")' —"
  fail "  __version__ must stay a single-line string literal"
fi

changelog_version="$(grep -m1 -oE '^#+ +v?[0-9]+\.[0-9]+\.[0-9]+' CHANGELOG.md 2>/dev/null \
  | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)"
if [ -n "$code_version" ] && [ "$code_version" = "$changelog_version" ]; then
  pass "CHANGELOG.md top version agrees ($changelog_version)"
else
  fail "version mismatch: __version__=${code_version:-?}  CHANGELOG=${changelog_version:-none}"
fi

tags_here="$(git tag --points-at HEAD 2>/dev/null || true)"
if [ -z "$tags_here" ]; then
  pass "HEAD carries no tag (fine — this is the pre-release state)"
else
  for t in $tags_here; do
    if [ "$(git cat-file -t "$t" 2>/dev/null)" = "tag" ]; then
      pass "tag $t is annotated"
    else
      fail "tag $t is lightweight — git describe ignores those; re-tag with: git tag -a"
    fi
  done
fi

# --------------------------------------------------------- 2. 语法
step "2. syntax"
if [ -z "$PY" ]; then
  fail "no python on PATH — cannot check syntax"
else
  syntax_report="$("$PY" - <<'PYEOF' 2>&1
import ast, pathlib
bad = []
for p in sorted(pathlib.Path("coat_side").rglob("*.py")):
    try:
        ast.parse(p.read_text(encoding="utf-8"), str(p))
    except SyntaxError as e:
        bad.append(f"{p}:{e.lineno}: {e.msg}")
print("\n".join(bad))
PYEOF
)"
  [ -z "$syntax_report" ] && pass "all .py under coat_side/ parse" || fail "$syntax_report"
fi

# --------------------------------------------------------- 3. 扩展测试
if [ "$QUICK" -eq 1 ]; then
  step "3. tests  (skipped: --quick)"
else
  step "3. tests"
  echo
  if "$REPO/tests/run_tests.sh"; then
    pass "tests/run_tests.sh green"
  else
    fail "tests/run_tests.sh reported failures (see output above)"
  fi
fi

# --------------------------------------------------------- 4. 打包依赖
step "4. packaging prerequisites"
if [ -z "$PY" ]; then
  fail "no python on PATH — cannot check the packer"
else
  pack_report="$("$PY" - <<'PYEOF' 2>&1
import ast, pathlib
p = pathlib.Path("install/build_pack.py")
try:
    ast.parse(p.read_text(encoding="utf-8"), str(p))
except SyntaxError as e:
    print(f"{p}:{e.lineno}: {e.msg}")
PYEOF
)"
  [ -z "$pack_report" ] && pass "install/build_pack.py parses" || fail "$pack_report"
fi

# --------------------------------------------------------- 汇总
echo
if [ "$failed" -eq 0 ]; then
  echo "VERIFY PASSED — this tree is releasable"
else
  echo "VERIFY FAILED"
fi
exit "$failed"
