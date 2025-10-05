FROM ghcr.io/astral-sh/uv:debian-slim

WORKDIR /app

COPY pyproject.toml . 
RUN uv python install

COPY uv.lock .
RUN uv sync --frozen

COPY . .

EXPOSE 5432

CMD ["uv", "run", "uvicorn", "--host", "0.0.0.0", "--port", "5432", "main:app"]
