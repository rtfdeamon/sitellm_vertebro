FROM ghcr.io/astral-sh/uv:debian-slim

WORKDIR app
COPY . .

RUN apt update && apt install g++ gcc libopenblas-dev pkg-config -y
ENV CMAKE_ARGS "-DGGML_BLAS=ON -DGGML_BLAS_VENDOR=OpenBLAS"
RUN uv sync

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "app:app", "--host", "0.0.0.0"]