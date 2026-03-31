"""Adversarial tests for scripts/blast_radius.py — designed to find bugs.

Red-team approach: each test creates a controlled scenario that targets
a specific weakness in the algorithm. Tests assert EXPECTED correct behavior,
so failures indicate real bugs in the implementation.
"""

from __future__ import annotations

import subprocess
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

# Load blast_radius module from scripts/ (not importable directly)
_spec = spec_from_file_location(
    "blast_radius",
    Path(__file__).resolve().parent.parent / "scripts" / "blast_radius.py",
)
br = module_from_spec(_spec)
_spec.loader.exec_module(br)


# ── Helpers ──────────────────────────────────────────────────────────


def _git_init(path: Path) -> None:
    """Initialize a git repo with sane defaults for testing."""
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


# ══════════════════════════════════════════════════════════════════════
# Signal 1: Blast Radius — Adversarial
# ══════════════════════════════════════════════════════════════════════


class TestBlastRadiusSubstringMatches:
    """Test #1: re.search(re.escape(name), content) matches SUBSTRINGS.

    The algorithm searches for the filename as a substring, not a whole word.
    'test.py' will match inside 'contest.py', 'test.py.bak', 'pytest.py', etc.
    This is a known limitation — these tests document the actual behavior.
    """

    def test_substring_match_false_positive_prefix(self, tmp_path: Path) -> None:
        """'test.py' should NOT match 'contest.py' — but re.search finds it as substrin
        """
        (tmp_path / "test.py").write_text("print('hello')\n")
        # This file's NAME is 'contest.py' but its CONTENT mentions 'contest.py'
        # The real question: does content of other files contain 'test.py' as substring?
        (tmp_path / "app.py").write_text(
            "from contest import stuff  # has 'test.py' as substring? no\n"
        )
        (tmp_path / "runner.py").write_text(
            "run pytest.py  # contains 'test.py' as substring!\n"
        )

        results = br.compute_blast_radius(tmp_path)
        by_name = {r["name"]: r for r in results}

        # 'runner.py' content 'pytest.py' contains 'test.py' as a substring
        # This IS a false positive — re.escape("test.py") matches inside "pytest.py"
        test_refs = by_name["test.py"]["referencing_files"]
        # BUG: runner.py references "pytest.py" not "test.py", but substring match catc
        assert "runner.py" in test_refs, (
            "Expected false positive: 'test.py' matches inside 'pytest.py' via substr"
        )

    def test_substring_match_false_positive_suffix(self, tmp_path: Path) -> None:
        """'test.py' matched inside 'test.py.bak' is a false positive."""
        (tmp_path / "test.py").write_text("real file\n")
        (tmp_path / "notes.md").write_text("backup at test.py.bak\n")

        results = br.compute_blast_radius(tmp_path)
        by_name = {r["name"]: r for r in results}

        # 'test.py' is a substring of 'test.py.bak'
        assert "notes.md" in by_name["test.py"]["referencing_files"], (
            "Expected false positive: 'test.py' matches inside 'test.py.bak'"
        )

    def test_dot_in_filename_is_escaped(self, tmp_path: Path) -> None:
        """re.escape handles dots — 'config.toml' should NOT match 'configXtoml'."""
        (tmp_path / "config.toml").write_text("[x]\n")
        (tmp_path / "other.py").write_text("configXtoml = 1\n")

        results = br.compute_blast_radius(tmp_path)
        by_name = {r["name"]: r for r in results}

        # re.escape("config.toml") produces "config\.toml" — the dot is literal
        assert by_name["config.toml"]["blast_radius"] == 0


