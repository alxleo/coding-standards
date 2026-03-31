"""Tests for scripts/blast_radius.py — change impact analysis.

Tests use synthetic repos with known file references, git histories,
and naming patterns. Each test verifies an algorithm produces correct
output on controlled input — no dependency on the hypothesis.
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


@pytest.fixture()
def synthetic_repo(tmp_path: Path) -> Path:
    """Create a repo with known file references for blast radius testing."""
    # config.toml is referenced by 3 files
    (tmp_path / "config.toml").write_text("[settings]\nkey = 'value'\n")
    (tmp_path / "ci.yml").write_text("run: check --config config.toml\n")
    (tmp_path / "justfile").write_text("check:\n  lint --config config.toml\n")
    (tmp_path / "README.md").write_text("See config.toml for settings\n")

    # lonely.py is referenced by nobody
    (tmp_path / "lonely.py").write_text("print('hello')\n")

    # app.py references lonely.py (but lonely doesn't reference app)
    (tmp_path / "app.py").write_text("import lonely\nlonely.run()\n")

    return tmp_path


@pytest.fixture()
def git_repo(tmp_path: Path) -> Path:
    """Create a git repo with known commit history for coupling tests."""
    subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True, check=False)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=tmp_path,
        capture_output=True,
        check=False,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=tmp_path,
        capture_output=True,
        check=False,
    )

    # Commit 1: a.py + b.py (coupled pair)
    (tmp_path / "a.py").write_text("v1")
    (tmp_path / "b.py").write_text("v1")
    subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True, check=False)
    subprocess.run(
        ["git", "commit", "-m", "c1", "--no-gpg-sign"],
        cwd=tmp_path,
        capture_output=True,
        check=False,
    )

    # Commit 2: a.py + b.py again (strengthens coupling)
    (tmp_path / "a.py").write_text("v2")
    (tmp_path / "b.py").write_text("v2")
    subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True, check=False)
    subprocess.run(
        ["git", "commit", "-m", "c2", "--no-gpg-sign"],
        cwd=tmp_path,
        capture_output=True,
        check=False,
    )

    # Commit 3: a.py + b.py + c.py
    (tmp_path / "a.py").write_text("v3")
    (tmp_path / "b.py").write_text("v3")
    (tmp_path / "c.py").write_text("v1")
    subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True, check=False)
    subprocess.run(
        ["git", "commit", "-m", "c3", "--no-gpg-sign"],
        cwd=tmp_path,
        capture_output=True,
        check=False,
    )

    # Commit 4: a.py alone (weakens a↔b coupling via Jaccard)
    (tmp_path / "a.py").write_text("v4")
    subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True, check=False)
    subprocess.run(
        ["git", "commit", "-m", "c4", "--no-gpg-sign"],
        cwd=tmp_path,
        capture_output=True,
        check=False,
    )

    # Commit 5: c.py alone (independent)
    (tmp_path / "c.py").write_text("v2")
    subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True, check=False)
    subprocess.run(
        ["git", "commit", "-m", "c5", "--no-gpg-sign"],
        cwd=tmp_path,
        capture_output=True,
        check=False,
    )

    return tmp_path


# ── Signal 1: Blast Radius ──────────────────────────────────────────


class TestBlastRadius:
    def test_counts_references_correctly(self, synthetic_repo: Path) -> None:
        results = br.compute_blast_radius(synthetic_repo)
        by_name = {r["name"]: r for r in results}

        # config.toml is referenced by ci.yml, justfile, README.md
        assert by_name["config.toml"]["blast_radius"] == 3

    def test_unreferenced_file_has_zero_blast_radius(self, synthetic_repo: Path) -> None:
        results = br.compute_blast_radius(synthetic_repo)
        by_name = {r["name"]: r for r in results}

        # lonely.py is not referenced by filename anywhere (import != filename ref)
        assert by_name["lonely.py"]["blast_radius"] == 0

    def test_referencing_files_are_listed(self, synthetic_repo: Path) -> None:
        results = br.compute_blast_radius(synthetic_repo)
        by_name = {r["name"]: r for r in results}

        refs = by_name["config.toml"]["referencing_files"]
        assert "ci.yml" in refs
        assert "justfile" in refs
        assert "README.md" in refs

    def test_self_references_excluded(self, synthetic_repo: Path) -> None:
        results = br.compute_blast_radius(synthetic_repo)
        for r in results:
            assert r["file"] not in r["referencing_files"]


# ── Signal 2: Temporal Coupling ──────────────────────────────────────


class TestTemporalCoupling:
    def test_coupled_files_detected(self, git_repo: Path) -> None:
        # a.py and b.py change together in 3 of 4 a-commits and 3 of 3 b-commits
        couplings = br.compute_temporal_coupling(
            git_repo,
            min_co_changes=2,
            min_coupling=0.2,
            min_revisions=2,
        )
        pairs = {(c["file_a"], c["file_b"]) for c in couplings}
        assert ("a.py", "b.py") in pairs

    def test_jaccard_score_correct(self, git_repo: Path) -> None:
        # a.py: 4 changes, b.py: 3 changes, co-changes: 3
        # Jaccard = 3 / (4 + 3 - 3) = 3/4 = 0.75
        couplings = br.compute_temporal_coupling(
            git_repo,
            min_co_changes=2,
            min_coupling=0.2,
            min_revisions=2,
        )
        ab = next(c for c in couplings if c["file_a"] == "a.py" and c["file_b"] == "b.py")
        assert ab["coupling"] == 0.75

    def test_weak_coupling_filtered(self, git_repo: Path) -> None:
        # With high min_coupling, weak pairs are filtered
        couplings = br.compute_temporal_coupling(
            git_repo,
            min_co_changes=2,
            min_coupling=0.9,
            min_revisions=2,
        )
        # a↔b at 0.75 should be filtered
        assert len(couplings) == 0

    def test_large_changeset_filtered(self, git_repo: Path) -> None:
        # With max_changeset=1, no commits qualify (all have 2+ files)
        couplings = br.compute_temporal_coupling(
            git_repo,
            min_co_changes=1,
            min_coupling=0.1,
            max_changeset=1,
            min_revisions=1,
        )
        assert len(couplings) == 0


# ── Signal 3: Naming Entropy ────────────────────────────────────────


class TestNamingEntropy:
    def test_classify_kebab(self) -> None:
        assert br._classify_name("my-script.py") == "kebab-case"

    def test_classify_snake(self) -> None:
        assert br._classify_name("my_script.py") == "snake_case"

    def test_classify_camel(self) -> None:
        assert br._classify_name("myScript.py") == "camelCase"

    def test_classify_pascal(self) -> None:
        assert br._classify_name("MyScript.py") == "PascalCase"

    def test_classify_flat(self) -> None:
        assert br._classify_name("script.py") == "flat"

    def test_classify_mixed(self) -> None:
        assert br._classify_name("my-script_thing.py") == "mixed"

    def test_classify_dotfile(self) -> None:
        assert br._classify_name(".yamllint") == "flat"

    def test_entropy_zero_for_uniform(self) -> None:
        """All same convention → entropy 0."""
        from collections import Counter

        counts = Counter({"snake_case": 10})
        assert br._shannon_entropy(counts) == 0.0

    def test_entropy_one_for_two_equal(self) -> None:
        """Two conventions 50/50 → entropy 1.0."""
        from collections import Counter

        counts = Counter({"snake_case": 5, "kebab-case": 5})
        assert br._shannon_entropy(counts) == pytest.approx(1.0)

    def test_directory_entropy(self, tmp_path: Path) -> None:
        """Directory with mixed conventions has positive entropy."""
        (tmp_path / "my-script.py").write_text("")
        (tmp_path / "my_other.py").write_text("")
        (tmp_path / "MyClass.py").write_text("")
        (tmp_path / "simple.py").write_text("")

        results = br.compute_naming_entropy(tmp_path)
        assert len(results) == 1
        assert results[0]["entropy"] > 1.0  # 3+ conventions = high entropy


# ── Signal 4: CIRank ────────────────────────────────────────────────


class TestCriticality:
    def test_most_referenced_ranks_highest(self, synthetic_repo: Path) -> None:
        ranked = br.compute_criticality(synthetic_repo)
        if not ranked:
            pytest.skip("Graph too small for meaningful PageRank")
        # config.toml has the most inbound references → should rank high
        top_files = [r["file"] for r in ranked[:3]]
        assert "config.toml" in top_files


# ── PR Review Mode ──────────────────────────────────────────────────


class TestPRReview:
    def test_high_blast_radius_flagged(self, synthetic_repo: Path) -> None:
        review = br.pr_review(synthetic_repo, ["config.toml"])
        assert len(review["high_blast_radius"]) == 1
        assert review["high_blast_radius"][0]["blast_radius"] == 3

    def test_low_blast_radius_not_flagged(self, synthetic_repo: Path) -> None:
        review = br.pr_review(synthetic_repo, ["lonely.py"])
        assert len(review["high_blast_radius"]) == 0

    def test_summary_totals(self, synthetic_repo: Path) -> None:
        review = br.pr_review(synthetic_repo, ["config.toml", "lonely.py"])
        assert review["summary"]["total_blast_radius"] == 3  # 3 + 0
