#!/usr/bin/env bash
set -euo pipefail

# This script installs micromamba via Homebrew, symlinks it to ~/.local/bin,
# initializes zsh with ~/micromamba, and configures conda-forge.

if ! command -v brew >/dev/null 2>&1; then
  cat <<'EOF' >&2
Homebrew not found.
Install Homebrew first, then rerun this script:
  https://brew.sh/
EOF
  exit 1
fi

# Install micromamba via Homebrew.
brew install micromamba

# Keep a stable location under ~/.local/bin.
mkdir -p "${HOME}/.local/bin"
ln -sf "$(brew --prefix)/bin/micromamba" "${HOME}/.local/bin/micromamba"

if ! command -v zsh >/dev/null 2>&1; then
  cat <<'EOF' >&2
zsh not found.
Install zsh or change the shell init command to your shell.
EOF
  exit 1
fi

MICROMAMBA="${HOME}/.local/bin/micromamba"
ZSHRC="${HOME}/.zshrc"
# Avoid duplicate init blocks if this script is re-run.
if [ -f "${ZSHRC}" ] && grep -q "mamba initialize" "${ZSHRC}"; then
  echo "Micromamba init block already present in ${ZSHRC}; skipping shell init."
else
  # Prefer newer flag; fall back for older micromamba.
  if "${MICROMAMBA}" shell init -s zsh --root-prefix "${HOME}/micromamba"; then
    :
  else
    "${MICROMAMBA}" shell init -s zsh -p "${HOME}/micromamba"
  fi
fi
# Use conda-forge with strict priority.
"${MICROMAMBA}" config set channel_priority strict
"${MICROMAMBA}" config prepend channels conda-forge

cat <<'EOF'
Done.
Restart your shell or run: source ~/.zshrc
EOF
