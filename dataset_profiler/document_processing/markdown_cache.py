"""Converted documents, kept in Redis by content hash, mode and model.

A vision-model conversion takes seconds per page, and the same MathE PDFs are
asked for again and again. The key is the hash of the file's bytes, so a
changed file is converted again whatever its FileObject id.

* Failures are not cached, and neither are conversions where the model failed
  on some pages (``fallback_pages``): a degraded result must not stay for a month.
* The cache is best effort: when Redis is down, documents are converted again.
"""

import os
from typing import Optional

from dataset_profiler.configs.config_logging import logger
from dataset_profiler.document_processing.service import ConversionMode, ConvertResult
from dataset_profiler.document_processing.vlm_transcription import vlm_model
from dataset_profiler.job_manager.job_storing import get_redis_client

DEFAULT_CACHE_TTL_SECONDS = 30 * 24 * 3600


def cache_ttl_seconds() -> int:
    value = os.environ.get("DOCUMENT_CACHE_TTL_SECONDS")
    return int(value) if value else DEFAULT_CACHE_TTL_SECONDS


def conversion_model(mode: ConversionMode) -> str:
    """The model a conversion in this mode uses now; part of the cache key."""
    return vlm_model() if mode == ConversionMode.QUALITY else "none"


def cache_key(sha256: str, mode: ConversionMode) -> str:
    return f"document_markdown:{sha256}:{mode.value}:{conversion_model(mode)}"


def get_cached(key: str) -> Optional[ConvertResult]:
    try:
        raw = get_redis_client().get(key)
        return None if raw is None else ConvertResult.model_validate_json(raw)
    except Exception as e:  # noqa: BLE001 - a cache miss, never an error
        logger.warning("Document cache lookup failed", key=key, error=str(e))
        return None


def store_cached(key: str, result: ConvertResult) -> bool:
    """Keep the conversion, unless some pages fell back to the text layer."""
    if result.fallback_pages:
        return False
    try:
        get_redis_client().set(key, result.model_dump_json(), ex=cache_ttl_seconds())
        return True
    except Exception as e:  # noqa: BLE001 - the conversion is still returned
        logger.warning("Document cache write failed", key=key, error=str(e))
        return False
