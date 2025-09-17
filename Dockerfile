FROM python:3.10-alpine as builder

ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV UV_SYSTEM_PYTHON=1

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project

ADD . /app

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked

RUN rm -rf dist && uv build --wheel --out-dir dist

FROM python:3.10-alpine

LABEL org.opencontainers.image.source=https://github.com/p2p-org/graphprotocol-public-poi-tool

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV UV_SYSTEM_PYTHON=1

RUN --mount=type=bind,from=builder,source=/app/dist,target=/app/dist \
    uv pip install /app/dist/graph_poitool*.whl

ENTRYPOINT ["poitool"]
