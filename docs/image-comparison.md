# Image size and build time: single-stage vs multi-stage

Measured with `scripts/measure-images.sh` on 2026-11-09 (Docker version 29.7.2, build a7dcaa6).
Sizes are the uncompressed image size reported by Docker. Times are wall-clock seconds on one
machine, so treat them as relative numbers rather than benchmarks.

## Image size

| Image | Single-stage | Multi-stage | Smaller by |
|---|---|---|---|
| Backend (Python) | 469 MB | 93 MB | 80% |
| Frontend (React) | 476 MB | 26 MB | 95% |

## Build time

| Image | Cold build (no cache) | Rebuild after a source change |
|---|---|---|
| Backend, single-stage | 27.2 s | 1.0 s |
| Backend, multi-stage | 19.3 s | 1.8 s |
| Frontend, single-stage | 12.9 s | 1.0 s |
| Frontend, multi-stage | 10.4 s | 1.6 s |

## What the numbers show

- **Frontend:** Node and its build tools are only needed to produce static files. The final
  image contains just those files and Nginx, which is where most of the saving comes from.
- **Backend:** most of the saving comes from the slim base image instead of the full Debian one.
  The builder stage keeps pip's build artifacts out of the runtime image.
- **Cold builds** take similar time for both variants. **Rebuilds** after a one-file change are
  fast in both because dependencies are installed in layers before the source is copied. The
  multi-stage rebuild is a little slower (extra stage and copy steps), which is a small price for
  images that are many times smaller.
