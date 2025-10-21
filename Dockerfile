FROM ghcr.io/astral-sh/uv:trixie-slim

WORKDIR /app

COPY pyproject.toml . 
RUN uv python install

COPY uv.lock .
RUN uv sync --frozen

COPY . .

EXPOSE 4567 

CMD ["uv", "run", "./src/main.py"]
