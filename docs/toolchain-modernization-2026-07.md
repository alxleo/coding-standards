# Toolchain modernization — 2026-07-31

This refresh moves the image from MegaLinter v9.4 to v9.6 and updates the bundled Python, Node, and standalone tools to current releases as of 2026-07-31. Version claims come from the upstream package registries, release APIs, and checksum files; the Dockerfile records every selected version and digest.

## Changes adopted

- MegaLinter v9.6.0 on Python 3.14 and Alpine 3.24.
- ESLint v10 with flat configuration, `@eslint/js`, `typescript-eslint`, `@eslint-react/eslint-plugin`, and `eslint-plugin-import-x`. The baked configuration now resolves its globally installed plugins from its own directory.
- Betterleaks v1.7.3 as the default secrets scanner. It preserves `.gitleaks.toml` and `.gitleaksignore` compatibility; the Gitleaks binary remains installed for consumers that invoke it directly.
- Trivy v0.72.0 with checksum verification. The previous Renovate ceiling for the compromised v0.69.4-v0.69.6 releases is no longer needed now that upstream has shipped post-incident releases and MegaLinter has re-enabled the scanner.
- Current stable releases of Ruff, Semgrep, ansible-lint, sqlfluff, zizmor, Hadolint, tflint, kubeconform, lychee, golangci-lint, shfmt, PMD, Caddy, conftest, Prettier, stylelint, and the other explicitly pinned packages in the Dockerfile.
- Renovate managers for the Dockerfile's PyPI, npm, MegaLinter, and annotated GitHub-release pins, so future drift is proposed automatically rather than rediscovered by hand.

## New rule surfaces reviewed

- Ruff 0.16 adds `B043`, `PLW0717`, `RUF050`, `RUF071`-`RUF076`, `RUF105`, `RUF106`, `RUF201`, and `UP051` within categories already selected by this repository. These are preview rules, except removed `RUF076`, so the stable policy does not silently enable them.
- Zizmor 1.25-1.28 adds audits for GitHub App credentials, unpinned tools, typosquatted actions, unsound ternaries, and ad-hoc package installation, plus stronger cache-poisoning and excessive-permission checks. They run under the existing Zizmor invocation after the binary update.
- Hadolint 2.15 adds checks for reserved build-stage names, secrets in `ARG`/`ENV`, `FROM --platform=$TARGETPLATFORM`, nonnumeric users, root-context copies, and untrusted registries. They run under the existing Hadolint invocation.
- MegaLinter v9.5-v9.6 adds clearer skipped-linter reasons and structured notices, removes sibling-Docker execution and Docker-socket exposure, adds Betterleaks, and fixes ansible-lint concurrency and Checkov temporary-path handling.

## Deliberate holds

- TypeScript stays at 6.0.2. TypeScript 7.0.2 is current, but `typescript-eslint` 8.65.0 declares support below TypeScript 6.1; crossing that peer boundary would make the lint image internally unsupported.
- Ruff preview remains disabled. Enabling a changing preview rule set is a policy decision and should be introduced with repository-specific finding counts and suppression guidance.
- MegaLinter's optional non-root execution is not enabled in this slice. Changing the container user affects bind-mount ownership and needs a dedicated consumer compatibility test.
- OSV-Scanner is not added merely because MegaLinter now exposes it. Trivy remains the vulnerability authority; adding a second scanner needs evidence that it catches a material gap without duplicating noise and database cost.

## Acceptance and follow-ups

The acceptance oracle is the repository's GitHub image workflow: build the exact branch image for amd64 and arm64, run every `.ci.json` command inside it, and run the image against this repository. Local Docker cannot currently provide that oracle because its snapshot store is corrupt.

Executable follow-ups, intentionally outside this bounded update:

1. Sample the new Ruff preview rules against the main homelab consumers, record finding counts, and enable only rules with actionable signal.
2. Run the image as MegaLinter's non-root user against bind mounts created by Linux and macOS Docker, then document or reject the ownership change.
3. Compare OSV-Scanner and Trivy on the same locked dependency fixtures before deciding whether OSV adds useful coverage.
4. Upgrade TypeScript only when the selected `typescript-eslint` release declares support for TypeScript 7 and the representative TS/TSX fixture passes.
