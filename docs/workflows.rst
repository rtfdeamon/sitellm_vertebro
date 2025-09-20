====================
Operational Workflows
====================

Local development
-----------------

1. Install system dependencies (``cmake``, ``openblas`` and, optionally,
   CUDA for accelerated llama.cpp builds).
2. Copy ``.env.example`` to ``.env`` and adjust Mongo/Redis credentials.
3. Create a Python environment via ``uv`` and sync dependencies::

       CMAKE_ARGS="-DGGML_CUDA=on -DGGML_BLAS=ON" uv sync

4. Start services::

       uvicorn app:app --reload
       celery -A worker worker --beat

5. Open ``http://localhost:18080/admin/`` to manage projects and trigger
   crawls.

Containerised stack
-------------------

``docker compose up --build`` starts the API, worker, Redis, MongoDB, Qdrant
and supporting services using configuration from ``compose.yaml``.  Additional
files:

* ``compose.gpu.yaml`` – enables GPU-backed llama.cpp/YaLLM.
* ``docker/dockerfile.*`` – service-specific build instructions.
* ``docker-compose.override.windows.yml`` – resource limits for Windows.

Knowledge base management
-------------------------

* Use the admin dash "Projects" card to create a domain and set the initial
  system prompt.  The prompt is applied to **every** subsequent LLM request,
  which is confirmed by ``project_prompt_attached`` entries in the logs.
* Upload documents manually through the "Knowledge Base" card or launch a
  crawl.  When the crawler finishes, the Celery worker queues an embeddings
  refresh so Redis stays in sync without a full rebuild.
* The "Logs" card surfaces ``llm_prompt_compiled`` events so operators can
  inspect the full prompt/knowledge combination used for each conversation.

Testing & quality gates
-----------------------

* ``python -m pytest`` – core unit tests.
* ``scripts/benchmark.py`` – load-testing helper; logs ``p95`` and
  throughput metrics.
* ``observability/metrics.py`` – automatically exposes Prometheus metrics at
  ``/metrics`` when the app runs under Uvicorn/Gunicorn.

Deployment automation
---------------------

* ``deploy_project.sh`` – interactive bootstrapper; collects env values,
  builds images sequentially and performs an initial crawl.
* ``deploy_project.ps1`` – Windows-friendly variant with zip backups.
* ``docs/deploy.md`` – describes the CI/CD pipeline for push-to-main rollout.
