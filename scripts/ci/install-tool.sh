#!/usr/bin/env bash
# Installs a pinned binary tool with SHA256 verification.
# Used by lint.yml to avoid repeating the cache/download/verify/extract pattern.
#
# Required env vars:
#   TOOL_NAME     — tool name (used for directory and messages)
#   TOOL_VERSION  — version string (no 'v' prefix)
#   TOOL_ARTIFACT — artifact filename (may use ${VERSION} placeholder)
#   TOOL_URL      — download base URL (may use ${VERSION} placeholder)
#   TOOL_CHECKSUMS — checksums filename (may use ${VERSION} placeholder)
#   TOOL_EXTRACT  — extraction command: "tar" or "unzip"
#   TOOL_BINARY   — binary name inside the archive (default: $TOOL_NAME)
#
# The script:
#   1. Downloads artifact + checksums file
#   2. Verifies SHA256
#   3. Extracts binary to ~/.${TOOL_NAME}/bin/
set -euo pipefail

BIN_DIR="$HOME/.${TOOL_NAME}/bin"
BINARY="${TOOL_BINARY:-$TOOL_NAME}"
VERSION="$TOOL_VERSION"

# Skip if binary already exists (Docker volume persistence on Gitea)
if [ -x "$BIN_DIR/$BINARY" ]; then
  echo "$TOOL_NAME already installed at $BIN_DIR/$BINARY — skipping download"
  exit 0
fi

# Expand ${VERSION} placeholders
ARTIFACT="${TOOL_ARTIFACT//\$\{VERSION\}/$VERSION}"
BASE_URL="${TOOL_URL//\$\{VERSION\}/$VERSION}"
CHECKSUMS="${TOOL_CHECKSUMS//\$\{VERSION\}/$VERSION}"

mkdir -p "$BIN_DIR"
cd /tmp

curl -fsSLO "${BASE_URL}/${ARTIFACT}"
curl -fsSLO "${BASE_URL}/${CHECKSUMS}"
grep "  ${ARTIFACT}" "$CHECKSUMS" | sha256sum -c -

case "$TOOL_EXTRACT" in
  tar)  tar -xzf "$ARTIFACT" -C "$BIN_DIR" "$BINARY" ;;
  unzip)
    unzip -o "$ARTIFACT" "$BINARY" -d "$BIN_DIR"
    chmod +x "$BIN_DIR/$BINARY"
    ;;
  *)
    echo "ERROR: unknown TOOL_EXTRACT=$TOOL_EXTRACT (expected tar or unzip)"
    exit 1
    ;;
esac

echo "Installed $TOOL_NAME $VERSION to $BIN_DIR"
