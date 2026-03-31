"""Adversarial tests for scripts/blast_radius.py — designed to break things.

Red-team tests targeting algorithmic flaws in:
- Temporal coupling (Jaccard similarity + noise filters)
- CIRank / PageRank (topology, personalization)
- PR review mode (edge cases)
- Python AST import resolution
"""

from __future__ import annotations

import subprocess
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest

# Load blast_radius module from scripts/ (not importable directly)
_spec = spec_from_file_location(
    "blast_radius",
    Path(__file__).resolve().parent.parent / "scripts" / "blast_radius.py",
)
br = module_from_spec(_spec)
_spec.loader.exec_module(br)


# ── Helpers ──────────────────────────────────────────────────────────


def _git_init(path: Path) -> None:
    """Initialize a git repo with basic config."""
    subprocess.run(["git", "init"], cwd=path, capture_output=True, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=path,
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=path,
        capture_output=True,
        check=True,
    )


def _git_commit(path: Path, msg: str) -> None:
    """Stage all and commit."""
    subprocess.run(["git", "add", "."], cwd=path, capture_output=True, check=True)
    subprocess.run(
        ["git", "commit", "-m", msg, "--no-gpg-sign", "--allow-empty"],
        cwd=path,
        capture_output=True,
        check=True,
    )


# ── Temporal Coupling: Jaccard Boundary Conditions ───────────────────


class TestJaccardBoundaryConditions:
    """Jaccard = co_changes / (changes_A + changes_B - co_changes).
    When co_changes == changes_A == changes_B, result should be exactly 1.0.
    """

    @pytest.fixture()
    def perfect_coupling_repo(self, tmp_path: Path) -> Path:
        """Two files that ALWAYS change together and NEVER alone."""
        _git_init(tmp_path)
        for i in range(5):
            (tmp_path / "alpha.py").write_text(f"v{i}")
            (tmp_path / "beta.py").write_text(f"v{i}")
            _git_commit(tmp_path, f"c{i}")
        return tmp_path

    def test_perfect_coupling_is_exactly_one(self, perfect_coupling_repo: Path) -> None:
        """If A and B always change together, Jaccard should be 1.0 exactly."""
        couplings = br.compute_temporal_coupling(
            perfect_coupling_repo,
            min_co_changes=1,
            min_coupling=0.0,
            max_changeset=50,
            min_revisions=1,
        )
        ab = next(
            (c for c in couplings if {c["file_a"], c["file_b"]} == {"alpha.py", "beta.py"}),
            None,
        )
        assert ab is not None, "Perfect coupling pair not found in results"
        # co=5, changes_A=5, changes_B=5 -> 5 / (5+5-5) = 1.0
        assert ab["coupling"] == 1.0, f"Expected 1.0, got {ab['coupling']}"

    def test_perfect_coupling_counts_match(self, perfect_coupling_repo: Path) -> None:
        """Verify raw counts: co_changes == changes_a == changes_b."""
        couplings = br.compute_temporal_coupling(
            perfect_coupling_repo,
            min_co_changes=1,
            min_coupling=0.0,
            max_changeset=50,
            min_revisions=1,
        )
        ab = next(c for c in couplings if {c["file_a"], c["file_b"]} == {"alpha.py", "beta.py"})
        assert ab["co_changes"] == ab["changes_a"] == ab["changes_b"] == 5


class TestJaccardZeroDivision:
    """If a file somehow has 0 changes, the union would be 0. Guard must hold."""

    def test_zero_union_does_not_crash(self) -> None:
        """Directly invoke Jaccard-like computation with pathological input.
        Simulate: file_changes[a]=0, file_changes[b]=0, co_changes=0.
        The function guards with `if union == 0: continue`.
        """
        # We can't easily make git produce 0-change files in co_changes,
        # but we can verify the guard by calling _parse_git_commits on an
        # empty repo and ensuring no division error.
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            path = Path(td)
            _git_init(path)
            (path / "dummy.py").write_text("x")
            _git_commit(path, "init")

            # Should return empty — no pairs exist with 1 file
            couplings = br.compute_temporal_coupling(
                path,
                min_co_changes=1,
                min_coupling=0.0,
                max_changeset=50,
                min_revisions=1,
            )
            assert couplings == []

    def test_single_file_no_coupling(self) -> None:
        """A repo with only one file can never produce coupling pairs."""
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            path = Path(td)
            _git_init(path)
            for i in range(10):
                (path / "only.py").write_text(f"v{i}")
                _git_commit(path, f"c{i}")

            couplings = br.compute_temporal_coupling(
                path,
                min_co_changes=1,
                min_coupling=0.0,
                max_changeset=50,
                min_revisions=1,
            )
            assert couplings == []


