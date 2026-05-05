# =============================================================================
# Multi-stage Dockerfile
# =============================================================================
# Why multi-stage?
# Stage 1 (builder): install dependencies using pip, which needs compilers and
#   build tools (some Python packages compile C extensions).
# Stage 2 (production): copy only the installed packages from stage 1 into a
#   fresh, minimal image. No pip, no compilers, no build cache in the final image.
#   This reduces the image size and the attack surface.
# =============================================================================

# ── Stage 1: builder ──────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /app

# Copy requirements FIRST (before the rest of the code).
# Docker caches each instruction as a layer. If requirements.txt hasn't changed,
# Docker reuses the cached pip install layer — much faster rebuilds on code changes.
COPY requirements.txt .

# --no-cache-dir: don't store pip's download cache in the image (saves space)
# --prefix=/install: install packages into /install instead of the system Python,
#   so we can copy just that folder into the production stage below.
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# ── Stage 2: production ───────────────────────────────────────────────────────
FROM python:3.12-slim AS production

WORKDIR /app

# Copy the installed packages from the builder stage — nothing else from it.
# The builder stage itself (with pip, build tools, cache) is discarded.
COPY --from=builder /install /usr/local

# Copy application code
COPY . .

# Why a non-root user?
# If the container is compromised, a root process can escape to the host OS.
# An unprivileged user limits the blast radius of a security breach.
RUN useradd --no-create-home --shell /bin/false appuser \
    && chown -R appuser /app
USER appuser

EXPOSE 8000

# Health check so Docker (and Compose's depends_on: condition: service_healthy) knows
# when the app is actually ready to serve requests, not just started.
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# --host 0.0.0.0: listen on all interfaces, not just localhost (required inside containers)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
