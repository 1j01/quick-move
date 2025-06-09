#!/bin/bash
# Usage: link_cli_globally.sh [--remove]
# This script creates a symbolic link to expose the quick-move CLI globally (i.e. outside of the virtual environment).
# If --remove is passed, it removes the existing symlink.

REPO_DIR=$(dirname "$(readlink -f "$0")")
CLI="quick-move"
# LINK_PATH="/usr/local/bin/$CLI" ? not sure of the difference
LINK_PATH="$HOME/.local/bin/$CLI"
LINK_TARGET="$REPO_DIR/.venv/bin/$CLI"
# On Windows, venv uses a Scripts directory instead of bin
# and maybe exe extension (untested)
# Also, not sure where to put the symlink on Windows.
if [ -d "$REPO_DIR/.venv/Scripts" ]; then
    LINK_TARGET="$REPO_DIR/.venv/Scripts/$CLI.exe"
    LINK_PATH="$HOME/.local/bin/$CLI.exe"
fi

if [ "$1" == "--remove" ]; then
    if [ -L "$LINK_PATH" ]; then
        echo "Removing symlink: $LINK_PATH"
        rm "$LINK_PATH"
    else
        echo "No symlink found at $LINK_PATH"
    fi
else
    if [ -L "$LINK_PATH" ]; then
        echo "Symlink already exists: $LINK_PATH"
    else
        echo "Creating symlink: $LINK_PATH -> $LINK_TARGET"
        ln -s "$LINK_TARGET" "$LINK_PATH"
    fi
fi
