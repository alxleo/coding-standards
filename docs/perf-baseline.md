# Performance Baseline

Captured 2026-04-02. Basis for measuring optimization impact.

## Measurement Protocol

- **CI runner**: GitHub-hosted `ubuntu-latest`
- **Local runner**: Apple Silicon (M-series), Docker Desktop
- **Repo snapshot**: `ab7caff` (coding-standards main, 2026-04-02)
- **Image tag**: `ghcr.io/alxleo/coding-standards:latest` (digest `sha256:536e52ac...`)
- **Image arch**: amd64 only (no arm64 build)
- **MegaLinter version**: 9.4.0
- **Timing source**: `megalinter-reports/megalinter-report.md` table (JSON `elapsed_time_s` is not populated — MegaLinter gap)
- **Extraction tool**: `scripts/extract_linter_timings.py`

### Smoke test definition

- `.ci.json` `test_commands`: 26 version/validation checks
- CI entrypoint tests: 3 commands (help, catalog, standards)
- CI config resolution: 1 check
- **Total: 30 distinct checks**

## Image

| Metric | Value |
|--------|-------|
| Uncompressed size | 11.6 GB |
| Architecture | amd64 only |
| Layer count | 221 (docker history) |
| Base image | oxsecurity/megalinter-cupcake:v9 |
| Active linters | 30 |

## CI Pipeline Timing (run 23876777054)

| Step | Duration |
|------|----------|
| fast-checks job | 2m 12s |
| Build image | 3m 23s |
| Smoke tests | 12s |
| Self-lint | 35s |
| Push image | 3m 25s |
| **Total pipeline** | **~10 min** |

## Per-Linter Timing (self-lint on coding-standards repo)

| Linter | Descriptor | Time | Files | Notes |
|--------|-----------|------|-------|-------|
| semgrep | REPOSITORY | 25.73s | repo | auto + trailofbits + custom rules |
| v8r | YAML | 16.70s | 48 | schema validation (bundled) |
| pyright | PYTHON | 11.75s | 16 | standard mode, no excludes |
| v8r | JSON | 11.75s | 7 | schema validation (bundled) |
| trivy | REPOSITORY | 9.45s | repo | vuln+misconfig+secret+license |
| pmd-cpd | COPYPASTE | 5.62s | repo | |
| publint | REPOSITORY | 5.13s | repo | |
| knip | REPOSITORY | 3.55s | repo | |
| gitleaks | REPOSITORY | 2.81s | repo | |
| prettier (YAML) | YAML | 2.65s | 48 | |
| npm-audit | REPOSITORY | 2.39s | repo | |
| oxlint | REPOSITORY | 2.03s | repo | |
| prettier (JSON) | JSON | 1.91s | 7 | |
| lychee | SPELL | 1.89s | 63 | |
| yamllint | YAML | 1.67s | 48 | |
| Other (15 linters) | various | < 1.5s each | — | |
| **Total** | | **116.70s** | **30 linters** | |

### Top 5 bottlenecks: 75.4s (65% of total)

1. semgrep: 25.73s
2. v8r YAML: 16.70s
3. pyright: 11.75s
4. v8r JSON: 11.75s
5. trivy: 9.45s

## Optimization Targets

| ID | Change | Target | Measured | Status |
|----|--------|--------|----------|--------|
| B1 | semgrep `--optimizations all` | test-driven | 0s (already default) | done — no-op |
| B2 | trivy drop secret+license scanners | 2-3s | -4.2s (9.45→5.27s) | done PR#83 |
| B3 | v8r ignore patterns | 2-4s | -22.7s (28.5→5.7s) | done PR#83 |
| B4 | pyright add excludes | 1-3s | ~0s (file-mode, not project) | done PR#83 |
| B5 | lychee cache + timeout + exclude | 12-15s | -17.3s (19.1→1.8s) | done PR#83 |
| C1 | CI skip rebuild on cache hit | 3 min | — | pending #90 |
| A | Alpine multi-arch migration | major (arch + size) | — | pending #84 |

## After B-series optimizations

Total lint time: **116.70s → 87.68s (25% reduction)**

Key changes: v8r ignore patterns (-23s), lychee cache/timeout (-17s), trivy scanner trim (-4s).
Remaining top bottlenecks: semgrep (23s), pyright (11s), pmd-cpd (6s).