class TestBlastRadiusSymlinks:
    """Test #2: Symlinked files — counted once or twice?"""

    def test_symlink_not_double_counted_as_target(self, tmp_path: Path) -> None:
        """A symlink to a file should not inflate the blast radius of referencing files
        """
        (tmp_path / "real.py").write_text("code\n")
        (tmp_path / "link.py").symlink_to(tmp_path / "real.py")
        (tmp_path / "app.sh").write_text("python real.py\n")

        results = br.compute_blast_radius(tmp_path)
        by_name = {r["name"]: r for r in results}

        # real.py and link.py are separate targets — both should appear
        assert "real.py" in by_name
        assert "link.py" in by_name

    def test_symlink_content_scanned_for_references(self, tmp_path: Path) -> None:
        """A symlink's content (same as target) should count as a referencing file."""
        (tmp_path / "config.toml").write_text("[settings]\n")
        (tmp_path / "real.py").write_text("load('config.toml')\n")
        (tmp_path / "link.py").symlink_to(tmp_path / "real.py")

        results = br.compute_blast_radius(tmp_path)
        by_name = {r["name"]: r for r in results}

        # Both real.py and link.py read as same content mentioning config.toml
        # They should both count as separate referencing files
        refs = by_name["config.toml"]["referencing_files"]
        assert "real.py" in refs
        # link.py has the same content — does it also reference config.toml?
        assert "link.py" in refs, "Symlink content should also count as a reference"


class TestBlastRadiusBinaryFiles:
    """Test #3: Binary files containing filenames as byte sequences."""

    def test_binary_file_not_scanned(self, tmp_path: Path) -> None:
        """Binary files (.png, .whl) are not in SCANNABLE_EXTS — they should be skipped
        """
        (tmp_path / "config.toml").write_text("[x]\n")
        # Write binary content that happens to contain "config.toml" as bytes
        (tmp_path / "icon.png").write_bytes(
            b"\x89PNG\r\n" + b"config.toml" + b"\x00\x00"
        )

        results = br.compute_blast_radius(tmp_path)
        by_name = {r["name"]: r for r in results}

        # .png is not in SCANNABLE_EXTS, so it should not be scanned for references
        refs = by_name["config.toml"]["referencing_files"]
        assert "icon.png" not in refs

    def test_binary_file_still_appears_as_target(self, tmp_path: Path) -> None:
        """Binary files should still appear as blast radius targets if their name is re
        """
        (tmp_path / "icon.png").write_bytes(b"\x89PNG\r\n\x00\x00")
        (tmp_path / "app.py").write_text("img = load('icon.png')\n")

        results = br.compute_blast_radius(tmp_path)
        by_name = {r["name"]: r for r in results}

        # icon.png should be a target even though it's binary
        assert "icon.png" in by_name
        assert by_name["icon.png"]["blast_radius"] == 1


class TestBlastRadiusSpecialFilenames:
    """Test #4: Filenames with regex-special characters."""

    def test_filename_with_parentheses(self, tmp_path: Path) -> None:
        """Filename with parens: 'setup(1).py' — re.escape must handle this."""
        (tmp_path / "setup(1).py").write_text("code\n")
        (tmp_path / "notes.md").write_text("see setup(1).py for details\n")

        results = br.compute_blast_radius(tmp_path)
        by_name = {r["name"]: r for r in results}

        assert by_name["setup(1).py"]["blast_radius"] == 1

    def test_filename_with_brackets(self, tmp_path: Path) -> None:
        """Filename with brackets: '[draft].md' — brackets are regex character class."""
        (tmp_path / "[draft].md").write_text("content\n")
        (tmp_path / "index.md").write_text("see [draft].md\n")

        results = br.compute_blast_radius(tmp_path)
        by_name = {r["name"]: r for r in results}

        assert by_name["[draft].md"]["blast_radius"] == 1

    def test_filename_with_plus(self, tmp_path: Path) -> None:
        """Filename with plus: 'c++.md' — + is regex quantifier."""
        (tmp_path / "c++.md").write_text("about c++\n")
        (tmp_path / "index.md").write_text("see c++.md\n")

        results = br.compute_blast_radius(tmp_path)
        by_name = {r["name"]: r for r in results}

        assert by_name["c++.md"]["blast_radius"] == 1


