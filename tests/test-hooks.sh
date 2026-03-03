# Negative tests for pre-commit hooks.
# Each hook MUST catch its intentionally-bad fixture.
# Two test modes:
#   assert_hook_catches  — hook must exit non-zero (reporting hooks)
#   assert_hook_fixes    — hook must modify the file (auto-fix hooks that exit 0)
set -uo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FIXTURES="$REPO_ROOT/tests/fixtures"

# Generate a test config without the global exclude line.
# The production config excludes tests/fixtures/ so the normal lint run
# ignores them, but we need pre-commit to process them for negative tests.
WORKDIR=$(mktemp -d)
trap 'rm -rf "$WORKDIR"' EXIT
CONFIG="$WORKDIR/.pre-commit-config.yaml"
# Strip the top-level exclude (so hooks can see test files) and any
# hook-level exclude on tests/fixtures/ (so forbid-cruft-files catches them).
grep -v '^exclude:' "$REPO_ROOT/configs/.pre-commit-config.yaml" \
    | grep -v '^\s*exclude: \^tests/fixtures/' > "$CONFIG"

PASSED=0
FAILED=0

# For reporting hooks: must exit non-zero.
assert_hook_catches() {
    local hook_id="$1"; shift
    printf "  %-45s " "$hook_id"

    local files=()
    for f in "$@"; do
        if [[ "$f" == "$WORKDIR"/* ]]; then
            files+=("$f")
        else
            local tmp_f="$WORKDIR/$(basename "$f")"
            cp "$f" "$tmp_f"
            [ -x "$f" ] && chmod +x "$tmp_f"
            files+=("$tmp_f")
        fi
    done

    if uvx pre-commit run "$hook_id" --config "$CONFIG" --files "${files[@]}" >/dev/null 2>&1; then
        echo "FAIL (hook passed — should have caught violation)"
        FAILED=$((FAILED + 1))
    else
        echo "OK"
        PASSED=$((PASSED + 1))
    fi
}

# For auto-fix hooks: must modify the file (they exit 0 after fixing).
assert_hook_fixes() {
    local hook_id="$1"; shift
    local content="$1"; shift
    local filename="$1"
    printf "  %-45s " "$hook_id"

    local target="$WORKDIR/$filename"
    printf '%b' "$content" > "$target"
    local before
    before=$(md5sum "$target" | cut -d' ' -f1)

    uvx pre-commit run "$hook_id" --config "$CONFIG" --files "$target" >/dev/null 2>&1 || true

    local after
    after=$(md5sum "$target" | cut -d' ' -f1)

    if [ "$before" != "$after" ]; then
        echo "OK"
        PASSED=$((PASSED + 1))
    else
        echo "FAIL (hook did not modify file — violation not detected)"
        FAILED=$((FAILED + 1))
    fi
}

assert_tool_catches() {
    local name="$1"; shift
    printf "  %-45s " "$name"
    if "$@" >/dev/null 2>&1; then
        echo "FAIL (tool passed — should have caught violation)"
        FAILED=$((FAILED + 1))
    else
        echo "OK"
        PASSED=$((PASSED + 1))
    fi
}

echo "=== Negative tests: each hook must catch its fixture ==="
echo ""

# ── Standard hygiene (reporting hooks — exit non-zero) ───
echo "Pre-commit hooks (reporting — must exit non-zero):"
assert_hook_catches check-yaml                      "$FIXTURES/check-yaml.bad.yaml"
assert_hook_catches check-json                      "$FIXTURES/check-json.bad.json"
assert_hook_catches check-toml                      "$FIXTURES/check-toml.bad.toml"
assert_hook_catches detect-private-key              "$FIXTURES/detect-private-key.bad.txt"
assert_hook_catches check-executables-have-shebangs "$FIXTURES/check-executables-have-shebangs.bad.sh"
assert_hook_catches markdownlint-cli2               "$FIXTURES/markdownlint-cli2.bad.md"

# ── Auto-fix hooks (must modify file) ───────────────────
# These can't be committed as fixtures — the very hooks we test would
# fix them. Content is generated fresh, then we check if the hook changed it.
echo ""
echo "Pre-commit hooks (auto-fix — must modify file):"
assert_hook_fixes end-of-file-fixer   'no newline at end'                            end-of-file-fixer.bad.txt
assert_hook_fixes trailing-whitespace "trailing spaces   \n"                         trailing-whitespace.bad.txt
assert_hook_fixes typos               "This is a sentance with a teh typo.\n"        typos.bad.txt
assert_hook_fixes ruff                "import os\nimport sys\n\nx = 1\n"             ruff.bad.py
assert_hook_fixes ruff-format         "x = {   \"a\":1,    \"b\":2,\n\"c\":3}\n"    ruff-format.bad.py

# ── Local: filename-pattern hooks (language: fail) ──────
echo ""
echo "Pre-commit hooks (local):"
assert_hook_catches forbid-cruft-files              "$FIXTURES/forbid-cruft-files.bad.bak"
assert_hook_catches block-secret-files              "$FIXTURES/block-secret-files.bad.env"
assert_hook_catches verify-sops-encryption          "$FIXTURES/verify-sops-encryption.bad.secrets.yaml"
assert_hook_catches pin-npm-versions                "$FIXTURES/pin-npm-versions.bad.sh"
assert_hook_catches temp-file-needs-trap            "$FIXTURES/temp-file-needs-trap.bad.sh"
assert_hook_catches forbid-bare-python              "$FIXTURES/forbid-bare-python.bad.sh"

# ── Direct tool invocations ─────────────────────────────
# These hooks have files: patterns (^\.github/workflows/) that won't
# match fixture paths, or require git staging. Test tools directly.
echo ""
echo "Direct tool tests (hooks with path filters):"

# gitleaks: needs --no-git --source with an isolated directory
GITLEAKS_DIR=$(mktemp -d)
cp "$FIXTURES/gitleaks.bad.txt" "$GITLEAKS_DIR/"
assert_tool_catches gitleaks    gitleaks detect --no-git --source "$GITLEAKS_DIR" --no-banner
rm -rf "$GITLEAKS_DIR"

assert_tool_catches actionlint  actionlint "$FIXTURES/actionlint.bad.yml"
assert_tool_catches zizmor      zizmor --no-progress "$FIXTURES/zizmor.bad.yml"

echo ""
echo "=== Results: $PASSED passed, $FAILED failed ==="
[ "$FAILED" -eq 0 ] || exit 1
