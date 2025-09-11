Standalone LLM Model Service
============================

What it is
- A small FastAPI microservice that exposes your LLM via HTTP:
  - `GET /healthz` — liveness probe
  - `GET /chat?question=...` — SSE streaming tokens
  - `POST /v1/completions {prompt, stream}` — JSON or SSE
- Optional API key: set `MODEL_API_KEY` to require `Authorization: Bearer <key>`

Run with Docker (recommended)
- Compose service name: `model` (port `9000` in container)
- External port: `${HOST_MODEL_PORT:-18001}`
- Bring up:
  ```bash
  docker compose -f compose.yaml -f compose.gpu.yaml up -d model
  ```
- Test:
  ```bash
  curl http://localhost:18001/healthz
  curl -N 'http://localhost:18001/chat?question=hello'
  ```

Install natively (systemd)
- One command (GPU optional):
  ```bash
  sudo MODEL_PORT=9000 LLM_MODEL='Vikhrmodels/Vikhr-YandexGPT-5-Lite-8B-it' \
    MODEL_API_KEY=secret APP_DIR=/opt/sitellm_vertebro \
    bash scripts/install_model_service.sh --gpu
  ```
- Service: `yallm-model.service`, listens on `MODEL_PORT` (default 9000)
- CUDA: prebuilt wheels used (`PIP_EXTRA_INDEX_URL`), driver must be present

Client examples
- SSE (bash):
  ```bash
  curl -N -H 'Authorization: Bearer secret' \
    'http://host:18001/chat?question=Привет'
  ```
- JSON (non‑stream):
  ```bash
  curl -s -X POST http://host:18001/v1/completions \
    -H 'Content-Type: application/json' \
    -d '{"prompt":"Hello","stream":false}'
  ```

Notes
- For GPU: ensure NVIDIA driver is installed on the host (`nvidia-smi`).
- The repo’s `backend/llm_client.py` handles CUDA/CPU selection automatically.