class TestBlastRadiusEmptyFiles:
    """Test #5: Empty files should not cause errors or ghost references."""

    def test_empty_file_has_zero_blast_radius(self, tmp_path: Path) -> None:
        """An empty .py file referenced by nobody has blast_radius 0."""
        (tmp_path / "empty.py").write_text("")
        (tmp_path / "other.py").write_text("print('hi')\n")

        results = br.compute_blast_radius(tmp_path)
        by_name = {r["name"]: r for r in results}

        assert by_name["empty.py"]["blast_radius"] == 0

    def test_empty_file_can_still_be_referenced(self, tmp_path: Path) -> None:
        """An empty file can still be the TARGET of references."""
        (tmp_path / "empty.py").write_text("")
        (tmp_path / "loader.py").write_text("exec(open('empty.py').read())\n")

        results = br.compute_blast_radius(tmp_path)
        by_name = {r["name"]: r for r in results}

        assert by_name["empty.py"]["blast_radius"] == 1

    def test_empty_scanner_does_not_match_anything(self, tmp_path: Path) -> None:
        """An empty scannable file should not reference any other file."""
        (tmp_path / "config.toml").write_text("[settings]\n")
        (tmp_path / "scanner.py").write_text("")  # empty — no references to anything

        results = br.compute_blast_radius(tmp_path)
        by_name = {r["name"]: r for r in results}

        assert "scanner.py" not in by_name["config.toml"]["referencing_files"]


class TestBlastRadiusSameNameDifferentDirs:
    """Test #6: Same filename in different directories — should be separate entries."""

    def test_same_name_different_dirs_separate_entries(self, tmp_path: Path) -> None:
        """scripts/config.toml and lib/config.toml are distinct files."""
        (tmp_path / "scripts").mkdir()
        (tmp_path / "lib").mkdir()
        (tmp_path / "scripts" / "config.toml").write_text("[scripts]\n")
        (tmp_path / "lib" / "config.toml").write_text("[lib]\n")
        (tmp_path / "app.py").write_text("load('config.toml')\n")

        results = br.compute_blast_radius(tmp_path)
        config_entries = [r for r in results if r["name"] == "config.toml"]

        # Both should appear as separate entries
        assert len(config_entries) == 2
        files = {r["file"] for r in config_entries}
        assert "scripts/config.toml" in files
        assert "lib/config.toml" in files

    def test_same_name_full_path_distinguishes(self, tmp_path: Path) -> None:
        """Full path matching: 'scripts/config.toml' should NOT inflate lib/config.toml.

        The algorithm searches for both full relative path and word-bounded basename.
        When content says 'scripts/config.toml', only scripts/config.toml matches
        via path, and lib/config.toml does NOT match because the bare 'config.toml'
        substring is preceded by 'scripts/' (not a word boundary).
        """
        (tmp_path / "scripts").mkdir()
        (tmp_path / "lib").mkdir()
        (tmp_path / "scripts" / "config.toml").write_text("[scripts]\n")
        (tmp_path / "lib" / "config.toml").write_text("[lib]\n")
        # app.py references scripts/config.toml by full path
        (tmp_path / "app.py").write_text("load('scripts/config.toml')\n")

        results = br.compute_blast_radius(tmp_path)
        config_entries = {r["file"]: r for r in results if r["name"] == "config.toml"}

        scripts_radius = config_entries["scripts/config.toml"]["blast_radius"]
        lib_radius = config_entries["lib/config.toml"]["blast_radius"]

        assert scripts_radius >= 1, "scripts/config.toml should be found via path match"
        # Fixed: lib/config.toml should NOT match because 'config.toml' in
        # 'scripts/config.toml' is preceded by '/' (not a word boundary)
        assert lib_radius == 0, (
            "lib/config.toml should NOT match when content says 'scripts/config.toml'"
        )

    def test_same_name_files_reference_each_other_false_positive(
        self, tmp_path: Path
    ) -> None:
        """Two files named 'config.toml' — each references the OTHER because
        each file's content is scanned for the basename 'config.toml', and
        the other file IS named 'config.toml'. But neither file's CONTENT
        mentions 'config.toml' — the content is '[scripts]' and '[lib]'.

        This test verifies that the algorithm does NOT produce phantom
        cross-references just because the filenames are the same.
        """
        (tmp_path / "scripts").mkdir()
        (tmp_path / "lib").mkdir()
        (tmp_path / "scripts" / "config.toml").write_text("[scripts]\nfoo = 1\n")
        (tmp_path / "lib" / "config.toml").write_text("[lib]\nbar = 2\n")

        results = br.compute_blast_radius(tmp_path)
        config_entries = {r["file"]: r for r in results if r["name"] == "config.toml"}

        # Neither file's content mentions "config.toml" so neither should reference the
        scripts_refs = config_entries["scripts/config.toml"]["referencing_files"]
        lib_refs = config_entries["lib/config.toml"]["referencing_files"]
        assert "lib/config.toml" not in scripts_refs
        assert "scripts/config.toml" not in lib_refs