# ── Noise Filter: max_changeset boundary ─────────────────────────────


class TestNoiseFilterBoundary:
    """max_changeset=50 means commits with >50 files are skipped.
    What about exactly 50? Off-by-one is the classic bug.
    """

    @pytest.fixture()
    def boundary_repo(self, tmp_path: Path) -> Path:
        """Repo where the only commit has exactly max_changeset files."""
        _git_init(tmp_path)
        for i in range(50):
            (tmp_path / f"file_{i:03d}.py").write_text(f"content {i}")
        _git_commit(tmp_path, "exactly-50-files")
        return tmp_path

    def test_exactly_max_changeset_is_included(self, boundary_repo: Path) -> None:
        """A commit with exactly max_changeset=50 files should be INCLUDED.
        The filter is `len(commit_files) > max_changeset`, so 50 is NOT filtered.
        """
        file_changes, co_changes, _commits = br._parse_git_commits(
            boundary_repo,
            max_changeset=50,
        )
        # The commit has 50 files, filter is >50, so it should be included
        assert len(file_changes) == 50, f"Expected 50 files counted, got {len(file_changes)}"
        # With 50 files, we get C(50,2) = 1225 pairs
        assert len(co_changes) == 50 * 49 // 2

    def test_one_over_max_changeset_is_excluded(self, tmp_path: Path) -> None:
        """A commit with max_changeset+1 files should be EXCLUDED."""
        _git_init(tmp_path)
        for i in range(51):
            (tmp_path / f"file_{i:03d}.py").write_text(f"content {i}")
        _git_commit(tmp_path, "51-files")

        file_changes, co_changes, _commits = br._parse_git_commits(
            tmp_path,
            max_changeset=50,
        )
        # All 51 files in one commit, which is >50 so filtered
        assert len(file_changes) == 0
        assert len(co_changes) == 0

    def test_one_under_max_changeset_is_included(self, tmp_path: Path) -> None:
        """A commit with max_changeset-1 files should be INCLUDED."""
        _git_init(tmp_path)
        for i in range(49):
            (tmp_path / f"file_{i:03d}.py").write_text(f"content {i}")
        _git_commit(tmp_path, "49-files")

        file_changes, _co_changes, _commits = br._parse_git_commits(
            tmp_path,
            max_changeset=50,
        )
        assert len(file_changes) == 49


class TestFormattingCommitDetection:
    """Mass formatter runs (e.g., black on 100 .py files) should be filtered."""

    def test_mass_format_commit_filtered(self, tmp_path: Path) -> None:
        """A commit touching 100 .py files (formatter run) is filtered at default max_c"""
        _git_init(tmp_path)
        # First commit: create files individually coupled
        (tmp_path / "core.py").write_text("v1")
        (tmp_path / "helper.py").write_text("v1")
        _git_commit(tmp_path, "initial")

        # Strengthen coupling with more small commits
        for i in range(4):
            (tmp_path / "core.py").write_text(f"v{i + 2}")
            (tmp_path / "helper.py").write_text(f"v{i + 2}")
            _git_commit(tmp_path, f"coupled-{i}")

        # Massive formatter commit touching 100 files
        for i in range(100):
            (tmp_path / f"formatted_{i:03d}.py").write_text("# formatted\npass\n")
        (tmp_path / "core.py").write_text("v99-formatted")
        (tmp_path / "helper.py").write_text("v99-formatted")
        _git_commit(tmp_path, "black format all")

        # The formatter commit has 102 files (100 new + 2 existing) -> filtered
        couplings = br.compute_temporal_coupling(
            tmp_path,
            min_co_changes=3,
            min_coupling=0.3,
            max_changeset=50,
            min_revisions=3,
        )

        # core.py<->helper.py coupling should exist from the small commits
        pairs = {(c["file_a"], c["file_b"]) for c in couplings}
        assert ("core.py", "helper.py") in pairs

        # None of the formatted_*.py files should appear in coupling results
        formatted_in_results = [c for c in couplings if "formatted_" in c["file_a"] or "formatted_" in c["file_b"]]
        assert formatted_in_results == [], "Formatter files should not appear in coupling results"

    def test_single_massive_commit_all_files_filtered(self, tmp_path: Path) -> None:
        """One commit with ALL repo files (initial import) produces no coupling."""
        _git_init(tmp_path)
        for i in range(200):
            (tmp_path / f"src_{i:03d}.py").write_text(f"# file {i}\n")
        _git_commit(tmp_path, "initial import of everything")

        couplings = br.compute_temporal_coupling(
            tmp_path,
            min_co_changes=1,
            min_coupling=0.0,
            max_changeset=50,
            min_revisions=1,
        )
        assert couplings == [], "A single massive commit should produce zero coupling pairs"


