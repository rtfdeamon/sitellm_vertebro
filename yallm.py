"""Wrappers around LlamaCpp for Yandex GPT models."""

from collections import namedtuple

from huggingface_hub import hf_hub_download
from langchain_community.llms import LlamaCpp
from langchain_community.embeddings import LlamaCppEmbeddings
from langchain_core.embeddings import Embeddings
from langchain_core.prompt_values import ChatPromptValue
from langchain_core.runnables.config import ensure_config
from langchain_core.messages.utils import convert_to_messages

from backend.cache import cache_response
import structlog

logger = structlog.get_logger(__name__)


YaGPTResponse = namedtuple("YaGPTResponse", ["speaker", "text"])


class YaLLM:
    """Asynchronous wrapper around ``LlamaCpp`` for text generation."""

    def __init__(self) -> None:
        """Download the model and prepare the ``LlamaCpp`` instance."""
        logger.info("download model")
        hf_hub_download(
            "yandex/YandexGPT-5-Lite-8B-instruct-GGUF",
            "YandexGPT-5-Lite-8B-instruct-Q4_K_M.gguf",
            local_dir=".",
        )
        self.llama = LlamaCpp(
            model_path="YandexGPT-5-Lite-8B-instruct-Q4_K_M.gguf",
            n_ctx=32768,
            use_mlock=True,
            n_gpu_layers=-1,
            verbose=False,
            n_batch=512,
        )
        logger.info("model ready")

    @cache_response
    async def respond(
        self, session: list[dict[str, str]], starting_prompt: list[dict[str, str]]
    ) -> str:
        """Generate a response for ``session`` using ``starting_prompt``.

        Parameters
        ----------
        session:
            Conversation history sent to the model.
        starting_prompt:
            Initial system messages prepended to ``session``.

        Returns
        -------
        str
            Text of the assistant reply.
        """
        session = convert_to_messages(starting_prompt + session)
        config = ensure_config(None)

        responses = await self.llama.agenerate_prompt(
            [ChatPromptValue(messages=session)],
            stop=None,
            callbacks=config.get("callbacks"),
            tags=config.get("tags"),
            metadata=config.get("metadata"),
            run_name=config.get("run_name"),
            run_id=config.pop("run_id", None),
        )
        processed = []

        for response in responses.generations[0]:
            speaker = "AI"
            ai_answer_start = f"{speaker}: "
            position = response.text.find(ai_answer_start)

            text = response.text[position + len(ai_answer_start) - 1 :]
            processed.append(YaGPTResponse(speaker, text))

        logger.info("generated", count=len(processed))
        return processed[-1].text if processed else ""


class YaLLMEmbeddings:
    """Provide embeddings model compatible with ``langchain``."""

    def __init__(self) -> None:
        """Download the embeddings model and initialize the wrapper."""
        logger.info("download embeddings model")
        hf_hub_download(
            "yandex/YandexGPT-5-Lite-8B-instruct-GGUF",
            "YandexGPT-5-Lite-8B-instruct-Q4_K_M.gguf",
            local_dir=".",
        )
        self.embeddings = LlamaCppEmbeddings(
            model_path="YandexGPT-5-Lite-8B-instruct-Q4_K_M.gguf",
            n_ctx=32768,
            n_gpu_layers=-1,
            verbose=False,
            n_batch=512,
        )

    def get_embeddings_model(self) -> Embeddings:
        """Return the underlying embeddings implementation.

        This model can be passed directly to ``langchain`` vector stores.
        """

        logger.info("embeddings ready")
        return self.embeddings