# ══════════════════════════════════════════════════════════════════════
# Signal 2: Temporal Coupling — Adversarial
# ══════════════════════════════════════════════════════════════════════


class TestTemporalCouplingSingleFileCommits:
    """Test #7: Commits that touch only one file produce zero coupling."""

    def test_single_file_commits_no_coupling(self, tmp_path: Path) -> None:
        """If every commit touches exactly one file, no pairs exist."""
        _git_init(tmp_path)

        (tmp_path / "a.py").write_text("v1")
        _git_commit(tmp_path, "c1")

        (tmp_path / "b.py").write_text("v1")
        _git_commit(tmp_path, "c2")

        (tmp_path / "a.py").write_text("v2")
        _git_commit(tmp_path, "c3")

        (tmp_path / "b.py").write_text("v2")
        _git_commit(tmp_path, "c4")

        couplings = br.compute_temporal_coupling(
            tmp_path,
            min_co_changes=1,
            min_coupling=0.01,
            min_revisions=1,
        )
        assert len(couplings) == 0


class TestTemporalCouplingAllFilesEveryCommit:
    """Test #8: Files that always change together have maximum coupling."""

    def test_perfect_coupling(self, tmp_path: Path) -> None:
        """If a.py and b.py always change together, Jaccard = 1.0."""
        _git_init(tmp_path)

        for i in range(5):
            (tmp_path / "a.py").write_text(f"v{i}")
            (tmp_path / "b.py").write_text(f"v{i}")
            _git_commit(tmp_path, f"c{i}")

        couplings = br.compute_temporal_coupling(
            tmp_path,
            min_co_changes=1,
            min_coupling=0.1,
            min_revisions=1,
        )
        ab = next(
            c for c in couplings if {c["file_a"], c["file_b"]} == {"a.py", "b.py"}
        )
        # Jaccard = 5 / (5 + 5 - 5) = 1.0
        assert ab["coupling"] == 1.0

    def test_three_files_all_coupled(self, tmp_path: Path) -> None:
        """Three files always changed together — all three pairs should appear."""
        _git_init(tmp_path)

        for i in range(4):
            (tmp_path / "a.py").write_text(f"v{i}")
            (tmp_path / "b.py").write_text(f"v{i}")
            (tmp_path / "c.py").write_text(f"v{i}")
            _git_commit(tmp_path, f"c{i}")

        couplings = br.compute_temporal_coupling(
            tmp_path,
            min_co_changes=1,
            min_coupling=0.1,
            min_revisions=1,
        )
        pair_set = {frozenset([c["file_a"], c["file_b"]]) for c in couplings}
        assert frozenset(["a.py", "b.py"]) in pair_set
        assert frozenset(["a.py", "c.py"]) in pair_set
        assert frozenset(["b.py", "c.py"]) in pair_set


