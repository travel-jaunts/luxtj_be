# ── Stage 1: dependency resolver ────────────────────────────────────────────
FROM python:3.14-slim AS builder

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy dependency manifests first for layer caching
COPY pyproject.toml uv.lock* ./

# Install dependencies into an isolated prefix (no project code yet)
RUN uv sync --frozen --no-install-project --no-dev

# Copy source and do the final install
COPY src/ ./src/
RUN uv sync --frozen --no-dev


# ── Stage 2: runtime image ───────────────────────────────────────────────────
FROM python:3.14-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

# Non-root user for security
RUN addgroup --system app && adduser --system --ingroup app app

WORKDIR /app

# Copy the virtualenv and source from builder
COPY --from=builder /app/.venv ./.venv
COPY --from=builder /app/src ./src

USER app

EXPOSE 8000

# uvicorn is installed inside the venv; reference app via module path
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
