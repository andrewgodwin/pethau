# syntax=docker/dockerfile:1

FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project --no-dev

COPY . /app

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev

RUN set -a && . /app/.env.build && set +a && \
    uv run python manage.py collectstatic --noinput && \
    rm /app/.env.build

FROM python:3.13-slim-bookworm

RUN groupadd --system app && useradd --system --create-home --gid app app

COPY --from=builder --chown=app:app /app /app

ENV PATH="/app/.venv/bin:$PATH"

WORKDIR /app
USER app

EXPOSE 8000

CMD ["gunicorn", "pethau.wsgi:application", "--bind", "0.0.0.0:8000"]
