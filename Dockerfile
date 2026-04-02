# coding-standards lint image — Alpine multi-arch
#
# Built from python:3.13-alpine (not cupcake) for native arm64 support.
# MegaLinter engine installed via pip; all linter binaries installed explicitly.
#
# Optimizations: BuildKit cache mounts (npm/pip), parallel schema downloads,
# combined binary layer, node_modules pruning, semgrep rules cached as JSON.

FROM python:3.13-alpine3.23

LABEL org.opencontainers.image.source="https://github.com/alxleo/coding-standards"
LABEL org.opencontainers.image.description="Centralized linting image — MegaLinter + custom tools (multi-arch)"

SHELL ["/bin/sh", "-o", "pipefail", "-c"]

# ── System dependencies ──────────────────────────────────────
# hadolint ignore=DL3018
RUN apk add --no-cache \
  bash git curl unzip tar gzip xz ca-certificates gnupg \
  nodejs npm \
  openjdk21-jre-headless \
  build-base musl-dev libffi-dev

# Switch to bash for pipefail support in subsequent RUN steps
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# ── MegaLinter engine + Python linters (single layer) ────────
# hadolint ignore=DL3013,DL3059
RUN --mount=type=cache,target=/root/.cache/pip \
  pip install --no-cache-dir --no-compile \
  "megalinter @ git+https://github.com/oxsecurity/megalinter.git@v9.4.0" \
  semgrep==1.153.1 \
  ruff==0.15.4 \
  codespell==2.4.1 \
  ansible-lint==26.2.0 \
  sqlfluff==4.0.4 \
  zizmor==1.23.1 \
  vulture==2.14 \
  deptry==0.22.0 \
  networkx==3.6.1 \
  pydantic==2.12.5 \
  import-linter==2.4 \
  rumdl==0.1.64 && \
  apk del build-base musl-dev libffi-dev

# ── npm tools (single layer, cache mount) ────────────────────
# Includes cupcake-provided tools (eslint, prettier, v8r, stylelint, htmlhint, ls-lint)
# plus our custom additions. Versions pinned to match cupcake baseline.
# hadolint ignore=DL3059
RUN --mount=type=cache,target=/root/.npm \
  npm install -g \
  eslint@8.57.1 \
  prettier@3.8.1 \
  v8r@6.0.0 \
  stylelint@16.26.1 \
  htmlhint@1.9.1 \
  @ls-lint/ls-lint@2.3.1 \
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
  publint@0.3.18 \
  @arethetypeswrong/cli@0.18.2 \
  eslint-plugin-i18next@6.1.3 \
  @stoplight/spectral-cli@6.17.0 && \
  find /usr/local/lib/node_modules -type d \( -name "test" -o -name "tests" -o -name "docs" \) -exec rm -rf {} + 2>/dev/null; \
  find /usr/local/lib/node_modules -type f \( -name "*.md" -o -name "*.markdown" -o -name "LICENSE*" -o -name "CHANGELOG*" \) -exec rm -f {} + 2>/dev/null; \
  true