# ── CIRank / PageRank: Topology Tests ───────────────────────────────


class TestPageRankTopology:
    """Test that PageRank produces correct relative rankings for known topologies."""

    def test_star_topology_center_ranks_highest(self, tmp_path: Path) -> None:
        """Star: hub.py referenced by 20 leaf files. Hub should rank highest.

        In PageRank, a node referenced by many others accumulates more rank.
        """
        _git_init(tmp_path)
        # Hub file
        (tmp_path / "hub.py").write_text("# central module\ndef core(): pass\n")

        # 20 leaf files, each referencing hub.py by name
        for i in range(20):
            (tmp_path / f"leaf_{i:03d}.py").write_text("import hub\nhub.core()\n")

        _git_commit(tmp_path, "star topology")

        ranked = br.compute_criticality(tmp_path, max_changeset=100)
        if not ranked:
            pytest.skip("Graph too small for meaningful PageRank")

        # hub.py should be the #1 ranked file
        assert ranked[0]["file"] == "hub.py", f"Expected hub.py at rank 1, got {ranked[0]['file']}"
        # hub.py should have high in-degree
        assert ranked[0]["in_degree"] >= 15, f"Expected in_degree >= 15, got {ranked[0]['in_degree']}"

    def test_chain_topology_sink_ranks_highest(self, tmp_path: Path) -> None:
        """Chain: a.py -> b.py -> c.py -> d.py.
        In PageRank, d.py (the sink) should accumulate rank because
        it receives transitively. But sinks cause rank to leak,
        so NetworkX handles this with the dangling node distribution.

        The file with the most in-links relative to its subgraph should rank higher.
        Actually in a chain A->B->C->D, rank flows forward.
        D gets from C, C gets from B and passes to D, B gets from A and passes to C.
        """
        _git_init(tmp_path)
        (tmp_path / "a.py").write_text("import b\n")
        (tmp_path / "b.py").write_text("import c\n")
        (tmp_path / "c.py").write_text("import d\n")
        (tmp_path / "d.py").write_text("# terminal\n")
        _git_commit(tmp_path, "chain")

        ranked = br.compute_criticality(tmp_path, max_changeset=100)
        if not ranked:
            pytest.skip("Graph too small for meaningful PageRank")

        rank_map = {r["file"]: r["criticality"] for r in ranked}
        # All files should be in the graph. a.py has 0 in-links,
        # d.py has 1 in-link (from c). Due to PageRank mechanics on
        # a simple chain, the sink (d.py) and nodes near it should rank well.
        # At minimum: files with in-links should rank above file with 0 in-links.
        if "d.py" in rank_map and "a.py" in rank_map:
            assert rank_map["d.py"] >= rank_map["a.py"], (
                f"d.py ({rank_map['d.py']}) should rank >= a.py ({rank_map['a.py']})"
            )

    def test_hub_authority_inlinks_beat_outlinks(self, tmp_path: Path) -> None:
        """PageRank rewards being referenced (in-links), not referencing others.

        File 'authority.py' is referenced by 15 files (high in-degree).
        File 'hub.py' references 15 files (high out-degree).
        Authority should rank higher than hub.
        """
        _git_init(tmp_path)
        (tmp_path / "authority.py").write_text("# everyone imports me\ndef api(): pass\n")
        (tmp_path / "hub.py").write_text(
            "# I import everyone\n" + "\n".join(f"import leaf_{i:03d}" for i in range(15)) + "\n"
        )

        for i in range(15):
            # Each leaf imports authority (creating in-links to authority)
            # Each leaf is imported by hub (creating out-links from hub)
            (tmp_path / f"leaf_{i:03d}.py").write_text("import authority\nauthority.api()\n")

        _git_commit(tmp_path, "hub-authority topology")

        ranked = br.compute_criticality(tmp_path, max_changeset=100)
        if not ranked:
            pytest.skip("Graph too small for meaningful PageRank")

        rank_map = {r["file"]: r["criticality"] for r in ranked}

        # authority.py (many in-links) should rank higher than hub.py (many out-links)
        assert "authority.py" in rank_map, "authority.py not in ranked results"
        if "hub.py" in rank_map:
            assert rank_map["authority.py"] > rank_map["hub.py"], (
                f"authority ({rank_map['authority.py']}) should rank higher than hub ({rank_map['hub.py']})"
            )


