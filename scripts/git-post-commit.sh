#!/usr/bin/env bash
# Post-commit: auto-clean cruft files (.del/.bak/.old/.tmp/.orig) + empty dirs.
# Only removes UNTRACKED cruft — tracked files are intentional (e.g. test fixtures).
cruft_count=0
while IFS= read -r -d '' file; do
    # Skip files tracked by git
    git ls-files --error-unmatch "$file" >/dev/null 2>&1 && continue
    if command -v trash >/dev/null 2>&1; then
        trash "$file" 2>/dev/null
    else
        rm -f "$file" 2>/dev/null
    fi
    cruft_count=$((cruft_count + 1))
done < <(find . -not -path "./.git/*" -not -path "./.worktrees/*" -type f \
    \( -name "*.del" -o -name "*.bak" -o -name "*.old" -o -name "*.tmp" -o -name "*.orig" \) -print0 2>/dev/null)

[ "$cruft_count" -gt 0 ] && echo "post-commit: cleaned $cruft_count cruft file(s)"

# Clean empty directories (leaf-first via -depth)
find . -depth -type d -empty -not -path "./.git/*" -not -path "./.worktrees/*" -delete 2>/dev/null
true
