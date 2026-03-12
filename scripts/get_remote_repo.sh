#!/usr/bin/env bash
set -euo pipefail

echo "[INFO] Fetching remote..."
git fetch origin

echo "[INFO] Resetting local branch to match remote..."
BRANCH="$(git rev-parse --abbrev-ref HEAD)"
git reset --hard "origin/${BRANCH}"

echo "[INFO] Cleaning untracked files and directories..."
git clean -fd

echo "[DONE] Local repo is now in sync with origin/${BRANCH}"