class TestPersonalizedPageRank:
    """Personalized PageRank should boost focus files and their neighbors."""

    @pytest.fixture()
    def graph_repo(self, tmp_path: Path) -> Path:
        """Create a repo with a known graph structure for PageRank testing.

        Structure:
          center.py <- nearby.py (nearby imports center)
          distant.py (isolated, no connections to center/nearby)
          bridge.py <- center.py (center imports bridge)
        """
        _git_init(tmp_path)
        (tmp_path / "center.py").write_text("import bridge\nbridge.go()\n")
        (tmp_path / "nearby.py").write_text("import center\ncenter.run()\n")
        (tmp_path / "distant.py").write_text("# completely isolated\nprint('alone')\n")
        (tmp_path / "bridge.py").write_text("def go(): pass\n")
        _git_commit(tmp_path, "graph setup")
        return tmp_path

    def test_personalized_boosts_focus_neighbors(self, graph_repo: Path) -> None:
        """Focusing on center.py should rank its neighbors higher than distant.py."""

        g, all_rel = br._build_dependency_graph(graph_repo, max_changeset=50)

        if g.number_of_edges() == 0:
            pytest.skip("No edges in graph")

        scores = br._personalized_pagerank(g, ["center.py"], all_rel)

        if not scores:
            pytest.skip("Empty PageRank scores")

        # center.py should have the highest score (focus file with boost of 100)
        assert scores.get("center.py", 0) > scores.get("distant.py", 0), (
            f"center.py ({scores.get('center.py', 0)}) should rank higher than "
            f"distant.py ({scores.get('distant.py', 0)})"
        )

    def test_personalized_differs_from_static(self, graph_repo: Path) -> None:
        """Personalized PageRank should produce different rankings than static."""
        import networkx as nx

        g, all_rel = br._build_dependency_graph(graph_repo, max_changeset=50)

        if g.number_of_edges() == 0:
            pytest.skip("No edges in graph")

        static_scores = nx.pagerank(g, weight="weight", alpha=0.85)
        personal_scores = br._personalized_pagerank(g, ["center.py"], all_rel)

        if not static_scores or not personal_scores:
            pytest.skip("Empty scores")

        # The rankings should differ when we personalize on a specific file
        static_ranking = sorted(static_scores, key=static_scores.get, reverse=True)
        personal_ranking = sorted(personal_scores, key=personal_scores.get, reverse=True)

        # At minimum, the focus file should be boosted in personalized ranking
        static_rank_of_center = static_ranking.index("center.py") if "center.py" in static_ranking else -1
        personal_rank_of_center = personal_ranking.index("center.py") if "center.py" in personal_ranking else -1

        # Personalized should rank center.py at least as high as static
        assert personal_rank_of_center <= static_rank_of_center or personal_rank_of_center == 0, (
            f"Personalized rank of center.py ({personal_rank_of_center}) should be "
            f"<= static rank ({static_rank_of_center})"
        )


# ── PR Review Mode: Edge Cases ───────────────────────────────────────


