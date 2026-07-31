# coding-standards lint image — Alpine multi-arch
#
# Built from python:3.14-alpine (not cupcake) for native arm64 support.
# MegaLinter engine installed via pip; all linter binaries installed explicitly.
#
# Optimizations: BuildKit cache mounts (npm/pip), parallel schema downloads,
# combined binary layer, node_modules pruning, semgrep rules cached as JSON.

# renovate: datasource=docker depName=python
FROM python:3.14-alpine3.24@sha256:26730869004e2b9c4b9ad09cab8625e81d256d1ce97e72df5520e806b1709f92

LABEL org.opencontainers.image.source="https://github.com/alxleo/coding-standards"
LABEL org.opencontainers.image.description="Centralized linting image — MegaLinter + custom tools (multi-arch)"

SHELL ["/bin/sh", "-o", "pipefail", "-c"]

# ── System dependencies ──────────────────────────────────────
# hadolint ignore=DL3018
RUN apk add --no-cache \
  bash git curl unzip tar gzip xz ca-certificates gnupg gcompat \
  nodejs npm \
  openjdk21-jre-headless \
  build-base musl-dev libffi-dev

# Switch to bash for pipefail support in subsequent RUN steps
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# ── MegaLinter engine + Python linters (single layer) ────────
# Semgrep 1.171+ requires Click 8.4; SQLFluff 4.2 requires Click <8.4.
# hadolint ignore=DL3013,DL3059
RUN --mount=type=cache,target=/root/.cache/pip \
  pip install --no-cache-dir --no-compile \
  "megalinter @ git+https://github.com/oxsecurity/megalinter.git@v9.6.0" \
  typer==0.27.0 \
  semgrep==1.170.0 \
  ruff==0.16.1 \
  codespell==2.4.3 \
  ansible-lint==26.6.0 \
  sqlfluff==4.2.2 \
  zizmor==1.28.0 \
  vulture==2.16 \
  deptry==0.25.1 \
  networkx==3.6.1 \
  pydantic==2.13.4 \
  import-linter==2.13 \
  rumdl==0.2.47 && \
  apk del build-base musl-dev libffi-dev