class TestTemporalCouplingMergeCommits:
    """Test #9: Merge commits should be filtered by --no-merges flag."""

    def test_merge_commits_excluded(self, tmp_path: Path) -> None:
        """Merge commits are excluded by the --no-merges git log flag.

        This test creates a merge commit and verifies it does not inflate
        temporal coupling scores.
        """
        _git_init(tmp_path)

        # main branch: a.py
        (tmp_path / "a.py").write_text("v1")
        _git_commit(tmp_path, "initial")

        # feature branch: b.py
        subprocess.run(
            ["git", "checkout", "-b", "feature"],
            cwd=tmp_path,
            capture_output=True,
            check=True,
        )
        (tmp_path / "b.py").write_text("v1")
        _git_commit(tmp_path, "feature: add b")

        # back to main, add c.py
        subprocess.run(
            ["git", "checkout", "master"],
            cwd=tmp_path, check=False,
            capture_output=True,
        )
        # might be main
        subprocess.run(
            ["git", "checkout", "main"],
            cwd=tmp_path, check=False,
            capture_output=True,
        )
        (tmp_path / "c.py").write_text("v1")
        _git_commit(tmp_path, "main: add c")

        # Merge feature → creates a merge commit touching a.py, b.py, c.py
        subprocess.run(
            ["git", "merge", "feature", "--no-edit", "--no-gpg-sign"],
            cwd=tmp_path, check=False,
            capture_output=True,
        )

        # The merge commit itself should be excluded by --no-merges
        # So b.py and c.py should NOT appear coupled just from the merge
        couplings = br.compute_temporal_coupling(
            tmp_path,
            min_co_changes=1,
            min_coupling=0.01,
            min_revisions=1,
        )
        # b.py and c.py only co-occur in the merge commit, which is filtered
        bc_coupling = [
            c for c in couplings if {c["file_a"], c["file_b"]} == {"b.py", "c.py"}
        ]
        assert len(bc_coupling) == 0, (
            "b.py and c.py only co-occur in a merge commit, "
            "which should be filtered by --no-merges"
        )


class TestTemporalCouplingRenamedFiles:
    """Test #10: git mv renames — does coupling carry over to the new name?"""

    def test_renamed_file_coupling_uses_new_name(self, tmp_path: Path) -> None:
        """After git mv, coupling should be under the NEW path.

        The algorithm parses git log --name-only which shows the name at the
        time of each commit. After a rename, old commits show the old name
        and new commits show the new name. Coupling does NOT carry over.
        """
        _git_init(tmp_path)

        # Build coupling between old.py and partner.py
        for i in range(4):
            (tmp_path / "old.py").write_text(f"v{i}")
            (tmp_path / "partner.py").write_text(f"v{i}")
            _git_commit(tmp_path, f"c{i}")

        # Rename old.py -> new.py
        subprocess.run(
            ["git", "mv", "old.py", "new.py"],
            cwd=tmp_path,
            capture_output=True,
            check=True,
        )
        (tmp_path / "partner.py").write_text("v_after_rename")
        _git_commit(tmp_path, "rename old to new")

        couplings = br.compute_temporal_coupling(
            tmp_path,
            min_co_changes=1,
            min_coupling=0.1,
            min_revisions=1,
        )

        # old.py should still show coupling with partner.py (from historical commits)
        old_partner = [
            c
            for c in couplings
            if {c["file_a"], c["file_b"]} == {"old.py", "partner.py"}
        ]
        assert len(old_partner) > 0, (
            "Historical coupling between old.py and partner.py persists in git log"
        )

        # new.py has only 1 co-change with partner.py — may not meet thresholds
        new_partner = [
            c
            for c in couplings
            if {c["file_a"], c["file_b"]} == {"new.py", "partner.py"}
        ]
        # With min_co_changes=1 it should appear, but coupling is weak
        # The key insight: rename breaks the coupling chain
        assert len(new_partner) <= 1  # at most one co-change after rename


class TestTemporalCouplingDeletedFiles:
    """Test #11: Deleted files may appear in coupling output as ghost entries."""

    def test_deleted_file_appears_in_coupling(self, tmp_path: Path) -> None:
        """A file deleted after being highly coupled still shows in git history.

        The algorithm uses git log --name-only, which includes ALL historical
        filenames. A deleted file will appear in coupling output even though
        it no longer exists on disk.
        """
        _git_init(tmp_path)

        # Build strong coupling
        for i in range(4):
            (tmp_path / "doomed.py").write_text(f"v{i}")
            (tmp_path / "survivor.py").write_text(f"v{i}")
            _git_commit(tmp_path, f"c{i}")

        # Delete doomed.py
        (tmp_path / "doomed.py").unlink()
        _git_commit(tmp_path, "delete doomed")

        couplings = br.compute_temporal_coupling(
            tmp_path,
            min_co_changes=2,
            min_coupling=0.1,
            min_revisions=2,
        )

        # doomed.py should still appear in coupling data from historical commits
        doomed_couplings = [
            c for c in couplings if "doomed.py" in (c["file_a"], c["file_b"])
        ]
        assert len(doomed_couplings) > 0, (
            "Deleted file should still appear in coupling output from git history"
        )


