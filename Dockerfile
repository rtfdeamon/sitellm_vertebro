
# Build stage
FROM python:3.10-slim AS build
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN apt-get update && apt-get install -y g++ gcc libopenblas-dev pkg-config curl \
    && pip install uv \
    && uv sync && rm -rf /var/lib/apt/lists/*
COPY . .

# Runtime stage
FROM python:3.10-slim
WORKDIR /app
COPY --from=build /usr/local /usr/local
COPY --from=build /app /app
EXPOSE 8000
HEALTHCHECK CMD curl -f http://localhost:8000/health || exit 1
CMD ["uv", "run", "uvicorn", "app:app", "--host", "0.0.0.0"]
