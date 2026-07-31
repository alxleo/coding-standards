# Semgrep test fixture for shell-hygiene.yml (semgrep --test convention:
# same basename as the rule file; annotated lines assert must-fire vs must-not).

# --- coding-standards.no-bare-python ---

# ruleid: coding-standards.no-bare-python
python3 scripts/generate.py

# ruleid: coding-standards.no-bare-python
result=$(python3 scripts/parse.py input.json)

# ruleid: coding-standards.no-bare-python
cat data.json | python scripts/transform.py

# ok: coding-standards.no-bare-python
uv run python3 scripts/generate.py

# ok: coding-standards.no-bare-python
count=$(sops -d "$f" 2>/dev/null | uv run python3 "$SCRIPT_DIR/convert.py" "$dir")

# ok: coding-standards.no-bare-python
# the user python and its bare interpreter has no yaml module

# ok: coding-standards.no-bare-python
# prefer uv over plain python3 for scripts

# ok: coding-standards.no-bare-python
python3 --version

# --- coding-standards.pin-npm-versions ---

# ruleid: coding-standards.pin-npm-versions
npx jscpd src/

# ok: coding-standards.pin-npm-versions
npx jscpd@4.0.8 src/