# ── npm tools (single layer, cache mount) ────────────────────
# Independently pinned JavaScript linters and config plugins.
# TypeScript stays on 6.0.2 until typescript-eslint supports TypeScript 7.
# hadolint ignore=DL3059
RUN --mount=type=cache,target=/root/.npm \
  npm install -g \
  eslint@10.8.0 \
  @eslint/js@10.0.1 \
  prettier@3.9.6 \
  v8r@6.1.0 \
  stylelint@17.14.1 \
  htmlhint@1.9.2 \
  @ls-lint/ls-lint@2.3.1 \
  @commitlint/cli@21.2.1 \
  @commitlint/config-conventional@21.2.0 \
  dclint@3.1.0 \
  pyright@1.1.411 \
  typescript@6.0.2 \
  typescript-eslint@8.65.0 \
  knip@6.31.0 \
  dependency-cruiser@18.1.0 \
  license-checker@25.0.1 \
  @eslint-react/eslint-plugin@5.18.1 \
  eslint-plugin-import-x@4.17.1 \
  eslint-plugin-unicorn@72.0.0 \
  eslint-plugin-security@4.0.1 \
  eslint-plugin-sonarjs@4.2.0 \
  eslint-plugin-testing-library@7.16.2 \
  oxlint@1.76.0 \
  type-coverage@2.30.1 \
  publint@0.3.22 \
  @arethetypeswrong/cli@0.18.5 \
  eslint-plugin-i18next@6.1.5 \
  @stoplight/spectral-cli@6.16.2 && \
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
  # renovate: datasource=github-releases depName=koalaman/shellcheck
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
  # renovate: datasource=github-releases depName=hadolint/hadolint
  HADOLINT_VERSION="2.15.1" && \
  HADOLINT_SHA256_amd64="c7187db94eeeeca956519a6af171adc31453941a1e777961f6e680f697c8c507" && \
  HADOLINT_SHA256_arm64="f6198ef8090f404dbb771abfee086eb8c48ac177f30da7fd3510aca35b344b5d" && \
  HADOLINT_SHA256=$([ "$TARGETARCH" = "arm64" ] && echo "$HADOLINT_SHA256_arm64" || echo "$HADOLINT_SHA256_amd64") && \
  HADOLINT_ARCH=$([ "$TARGETARCH" = "arm64" ] && echo "arm64" || echo "x86_64") && \
  curl -fsSL "https://github.com/hadolint/hadolint/releases/download/v${HADOLINT_VERSION}/hadolint-linux-${HADOLINT_ARCH}" \
    -o /usr/local/bin/hadolint && \
  echo "${HADOLINT_SHA256}  /usr/local/bin/hadolint" | sha256sum -c - && \
  chmod +x /usr/local/bin/hadolint && \
  # ── actionlint ──
  # renovate: datasource=github-releases depName=rhysd/actionlint
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
  # renovate: datasource=github-releases depName=gitleaks/gitleaks
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
  # ── betterleaks (gitleaks successor; gitleaks retained for compatibility) ──
  # renovate: datasource=github-releases depName=betterleaks/betterleaks
  BETTERLEAKS_VERSION="1.7.3" && \
  BETTERLEAKS_SHA256_amd64="9d2ed6fc387bc1c3f95557d5539077b1ce422f0db5ec38db5f14a141ad2947bf" && \
  BETTERLEAKS_SHA256_arm64="0541cd2980964a6fb8ea768e8b9507c91a3c06229193462f33a3ecd9cb146b99" && \
  BETTERLEAKS_SHA256=$([ "$TARGETARCH" = "arm64" ] && echo "$BETTERLEAKS_SHA256_arm64" || echo "$BETTERLEAKS_SHA256_amd64") && \
  BETTERLEAKS_ARCH=$([ "$TARGETARCH" = "arm64" ] && echo "arm64" || echo "x64") && \
  curl -fsSL "https://github.com/betterleaks/betterleaks/releases/download/v${BETTERLEAKS_VERSION}/betterleaks_${BETTERLEAKS_VERSION}_linux_${BETTERLEAKS_ARCH}.tar.gz" \
    -o /tmp/betterleaks.tar.gz && \
  echo "${BETTERLEAKS_SHA256}  /tmp/betterleaks.tar.gz" | sha256sum -c - && \
  tar -xzf /tmp/betterleaks.tar.gz -C /usr/local/bin betterleaks && \
  rm /tmp/betterleaks.tar.gz && \
  # ── trivy (post-incident release; checksum-pinned) ──
  # renovate: datasource=github-releases depName=aquasecurity/trivy
  TRIVY_VERSION="0.72.0" && \
  TRIVY_SHA256_amd64="bbb64b9695866ce4a7a8f5c9592002c5961cab378577fa3f8a040df362b9b2ea" && \
  TRIVY_SHA256_arm64="2ca2c023109c2db6b2b77366b6717291452d4531167377d95c79547f0c8e3467" && \
  TRIVY_SHA256=$([ "$TARGETARCH" = "arm64" ] && echo "$TRIVY_SHA256_arm64" || echo "$TRIVY_SHA256_amd64") && \
  TRIVY_ARCH=$([ "$TARGETARCH" = "arm64" ] && echo "ARM64" || echo "64bit") && \
  curl -fsSL "https://github.com/aquasecurity/trivy/releases/download/v${TRIVY_VERSION}/trivy_${TRIVY_VERSION}_Linux-${TRIVY_ARCH}.tar.gz" \
    -o /tmp/trivy.tar.gz && \
  echo "${TRIVY_SHA256}  /tmp/trivy.tar.gz" | sha256sum -c - && \
  tar -xzf /tmp/trivy.tar.gz -C /usr/local/bin trivy && \
  rm /tmp/trivy.tar.gz && \
  # ── tflint ──
  # renovate: datasource=github-releases depName=terraform-linters/tflint
  TFLINT_VERSION="0.64.0" && \
  TFLINT_SHA256_amd64="cca9d13e2e1d7a2c627af60ff899a3c9b74212899416aeb96ec764d2ef954537" && \
  TFLINT_SHA256_arm64="560da89aacf59389d4eb029730dd5b109b7288096c32f2726a0d9e783a5ea8eb" && \
  TFLINT_SHA256=$([ "$TARGETARCH" = "arm64" ] && echo "$TFLINT_SHA256_arm64" || echo "$TFLINT_SHA256_amd64") && \
  curl -fsSL "https://github.com/terraform-linters/tflint/releases/download/v${TFLINT_VERSION}/tflint_linux_${TARGETARCH}.zip" \
    -o /tmp/tflint.zip && \
  echo "${TFLINT_SHA256}  /tmp/tflint.zip" | sha256sum -c - && \
  unzip -q /tmp/tflint.zip -d /usr/local/bin && \
  rm /tmp/tflint.zip && \
  # ── editorconfig-checker ──
  # renovate: datasource=github-releases depName=editorconfig-checker/editorconfig-checker
  EC_VERSION="3.8.0" && \
  EC_SHA256_amd64="613bd88f34165a334adcb6b7e92a123c9de0eada65846d31af63613b779ff3be" && \
  EC_SHA256_arm64="5676889ac4eed1036180ffbe2aeb2062d985ac50f7e6035fe61160c6b8be2c33" && \
  EC_SHA256=$([ "$TARGETARCH" = "arm64" ] && echo "$EC_SHA256_arm64" || echo "$EC_SHA256_amd64") && \
  curl -fsSL "https://github.com/editorconfig-checker/editorconfig-checker/releases/download/v${EC_VERSION}/ec-linux-${TARGETARCH}.tar.gz" \
    -o /tmp/ec.tar.gz && \
  echo "${EC_SHA256}  /tmp/ec.tar.gz" | sha256sum -c - && \
  tar -xzf /tmp/ec.tar.gz -C /usr/local/bin --strip-components=1 && \
  mv /usr/local/bin/ec-linux-${TARGETARCH} /usr/local/bin/editorconfig-checker 2>/dev/null || true && \
  rm /tmp/ec.tar.gz && \
  # ── kubeconform ──
  # renovate: datasource=github-releases depName=yannh/kubeconform
  KUBECONFORM_VERSION="0.8.0" && \
  KUBECONFORM_SHA256_amd64="9bc2bffbf71f261128533edaf912153948b7ff238f9a531ae6d34466ec287883" && \
  KUBECONFORM_SHA256_arm64="1f53fc8e81258197a35e8603054162a5af1de8c5af13746c71ab680d9534ed87" && \
  KUBECONFORM_SHA256=$([ "$TARGETARCH" = "arm64" ] && echo "$KUBECONFORM_SHA256_arm64" || echo "$KUBECONFORM_SHA256_amd64") && \
  curl -fsSL "https://github.com/yannh/kubeconform/releases/download/v${KUBECONFORM_VERSION}/kubeconform-linux-${TARGETARCH}.tar.gz" \
    -o /tmp/kubeconform.tar.gz && \
  echo "${KUBECONFORM_SHA256}  /tmp/kubeconform.tar.gz" | sha256sum -c - && \
  tar -xzf /tmp/kubeconform.tar.gz -C /usr/local/bin kubeconform && \
  rm /tmp/kubeconform.tar.gz && \
  # ── lychee ──
  # renovate: datasource=github-releases depName=lycheeverse/lychee
  LYCHEE_VERSION="0.24.2" && \
  LYCHEE_SHA256_amd64="73657a111819a30c47c08352896796f23d64e4eb2b3ed39b6d32149241566fc5" && \
  LYCHEE_SHA256_arm64="5d0b0e3aeab240f41920c633a6eaf97599be6eedda034b36e858ede7dba5e535" && \
  LYCHEE_SHA256=$([ "$TARGETARCH" = "arm64" ] && echo "$LYCHEE_SHA256_arm64" || echo "$LYCHEE_SHA256_amd64") && \
  LYCHEE_ARCH=$([ "$TARGETARCH" = "arm64" ] && echo "aarch64" || echo "x86_64") && \
  curl -fsSL "https://github.com/lycheeverse/lychee/releases/download/lychee-v${LYCHEE_VERSION}/lychee-${LYCHEE_ARCH}-unknown-linux-musl.tar.gz" \
    -o /tmp/lychee.tar.gz && \
  echo "${LYCHEE_SHA256}  /tmp/lychee.tar.gz" | sha256sum -c - && \
  tar -xzf /tmp/lychee.tar.gz -C /usr/local/bin --strip-components=1 "lychee-${LYCHEE_ARCH}-unknown-linux-musl/lychee" && \
  rm /tmp/lychee.tar.gz && \
  # ── golangci-lint (new addition) ──
  # renovate: datasource=github-releases depName=golangci/golangci-lint
  GOLANGCI_VERSION="2.12.2" && \
  GOLANGCI_SHA256_amd64="8df580d2670fed8fa984aac0507099af8df275e665215f5c7a2ae3943893a553" && \
  GOLANGCI_SHA256_arm64="44cd40a8c76c86755375adfeea52cfd3533cb43d7bd647771e0ae065e166df3a" && \
  GOLANGCI_SHA256=$([ "$TARGETARCH" = "arm64" ] && echo "$GOLANGCI_SHA256_arm64" || echo "$GOLANGCI_SHA256_amd64") && \
  curl -fsSL "https://github.com/golangci/golangci-lint/releases/download/v${GOLANGCI_VERSION}/golangci-lint-${GOLANGCI_VERSION}-linux-${TARGETARCH}.tar.gz" \
    -o /tmp/golangci-lint.tar.gz && \
  echo "${GOLANGCI_SHA256}  /tmp/golangci-lint.tar.gz" | sha256sum -c - && \
  tar -xzf /tmp/golangci-lint.tar.gz -C /usr/local/bin --strip-components=1 "golangci-lint-${GOLANGCI_VERSION}-linux-${TARGETARCH}/golangci-lint" && \
  rm /tmp/golangci-lint.tar.gz && \
  # ── shfmt ──
  # renovate: datasource=github-releases depName=mvdan/sh
  SHFMT_VERSION="3.13.1" && \
  SHFMT_SHA256_amd64="fb096c5d1ac6beabbdbaa2874d025badb03ee07929f0c9ff67563ce8c75398b1" && \
  SHFMT_SHA256_arm64="32d92acaa5cd8abb29fc49dac123dc412442d5713967819d8af2c29f1b3857c7" && \
  SHFMT_SHA256=$([ "$TARGETARCH" = "arm64" ] && echo "$SHFMT_SHA256_arm64" || echo "$SHFMT_SHA256_amd64") && \
  curl -fsSL "https://github.com/mvdan/sh/releases/download/v${SHFMT_VERSION}/shfmt_v${SHFMT_VERSION}_linux_${TARGETARCH}" \
    -o /usr/local/bin/shfmt && \
  echo "${SHFMT_SHA256}  /usr/local/bin/shfmt" | sha256sum -c - && \
  chmod +x /usr/local/bin/shfmt && \
  # ── dotenv-linter (Alpine/musl build) ──
  # renovate: datasource=github-releases depName=dotenv-linter/dotenv-linter
  DOTENV_VERSION="4.0.0" && \
  DOTENV_SHA256_amd64="88a9f2ccfbfea621e5b4691246c419de71d79c7596def888849496695cd8a082" && \
  DOTENV_SHA256_arm64="819153e4f43ce016ebd076653e611431d5207e4fa5623a83028dfca92b1c3201" && \
  DOTENV_SHA256=$([ "$TARGETARCH" = "arm64" ] && echo "$DOTENV_SHA256_arm64" || echo "$DOTENV_SHA256_amd64") && \
  DOTENV_ARCH=$([ "$TARGETARCH" = "arm64" ] && echo "aarch64" || echo "x86_64") && \
  curl -fsSL "https://github.com/dotenv-linter/dotenv-linter/releases/download/v${DOTENV_VERSION}/dotenv-linter-alpine-${DOTENV_ARCH}.tar.gz" \
    -o /tmp/dotenv-linter.tar.gz && \
  echo "${DOTENV_SHA256}  /tmp/dotenv-linter.tar.gz" | sha256sum -c - && \
  tar -xzf /tmp/dotenv-linter.tar.gz -C /usr/local/bin dotenv-linter && \
  rm /tmp/dotenv-linter.tar.gz && \
  # ── checkmake (Makefile linter, glibc — needs gcompat) ──
  # renovate: datasource=github-releases depName=mrtazz/checkmake
  CHECKMAKE_VERSION="0.3.2" && \
  CHECKMAKE_SHA256_amd64="e2effb876913f3ee2caef0ba35f6202c5e8a3cd55a077d8d2b9ce2034257b6af" && \
  CHECKMAKE_SHA256_arm64="409167c4abb99407bd232c3bbd351b8a39df57997feafde5a08bddffb0f2dcb4" && \
  CHECKMAKE_SHA256=$([ "$TARGETARCH" = "arm64" ] && echo "$CHECKMAKE_SHA256_arm64" || echo "$CHECKMAKE_SHA256_amd64") && \
  curl -fsSL "https://github.com/mrtazz/checkmake/releases/download/v${CHECKMAKE_VERSION}/checkmake-v${CHECKMAKE_VERSION}.linux.${TARGETARCH}" \
    -o /usr/local/bin/checkmake && \
  echo "${CHECKMAKE_SHA256}  /usr/local/bin/checkmake" | sha256sum -c - && \
  chmod +x /usr/local/bin/checkmake && \
  # ── PMD-CPD (Java, arch-agnostic) ──
  # renovate: datasource=github-releases depName=pmd/pmd
  PMD_VERSION="7.26.0" && \
  PMD_SHA256="9f55cb7ff0e9f9a66dd2f005eaa370e84c8a4cd971b134aa14a930c4a283ebc9" && \
  curl -fsSL "https://github.com/pmd/pmd/releases/download/pmd_releases%2F${PMD_VERSION}/pmd-dist-${PMD_VERSION}-bin.zip" \
    -o /tmp/pmd.zip && \
  echo "${PMD_SHA256}  /tmp/pmd.zip" | sha256sum -c - && \
  unzip -q /tmp/pmd.zip -d /opt && \
  ln -s /opt/pmd-bin-${PMD_VERSION}/bin/pmd /usr/local/bin/pmd && \
  rm /tmp/pmd.zip && \
  # ── caddy (Caddyfile formatter) ──
  # renovate: datasource=github-releases depName=caddyserver/caddy
  CADDY_VERSION="2.11.4" && \
  CADDY_SHA256_amd64="527fbf917c39189a1e3b31d34fa955601680b2d5c8055d2a87b8b9588dec7bb9" && \
  CADDY_SHA256_arm64="52d42ae12b3462097e9868da6dfed3c9648ae12edd3b3638102312af84cb6904" && \
  CADDY_SHA256=$([ "$TARGETARCH" = "arm64" ] && echo "$CADDY_SHA256_arm64" || echo "$CADDY_SHA256_amd64") && \
  curl -fsSL "https://github.com/caddyserver/caddy/releases/download/v${CADDY_VERSION}/caddy_${CADDY_VERSION}_linux_${TARGETARCH}.tar.gz" \
    -o /tmp/caddy.tar.gz && \
  echo "${CADDY_SHA256}  /tmp/caddy.tar.gz" | sha256sum -c - && \
  tar -xzf /tmp/caddy.tar.gz -C /usr/local/bin caddy && \
  chmod +x /usr/local/bin/caddy && \
  rm /tmp/caddy.tar.gz && \
  # ── just (task runner) ──
  # renovate: datasource=github-releases depName=casey/just
  JUST_VERSION="1.57.0" && \
  JUST_SHA256_amd64="45b548094283cb9739af8f13273b8cddeee869f5b4ef2bb631b1f311cb566155" && \
  JUST_SHA256_arm64="f225044a81adea6e0b3a8b9370aaf374e6af76c8735ae263ac993df55fd137ec" && \
  JUST_SHA256=$([ "$TARGETARCH" = "arm64" ] && echo "$JUST_SHA256_arm64" || echo "$JUST_SHA256_amd64") && \
  JUST_ARCH=$([ "$TARGETARCH" = "arm64" ] && echo "aarch64" || echo "x86_64") && \
  curl -fsSL "https://github.com/casey/just/releases/download/${JUST_VERSION}/just-${JUST_VERSION}-${JUST_ARCH}-unknown-linux-musl.tar.gz" \
    -o /tmp/just.tar.gz && \
  echo "${JUST_SHA256}  /tmp/just.tar.gz" | sha256sum -c - && \
  tar -xzf /tmp/just.tar.gz -C /usr/local/bin just && \
  chmod +x /usr/local/bin/just && \
  rm /tmp/just.tar.gz && \
  # ── conftest (OPA/Rego policy runner) ──
  # renovate: datasource=github-releases depName=open-policy-agent/conftest
  CONFTEST_VERSION="0.68.2" && \
  CONFTEST_SHA256_amd64="e8144c6d6d2ae0260b869caa60c7c262a1f95ac63ec1e5d2fb19be452d606347" && \
  CONFTEST_SHA256_arm64="4005441089655ded475384cb87d57762ae08ebef78305bada49c70530d2f4184" && \
  CONFTEST_SHA256=$([ "$TARGETARCH" = "arm64" ] && echo "$CONFTEST_SHA256_arm64" || echo "$CONFTEST_SHA256_amd64") && \
  CONFTEST_ARCH=$([ "$TARGETARCH" = "arm64" ] && echo "arm64" || echo "x86_64") && \
  curl -fsSL "https://github.com/open-policy-agent/conftest/releases/download/v${CONFTEST_VERSION}/conftest_${CONFTEST_VERSION}_Linux_${CONFTEST_ARCH}.tar.gz" \
    -o /tmp/conftest.tar.gz && \
  echo "${CONFTEST_SHA256}  /tmp/conftest.tar.gz" | sha256sum -c - && \
  tar -xzf /tmp/conftest.tar.gz -C /usr/local/bin conftest && \
  rm /tmp/conftest.tar.gz