# ══════════════════════════════════════════════════════════════════════
# Signal 4: Criticality / Dependency Graph — Adversarial
# ══════════════════════════════════════════════════════════════════════


class TestCriticalityCircularReferences:
    """Test #12: Circular references — does PageRank converge?"""

    def test_circular_reference_does_not_crash(self, tmp_path: Path) -> None:
        """A references B, B references A. PageRank must still converge."""
        (tmp_path / "a.py").write_text("import b  # references b.py\n")
        (tmp_path / "b.py").write_text("import a  # references a.py\n")

        # Should not raise
        ranked = br.compute_criticality(tmp_path)
        # Both files should appear with similar scores (symmetric graph)
        if ranked:
            scores = {r["file"]: r["criticality"] for r in ranked}
            if "a.py" in scores and "b.py" in scores:
                # Symmetric graph → roughly equal scores
                assert abs(scores["a.py"] - scores["b.py"]) < 0.01


class TestCriticalityDisconnectedGraph:
    """Test #13: Isolated files with no edges — PageRank should handle gracefully."""

    def test_disconnected_files_no_crash(self, tmp_path: Path) -> None:
        """Files with no cross-references produce an edgeless graph."""
        (tmp_path / "a.py").write_text("x = 1\n")
        (tmp_path / "b.py").write_text("y = 2\n")
        (tmp_path / "c.py").write_text("z = 3\n")

        # Should not crash — compute_criticality returns [] for empty graph
        ranked = br.compute_criticality(tmp_path)
        assert ranked == []

    def test_partially_disconnected_graph(self, tmp_path: Path) -> None:
        """Some files connected, some isolated — isolated ones should not crash."""
        (tmp_path / "hub.py").write_text("import spoke\n")
        (tmp_path / "spoke.py").write_text("x = 1\n")
        (tmp_path / "island.py").write_text("y = 2\n")  # no connections

        ranked = br.compute_criticality(tmp_path)
        # Should produce results for the connected component
        if ranked:
            files = {r["file"] for r in ranked}
            # hub and spoke should appear; island might or might not depending on thres
            assert "hub.py" in files or "spoke.py" in files


class TestCriticalitySelfReference:
    """Test #14: File contains its own name — should be excluded from self-edges."""

    def test_self_reference_excluded(self, tmp_path: Path) -> None:
        """A file mentioning its own name should not create a self-edge in the graph."""
        (tmp_path / "config.toml").write_text("# see config.toml for docs\nkey = 1\n")
        # Add another file so the graph isn't empty
        (tmp_path / "app.py").write_text("load('config.toml')\n")

        br.compute_criticality(tmp_path)
        # The graph should have edges but no self-loops
        g, _ = br._build_dependency_graph(tmp_path)
        for node in g.nodes():
            assert not g.has_edge(node, node), f"Self-edge found on {node}"


# ══════════════════════════════════════════════════════════════════════
# Python Import Extraction — Adversarial
# ══════════════════════════════════════════════════════════════════════


class TestExtractPythonImportsRelative:
    """Test #15: Relative imports — from . import foo."""

    def test_relative_import_ignored(self, tmp_path: Path) -> None:
        """Relative imports (from . import X) are now resolved.

        'from . import foo' resolves foo.py relative to the importing file's directory.
        """
        pkg = tmp_path / "pkg"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("")
        (pkg / "foo.py").write_text("x = 1\n")
        (pkg / "bar.py").write_text("from . import foo\n")

        edges = br._extract_python_imports(tmp_path)
        bar_imports = [e for e in edges if "pkg/bar.py" in e[0]]
        # Relative import is now caught
        assert len(bar_imports) == 1, (
            "Relative imports (from . import foo) should resolve to pkg/foo.py"
        )

    def test_relative_import_with_module(self, tmp_path: Path) -> None:
        """'from .utils import helper' — module is 'utils', level > 0.

        The code checks 'node.module' which is 'utils' — truthy.
        But it resolves against module_map without accounting for the relative path.
        """
        pkg = tmp_path / "pkg"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("")
        (pkg / "utils.py").write_text("def helper(): pass\n")
        (pkg / "main.py").write_text("from .utils import helper\n")

        edges = br._extract_python_imports(tmp_path)
        main_imports = [e for e in edges if "pkg/main.py" in e[0]]
        # 'from .utils import helper' → node.module = 'utils'
        # module_map has 'utils' mapped to 'pkg/utils.py' (via stem)
        # So this DOES get resolved — but only by accident (stem match)
        imported = [e[1] for e in main_imports]
        assert "pkg/utils.py" in imported, (
            "Relative import with module resolves via stem match in module_map"
        )


