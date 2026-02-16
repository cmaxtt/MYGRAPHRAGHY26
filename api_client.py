import logging
import asyncio
from typing import List, Optional, cast
from openai import AsyncOpenAI
from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine
from cachetools import LRUCache

from config import settings

logger = logging.getLogger(__name__)


class DeepSeekClient:
    """
    Production client for DeepSeek API integration (OpenAI-compatible).
    Includes PII scrubbing and caching.
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DeepSeekClient, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.api_key = settings.DEEPSEEK_API_KEY
        self.base_url = settings.DEEPSEEK_BASE_URL

        if not self.api_key:
            logger.warning("DEEPSEEK_API_KEY is not set. API calls will fail.")
            # Create a dummy client or handle it to avoid crash on init
            # OpenAI client requires api_key, so we can pass a dummy one if missing,
            # but calls will fail. This allows the app to load.
            self.client = AsyncOpenAI(api_key="dummy", base_url=self.base_url)
        else:
            self.client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)

        self.chat_model = settings.DEEPSEEK_MODEL_CHAT
        self.reasoner_model = settings.DEEPSEEK_MODEL_REASONER
        self.embed_model = settings.DEEPSEEK_MODEL_EMBED

        # Local Embedding Model limit
        self._local_embed_model = None

        # PII Scrubbing
        try:
            self.analyzer = AnalyzerEngine()
            self.anonymizer = AnonymizerEngine()
            self._pii_enabled = True
        except Exception as e:
            logger.error(f"Failed to initialize Presidio: {e}. PII scrubbing disabled.")
            self._pii_enabled = False

        # In-memory LRU cache for embeddings (max 1000 items)
        self.embedding_cache = LRUCache(maxsize=1000)

        self._initialized = True

    async def _scrub_pii(self, text: str) -> str:
        """Scrub PII from text using Presidio."""
        if not self._pii_enabled:
            return text

        try:
            results = self.analyzer.analyze(
                text=text,
                language="en",
                entities=["PERSON", "PHONE_NUMBER", "EMAIL_ADDRESS", "IP_ADDRESS"],
            )
            anonymized_result = self.anonymizer.anonymize(
                text=text, analyzer_results=results
            )
            return anonymized_result.text
        except Exception as e:
            logger.error(f"Error scrubbing PII: {e}")
            return text

    async def get_completion(
        self,
        prompt: str,
        system_prompt: str = "",
        model: str = None,
        scrub_pii: bool = True,
    ) -> str:
        """
        Handles LLM synthesis with PII scrubbing and optional prompt caching.
        """
        target_model = model or self.chat_model

        # Scrub PII from user prompt
        safe_prompt = await self._scrub_pii(prompt) if scrub_pii else prompt

        # DeepSeek Prompt Caching: Put static large context in system prompt at the beginning
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.append({"role": "user", "content": safe_prompt})

        try:
            response = await self.client.chat.completions.create(
                model=target_model, messages=messages, stream=False
            )
            content = response.choices[0].message.content
            if content is None:
                logger.warning(
                    f"Start of response content is None. Full response: {response}"
                )
                return ""
            return content
        except Exception as e:
            logger.error(f"Error in get_completion: {e}")
            raise

    async def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generates vectors via local SentenceTransformer for high performance/availability.
        Keeps API for Chat/Reasoning only.
        """
        if isinstance(texts, str):
            texts = [texts]

        # Check cache first
        results: List[Optional[List[float]]] = [None] * len(texts)
        uncached_indices = []
        uncached_texts = []

        for i, text in enumerate(texts):
            cached = self.embedding_cache.get(text)
            if cached:
                # Ensure cached embedding is a list (not tensor)
                if hasattr(cached, "tolist"):
                    cached = cached.tolist()
                    self.embedding_cache[text] = cached  # update cache with list
                results[i] = cached
            else:
                uncached_indices.append(i)
                uncached_texts.append(text)

        if not uncached_texts:
            # All results should be non-None now
            assert all(r is not None for r in results)
            return cast(List[List[float]], results)

        # Scrub PII
        safe_texts = [await self._scrub_pii(t) for t in uncached_texts]

        # Lazy load model
        if self._local_embed_model is None:
            from sentence_transformers import SentenceTransformer

            # Using all-mpnet-base-v2 (768d)
            model_name = "sentence-transformers/all-mpnet-base-v2"
            if (
                settings.DEEPSEEK_MODEL_EMBED
                and "sentence-transformers" in settings.DEEPSEEK_MODEL_EMBED
            ):
                model_name = settings.DEEPSEEK_MODEL_EMBED

            logger.info(f"Loading local embedding model: {model_name}...")
            # Run in executor to avoid blocking event loop during load
            loop = asyncio.get_running_loop()
            self._local_embed_model = await loop.run_in_executor(
                None, SentenceTransformer, model_name
            )

        assert self._local_embed_model is not None, "Embedding model not loaded"
        try:
            # Encoding is CPU bound, run in thread
            loop = asyncio.get_running_loop()
            embeddings = await loop.run_in_executor(
                None,
                lambda: self._local_embed_model.encode(safe_texts, convert_to_numpy=False, normalize_embeddings=True),  # type: ignore
            )

            # Update results and cache
            for j, embedding in enumerate(embeddings):
                original_idx = uncached_indices[j]
                original_text = texts[original_idx]

                # Convert tensor to list of floats for database compatibility
                embedding_list = embedding.tolist()
                results[original_idx] = embedding_list
                self.embedding_cache[original_text] = embedding_list

        except Exception as e:
            logger.error(f"Error getting local embeddings: {e}")
            raise

        return cast(List[List[float]], results)

    async def get_reasoning(self, prompt: str) -> str:
        """
        Uses DeepSeek Reasoner (R1) for complex tasks like Entity Resolution.
        """
        return await self.get_completion(prompt, model=self.reasoner_model)


api_client = DeepSeekClient()
