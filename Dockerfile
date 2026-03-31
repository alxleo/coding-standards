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

LABEL org.opencontainers.image.source="https://github.com/alxleo/coding-standards"
LABEL org.opencontainers.image.description="Centralized linting image — MegaLinter cupcake + custom tools"

# Patch base image CVEs (MegaLinter may lag behind Alpine security updates)
# glibc-bin trigger may fail in MegaLinter's custom Alpine — allow partial success
# hadolint ignore=DL3018,DL3059
RUN apk upgrade --no-cache; exit 0

# ── Custom tool installs ──────────────────────────────────────
# Tools MegaLinter doesn't include natively.
# Each gets a plugin descriptor in plugins/ for MegaLinter orchestration.

# trivy — vulnerability + IaC scanner (pinned, pre-compromise)
COPY --from=trivy /usr/local/bin/trivy /usr/local/bin/trivy
# Pre-cache trivy vulnerability DB (saves ~10s per run)
RUN trivy fs --download-db-only --no-progress --cache-dir /root/.cache/trivy

# npm-based tools (single layer to reduce image size)
RUN npm install -g \
  @commitlint/cli@20.5.0 \
  @commitlint/config-conventional@20.5.0 \
  dclint@3.1.0 \
  pyright@1.1.408 \
  typescript@6.0.2 \
  knip@6.1.0 \
  dependency-cruiser@17.3.10 \
  license-checker@25.0.1 \
  eslint-plugin-unicorn@62.0.0 \
  eslint-plugin-security@3.0.1 \
  eslint-plugin-sonarjs@3.0.2 \
  eslint-plugin-testing-library@7.4.0 \
  oxlint@1.39.0 \
  type-coverage@2.29.7 \
  typescript-coverage-report@1.0.0

# zizmor — GitHub Actions security scanner
RUN pip install --no-cache-dir zizmor==1.23.1

# Python project analysis tools
RUN pip install --no-cache-dir vulture==2.14 deptry==0.22.0 import-linter==2.4

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# PMD-CPD — copy-paste detector (replaces jscpd, ~50x faster)
RUN PMD_VERSION="7.12.0" && \
  PMD_SHA256="418dd819d38a16a49d7f345ef9a0a51e9f53e99f022d8b0722de77b7049bb8b8" && \
  curl -fsSL "https://github.com/pmd/pmd/releases/download/pmd_releases%2F${PMD_VERSION}/pmd-dist-${PMD_VERSION}-bin.zip" \
    -o /tmp/pmd.zip && \
  echo "${PMD_SHA256}  /tmp/pmd.zip" | sha256sum -c - && \
  unzip -q /tmp/pmd.zip -d /opt && \
  ln -s /opt/pmd-bin-${PMD_VERSION}/bin/pmd /usr/local/bin/pmd && \
  rm /tmp/pmd.zip

# caddy — Caddyfile formatter (pinned version with checksum, multi-arch)
ARG TARGETARCH=amd64
RUN CADDY_VERSION="2.11.2" && \
  CADDY_SHA256="94391dfefe1f278ac8f387ab86162f0e88d87ff97df367f360e51e3cda3df56f" && \
  curl -fsSL "https://github.com/caddyserver/caddy/releases/download/v${CADDY_VERSION}/caddy_${CADDY_VERSION}_linux_${TARGETARCH}.tar.gz" \
    -o /tmp/caddy.tar.gz && \
  echo "${CADDY_SHA256}  /tmp/caddy.tar.gz" | sha256sum -c - && \
  tar -xzf /tmp/caddy.tar.gz -C /usr/local/bin caddy && \
  chmod +x /usr/local/bin/caddy && \
  rm /tmp/caddy.tar.gz

# just — justfile formatter (pinned version with checksum, no curl | bash)
RUN JUST_VERSION="1.48.1" && \
  JUST_SHA256="9293e553ce401d1b524bf4e104918f72f268e3f9c6827e0055fe98d84a1b2522" && \
  curl -fsSL "https://github.com/casey/just/releases/download/${JUST_VERSION}/just-${JUST_VERSION}-x86_64-unknown-linux-musl.tar.gz" \
    -o /tmp/just.tar.gz && \
  echo "${JUST_SHA256}  /tmp/just.tar.gz" | sha256sum -c - && \
  tar -xzf /tmp/just.tar.gz -C /usr/local/bin just && \
  chmod +x /usr/local/bin/just && \
  rm /tmp/just.tar.gz

# conftest — OPA/Rego policy engine for structural validation
RUN CONFTEST_SHA256="0863738f798c1850269a121ef56c2df1ab88074204c480f282f3baf2726898fd" && \
  curl -fsSL "https://github.com/open-policy-agent/conftest/releases/download/v0.58.0/conftest_0.58.0_Linux_x86_64.tar.gz" \
    -o /tmp/conftest.tar.gz && \
  echo "${CONFTEST_SHA256}  /tmp/conftest.tar.gz" | sha256sum -c - && \
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

# ── Mechanism scripts + reporting ─────────────────────────────
COPY scripts/ci/check-drift.sh scripts/ci/check-expiry.py scripts/report-statuses.py scripts/generate-repo-manifest.py scripts/generate-catalog.py scripts/manifest_schema.py scripts/show_warnings.py /opt/coding-standards/scripts/
RUN chmod +x /opt/coding-standards/scripts/check-drift.sh /opt/coding-standards/scripts/generate-repo-manifest.py

# ── Linter config files ──────────────────────────────────────
# Baked into image at /opt/coding-standards/configs
# LINTER_RULES_PATH in .mega-linter.yml points here
COPY lint-configs-626465/ /opt/coding-standards/configs/

# ── Default config ────────────────────────────────────────────
# Baked config used when no workspace .mega-linter.yml exists.
# Consumer repos use EXTENDS with a raw GitHub URL to inherit this:
#   EXTENDS: https://raw.githubusercontent.com/alxleo/coding-standards/main/.mega-linter-default.yml
# ── Entrypoint (command router) ──────────────────────────────
# Routes: lint [linter], fix, standards, catalog, help
# No args → falls through to MegaLinter's /entrypoint.sh
COPY scripts/entrypoint.sh /opt/coding-standards/entrypoint.sh
RUN chmod +x /opt/coding-standards/entrypoint.sh
ENTRYPOINT ["/bin/bash", "/opt/coding-standards/entrypoint.sh"]

# ── Generated catalog ────────────────────────────────────────
COPY docs/catalog.md /opt/coding-standards/docs/catalog.md

# ── Default config ────────────────────────────────────────────
# Consumer repos use EXTENDS with a raw GitHub URL to inherit this:
#   EXTENDS: https://raw.githubusercontent.com/alxleo/coding-standards/main/.mega-linter-default.yml
COPY .mega-linter-default.yml /opt/coding-standards/.mega-linter.yml
