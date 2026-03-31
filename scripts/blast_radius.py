#!/usr/bin/env python3
"""Repo change-impact analysis: blast radius, temporal coupling, criticality ranking.

Answers "how hard is it to make a correct change?" with four signals:

1. Blast radius: how many files reference this file's name?
2. Temporal coupling: which files always change together? (Jaccard, git history)
3. Naming entropy: how many naming conventions coexist per directory?
4. Criticality: CIRank (PageRank weighted by co-change frequency)

Usage:
  python3 scripts/blast_radius.py                        # full report
  python3 scripts/blast_radius.py --pr FILE [FILE ...]   # PR review mode
  python3 scripts/blast_radius.py --top 10               # top 10 blast radius
  python3 scripts/blast_radius.py --coupling             # temporal coupling
  python3 scripts/blast_radius.py --entropy              # naming entropy
  python3 scripts/blast_radius.py --rank                 # criticality ranking
  python3 scripts/blast_radius.py --file ruff.toml       # single file deep dive
  python3 scripts/blast_radius.py --json                 # machine-readable

References:
  Wang et al. (2014) "Network-Based Analysis of Software Change Propagation"
  Zimmermann et al. (2005) "Mining Version Histories to Guide Software Changes"
  CodeScene temporal coupling noise filters
  Aider repomap personalized PageRank
"""

from __future__ import annotations

import argparse
import json
import math
import re
import subprocess
import sys
from collections import Counter
from itertools import combinations
from pathlib import Path
from typing import Any

import networkx as nx

EXCLUDED_DIRS = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".ruff_cache",
    "megalinter-reports",
    ".claude",
}

SCANNABLE_EXTS = {
    ".py",
    ".yml",
    ".yaml",
    ".toml",
    ".json",
    ".sh",
    ".bash",
    ".mjs",
    ".js",
    ".ts",
    ".md",
    ".cfg",
    ".ini",
    ".conf",
}

SCANNABLE_NAMES = {"Dockerfile", "justfile", "Makefile", "Jenkinsfile"}

GENERIC_NAMES = {"__init__.py", ".gitignore", "README.md", "LICENSE", ".DS_Store"}

# Thresholds
MIN_DIR_FILES = 3  # minimum files per directory for entropy calculation
MIN_BLAST_RADIUS = 3  # minimum blast radius to flag in PR review
MAX_REFS_SHOWN = 5  # max referencing files shown in detail output


def _is_excluded(path: Path) -> bool:
    return any(part in EXCLUDED_DIRS for part in path.parts)


def _is_scannable(path: Path) -> bool:
    # nosemgrep: python-silent-fallback-or — boolean logic, not fallback
    return path.suffix in SCANNABLE_EXTS or path.name in SCANNABLE_NAMES


def _collect_files(root: Path) -> list[Path]:
    return [p for p in root.rglob("*") if p.is_file() and not _is_excluded(p.relative_to(root))]


# ── Signal 1: Blast Radius ──────────────────────────────────────────


def compute_blast_radius(root: Path) -> list[dict[str, Any]]:
    """For each file, count how many other files reference its name."""
    all_files = _collect_files(root)
    scannable = [f for f in all_files if _is_scannable(f)]

    file_contents: dict[Path, str] = {}
    for f in scannable:
        try:
            file_contents[f] = f.read_text(errors="replace")
        except OSError:
            continue

    results = []
    for target in all_files:
        name = target.name
        if name in GENERIC_NAMES:
            continue
        rel = str(target.relative_to(root))

        # Search for both the full relative path and the basename with word boundaries.
        # Word boundary prevents "test.py" matching inside "pytest.py".
        # Full path search distinguishes "scripts/config.toml" from "lib/config.toml".
        patterns = [re.escape(rel)]
        if "/" in rel:
            # Also match bare filename with word boundary (catches loose references)
            patterns.append(r"(?<![a-zA-Z0-9_/\-])" + re.escape(name) + r"(?![a-zA-Z0-9_\-])")
        else:
            patterns.append(r"(?<![a-zA-Z0-9_/\-])" + re.escape(name) + r"(?![a-zA-Z0-9_\-])")
        combined = "|".join(patterns)

        referencing = [
            str(s.relative_to(root))
            for s, content in file_contents.items()
            if s != target and re.search(combined, content)
        ]

        results.append(
            {
                "file": rel,
                "name": name,
                "blast_radius": len(referencing),
                "referencing_files": sorted(referencing),
            }
        )

    results.sort(key=lambda r: r["blast_radius"], reverse=True)
    return results


