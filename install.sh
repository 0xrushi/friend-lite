#!/bin/sh
set -e

REPO="https://github.com/SimpleOpenSoftware/chronicle.git"
DIR="chronicle"

# Get latest release tag
TAG=$(curl -sL https://api.github.com/repos/SimpleOpenSoftware/chronicle/releases/latest | grep -o '"tag_name": *"[^"]*"' | head -1 | cut -d'"' -f4)

if [ -z "$TAG" ]; then
    echo "error: could not determine latest release"
    exit 1
fi

echo "Installing Chronicle $TAG..."

if [ -d "$DIR" ]; then
    echo "error: directory '$DIR' already exists"
    exit 1
fi

git clone --depth 1 --branch "$TAG" "$REPO" "$DIR"
cd "$DIR"

# Install uv if missing
if ! command -v uv > /dev/null 2>&1; then
    echo "Installing uv package manager..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    . "$HOME/.local/bin/env" 2>/dev/null || export PATH="$HOME/.local/bin:$PATH"
fi

# Reconnect stdin for interactive wizard
exec < /dev/tty
./wizard.sh
