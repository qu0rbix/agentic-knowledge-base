#!/usr/bin/env bash
# usage: scripts/new-kb.sh <target-folder>
# Copies the template into a new folder, initialises git, and tells you how to start.
set -euo pipefail
target="${1:?usage: new-kb.sh <target-folder>}"
here="$(cd "$(dirname "$0")/.." && pwd)"
[ -e "$target" ] && { echo "$target already exists"; exit 1; }
cp -r "$here/template" "$target"
cd "$target"
git init -q && git config core.longpaths true 2>/dev/null || true
git add -A && git commit -qm "New knowledge base from agentic-knowledge-base template"
echo "Created $target. Next:"
echo "  cd \"$target\" && claude"
echo "  then say: set up this KB   (runs the init-kb interview)"
