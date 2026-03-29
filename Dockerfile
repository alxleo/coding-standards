# coding-standards lint image
# MegaLinter cupcake base + custom project analyzers
#
# Usage:
#   docker run --rm -v $PWD:/tmp/lint ghcr.io/alxleo/coding-standards:latest
#   docker run --rm -v $PWD:/tmp/lint -e APPLY_FIXES=all ghcr.io/alxleo/coding-standards:latest
#
# Build:
#   docker build -t coding-standards .
#
# All images SHA-pinned. Renovate automates digest updates.

# renovate: datasource=docker depName=ghcr.io/aquasecurity/trivy
FROM ghcr.io/aquasecurity/trivy:0.69.3@sha256:bcc376de8d77cfe086a917230e818dc9f8528e3c852f7b1aff648949b6258d1c AS trivy

# renovate: datasource=docker depName=oxsecurity/megalinter-cupcake
FROM oxsecurity/megalinter-cupcake:v9@sha256:e4ac6e253ef839c448cfe36a4659c8a56c7244d93c41124801511ba2ef5e08b9 AS base

# ── Custom tool installs ──────────────────────────────────────
# Tools MegaLinter doesn't include natively.
# Each gets a plugin descriptor in plugins/ for MegaLinter orchestration.

# trivy — vulnerability + IaC scanner (pinned, pre-compromise)
COPY --from=trivy /usr/local/bin/trivy /usr/local/bin/trivy
# Pre-cache trivy vulnerability DB (saves ~10s per run)
RUN trivy fs --download-db-only --no-progress --cache-dir /root/.cache/trivy

# npm-based tools (single layer to reduce image size)
# hadolint ignore=DL3016
RUN npm install -g \
  @commitlint/cli \
  @commitlint/config-conventional \
  dclint \
  pyright \
  typescript \
  knip \
  dependency-cruiser \
  license-checker

# zizmor — GitHub Actions security scanner
# hadolint ignore=DL3013
RUN pip install --no-cache-dir zizmor

# PMD-CPD — copy-paste detector (replaces jscpd, ~50x faster)
RUN curl -fsSL "https://github.com/pmd/pmd/releases/download/pmd_releases%2F7.12.0/pmd-dist-7.12.0-bin.zip" \
  -o /tmp/pmd.zip && \
  unzip -q /tmp/pmd.zip -d /opt && \
  ln -s /opt/pmd-bin-7.12.0/bin/pmd /usr/local/bin/pmd && \
  rm /tmp/pmd.zip

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# caddy — Caddyfile formatter
RUN curl -fsSL 'https://caddyserver.com/api/download?os=linux&arch=amd64' \
  -o /usr/local/bin/caddy && chmod +x /usr/local/bin/caddy

# just — justfile formatter
RUN curl -fsSL https://just.systems/install.sh | bash -s -- --to /usr/local/bin

# conftest — OPA/Rego policy engine for structural validation
RUN curl -fsSL "https://github.com/open-policy-agent/conftest/releases/download/v0.58.0/conftest_0.58.0_Linux_x86_64.tar.gz" \
  -o /tmp/conftest.tar.gz && \
  tar xzf /tmp/conftest.tar.gz -C /usr/local/bin conftest && \
  rm /tmp/conftest.tar.gz

# ── Schema download (v8r offline validation) ─────────────────
COPY scripts/download-schemas.sh /tmp/download-schemas.sh
RUN chmod +x /tmp/download-schemas.sh && \
    /tmp/download-schemas.sh /opt/coding-standards/schemas && \
    rm /tmp/download-schemas.sh

# ── Plugin descriptors ────────────────────────────────────────
# Tell MegaLinter how to invoke our custom tools
COPY plugins/ /mega-linter-plugin-custom/

# ── Centralized semgrep rules ─────────────────────────────────
COPY semgrep-rules/ /opt/coding-standards/semgrep-rules/

# ── Shared Conftest policies ─────────────────────────────────
COPY policies/ /opt/coding-standards/policies/

# ── Mechanism scripts (drift checker, expiry enforcer) ────────
COPY scripts/ci/check-drift.sh scripts/ci/check-expiry.py /opt/coding-standards/scripts/
RUN chmod +x /opt/coding-standards/scripts/check-drift.sh

# ── Linter config files ──────────────────────────────────────
# Baked into image at /opt/coding-standards/configs
# LINTER_RULES_PATH in .mega-linter.yml points here
COPY lint-configs-626465/ /opt/coding-standards/configs/

# ── Default config ────────────────────────────────────────────
# Baseline .mega-linter.yml baked into image. Consumer repos override by
# placing their own .mega-linter.yml in the workspace root (which takes
# precedence since MegaLinter checks /tmp/lint/ first).
COPY .mega-linter-default.yml /opt/coding-standards/.mega-linter.yml
ENV MEGALINTER_CONFIG="/opt/coding-standards/.mega-linter.yml"