# ── Trivy DB pre-cache (best effort; never masks binary install failures) ──
RUN trivy --cache-dir /root/.cache/trivy fs --download-db-only --db-repository ghcr.io/aquasecurity/trivy-db:2 --no-progress 2>/dev/null || true

# ── Build asset downloads (schemas + semgrep rules) ──────────
COPY build-assets.yml scripts/download_build_assets.py /tmp/
RUN python3 /tmp/download_build_assets.py --config /tmp/build-assets.yml && \
    rm /tmp/build-assets.yml /tmp/download_build_assets.py

# ── Rule catalog (structured rule data for all tools) ────────
COPY semgrep-rules/ /tmp/catalog-build/semgrep-rules/
COPY Dockerfile /tmp/catalog-build/Dockerfile
COPY scripts/generate_rule_catalog.py /tmp/
# hadolint ignore=DL3059
RUN python3 /tmp/generate_rule_catalog.py \
      --root /tmp/catalog-build --output /opt/coding-standards/rule-catalog.json && \
    rm /tmp/generate_rule_catalog.py && rm -rf /tmp/catalog-build /tmp/hadolint-wiki

# ── Plugin descriptors ────────────────────────────────────────
COPY plugins/ /mega-linter-plugin-custom/

# ── Centralized semgrep rules ─────────────────────────────────
COPY semgrep-rules/ /rules/custom/