# ── Signal 2: Temporal Coupling ──────────────────────────────────────


def _parse_git_commits(
    root: Path, max_changeset: int = 50
) -> tuple[
    Counter[str],
    Counter[tuple[str, str]],
    list[set[str]],
]:
    """Parse git log into per-file change counts and co-change counts."""
    try:
        result = subprocess.run(
            ["git", "log", "--name-only", "--pretty=format:", "--no-merges"],
            capture_output=True,
            text=True,
            cwd=root,
            timeout=30,
            check=False,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return Counter(), Counter(), []

    commits: list[set[str]] = []
    current: set[str] = set()
    for raw_line in result.stdout.splitlines():
        line = raw_line.strip()
        if not line:
            if current:
                commits.append(current)
                current = set()
        elif not _is_excluded(Path(line)):
            current.add(line)
    if current:
        commits.append(current)

    file_changes: Counter[str] = Counter()
    co_changes: Counter[tuple[str, str]] = Counter()

    for commit_files in commits:
        if len(commit_files) > max_changeset:
            continue
        files = sorted(commit_files)
        for f in files:
            file_changes[f] += 1
        for a, b in combinations(files, 2):
            co_changes[(a, b)] += 1

    return file_changes, co_changes, commits


def compute_temporal_coupling(
    root: Path,
    min_co_changes: int = 3,
    min_coupling: float = 0.3,
    max_changeset: int = 50,
    min_revisions: int = 3,
) -> list[dict[str, Any]]:
    """From git history, find files that always change together.

    Uses Jaccard similarity (Zimmermann et al. 2005, CodeScene):
      coupling(A, B) = co_changes(A,B) / (changes(A) + changes(B) - co_changes(A,B))

    Noise filters (per CodeScene best practices):
      - Changesets > max_changeset files are skipped (mass refactors, formatting)
      - Files with < min_revisions total changes are skipped
      - Pairs with < min_co_changes shared commits are skipped
    """
    file_changes, co_changes, _ = _parse_git_commits(root, max_changeset)

    couplings = []
    for (a, b), co_count in co_changes.items():
        if co_count < min_co_changes:
            continue
        # nosemgrep: python-silent-fallback-or — boolean comparison, not fallback
        if file_changes[a] < min_revisions or file_changes[b] < min_revisions:
            continue
        union = file_changes[a] + file_changes[b] - co_count
        if union == 0:
            continue
        score = co_count / union
        if score >= min_coupling:
            couplings.append(
                {
                    "file_a": a,
                    "file_b": b,
                    "co_changes": co_count,
                    "changes_a": file_changes[a],
                    "changes_b": file_changes[b],
                    "coupling": round(score, 3),
                }
            )

    couplings.sort(key=lambda c: c["coupling"], reverse=True)
    return couplings


# ── Signal 3: Naming Entropy ────────────────────────────────────────


def _classify_name(name: str) -> str:
    stem = Path(name).stem
    stem = stem.removeprefix(".")
    if not stem:
        return "other"
    if "-" in stem and "_" not in stem:
        return "kebab-case"
    if "_" in stem and "-" not in stem:
        return "snake_case"
    if "-" in stem and "_" in stem:
        return "mixed"
    if len(stem) > 1 and stem[0].isupper() and any(c.isupper() for c in stem[1:]):
        return "PascalCase"
    if stem[0].islower() and any(c.isupper() for c in stem[1:]):
        return "camelCase"
    return "flat"


def _shannon_entropy(counts: Counter) -> float:
    total = sum(counts.values())
    if total == 0:
        return 0.0
    probs = [c / total for c in counts.values()]
    return -sum(p * math.log2(p) for p in probs if p > 0)


def compute_naming_entropy(root: Path) -> list[dict[str, Any]]:
    dirs: dict[str, list[str]] = {}
    for f in _collect_files(root):
        rel = f.relative_to(root)
        parent = str(rel.parent) if rel.parent != Path(".") else "."
        dirs.setdefault(parent, []).append(f.name)

    results = []
    for directory, names in sorted(dirs.items()):
        if len(names) < MIN_DIR_FILES:
            continue
        conventions = Counter(_classify_name(n) for n in names)
        ent = _shannon_entropy(conventions)
        results.append(
            {
                "directory": directory,
                "file_count": len(names),
                "conventions": dict(conventions.most_common()),
                "entropy": round(ent, 2),
            }
        )

    results.sort(key=lambda r: r["entropy"], reverse=True)
    return results


# ── Signal 4: CIRank (PageRank weighted by co-change) ──────────────


def _extract_python_imports(root: Path) -> list[tuple[str, str]]:
    """Extract Python import dependencies via stdlib ast.

    Returns (importer, imported_file) pairs for files within the repo.
    More precise than grep for .py files — resolves import statements
    to actual file paths.
    """
    import ast as ast_mod

    py_files = [f for f in _collect_files(root) if f.suffix == ".py" and not _is_excluded(f.relative_to(root))]

    # Build module name → file path mapping
    # Use dotted path as primary key to avoid stem collisions
    # (scripts/utils.py and lib/utils.py both have stem "utils")
    module_map: dict[str, str] = {}
    stem_map: dict[str, list[str]] = {}  # stem → [paths] for ambiguous resolution
    for f in py_files:
        rel = f.relative_to(root)
        # Dotted path: scripts.manifest_schema (unique, preferred)
        parts = [*list(rel.parent.parts), rel.stem]
        if parts[0] != ".":
            module_map[".".join(parts)] = str(rel)
        # Stem-only: manifest_schema (may collide — track all candidates)
        stem_map.setdefault(rel.stem, []).append(str(rel))

    # Only add unambiguous stems to module_map
    for stem, paths in stem_map.items():
        if len(paths) == 1 and stem not in module_map:
            module_map[stem] = paths[0]

    def _resolve_relative_import(
        node: ast_mod.ImportFrom, importer: str, importer_dir: Path,
    ) -> list[tuple[str, str]]:
        """Resolve `from . import foo` style imports."""
        rel_dir = importer_dir
        for _ in range(node.level - 1):
            rel_dir = rel_dir.parent
        found = []
        for alias in node.names:
            candidate = rel_dir / f"{alias.name}.py"
            if candidate.exists():
                target = str(candidate.relative_to(root))
                if target != importer:
                    found.append((importer, target))
        return found

    def _resolve_module(mod: str, importer: str) -> str | None:
        """Resolve a module name to a file path, or None."""
        for candidate in [mod, mod.rsplit(".", 1)[-1]]:
            if candidate in module_map and module_map[candidate] != importer:
                return module_map[candidate]
        return None

    edges: list[tuple[str, str]] = []
    for f in py_files:
        try:
            tree = ast_mod.parse(f.read_text(errors="replace"), filename=str(f))
        except SyntaxError:
            continue

        importer = str(f.relative_to(root))
        importer_dir = f.parent

        for node in ast_mod.walk(tree):
            if isinstance(node, ast_mod.Import):
                for alias in node.names:
                    resolved = _resolve_module(alias.name, importer)
                    if resolved:
                        edges.append((importer, resolved))
            elif isinstance(node, ast_mod.ImportFrom):
                if node.module:
                    resolved = _resolve_module(node.module, importer)
                    if resolved:
                        edges.append((importer, resolved))
                elif node.level and node.level > 0:
                    edges.extend(_resolve_relative_import(node, importer, importer_dir))

    return edges


def _build_dependency_graph(
    root: Path,
    max_changeset: int = 50,
) -> tuple[nx.DiGraph, list[str]]:
    """Build the combined dependency graph (structural + AST + temporal weights).

    Three edge sources:
    1. Filename grep (blast radius) — config-to-code references
    2. Python AST imports — precise code-to-code dependencies
    3. Co-change weights on all edges — temporal signal

    Returns (graph, all_node_names).
    """
    all_files = _collect_files(root)
    scannable = [f for f in all_files if _is_scannable(f)]

    file_contents: dict[str, str] = {}
    for f in scannable:
        try:
            file_contents[str(f.relative_to(root))] = f.read_text(errors="replace")
        except OSError:
            continue

    _, co_changes, _ = _parse_git_commits(root, max_changeset)

    g = nx.DiGraph()
    all_rel = [str(f.relative_to(root)) for f in all_files]
    g.add_nodes_from(all_rel)

    # Layer 1: filename grep edges (config-to-code)
    for target in all_files:
        name = target.name
        if name in GENERIC_NAMES:
            continue
        target_rel = str(target.relative_to(root))
        for scanner_rel, content in file_contents.items():
            if scanner_rel == target_rel:
                continue
            if re.search(re.escape(name), content):
                pair = tuple(sorted([scanner_rel, target_rel]))
                co_count = co_changes.get(pair, 0)
                weight = max(co_count, 1)
                g.add_edge(scanner_rel, target_rel, weight=weight)

    # Layer 2: Python AST import edges (code-to-code)
    for importer, imported in _extract_python_imports(root):
        if not g.has_edge(importer, imported):
            pair = tuple(sorted([importer, imported]))
            co_count = co_changes.get(pair, 0)
            g.add_edge(importer, imported, weight=max(co_count, 1), source="ast")

    return g, all_rel


def compute_criticality(root: Path, max_changeset: int = 50) -> list[dict[str, Any]]:
    """CIRank: PageRank on dependency graph weighted by co-change frequency.

    Wang et al. (2014) showed CIRank has the highest correlation (0.52-0.81)
    with actual change propagation scope.

    Graph: filename grep (configs) + Python AST imports (code) + co-change weights.
    """
    g, all_rel = _build_dependency_graph(root, max_changeset)

    if g.number_of_edges() == 0:
        return []

    try:
        scores = nx.pagerank(g, weight="weight", alpha=0.85, max_iter=100)
    except nx.PowerIterationFailedConvergence:
        scores = nx.pagerank(g, weight="weight", alpha=0.85, max_iter=500, tol=1e-4)

    return [
        {
            "file": f,
            "criticality": round(score, 6),
            "in_degree": g.in_degree(f),
            "out_degree": g.out_degree(f),
        }
        for f, score in sorted(scores.items(), key=lambda x: x[1], reverse=True)
        if score > 1.0 / len(all_rel)
    ]


# ── PR Review Mode ──────────────────────────────────────────────────


def _personalized_pagerank(
    g: nx.DiGraph,
    focus_files: list[str],
    all_nodes: list[str],
) -> dict[str, float]:
    """Personalized PageRank — ranks files by relevance to focus files.

    Aider (2023): personalized PageRank on the dependency graph gives
    context-aware ranking. Changed files get weight 100, others get 1.
    "Given I'm editing these files, what OTHER files matter most?"
    """
    if g.number_of_edges() == 0:
        return {}

    personalization = {}
    focus_set = set(focus_files)
    for node in all_nodes:
        personalization[node] = 100.0 if node in focus_set else 1.0

    try:
        scores = nx.pagerank(
            g,
            weight="weight",
            alpha=0.85,
            max_iter=100,
            personalization=personalization,
        )
    except nx.PowerIterationFailedConvergence:
        scores = nx.pagerank(
            g,
            weight="weight",
            alpha=0.85,
            max_iter=500,
            tol=1e-4,
            personalization=personalization,
        )

    return scores


def pr_review(root: Path, changed_files: list[str]) -> dict[str, Any]:
    """Given changed files, report what else needs attention.

    Uses personalized PageRank (Aider-style): ranks ALL files by
    relevance to the changed files, not just static importance.

    Output for a PR reviewer:
    - High blast radius files in the change
    - Files temporally coupled but NOT in the PR
    - Context-aware ranking of files most relevant to this change
    """
    radius_data = compute_blast_radius(root)
    radius_map = {r["file"]: r for r in radius_data}

    coupling_data = compute_temporal_coupling(root, min_co_changes=2, min_coupling=0.2)

    # Personalized PageRank: "given these changed files, what else matters?"
    g, all_rel = _build_dependency_graph(root)
    pr_scores = _personalized_pagerank(g, changed_files, all_rel)
    crit_map = pr_scores  # context-aware, not static

    # Files with high blast radius that were changed
    high_risk = []
    for f in changed_files:
        entry = radius_map.get(f)
        if entry and entry["blast_radius"] >= MIN_BLAST_RADIUS:
            high_risk.append(
                {
                    "file": f,
                    "blast_radius": entry["blast_radius"],
                    "referencing_files": entry["referencing_files"],
                    "criticality": crit_map.get(f, 0),
                }
            )

    # Files NOT in the PR that are temporally coupled to changed files
    missing_files = []
    changed_set = set(changed_files)
    for c in coupling_data:
        if c["file_a"] in changed_set and c["file_b"] not in changed_set:
            missing_files.append(
                {
                    "missing": c["file_b"],
                    "coupled_to": c["file_a"],
                    "coupling": c["coupling"],
                    "co_changes": c["co_changes"],
                }
            )
        elif c["file_b"] in changed_set and c["file_a"] not in changed_set:
            missing_files.append(
                {
                    "missing": c["file_a"],
                    "coupled_to": c["file_b"],
                    "coupling": c["coupling"],
                    "co_changes": c["co_changes"],
                }
            )

    # Personalized PageRank: top files NOT in the PR ranked by relevance
    relevant_outside = [
        {"file": f, "relevance": round(score, 6)}
        for f, score in sorted(pr_scores.items(), key=lambda x: x[1], reverse=True)
        if f not in changed_set and score > 0
    ][:10]

    return {
        "changed_files": changed_files,
        "high_blast_radius": high_risk,
        "possibly_missing": missing_files,
        "most_relevant_outside_pr": relevant_outside,
        "summary": {
            "total_blast_radius": sum(radius_map.get(f, {}).get("blast_radius", 0) for f in changed_files),
            "files_at_risk": len(high_risk),
            "possibly_missing_count": len(missing_files),
        },
    }


# ── Output ──────────────────────────────────────────────────────────


def print_blast_radius(results: list[dict], top: int | None = None) -> None:
    results = [r for r in results if r["blast_radius"] >= 1]
    if top:
        results = results[:top]
    if not results:
        print("No files with blast radius >= 1")
        return

    max_name = max(len(r["name"]) for r in results)
    max_file = min(max(len(r["file"]) for r in results), 55)

    print(f"\n{'File':<{max_file}}  {'Name':<{max_name}}  Radius  Top references")
    print(f"{'─' * max_file}  {'─' * max_name}  ──────  ──────────────")

    for r in results:
        refs = ", ".join(r["referencing_files"][:MIN_BLAST_RADIUS])
        extra = (
            f" +{len(r['referencing_files']) - MIN_BLAST_RADIUS}"
            if len(r["referencing_files"]) > MIN_BLAST_RADIUS
            else ""
        )
        file_col = f"{r['file'][:max_file]:<{max_file}}"
        name_col = f"{r['name']:<{max_name}}"
        print(f"{file_col}  {name_col}  {r['blast_radius']:>6}  {refs}{extra}")

    total = sum(r["blast_radius"] for r in results)
    print(f"\nTotal: {total} references across {len(results)} files")


def print_coupling(couplings: list[dict]) -> None:
    if not couplings:
        print("\nNo temporal coupling found (min 3 co-changes, min 0.3 Jaccard)")
        return

    print(f"\n{'File A':<45}  {'File B':<45}  Co-chg  Jaccard")
    print(f"{'─' * 45}  {'─' * 45}  ──────  ───────")

    for c in couplings[:20]:
        print(f"{c['file_a'][:45]:<45}  {c['file_b'][:45]:<45}  {c['co_changes']:>6}  {c['coupling']:>7.1%}")


def print_entropy(entries: list[dict]) -> None:
    if not entries:
        print("\nNo directories with 3+ files")
        return

    print(f"\n{'Directory':<40}  Files  Entropy  Conventions")
    print(f"{'─' * 40}  ─────  ───────  ───────────")

    for e in entries:
        convs = ", ".join(f"{k}:{v}" for k, v in e["conventions"].items())
        d = f"{e['directory'][:40]:<40}"
        print(f"{d}  {e['file_count']:>5}  {e['entropy']:>7.2f}  {convs}")


def print_criticality(ranked: list[dict], top: int = 20) -> None:
    if not ranked:
        print("\nNo criticality data (empty graph)")
        return

    print(f"\n{'File':<55}  CIRank    In  Out")
    print(f"{'─' * 55}  ────────  ──  ───")

    for r in ranked[:top]:
        print(f"{r['file'][:55]:<55}  {r['criticality']:>8.4f}  {r['in_degree']:>2}  {r['out_degree']:>3}")


def print_pr_review(review: dict[str, Any]) -> None:
    print(f"\n── PR Change Impact Analysis ({'─' * 40})")
    print(f"Changed files: {len(review['changed_files'])}")
    print(f"Total blast radius: {review['summary']['total_blast_radius']}")

    if review["high_blast_radius"]:
        print("\nHigh blast radius files (>= 3 references):")
        for h in review["high_blast_radius"]:
            crit = f" (criticality: {h['criticality']:.4f})" if h["criticality"] else ""
            print(f"  {h['file']} — {h['blast_radius']} refs{crit}")
            for ref in h["referencing_files"][:MAX_REFS_SHOWN]:
                print(f"    ← {ref}")
            if len(h["referencing_files"]) > MAX_REFS_SHOWN:
                print(f"    ... +{len(h['referencing_files']) - MAX_REFS_SHOWN} more")

    if review["possibly_missing"]:
        print("\nFiles NOT in PR that usually change with these files:")
        for m in review["possibly_missing"]:
            print(f"  {m['missing']} ↔ {m['coupled_to']} ({m['coupling']:.0%} coupling, {m['co_changes']} co-changes)")
    else:
        print("\nNo missing coupled files detected.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Repo change-impact analysis",
    )
    parser.add_argument("--top", type=int, help="Show top N files")
    parser.add_argument("--file", help="Deep dive on a specific file")
    parser.add_argument("--pr", nargs="+", metavar="FILE", help="PR review mode: list changed files")
    parser.add_argument("--coupling", action="store_true", help="Show temporal coupling")
    parser.add_argument("--entropy", action="store_true", help="Show naming entropy")
    parser.add_argument("--rank", action="store_true", help="Show CIRank criticality")
    parser.add_argument("--json", action="store_true", help="JSON output (all signals)")
    parser.add_argument("--min-coupling", type=float, default=0.3)
    parser.add_argument("--min-co-changes", type=int, default=3)
    args = parser.parse_args()

    root = Path(__file__).resolve().parent.parent

    if args.json:
        data = {
            "blast_radius": compute_blast_radius(root),
            "temporal_coupling": compute_temporal_coupling(
                root,
                args.min_co_changes,
                args.min_coupling,
            ),
            "naming_entropy": compute_naming_entropy(root),
            "criticality": compute_criticality(root),
        }
        json.dump(data, sys.stdout, indent=2)
        print()
        return

    if args.pr:
        review = pr_review(root, args.pr)
        if "--json" in sys.argv:
            json.dump(review, sys.stdout, indent=2)
        else:
            print_pr_review(review)
        return

    if args.file:
        radius = compute_blast_radius(root)
        matches = [r for r in radius if any((args.file in r["file"], args.file == r["name"]))]
        for m in matches:
            print(f"\n{m['file']} (blast radius: {m['blast_radius']})")
            for ref in m["referencing_files"]:
                print(f"  ← {ref}")

        coupling = compute_temporal_coupling(root, args.min_co_changes, args.min_coupling)
        file_couplings = [c for c in coupling if any((args.file in c["file_a"], args.file in c["file_b"]))]
        if file_couplings:
            print("\nTemporal coupling:")
            for c in file_couplings:
                other = c["file_b"] if args.file in c["file_a"] else c["file_a"]
                print(f"  ↔ {other} ({c['coupling']:.0%}, {c['co_changes']} co-changes)")

        crit = compute_criticality(root)
        file_crit = [r for r in crit if args.file in r["file"]]
        if file_crit:
            c = file_crit[0]
            print(f"\nCriticality: {c['criticality']:.6f} (in:{c['in_degree']} out:{c['out_degree']})")
        return

    if args.coupling:
        print_coupling(compute_temporal_coupling(root, args.min_co_changes, args.min_coupling))
        return

    if args.entropy:
        print_entropy(compute_naming_entropy(root))
        return

    if args.rank:
        top_rank = args.top if args.top else 20
        print_criticality(compute_criticality(root), top_rank)
        return

    # Default: all four signals
    top_radius = args.top if args.top else 15
    print_blast_radius(compute_blast_radius(root), top_radius)
    print_coupling(compute_temporal_coupling(root, args.min_co_changes, args.min_coupling))
    print_entropy(compute_naming_entropy(root))
    print_criticality(compute_criticality(root), 10)


if __name__ == "__main__":
    main()