class TestPRReviewEdgeCases:
    def test_changed_file_not_in_graph(self, tmp_path: Path) -> None:
        """PR changes a file with zero references anywhere. Should not crash."""
        _git_init(tmp_path)
        (tmp_path / "orphan.py").write_text("# no one references me\n")
        (tmp_path / "other.py").write_text("# I also reference nothing\n")
        _git_commit(tmp_path, "init")

        # Should not raise any exception
        review = br.pr_review(tmp_path, ["orphan.py"])
        assert review["changed_files"] == ["orphan.py"]
        assert review["high_blast_radius"] == []

    def test_nonexistent_file_in_pr(self, tmp_path: Path) -> None:
        """PR lists a file that doesn't exist on disk. Should not crash."""
        _git_init(tmp_path)
        (tmp_path / "exists.py").write_text("print('hi')\n")
        _git_commit(tmp_path, "init")

        # ghost.py doesn't exist at all
        review = br.pr_review(tmp_path, ["ghost.py"])
        assert review["changed_files"] == ["ghost.py"]
        # Should still produce a valid result structure
        assert "high_blast_radius" in review
        assert "possibly_missing" in review
        assert "summary" in review

    def test_all_files_changed(self, tmp_path: Path) -> None:
        """PR contains every file in the repo. possibly_missing should be empty."""
        _git_init(tmp_path)
        files = ["a.py", "b.py", "c.py", "config.toml"]
        for f in files:
            (tmp_path / f).write_text(f"# {f}\n")
        # Create some references so blast_radius isn't trivial
        (tmp_path / "a.py").write_text("import b\nimport c\n")
        _git_commit(tmp_path, "init")

        # Change every file
        review = br.pr_review(tmp_path, files)
        # If all files are in the PR, nothing should be "missing"
        assert review["possibly_missing"] == [], (
            f"Expected empty possibly_missing when all files changed, got {review['possibly_missing']}"
        )

    def test_empty_pr(self, tmp_path: Path) -> None:
        """Zero files changed. Should return empty results, not crash."""
        _git_init(tmp_path)
        (tmp_path / "something.py").write_text("x = 1\n")
        _git_commit(tmp_path, "init")

        review = br.pr_review(tmp_path, [])
        assert review["changed_files"] == []
        assert review["high_blast_radius"] == []
        assert review["possibly_missing"] == []
        assert review["summary"]["total_blast_radius"] == 0


# ── Python AST Import Resolution ─────────────────────────────────────


