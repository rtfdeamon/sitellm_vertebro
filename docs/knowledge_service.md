# Knowledge Processing Service

The background service periodically refreshes the Redis vector store when the
crawler queue stays idle for more than a configured threshold. Settings are
stored in Mongo under the `knowledge_service` key which can be manipulated via
REST or the admin UI.

## Endpoints

| Method | Path                                   | Description                          |
|--------|----------------------------------------|--------------------------------------|
| GET    | `/api/v1/admin/knowledge/service`      | Returns the current configuration and status (including the latest action message). |
| POST   | `/api/v1/admin/knowledge/service`      | Updates the `enabled` flag and timing thresholds. |
| GET    | `/api/v1/admin/llm/knowledge/service`  | Same as above, exposed under the LLM router for internal clients. |
| POST   | `/api/v1/admin/llm/knowledge/service`  | Same update endpoint under the LLM router. |

## Status Payload

```
{
  "enabled": true,
  "running": true,
  "idle_threshold_seconds": 300,
  "poll_interval_seconds": 60,
  "cooldown_seconds": 900,
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
queue is active, waiting for cooldown, or an execution completes with/without
errors.

## Service Runtime

The standalone process lives in `knowledge_service/service.py`. It:

1. Polls the queue depth via `core.status.status_dict()`.
2. Uses the stored thresholds to decide when to trigger `worker.update_vector_store`.
3. Saves status metadata (idle timer, queue depth, last action) back to Mongo for consumption by the UI.

Start the service by running:

```bash
python -m knowledge_service
```

Docker/compose deployments can run it in a dedicated container using the same
entry point.
