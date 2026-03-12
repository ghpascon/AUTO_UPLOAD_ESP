#!/usr/bin/env bash
set -euo pipefail

poetry cache clear pypi --all --no-interaction
poetry sync
poetry lock
poetry install
