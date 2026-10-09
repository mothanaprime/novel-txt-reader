#!/usr/bin/env bash
# Compatibility entry point. Install pinned dependencies with npm ci at repo root.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../../../../.." && pwd)"
cd "$ROOT"
exec npm test