# ── Shared Conftest policies ─────────────────────────────────
COPY policies/ /opt/coding-standards/policies/

# ── Mechanism scripts + reporting ─────────────────────────────
COPY --chmod=755 scripts/ci/check_expiry.py scripts/megalinter_report_statuses.py scripts/generate_repo_manifest.py scripts/show_catalog.py scripts/manifest_schema.py scripts/show_warnings.py scripts/blast_radius.py scripts/show_config.py scripts/recommend.py /opt/coding-standards/scripts/

# ── Linter config files ──────────────────────────────────────
COPY lint-configs/ /opt/coding-standards/configs/
# Node resolves ESM plugin imports relative to eslint.config.mjs, not the
# globally installed eslint executable. Expose the pinned global packages at
# the baked config boundary without copying another node_modules tree.
RUN ln -s /usr/local/lib/node_modules /opt/coding-standards/configs/node_modules

# ── Entrypoint ───────────────────────────────────────────────
COPY --chmod=755 scripts/entrypoint.py /opt/coding-standards/entrypoint.py
# MegaLinter requires root for tool installs and workspace writes.
# nosemgrep: dockerfile.security.missing-user-entrypoint.missing-user-entrypoint
ENTRYPOINT ["python3", "/opt/coding-standards/entrypoint.py"]

# ── Consumer files (justfile, help docs, templates) ──────────
COPY consumer.just /opt/coding-standards/consumer.just
COPY docs/help/ /opt/coding-standards/docs/help/
COPY templates/ /opt/coding-standards/templates/

# ── Default config ────────────────────────────────────────────
COPY .mega-linter-default.yml /opt/coding-standards/.mega-linter-default.yml