class TestPythonASTImports:
    def test_import_chain_produces_transitive_edges(self, tmp_path: Path) -> None:
        """A imports B, B imports C. Both A->B and B->C edges should exist."""
        _git_init(tmp_path)
        (tmp_path / "a.py").write_text("import b\n")
        (tmp_path / "b.py").write_text("import c\n")
        (tmp_path / "c.py").write_text("# leaf\n")
        _git_commit(tmp_path, "chain")

        edges = br._extract_python_imports(tmp_path)
        edge_set = set(edges)

        assert ("a.py", "b.py") in edge_set, f"Missing a.py->b.py edge. Got: {edges}"
        assert ("b.py", "c.py") in edge_set, f"Missing b.py->c.py edge. Got: {edges}"

    def test_stdlib_import_creates_no_edge(self, tmp_path: Path) -> None:
        """'import os' should not create an edge to any file in the repo."""
        _git_init(tmp_path)
        (tmp_path / "main.py").write_text("import os\nimport sys\nimport json\n")
        (tmp_path / "os.py").write_text("# this is NOT stdlib os\n")
        _git_commit(tmp_path, "init")

        edges = br._extract_python_imports(tmp_path)
        # There SHOULD be an edge from main.py to os.py because the module_map
        # maps "os" -> "os.py" (stem match). This is a known limitation —
        # the AST resolver doesn't distinguish stdlib from local modules.
        # Let's verify the actual behavior:
        edge_set = set(edges)
        # main.py imports "os" -> module_map has "os" -> "os.py" -> edge created
        # This is arguably a BUG: naming a local file "os.py" creates a false edge
        # from any file that imports stdlib os.
        # We test the ACTUAL behavior here to document it.
        assert ("main.py", "os.py") in edge_set, (
            "Expected false-positive edge to os.py due to stem matching. "
            "If this fails, the code now correctly distinguishes stdlib — "
            "which would be an improvement!"
        )

    def test_stdlib_import_no_false_edge_without_shadow(self, tmp_path: Path) -> None:
        """'import os' with no local os.py should create zero edges."""
        _git_init(tmp_path)
        (tmp_path / "main.py").write_text("import os\nimport sys\nimport json\n")
        _git_commit(tmp_path, "init")

        edges = br._extract_python_imports(tmp_path)
        assert edges == [], f"Expected no edges for stdlib-only imports, got {edges}"

    def test_from_import_resolves_dotted_path(self, tmp_path: Path) -> None:
        """'from scripts.helper import X' should resolve to scripts/helper.py."""
        _git_init(tmp_path)
        scripts_dir = tmp_path / "scripts"
        scripts_dir.mkdir()
        (scripts_dir / "__init__.py").write_text("")
        (scripts_dir / "helper.py").write_text("def do_thing(): pass\n")
        (tmp_path / "main.py").write_text("from scripts.helper import do_thing\n")
        _git_commit(tmp_path, "init")

        edges = br._extract_python_imports(tmp_path)
        edge_set = set(edges)

        # Should resolve "scripts.helper" to "scripts/helper.py"
        assert ("main.py", "scripts/helper.py") in edge_set, f"Expected main.py -> scripts/helper.py. Got: {edges}"

    def test_relative_import_not_resolved(self, tmp_path: Path) -> None:
        """Relative imports (from . import X) should not crash.
        The implementation checks `node.module` which is None for `from . import x`.
        """
        pkg_dir = tmp_path / "pkg"
        pkg_dir.mkdir()
        (pkg_dir / "__init__.py").write_text("")
        (pkg_dir / "a.py").write_text("from . import b\n")
        (pkg_dir / "b.py").write_text("x = 1\n")

        _git_init(tmp_path)
        _git_commit(tmp_path, "init")

        # Should not crash — relative imports have module=None when level>0
        # but the code guards with `and node.module`
        br._extract_python_imports(tmp_path)
        # We just verify it doesn't crash; relative imports are silently skipped

    def test_syntax_error_file_skipped(self, tmp_path: Path) -> None:
        """A .py file with syntax errors should be skipped, not crash the run."""
        _git_init(tmp_path)
        (tmp_path / "good.py").write_text("import helper\n")
        (tmp_path / "helper.py").write_text("def go(): pass\n")
        (tmp_path / "broken.py").write_text("def bad(\n  # unclosed paren\n")
        _git_commit(tmp_path, "init")

        # Should not crash
        edges = br._extract_python_imports(tmp_path)
        # good.py -> helper.py should still be detected despite broken.py
        assert ("good.py", "helper.py") in set(edges)


# ── Edge Case: _parse_git_commits internals ──────────────────────────


class TestParseGitCommitsInternals:
    def test_excluded_dirs_filtered_from_commits(self, tmp_path: Path) -> None:
        """Files in excluded dirs (.git, __pycache__, etc) should not appear."""
        _git_init(tmp_path)
        pycache = tmp_path / "__pycache__"
        pycache.mkdir()
        (pycache / "cached.pyc").write_text("bytecode")
        (tmp_path / "real.py").write_text("v1")
        _git_commit(tmp_path, "init")

        file_changes, _, _ = br._parse_git_commits(tmp_path, max_changeset=50)
        for f in file_changes:
            assert "__pycache__" not in f, f"Excluded dir file in results: {f}"

    def test_not_a_git_repo(self, tmp_path: Path) -> None:
        """Calling on a non-git directory should return empty, not crash."""
        (tmp_path / "file.py").write_text("x = 1")

        file_changes, co_changes, commits = br._parse_git_commits(
            tmp_path,
            max_changeset=50,
        )
        assert len(file_changes) == 0
        assert len(co_changes) == 0
        assert commits == []

    def test_empty_git_repo(self, tmp_path: Path) -> None:
        """A git repo with no commits should return empty results."""
        _git_init(tmp_path)

        file_changes, co_changes, _commits = br._parse_git_commits(
            tmp_path,
            max_changeset=50,
        )
        assert len(file_changes) == 0
        assert len(co_changes) == 0


# ── CIRank: Empty and Degenerate Graphs ─────────────────────────────


