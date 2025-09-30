# Knowledge Processing Service

The knowledge processing service keeps the Redis vector store in sync with
ingested documents. It can work in two modes:

* **Manual** – the default, where updates are launched explicitly through the
  API or the admin UI button. Use this mode when you want to control when the
  system rewrites embeddings (for example, after editing the processing prompt).
* **Auto** – legacy behaviour that monitors the crawler queue and launches an
  update once the queue remains idle for a configured amount of time.

Settings, including the processing prompt shown in the admin panel, are stored
in Mongo under the `knowledge_service` key. They can be modified via REST or
the admin UI.

## Endpoints

| Method | Path                                       | Description |
|--------|--------------------------------------------|-------------|
| GET    | `/api/v1/admin/knowledge/service`          | Returns the current configuration and status (including the latest action message). |
| POST   | `/api/v1/admin/knowledge/service`          | Updates the `enabled` flag, mode, prompt and timing thresholds. |
| POST   | `/api/v1/admin/knowledge/service/run`      | Triggers a manual update immediately (blocks until it finishes). |
| GET    | `/api/v1/admin/llm/knowledge/service`      | Same as above, exposed under the LLM router for internal clients. |
| POST   | `/api/v1/admin/llm/knowledge/service`      | Same update endpoint under the LLM router. |
| POST   | `/api/v1/admin/llm/knowledge/service/run`  | Manual trigger endpoint via the LLM router. |
| GET    | `/api/v1/knowledge/service`                | Backward-compatible status alias. |
| POST   | `/api/v1/knowledge/service`                | Backward-compatible update alias. |
| POST   | `/api/v1/knowledge/service/run`            | Backward-compatible manual trigger alias. |

## Status Payload

```
{
  "enabled": true,
  "running": true,
  "idle_threshold_seconds": 300,
  "poll_interval_seconds": 60,
  "cooldown_seconds": 900,
  "mode": "manual",
  "processing_prompt": "...",
  "manual_reason": null,
  "last_run_ts": 1726850000.0,
  "last_reason": "queue_idle",
  "last_queue": 0,
  "idle_seconds": 120,
  "last_seen_ts": 1726850123.0,
  "updated_at": 1726850123.0,
  "last_error": null,
  "message": "Интеллектуальная обработка завершена успешно"
}
```

`message` is human-readable and surfaced in the admin UI. It reports when the
queue is active, when the service is waiting in auto mode, or how a manual run
completes. `manual_reason` mirrors the value passed to the `/run` endpoint
(`null` when default) so that operators can see why the last manual update was
triggered.

## Processing Prompt

The `processing_prompt` field stores free-form instructions that describe how
documents should be processed before embeddings are refreshed. The default
prompt directs the service (or a human operator) to handle each document in
small chunks so that the text fits the current LLM context window and updates
the stored representation sequentially. You can edit the prompt via the admin
dashboard; the value is persisted in Mongo and returned by the status endpoint.

## Service Runtime

The standalone process lives in `knowledge_service/service.py`. It:

1. Polls the queue depth via `core.status.status_dict()`.
2. Checks the `mode` and, if set to `auto`, uses the stored thresholds to decide
   when to trigger `worker.update_vector_store`.
3. If the mode is `manual`, it simply refreshes the status in Mongo without
   launching updates, allowing `/run` calls to stay authoritative.
4. Saves status metadata (idle timer, queue depth, last action, prompt) back to
   Mongo for consumption by the UI.

Start the service by running:

```bash
python -m knowledge_service
```

Docker/compose deployments can run it in a dedicated container using the same
entry point.
