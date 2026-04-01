# coding-standards lint image
# MegaLinter cupcake base + custom project analyzers
#
# Optimizations: BuildKit cache mounts (npm/pip), parallel schema downloads,
# combined binary layer, node_modules pruning, runtime pruning.

# renovate: datasource=docker depName=oxsecurity/megalinter-cupcake
FROM oxsecurity/megalinter-cupcake:v9@sha256:e4ac6e253ef839c448cfe36a4659c8a56c7244d93c41124801511ba2ef5e08b9

LABEL org.opencontainers.image.source="https://github.com/alxleo/coding-standards"
LABEL org.opencontainers.image.description="Centralized linting image — MegaLinter cupcake + custom tools"

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# ── npm tools (single layer, cache mount) ────────────────────
# hadolint ignore=DL3059
RUN --mount=type=cache,target=/root/.npm \
  npm install -g \
  @commitlint/cli@20.5.0 \
  @commitlint/config-conventional@20.5.0 \
  dclint@3.1.0 \
  pyright@1.1.408 \
  typescript@6.0.2 \
  knip@6.1.0 \
  dependency-cruiser@17.3.10 \
  license-checker@25.0.1 \
  eslint-plugin-unicorn@64.0.0 \
  eslint-plugin-security@4.0.0 \
  eslint-plugin-sonarjs@4.0.2 \
  eslint-plugin-testing-library@7.16.2 \
  oxlint@1.57.0 \
  type-coverage@2.29.7 \
  typescript-coverage-report@1.1.1 \
  publint@0.3.18 \
  @arethetypeswrong/cli@0.18.2 \
  eslint-plugin-i18next@6.1.3 && \
  find /usr/local/lib/node_modules -type d \( -name "test" -o -name "tests" -o -name "docs" \) -exec rm -rf {} + && \
  find /usr/local/lib/node_modules -type f \( -name "*.md" -o -name "*.markdown" -o -name "LICENSE*" -o -name "CHANGELOG*" \) -exec rm -f {} +

# ── Python tools (cache mount, no-compile) ───────────────────
# hadolint ignore=DL3059
RUN --mount=type=cache,target=/root/.cache/pip \
  pip install --no-cache-dir --no-compile \
  zizmor==1.23.1 \
  vulture==2.14 \
  deptry==0.22.0 \
  networkx==3.6.1 \
  pydantic==2.12.5 \
  import-linter==2.4

# ── Binary tools (combined layer, SHA-pinned) ────────────────
ARG TARGETARCH=amd64
RUN PMD_VERSION="7.12.0" && \
  PMD_SHA256="418dd819d38a16a49d7f345ef9a0a51e9f53e99f022d8b0722de77b7049bb8b8" && \
  CADDY_VERSION="2.11.2" && \
  CADDY_SHA256="94391dfefe1f278ac8f387ab86162f0e88d87ff97df367f360e51e3cda3df56f" && \
  JUST_VERSION="1.48.1" && \
  JUST_SHA256="9293e553ce401d1b524bf4e104918f72f268e3f9c6827e0055fe98d84a1b2522" && \
  CONFTEST_SHA256="0863738f798c1850269a121ef56c2df1ab88074204c480f282f3baf2726898fd" && \
  curl -fsSL "https://github.com/pmd/pmd/releases/download/pmd_releases%2F${PMD_VERSION}/pmd-dist-${PMD_VERSION}-bin.zip" \
    -o /tmp/pmd.zip && \
  echo "${PMD_SHA256}  /tmp/pmd.zip" | sha256sum -c - && \
  unzip -q /tmp/pmd.zip -d /opt && \
  ln -s /opt/pmd-bin-${PMD_VERSION}/bin/pmd /usr/local/bin/pmd && \
  rm /tmp/pmd.zip && \
  curl -fsSL "https://github.com/caddyserver/caddy/releases/download/v${CADDY_VERSION}/caddy_${CADDY_VERSION}_linux_${TARGETARCH}.tar.gz" \
    -o /tmp/caddy.tar.gz && \
  echo "${CADDY_SHA256}  /tmp/caddy.tar.gz" | sha256sum -c - && \
  tar -xzf /tmp/caddy.tar.gz -C /usr/local/bin caddy && \
  chmod +x /usr/local/bin/caddy && \
  rm /tmp/caddy.tar.gz && \
  curl -fsSL "https://github.com/casey/just/releases/download/${JUST_VERSION}/just-${JUST_VERSION}-x86_64-unknown-linux-musl.tar.gz" \
    -o /tmp/just.tar.gz && \
  echo "${JUST_SHA256}  /tmp/just.tar.gz" | sha256sum -c - && \
  tar -xzf /tmp/just.tar.gz -C /usr/local/bin just && \
  chmod +x /usr/local/bin/just && \
  rm /tmp/just.tar.gz && \
  curl -fsSL "https://github.com/open-policy-agent/conftest/releases/download/v0.58.0/conftest_0.58.0_Linux_x86_64.tar.gz" \
    -o /tmp/conftest.tar.gz && \
  echo "${CONFTEST_SHA256}  /tmp/conftest.tar.gz" | sha256sum -c - && \
  tar xzf /tmp/conftest.tar.gz -C /usr/local/bin conftest && \
  rm /tmp/conftest.tar.gz

# ── Schema download (parallel) ───────────────────────────────
COPY scripts/download-schemas.sh /tmp/download-schemas.sh
RUN chmod +x /tmp/download-schemas.sh && \
    /tmp/download-schemas.sh /opt/coding-standards/schemas && \
    rm /tmp/download-schemas.sh

# ── Plugin descriptors ────────────────────────────────────────
COPY plugins/ /mega-linter-plugin-custom/

# ── Centralized semgrep rules ─────────────────────────────────
COPY semgrep-rules/ /opt/coding-standards/semgrep-rules/

# ── Shared Conftest policies ─────────────────────────────────
COPY policies/ /opt/coding-standards/policies/

# ── Mechanism scripts + reporting ─────────────────────────────
COPY --chmod=755 scripts/ci/check-drift.sh scripts/ci/check-expiry.py scripts/megalinter_report_statuses.py scripts/generate_repo_manifest.py scripts/generate_catalog.py scripts/manifest_schema.py scripts/show_warnings.py scripts/blast_radius.py scripts/show_config.py /opt/coding-standards/scripts/

# ── Linter config files ──────────────────────────────────────
COPY lint-configs/ /opt/coding-standards/configs/

# ── Entrypoint ───────────────────────────────────────────────
COPY --chmod=755 scripts/entrypoint.sh /opt/coding-standards/entrypoint.sh
# MegaLinter requires root for tool installs and workspace writes.
# nosemgrep: dockerfile.security.missing-user-entrypoint.missing-user-entrypoint
ENTRYPOINT ["/bin/bash", "/opt/coding-standards/entrypoint.sh"]

# ── Generated catalog ────────────────────────────────────────
COPY docs/catalog.md /opt/coding-standards/docs/catalog.md

# ── Default config ────────────────────────────────────────────
COPY .mega-linter-default.yml /opt/coding-standards/.mega-linter-default.yml
