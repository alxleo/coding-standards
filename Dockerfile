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
  license-checker@25.0.1

# zizmor — GitHub Actions security scanner
RUN pip install --no-cache-dir zizmor==1.23.1

# PMD-CPD — copy-paste detector (replaces jscpd, ~50x faster)
RUN PMD_VERSION="7.12.0" && \
  PMD_SHA256="418dd819d38a16a49d7f345ef9a0a51e9f53e99f022d8b0722de77b7049bb8b8" && \
  curl -fsSL "https://github.com/pmd/pmd/releases/download/pmd_releases%2F${PMD_VERSION}/pmd-dist-${PMD_VERSION}-bin.zip" \
    -o /tmp/pmd.zip && \
  echo "${PMD_SHA256}  /tmp/pmd.zip" | sha256sum -c - && \
  unzip -q /tmp/pmd.zip -d /opt && \
  ln -s /opt/pmd-bin-${PMD_VERSION}/bin/pmd /usr/local/bin/pmd && \
  rm /tmp/pmd.zip

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

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

# ── Mechanism scripts (drift checker, expiry enforcer) ────────
COPY scripts/ci/check-drift.sh scripts/ci/check-expiry.py /opt/coding-standards/scripts/
RUN chmod +x /opt/coding-standards/scripts/check-drift.sh

# ── Linter config files ──────────────────────────────────────
# Baked into image at /opt/coding-standards/configs
# LINTER_RULES_PATH in .mega-linter.yml points here
COPY lint-configs-626465/ /opt/coding-standards/configs/

# ── Default config ────────────────────────────────────────────
# Baseline .mega-linter.yml baked into image and used by default via
# MEGALINTER_CONFIG. When set, this env var takes absolute precedence —
# a workspace .mega-linter.yml will NOT override it.
# Consumer repos that need a different config should override
# MEGALINTER_CONFIG at runtime:
#   docker run -e MEGALINTER_CONFIG=".mega-linter.yml" ...
COPY .mega-linter-default.yml /opt/coding-standards/.mega-linter.yml
ENV MEGALINTER_CONFIG="/opt/coding-standards/.mega-linter.yml"