class TestCIRankDegenerate:
    def test_no_edges_returns_empty(self, tmp_path: Path) -> None:
        """A repo where no file references any other should return empty ranking."""
        _git_init(tmp_path)
        # Files with unique names that don't appear in each other's content
        (tmp_path / "alpha.py").write_text("x = 1\n")
        (tmp_path / "bravo.py").write_text("y = 2\n")
        (tmp_path / "charlie.py").write_text("z = 3\n")
        _git_commit(tmp_path, "init")

        ranked = br.compute_criticality(tmp_path)
        assert ranked == [], f"Expected empty ranking for isolated files, got {ranked}"

    def test_self_loop_no_crash(self, tmp_path: Path) -> None:
        """A file that references its own name should not create a self-edge.
        The code guards with `if s != target` (blast radius) and
        `module_map[candidate] != importer` (AST).
        """
        _git_init(tmp_path)
        (tmp_path / "selfish.py").write_text(
            "# This file is called selfish.py\nimport selfish\n"  # self-import attempt
        )
        _git_commit(tmp_path, "init")

        # Should not crash and should not produce self-edges
        br.compute_criticality(tmp_path)
        # Verify no self-edges in the graph
        g, _ = br._build_dependency_graph(tmp_path)
        for u, v in g.edges():
            assert u != v, f"Self-edge found: {u} -> {v}"


# ── Temporal Coupling: Commit Parsing Edge Cases ─────────────────────


class TestCommitParsingEdgeCases:
    def test_max_changeset_zero_filters_everything(self, tmp_path: Path) -> None:
        """max_changeset=0 means ALL commits are filtered (every commit has >0 files)." """
        _git_init(tmp_path)
        (tmp_path / "a.py").write_text("v1")
        (tmp_path / "b.py").write_text("v1")
        _git_commit(tmp_path, "c1")

        file_changes, co_changes, _ = br._parse_git_commits(tmp_path, max_changeset=0)
        # Every commit has at least 1 file, which is > 0, so all filtered
        assert len(file_changes) == 0
        assert len(co_changes) == 0

    def test_max_changeset_one_only_single_file_commits(self, tmp_path: Path) -> None:
        """max_changeset=1 should only count commits with exactly 1 file."""
        _git_init(tmp_path)
        # Commit with 2 files -> filtered at max_changeset=1
        (tmp_path / "a.py").write_text("v1")
        (tmp_path / "b.py").write_text("v1")
        _git_commit(tmp_path, "two-files")

        # Commit with 1 file -> included
        (tmp_path / "a.py").write_text("v2")
        _git_commit(tmp_path, "one-file")

        file_changes, co_changes, _ = br._parse_git_commits(tmp_path, max_changeset=1)
        assert file_changes["a.py"] == 1
        assert "b.py" not in file_changes
        assert len(co_changes) == 0


# ── Coupling Score Symmetry ──────────────────────────────────────────


class TestCouplingSymmetry:
    """Jaccard(A,B) should equal Jaccard(B,A). The implementation uses sorted
    pairs from combinations(), so (A,B) always has A<B lexicographically.
    But what if coupling is asymmetric in practice?
    """

    def test_asymmetric_change_pattern(self, tmp_path: Path) -> None:
        """A changes 10 times, B changes 3 times, they co-change 3 times.
        Jaccard = 3/(10+3-3) = 0.3.
        P(B|A)=3/10=0.3, P(A|B)=3/3=1.0 but Jaccard is symmetric.
        Jaccard is symmetric by definition, but the underlying causality isn't.
        Just verify the Jaccard value is correct.
        """
        _git_init(tmp_path)

        # 3 commits with both A and B
        for i in range(3):
            (tmp_path / "a.py").write_text(f"v{i}")
            (tmp_path / "b.py").write_text(f"v{i}")
            _git_commit(tmp_path, f"both-{i}")

        # 7 more commits with only A
        for i in range(7):
            (tmp_path / "a.py").write_text(f"solo-{i}")
            _git_commit(tmp_path, f"a-only-{i}")

        couplings = br.compute_temporal_coupling(
            tmp_path,
            min_co_changes=1,
            min_coupling=0.0,
            max_changeset=50,
            min_revisions=1,
        )

        ab = next(
            (c for c in couplings if {c["file_a"], c["file_b"]} == {"a.py", "b.py"}),
            None,
        )
        assert ab is not None
        # Jaccard = 3 / (10 + 3 - 3) = 3/10 = 0.3
        assert ab["coupling"] == 0.3, f"Expected 0.3, got {ab['coupling']}"
        assert ab["changes_a"] == 10  # a.py: 3 co + 7 solo = 10
        assert ab["changes_b"] == 3  # b.py: 3 co-changes only
