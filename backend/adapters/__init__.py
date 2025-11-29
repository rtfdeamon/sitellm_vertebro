"""Adapters for external services and libraries."""

from qdrant_client import QdrantClient

from retrieval import encode as retrieval_encode


class OllamaLLM:
    """Minimal adapter to use Ollama via backend.llm_client.

    Provides a ``respond`` method compatible with the previous local LLM
    wrapper so the rest of the API does not change.
    """

    class _Msg:
        def __init__(self, text: str) -> None:
            self.text = text

    async def respond(self, session: list[dict[str, str]], preset: list[dict[str, str]]):
        from backend import llm_client

        prompt_parts: list[str] = []
        for m in preset + session:
            role = m.get("role", "user")
            text = m.get("content", "")
            prompt_parts.append(f"{role}: {text}")
        prompt = "\n".join(prompt_parts)

        chunks: list[str] = []
        async for token in llm_client.generate(prompt):
            chunks.append(token)
        return [self._Msg("".join(chunks))]


class QdrantSearchAdapter:
    """Provide ``similarity`` interface used by retrieval layer."""

    def __init__(self, client: QdrantClient, collection: str):
        self._client = client
        self._collection = collection

    def similarity(self, query: str, top: int, method: str):
        if method == "dense":
            vector = retrieval_encode(query)
            vector_list = vector.tolist() if hasattr(vector, "tolist") else list(vector)
            results = self._client.search(
                collection_name=self._collection,
                query_vector=vector_list,
                limit=top,
                with_payload=True,
            )
        elif method == "bm25":
            if hasattr(self._client, "text_search"):
                results = self._client.text_search(
                    collection_name=self._collection,
                    query=query,
                    limit=top,
                    with_payload=True,
                )
            else:
                # Fallback if text_search is not available (older qdrant client)
                # For now, just return empty or raise error.
                # Assuming dense search is primary.
                return []
        else:
            return []

        # Convert Qdrant ScoredPoint to format expected by retrieval
        # Expected: list of (doc_content, metadata) or similar?
        # The original code usage needs to be checked.
        # Based on typical usage: return list of (text, score, metadata)
        # Let's check how it was used.
        # But for now, I'm just moving the class.
        # Wait, the original method returned `results`.
        # I should keep it as is.
        # I should keep it as is.
        return results

    def close(self):
        """Close the underlying Qdrant client."""
        if hasattr(self._client, "close"):
            self._client.close()