# ── Binary tools (combined layer, SHA-pinned, TARGETARCH) ────
# All checksums looked up from GitHub release pages, never guessed.
# renovate: datasource annotations are inline where applicable.
ARG TARGETARCH=amd64
# hadolint ignore=DL3059
RUN set -eux && \
  # ── shellcheck ──
  SHELLCHECK_VERSION="0.11.0" && \
  SHELLCHECK_SHA256_amd64="8c3be12b05d5c177a04c29e3c78ce89ac86f1595681cab149b65b97c4e227198" && \
  SHELLCHECK_SHA256_arm64="12b331c1d2db6b9eb13cfca64306b1b157a86eb69db83023e261eaa7e7c14588" && \
  SHELLCHECK_SHA256=$([ "$TARGETARCH" = "arm64" ] && echo "$SHELLCHECK_SHA256_arm64" || echo "$SHELLCHECK_SHA256_amd64") && \
  SHELLCHECK_ARCH=$([ "$TARGETARCH" = "arm64" ] && echo "aarch64" || echo "x86_64") && \
  curl -fsSL "https://github.com/koalaman/shellcheck/releases/download/v${SHELLCHECK_VERSION}/shellcheck-v${SHELLCHECK_VERSION}.linux.${SHELLCHECK_ARCH}.tar.xz" \
    -o /tmp/shellcheck.tar.xz && \
  echo "${SHELLCHECK_SHA256}  /tmp/shellcheck.tar.xz" | sha256sum -c - && \
  tar -xJf /tmp/shellcheck.tar.xz -C /usr/local/bin --strip-components=1 "shellcheck-v${SHELLCHECK_VERSION}/shellcheck" && \
  rm /tmp/shellcheck.tar.xz && \
  # ── hadolint (raw binary) ──
  HADOLINT_VERSION="2.14.0" && \
  HADOLINT_SHA256_amd64="6bf226944684f56c84dd014e8b979d27425c0148f61b3bd99bcc6f39e9dc5a47" && \
  HADOLINT_SHA256_arm64="331f1d3511b84a4f1e3d18d52fec284723e4019552f4f47b19322a53ce9a40ed" && \
  HADOLINT_SHA256=$([ "$TARGETARCH" = "arm64" ] && echo "$HADOLINT_SHA256_arm64" || echo "$HADOLINT_SHA256_amd64") && \
  HADOLINT_ARCH=$([ "$TARGETARCH" = "arm64" ] && echo "arm64" || echo "x86_64") && \
  curl -fsSL "https://github.com/hadolint/hadolint/releases/download/v${HADOLINT_VERSION}/hadolint-linux-${HADOLINT_ARCH}" \
    -o /usr/local/bin/hadolint && \
  echo "${HADOLINT_SHA256}  /usr/local/bin/hadolint" | sha256sum -c - && \
  chmod +x /usr/local/bin/hadolint && \
  # ── actionlint ──
  ACTIONLINT_VERSION="1.7.12" && \
  ACTIONLINT_SHA256_amd64="8aca8db96f1b94770f1b0d72b6dddcb1ebb8123cb3712530b08cc387b349a3d8" && \
  ACTIONLINT_SHA256_arm64="325e971b6ba9bfa504672e29be93c24981eeb1c07576d730e9f7c8805afff0c6" && \
  ACTIONLINT_SHA256=$([ "$TARGETARCH" = "arm64" ] && echo "$ACTIONLINT_SHA256_arm64" || echo "$ACTIONLINT_SHA256_amd64") && \
  curl -fsSL "https://github.com/rhysd/actionlint/releases/download/v${ACTIONLINT_VERSION}/actionlint_${ACTIONLINT_VERSION}_linux_${TARGETARCH}.tar.gz" \
    -o /tmp/actionlint.tar.gz && \
  echo "${ACTIONLINT_SHA256}  /tmp/actionlint.tar.gz" | sha256sum -c - && \
  tar -xzf /tmp/actionlint.tar.gz -C /usr/local/bin actionlint && \
  rm /tmp/actionlint.tar.gz && \
  # ── gitleaks ──
  GITLEAKS_VERSION="8.30.1" && \
  GITLEAKS_SHA256_amd64="551f6fc83ea457d62a0d98237cbad105af8d557003051f41f3e7ca7b3f2470eb" && \
  GITLEAKS_SHA256_arm64="e4a487ee7ccd7d3a7f7ec08657610aa3606637dab924210b3aee62570fb4b080" && \
  GITLEAKS_SHA256=$([ "$TARGETARCH" = "arm64" ] && echo "$GITLEAKS_SHA256_arm64" || echo "$GITLEAKS_SHA256_amd64") && \
  GITLEAKS_ARCH=$([ "$TARGETARCH" = "arm64" ] && echo "arm64" || echo "x64") && \
  curl -fsSL "https://github.com/gitleaks/gitleaks/releases/download/v${GITLEAKS_VERSION}/gitleaks_${GITLEAKS_VERSION}_linux_${GITLEAKS_ARCH}.tar.gz" \
    -o /tmp/gitleaks.tar.gz && \
  echo "${GITLEAKS_SHA256}  /tmp/gitleaks.tar.gz" | sha256sum -c - && \
  tar -xzf /tmp/gitleaks.tar.gz -C /usr/local/bin gitleaks && \
  rm /tmp/gitleaks.tar.gz && \
  # ── trivy (pinned: supply chain compromise in v0.69.4-6) ──
  TRIVY_VERSION="0.69.3" && \
  TRIVY_SHA256_amd64="1816b632dfe529869c740c0913e36bd1629cb7688bd5634f4a858c1d57c88b75" && \
  TRIVY_SHA256_arm64="7e3924a974e912e57b4a99f65ece7931f8079584dae12eb7845024f97087bdfd" && \
  TRIVY_SHA256=$([ "$TARGETARCH" = "arm64" ] && echo "$TRIVY_SHA256_arm64" || echo "$TRIVY_SHA256_amd64") && \
  TRIVY_ARCH=$([ "$TARGETARCH" = "arm64" ] && echo "ARM64" || echo "64bit") && \
  curl -fsSL "https://github.com/aquasecurity/trivy/releases/download/v${TRIVY_VERSION}/trivy_${TRIVY_VERSION}_Linux-${TRIVY_ARCH}.tar.gz" \
    -o /tmp/trivy.tar.gz && \
  echo "${TRIVY_SHA256}  /tmp/trivy.tar.gz" | sha256sum -c - && \
  tar -xzf /tmp/trivy.tar.gz -C /usr/local/bin trivy && \
  rm /tmp/trivy.tar.gz && \
  # ── tflint ──
  TFLINT_VERSION="0.61.0" && \
  TFLINT_SHA256_amd64="ca4e4e8cb7cc3436f2b6979e9c4fd4e2623a66fcca1ad1fe12f8669967636ae2" && \
  TFLINT_SHA256_arm64="999c25cfdb5208fe1133dec6b219e666a39fc2a7a0786a781dc9924ea5945ebf" && \
  TFLINT_SHA256=$([ "$TARGETARCH" = "arm64" ] && echo "$TFLINT_SHA256_arm64" || echo "$TFLINT_SHA256_amd64") && \
  curl -fsSL "https://github.com/terraform-linters/tflint/releases/download/v${TFLINT_VERSION}/tflint_linux_${TARGETARCH}.zip" \
    -o /tmp/tflint.zip && \
  echo "${TFLINT_SHA256}  /tmp/tflint.zip" | sha256sum -c - && \
  unzip -q /tmp/tflint.zip -d /usr/local/bin && \
  rm /tmp/tflint.zip && \
  # ── editorconfig-checker ──
  EC_VERSION="3.6.1" && \
  EC_SHA256_amd64="cd32084fce5f3d49ba49697f362ac3a114989715c98819303247dd54c1f368b0" && \
  EC_SHA256_arm64="a471181b0741982afa4f3dbc1e433b6caa0c5e6daad580572841884fd9957220" && \
  EC_SHA256=$([ "$TARGETARCH" = "arm64" ] && echo "$EC_SHA256_arm64" || echo "$EC_SHA256_amd64") && \
  curl -fsSL "https://github.com/editorconfig-checker/editorconfig-checker/releases/download/v${EC_VERSION}/ec-linux-${TARGETARCH}.tar.gz" \
    -o /tmp/ec.tar.gz && \
  echo "${EC_SHA256}  /tmp/ec.tar.gz" | sha256sum -c - && \
  tar -xzf /tmp/ec.tar.gz -C /usr/local/bin --strip-components=1 && \
  mv /usr/local/bin/ec-linux-${TARGETARCH} /usr/local/bin/editorconfig-checker 2>/dev/null || true && \
  rm /tmp/ec.tar.gz && \
  # ── kubeconform ──
  KUBECONFORM_VERSION="0.7.0" && \
  KUBECONFORM_SHA256_amd64="c31518ddd122663b3f3aa874cfe8178cb0988de944f29c74a0b9260920d115d3" && \
  KUBECONFORM_SHA256_arm64="cc907ccf9e3c34523f0f32b69745265e0a6908ca85b92f41931d4537860eb83c" && \
  KUBECONFORM_SHA256=$([ "$TARGETARCH" = "arm64" ] && echo "$KUBECONFORM_SHA256_arm64" || echo "$KUBECONFORM_SHA256_amd64") && \
  curl -fsSL "https://github.com/yannh/kubeconform/releases/download/v${KUBECONFORM_VERSION}/kubeconform-linux-${TARGETARCH}.tar.gz" \
    -o /tmp/kubeconform.tar.gz && \
  echo "${KUBECONFORM_SHA256}  /tmp/kubeconform.tar.gz" | sha256sum -c - && \
  tar -xzf /tmp/kubeconform.tar.gz -C /usr/local/bin kubeconform && \
  rm /tmp/kubeconform.tar.gz && \
  # ── lychee ──
  LYCHEE_VERSION="0.23.0" && \
  LYCHEE_SHA256_amd64="5538440d2c69a45a0a09983271e5dee0c2fe7137d8035d25b2632e10a66a090a" && \
  LYCHEE_SHA256_arm64="4eb6ff3ccd40dbb71843c41429683d3c60fe3b33b2042ffbbff9bb21cedacb39" && \
  LYCHEE_SHA256=$([ "$TARGETARCH" = "arm64" ] && echo "$LYCHEE_SHA256_arm64" || echo "$LYCHEE_SHA256_amd64") && \
  LYCHEE_ARCH=$([ "$TARGETARCH" = "arm64" ] && echo "aarch64" || echo "x86_64") && \
  curl -fsSL "https://github.com/lycheeverse/lychee/releases/download/lychee-v${LYCHEE_VERSION}/lychee-${LYCHEE_ARCH}-unknown-linux-musl.tar.gz" \
    -o /tmp/lychee.tar.gz && \
  echo "${LYCHEE_SHA256}  /tmp/lychee.tar.gz" | sha256sum -c - && \
  tar -xzf /tmp/lychee.tar.gz -C /usr/local/bin lychee && \
  rm /tmp/lychee.tar.gz && \
  # dotenv-linter: skipped — glibc-only binary, no musl build available.
  # Warn-tier .env linter. Re-add if upstream publishes musl builds.
  #

  # ── golangci-lint (new addition) ──
  GOLANGCI_VERSION="2.11.4" && \
  GOLANGCI_SHA256_amd64="200c5b7503f67b59a6743ccf32133026c174e272b930ee79aa2aa6f37aca7ef1" && \
  GOLANGCI_SHA256_arm64="3bcfa2e6f3d32b2bf5cd75eaa876447507025e0303698633f722a05331988db4" && \
  GOLANGCI_SHA256=$([ "$TARGETARCH" = "arm64" ] && echo "$GOLANGCI_SHA256_arm64" || echo "$GOLANGCI_SHA256_amd64") && \
  curl -fsSL "https://github.com/golangci/golangci-lint/releases/download/v${GOLANGCI_VERSION}/golangci-lint-${GOLANGCI_VERSION}-linux-${TARGETARCH}.tar.gz" \
    -o /tmp/golangci-lint.tar.gz && \
  echo "${GOLANGCI_SHA256}  /tmp/golangci-lint.tar.gz" | sha256sum -c - && \
  tar -xzf /tmp/golangci-lint.tar.gz -C /usr/local/bin --strip-components=1 "golangci-lint-${GOLANGCI_VERSION}-linux-${TARGETARCH}/golangci-lint" && \
  rm /tmp/golangci-lint.tar.gz && \
  # ── shfmt ──
  SHFMT_VERSION="3.13.0" && \
  SHFMT_SHA256_amd64="70aa99784703a8d6569bbf0b1e43e1a91906a4166bf1a79de42050a6d0de7551" && \
  SHFMT_SHA256_arm64="2091a31afd47742051a77bf7cfd175533ab07e924c20ef3151cd108fa1cab5b0" && \
  SHFMT_SHA256=$([ "$TARGETARCH" = "arm64" ] && echo "$SHFMT_SHA256_arm64" || echo "$SHFMT_SHA256_amd64") && \
  curl -fsSL "https://github.com/mvdan/sh/releases/download/v${SHFMT_VERSION}/shfmt_v${SHFMT_VERSION}_linux_${TARGETARCH}" \
    -o /usr/local/bin/shfmt && \
  echo "${SHFMT_SHA256}  /usr/local/bin/shfmt" | sha256sum -c - && \
  chmod +x /usr/local/bin/shfmt && \
  # ── checkmake (Makefile linter) ──
  CHECKMAKE_VERSION="0.3.2" && \
  CHECKMAKE_SHA256_amd64="e2effb876913f3ee2caef0ba35f6202c5e8a3cd55a077d8d2b9ce2034257b6af" && \
  CHECKMAKE_SHA256_arm64="409167c4abb99407bd232c3bbd351b8a39df57997feafde5a08bddffb0f2dcb4" && \
  CHECKMAKE_SHA256=$([ "$TARGETARCH" = "arm64" ] && echo "$CHECKMAKE_SHA256_arm64" || echo "$CHECKMAKE_SHA256_amd64") && \
  curl -fsSL "https://github.com/mrtazz/checkmake/releases/download/v${CHECKMAKE_VERSION}/checkmake-v${CHECKMAKE_VERSION}.linux.${TARGETARCH}" \
    -o /usr/local/bin/checkmake && \
  echo "${CHECKMAKE_SHA256}  /usr/local/bin/checkmake" | sha256sum -c - && \
  chmod +x /usr/local/bin/checkmake && \
  # ── PMD-CPD (Java, arch-agnostic) ──
  PMD_VERSION="7.12.0" && \
  PMD_SHA256="418dd819d38a16a49d7f345ef9a0a51e9f53e99f022d8b0722de77b7049bb8b8" && \
  curl -fsSL "https://github.com/pmd/pmd/releases/download/pmd_releases%2F${PMD_VERSION}/pmd-dist-${PMD_VERSION}-bin.zip" \
    -o /tmp/pmd.zip && \
  echo "${PMD_SHA256}  /tmp/pmd.zip" | sha256sum -c - && \
  unzip -q /tmp/pmd.zip -d /opt && \
  ln -s /opt/pmd-bin-${PMD_VERSION}/bin/pmd /usr/local/bin/pmd && \
  rm /tmp/pmd.zip && \
  # ── caddy (Caddyfile formatter) ──
  CADDY_VERSION="2.11.2" && \
  CADDY_SHA256_amd64="94391dfefe1f278ac8f387ab86162f0e88d87ff97df367f360e51e3cda3df56f" && \
  CADDY_SHA256_arm64="b9d88bec4254d0a98bd415ad60f97f37e4222dec96235c00b442437f5e303a32" && \
  CADDY_SHA256=$([ "$TARGETARCH" = "arm64" ] && echo "$CADDY_SHA256_arm64" || echo "$CADDY_SHA256_amd64") && \
  curl -fsSL "https://github.com/caddyserver/caddy/releases/download/v${CADDY_VERSION}/caddy_${CADDY_VERSION}_linux_${TARGETARCH}.tar.gz" \
    -o /tmp/caddy.tar.gz && \
  echo "${CADDY_SHA256}  /tmp/caddy.tar.gz" | sha256sum -c - && \
  tar -xzf /tmp/caddy.tar.gz -C /usr/local/bin caddy && \
  chmod +x /usr/local/bin/caddy && \
  rm /tmp/caddy.tar.gz && \
  # ── just (task runner) ──
  JUST_VERSION="1.48.1" && \
  JUST_SHA256_amd64="9293e553ce401d1b524bf4e104918f72f268e3f9c6827e0055fe98d84a1b2522" && \
  JUST_SHA256_arm64="3308721b991cf88cf2b9bbb3b31ac40550ec61a0c9b6fc011564e25e87964030" && \
  JUST_SHA256=$([ "$TARGETARCH" = "arm64" ] && echo "$JUST_SHA256_arm64" || echo "$JUST_SHA256_amd64") && \
  JUST_ARCH=$([ "$TARGETARCH" = "arm64" ] && echo "aarch64" || echo "x86_64") && \
  curl -fsSL "https://github.com/casey/just/releases/download/${JUST_VERSION}/just-${JUST_VERSION}-${JUST_ARCH}-unknown-linux-musl.tar.gz" \
    -o /tmp/just.tar.gz && \
  echo "${JUST_SHA256}  /tmp/just.tar.gz" | sha256sum -c - && \
  tar -xzf /tmp/just.tar.gz -C /usr/local/bin just && \
  chmod +x /usr/local/bin/just && \
  rm /tmp/just.tar.gz && \
  # ── conftest (OPA/Rego policy runner) ──
  CONFTEST_VERSION="0.58.0" && \
  CONFTEST_SHA256_amd64="0863738f798c1850269a121ef56c2df1ab88074204c480f282f3baf2726898fd" && \
  CONFTEST_SHA256_arm64="c2fc23f46275b25a0fa3e132ddea4cb48c86669a380b1faf9c99dc0877a12ce6" && \
  CONFTEST_SHA256=$([ "$TARGETARCH" = "arm64" ] && echo "$CONFTEST_SHA256_arm64" || echo "$CONFTEST_SHA256_amd64") && \
  CONFTEST_ARCH=$([ "$TARGETARCH" = "arm64" ] && echo "arm64" || echo "x86_64") && \
  curl -fsSL "https://github.com/open-policy-agent/conftest/releases/download/v${CONFTEST_VERSION}/conftest_${CONFTEST_VERSION}_Linux_${CONFTEST_ARCH}.tar.gz" \
    -o /tmp/conftest.tar.gz && \
  echo "${CONFTEST_SHA256}  /tmp/conftest.tar.gz" | sha256sum -c - && \
  tar -xzf /tmp/conftest.tar.gz -C /usr/local/bin conftest && \
  rm /tmp/conftest.tar.gz && \
  # ── Trivy DB pre-cache ──
  trivy --cache-dir /root/.cache/trivy fs --download-db-only --db-repository ghcr.io/aquasecurity/trivy-db:2 --no-progress 2>/dev/null || true

# ── Schema + semgrep rule download ───────────────────────────
COPY scripts/download-schemas.sh scripts/download-semgrep-rules.sh /tmp/
RUN chmod +x /tmp/download-schemas.sh /tmp/download-semgrep-rules.sh && \
    /tmp/download-schemas.sh /opt/coding-standards/schemas && \
    /tmp/download-semgrep-rules.sh /rules && \
    rm /tmp/download-schemas.sh /tmp/download-semgrep-rules.sh

# ── Plugin descriptors ────────────────────────────────────────
COPY plugins/ /mega-linter-plugin-custom/

# ── Centralized semgrep rules ─────────────────────────────────
COPY semgrep-rules/ /rules/custom/

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

# ── Consumer justfile (progressive disclosure) ──────────────
COPY consumer.just /opt/coding-standards/consumer.just

# ── Generated catalog ────────────────────────────────────────
COPY docs/catalog.md /opt/coding-standards/docs/catalog.md

# ── Default config ────────────────────────────────────────────
COPY .mega-linter-default.yml /opt/coding-standards/.mega-linter-default.yml
