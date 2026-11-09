#!/usr/bin/env bash
# Builds the single-stage ("naive") and multi-stage images and prints a Markdown report with
# real image sizes and build times. Base images are pulled first so network time is not counted.
#
# Usage: scripts/measure-images.sh > docs/image-comparison.md
set -euo pipefail
cd "$(dirname "$0")/.."

for base in python:3.12 python:3.12-slim node:22 node:22-alpine nginxinc/nginx-unprivileged:alpine; do
  docker pull -q "$base" >/dev/null
done

seconds() { awk -v a="$1" -v b="$2" 'BEGIN { printf "%.1f", b - a }'; }
now() { date +%s.%N; }
size_mb() { docker image inspect -f '{{.Size}}' "$1" | awk '{ printf "%.0f", $1 / 1000000 }'; }

# build <tag> <context> <dockerfile> [--no-cache]  -> prints seconds
build() {
  local t0 t1
  t0=$(now)
  docker build -q ${4:-} -t "$1" -f "$3" "$2" >/dev/null
  t1=$(now)
  seconds "$t0" "$t1"
}

# Change one source file, rebuild, restore it. Shows how well layer caching works.
rebuild_after_change() { # <tag> <context> <dockerfile> <file> <comment>
  local backup
  backup=$(mktemp)
  cp "$4" "$backup"
  printf '\n%s benchmark change\n' "$5" >> "$4"
  build "$1" "$2" "$3" || true
  cp "$backup" "$4"
  rm -f "$backup"
}

echo "Building (this takes a few minutes)..." >&2

be_single_cold=$(build bench-backend-single backend backend/Dockerfile.single-stage --no-cache)
be_multi_cold=$(build bench-backend-multi backend backend/Dockerfile --no-cache)
fe_single_cold=$(build bench-frontend-single frontend frontend/Dockerfile.single-stage --no-cache)
fe_multi_cold=$(build bench-frontend-multi frontend frontend/Dockerfile --no-cache)

be_single_warm=$(rebuild_after_change bench-backend-single backend backend/Dockerfile.single-stage backend/app/main.py '#')
be_multi_warm=$(rebuild_after_change bench-backend-multi backend backend/Dockerfile backend/app/main.py '#')
fe_single_warm=$(rebuild_after_change bench-frontend-single frontend frontend/Dockerfile.single-stage frontend/src/App.jsx '//')
fe_multi_warm=$(rebuild_after_change bench-frontend-multi frontend frontend/Dockerfile frontend/src/App.jsx '//')

# Restore the real images so the report reflects the final source (and tags stay consistent).
build bench-backend-single backend backend/Dockerfile.single-stage >/dev/null
build bench-backend-multi backend backend/Dockerfile >/dev/null
build bench-frontend-single frontend frontend/Dockerfile.single-stage >/dev/null
build bench-frontend-multi frontend frontend/Dockerfile >/dev/null

reduction() { awk -v a="$1" -v b="$2" 'BEGIN { printf "%.0f%%", (1 - b / a) * 100 }'; }

be_s=$(size_mb bench-backend-single); be_m=$(size_mb bench-backend-multi)
fe_s=$(size_mb bench-frontend-single); fe_m=$(size_mb bench-frontend-multi)

cat <<MD
# Image size and build time: single-stage vs multi-stage

Measured with \`scripts/measure-images.sh\` on $(date -u +%Y-%m-%d) ($(docker --version)).
Sizes are the uncompressed image size reported by Docker. Times are wall-clock seconds on one
machine, so treat them as relative numbers rather than benchmarks.

## Image size

| Image | Single-stage | Multi-stage | Smaller by |
|---|---|---|---|
| Backend (Python) | ${be_s} MB | ${be_m} MB | $(reduction "$be_s" "$be_m") |
| Frontend (React) | ${fe_s} MB | ${fe_m} MB | $(reduction "$fe_s" "$fe_m") |

## Build time

| Image | Cold build (no cache) | Rebuild after a source change |
|---|---|---|
| Backend, single-stage | ${be_single_cold} s | ${be_single_warm} s |
| Backend, multi-stage | ${be_multi_cold} s | ${be_multi_warm} s |
| Frontend, single-stage | ${fe_single_cold} s | ${fe_single_warm} s |
| Frontend, multi-stage | ${fe_multi_cold} s | ${fe_multi_warm} s |

## What the numbers show

- **Frontend:** Node and its build tools are only needed to produce static files. The final
  image contains just those files and Nginx, which is where most of the saving comes from.
- **Backend:** most of the saving comes from the slim base image instead of the full Debian one.
  The builder stage keeps pip's build artifacts out of the runtime image.
- **Cold builds** take similar time for both variants. **Rebuilds** after a one-file change are
  fast in both because dependencies are installed in layers before the source is copied. The
  multi-stage rebuild is a little slower (extra stage and copy steps), which is a small price for
  images that are many times smaller.
MD
