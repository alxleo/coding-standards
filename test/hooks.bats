#!/usr/bin/env bats
# Tests for scripts/hooks/shell-hygiene (merged hook)

HOOK=scripts/hooks/shell-hygiene

setup() {
  WORKDIR=$(mktemp -d)
}

teardown() {
  rm -rf "$WORKDIR"
}

# ── Check 1: forbid bare python/python3 ───────────────

@test "rejects bare python3" {
  echo 'python3 script.py' > "$WORKDIR/test.sh"
  run "$HOOK" "$WORKDIR/test.sh"
  [ "$status" -eq 1 ]
}

@test "rejects bare python" {
  echo 'python script.py' > "$WORKDIR/test.sh"
  run "$HOOK" "$WORKDIR/test.sh"
  [ "$status" -eq 1 ]
}

@test "allows uv run python3" {
  echo 'uv run python3 script.py' > "$WORKDIR/test.sh"
  run "$HOOK" "$WORKDIR/test.sh"
  [ "$status" -eq 0 ]
}

@test "allows uv run --no-project python3" {
  echo 'uv run --no-project python3 -c "print(1)"' > "$WORKDIR/test.sh"
  run "$HOOK" "$WORKDIR/test.sh"
  [ "$status" -eq 0 ]
}

@test "allows pythonic (embedded word)" {
  echo 'echo "pythonic code"' > "$WORKDIR/test.sh"
  run "$HOOK" "$WORKDIR/test.sh"
  [ "$status" -eq 0 ]
}

# ── Check 2: mktemp needs trap ────────────────────────

@test "rejects mktemp without trap" {
  cat > "$WORKDIR/test.sh" <<'SH'
#!/usr/bin/env bash
TMPFILE=$(mktemp)
echo "hello" > "$TMPFILE"
SH
  run "$HOOK" "$WORKDIR/test.sh"
  [ "$status" -eq 1 ]
  [[ "$output" == *"mktemp without trap"* ]]
}

@test "allows mktemp with trap" {
  cat > "$WORKDIR/test.sh" <<'SH'
#!/usr/bin/env bash
TMPFILE=$(mktemp)
trap 'rm -f "$TMPFILE"' EXIT
echo "hello" > "$TMPFILE"
SH
  run "$HOOK" "$WORKDIR/test.sh"
  [ "$status" -eq 0 ]
}

@test "allows scripts without mktemp" {
  echo 'echo "no temp files"' > "$WORKDIR/test.sh"
  run "$HOOK" "$WORKDIR/test.sh"
  [ "$status" -eq 0 ]
}

# ── Check 3: pinned npx versions ─────────────────────

@test "rejects unpinned npx" {
  echo 'npx eslint .' > "$WORKDIR/test.sh"
  run "$HOOK" "$WORKDIR/test.sh"
  [ "$status" -eq 1 ]
}

@test "allows pinned npx with @version" {
  echo 'npx eslint@8 .' > "$WORKDIR/test.sh"
  run "$HOOK" "$WORKDIR/test.sh"
  [ "$status" -eq 0 ]
}

@test "allows npx --yes" {
  echo 'npx --yes eslint .' > "$WORKDIR/test.sh"
  run "$HOOK" "$WORKDIR/test.sh"
  [ "$status" -eq 0 ]
}

@test "allows npx with flags" {
  echo 'npx -p eslint' > "$WORKDIR/test.sh"
  run "$HOOK" "$WORKDIR/test.sh"
  [ "$status" -eq 0 ]
}

# ── Multiple violations ──────────────────────────────

@test "reports all violations in one file" {
  cat > "$WORKDIR/test.sh" <<'SH'
#!/usr/bin/env bash
TMPFILE=$(mktemp)
python3 script.py
npx eslint .
SH
  run "$HOOK" "$WORKDIR/test.sh"
  [ "$status" -eq 1 ]
  [[ "$output" == *"python3"* ]]
  [[ "$output" == *"mktemp without trap"* ]]
  [[ "$output" == *"npx eslint"* ]]
}

@test "no files to check" {
  run "$HOOK"
  [ "$status" -eq 0 ]
}