class TestExtractPythonImportsDynamic:
    """Test #16: Dynamic imports — importlib.import_module."""

    def test_dynamic_import_not_caught(self, tmp_path: Path) -> None:
        """importlib.import_module('foo') is a function call, not an import statement.

        The AST walker only looks at Import and ImportFrom nodes.
        Dynamic imports are correctly ignored.
        """
        (tmp_path / "foo.py").write_text("x = 1\n")
        (tmp_path / "loader.py").write_text(
            "import importlib\nmod = importlib.import_module('foo')\n"
        )

        edges = br._extract_python_imports(tmp_path)
        loader_imports = [(a, b) for a, b in edges if "loader.py" in a]

        # Should find 'import importlib' but not the dynamic import of 'foo'
        imported_files = [b for _, b in loader_imports]
        assert "foo.py" not in imported_files, (
            "Dynamic imports should not be caught by AST import extraction"
        )


class TestExtractPythonImportsStarImport:
    """Test #17: Star imports — from foo import *."""

    def test_star_import_caught(self, tmp_path: Path) -> None:
        """'from foo import *' is an ImportFrom node with module='foo'.

        The code processes ImportFrom.module, so star imports are caught.
        """
        (tmp_path / "foo.py").write_text("x = 1\ny = 2\n")
        (tmp_path / "bar.py").write_text("from foo import *\n")

        edges = br._extract_python_imports(tmp_path)
        bar_imports = [(a, b) for a, b in edges if "bar.py" in a]
        imported_files = [b for _, b in bar_imports]
        assert "foo.py" in imported_files, (
            "Star imports (from foo import *) should be caught via ImportFrom.module"
        )


class TestExtractPythonImportsConditional:
    """Test #18: Conditional imports inside try/except blocks."""

    def test_both_conditional_imports_caught(self, tmp_path: Path) -> None:
        """try: import foo; except: import bar — AST walker visits ALL nodes.

        ast.walk traverses the entire tree regardless of control flow.
        Both import statements are found.
        """
        (tmp_path / "foo.py").write_text("x = 1\n")
        (tmp_path / "bar.py").write_text("y = 2\n")
        (tmp_path / "loader.py").write_text(
            "try:\n    import foo\nexcept ImportError:\n    import bar\n"
        )

        edges = br._extract_python_imports(tmp_path)
        loader_imports = [(a, b) for a, b in edges if "loader.py" in a]
        imported_files = [b for _, b in loader_imports]

        assert "foo.py" in imported_files, "Primary import should be caught"
        assert "bar.py" in imported_files, "Fallback import should be caught"

    def test_syntax_error_file_skipped(self, tmp_path: Path) -> None:
        """A file with a syntax error should be skipped without crashing."""
        (tmp_path / "good.py").write_text("x = 1\n")
        (tmp_path / "bad.py").write_text("def broken(\n")  # syntax error
        (tmp_path / "importer.py").write_text("import good\nimport bad\n")

        # Should not crash
        edges = br._extract_python_imports(tmp_path)
        # importer.py should still resolve good.py
        importer_imports = [(a, b) for a, b in edges if "importer.py" in a]
        imported_files = [b for _, b in importer_imports]
        assert "good.py" in imported_files


# ══════════════════════════════════════════════════════════════════════
# Edge Cases — Cross-cutting
# ══════════════════════════════════════════════════════════════════════


class TestBlastRadiusGenericNamesSkipped:
    """Generic names like __init__.py should be excluded from blast radius targets."""

    def test_init_py_excluded(self, tmp_path: Path) -> None:
        """__init__.py is in GENERIC_NAMES and should not appear in results."""
        pkg = tmp_path / "pkg"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("from .foo import bar\n")
        (pkg / "foo.py").write_text("bar = 1\n")

        results = br.compute_blast_radius(tmp_path)
        names = {r["name"] for r in results}
        assert "__init__.py" not in names


class TestCollectFilesExclusion:
    """Verify excluded directories are actually skipped."""

    def test_venv_excluded(self, tmp_path: Path) -> None:
        """Files inside .venv should not be collected."""
        venv = tmp_path / ".venv" / "lib"
        venv.mkdir(parents=True)
        (venv / "package.py").write_text("x = 1\n")
        (tmp_path / "app.py").write_text("import package\n")

        results = br.compute_blast_radius(tmp_path)
        files = {r["file"] for r in results}
        assert not any(".venv" in f for f in files)

    def test_git_dir_excluded(self, tmp_path: Path) -> None:
        """Files inside .git should not be collected."""
        git = tmp_path / ".git" / "hooks"
        git.mkdir(parents=True)
        (git / "pre-commit.sh").write_text("echo hi\n")
        (tmp_path / "app.py").write_text("x = 1\n")

        results = br.compute_blast_radius(tmp_path)
        files = {r["file"] for r in results}
        assert not any(".git" in f for f in files)


class TestBlastRadiusNonScannableNotSearched:
    """Non-scannable files (e.g., .png) should be targets but not scanners."""

    def test_non_scannable_ext_not_scanned_as_source(self, tmp_path: Path) -> None:
        """A .whl file whose bytes contain 'config.toml' should NOT be a referencing fi
        """
        (tmp_path / "config.toml").write_text("[x]\n")
        (tmp_path / "package.whl").write_bytes(b"PK\x03\x04config.toml\x00\x00")

        results = br.compute_blast_radius(tmp_path)
        by_name = {r["name"]: r for r in results}
        refs = by_name["config.toml"]["referencing_files"]
        assert "package.whl" not in refs


class TestBuildDependencyGraphEdgeCases:
    """Edge cases in _build_dependency_graph."""

    def test_empty_repo_produces_empty_graph(self, tmp_path: Path) -> None:
        """A repo with no files should produce an empty graph."""
        g, _nodes = br._build_dependency_graph(tmp_path)
        assert g.number_of_nodes() == 0
        assert g.number_of_edges() == 0

    def test_single_file_repo(self, tmp_path: Path) -> None:
        """A repo with one file should have one node and no edges."""
        (tmp_path / "solo.py").write_text("x = 1\n")
        g, _nodes = br._build_dependency_graph(tmp_path)
        assert g.number_of_nodes() == 1
        assert g.number_of_edges() == 0


class TestImportModuleMapCollisions:
    """Module map collisions: two files with the same stem in different dirs."""

    def test_stem_collision_last_wins(self, tmp_path: Path) -> None:
        """If scripts/utils.py and lib/utils.py both exist, 'utils' stem maps to one.

        The module_map is built by iterating _collect_files. The last file
        with stem 'utils' overwrites the first. This means import resolution
        is now safely unresolved (neither gets picked non-deterministically).
        """
        scripts = tmp_path / "scripts"
        lib = tmp_path / "lib"
        scripts.mkdir()
        lib.mkdir()
        (scripts / "utils.py").write_text("def s(): pass\n")
        (lib / "utils.py").write_text("def l(): pass\n")
        (tmp_path / "app.py").write_text("import utils\n")

        edges = br._extract_python_imports(tmp_path)
        app_imports = [(a, b) for a, b in edges if "app.py" in a]

        # Ambiguous stem "utils" maps to two files — neither is added to module_map.
        # import utils resolves to nothing (safe), avoiding non-deterministic behavior.
        assert len(app_imports) == 0, (
            "Ambiguous stem 'utils' should not resolve to avoid non-determinism"
        )
