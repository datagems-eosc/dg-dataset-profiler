"""Ray task behind the MathE document endpoints: convert one PDF to Markdown."""

import ray
from structlog.contextvars import bind_contextvars, clear_contextvars

from dataset_profiler.configs.config_logging import logger
from dataset_profiler.document_processing.markdown_cache import store_cached
from dataset_profiler.document_processing.service import ConversionMode, convert_document
from dataset_profiler.document_processing.vlm_transcription import (
    TranscriptionError,
    UnsupportedDocumentError,
)

CONVERSION_FAILED = "The document could not be converted"


def convert_and_cache(path: str, mode: str, cache_key: str, file_object_id: str) -> dict:
    """``{"result": ConvertResult as JSON}`` or ``{"error": message}``. Never raises.

    A successful conversion is cached here, so that a request that timed out
    is served from the cache when it is retried.
    """
    clear_contextvars()
    bind_contextvars(file_object_id=file_object_id)
    try:
        logger.info("Document conversion started", mode=mode)
        result = convert_document(path, ConversionMode(mode))
        store_cached(cache_key, result)
        logger.info("Document conversion completed", pages=result.pages,
                    fallback_pages=result.fallback_pages)
        return {"result": result.model_dump(mode="json")}
    except UnsupportedDocumentError as e:
        logger.warning("Document conversion refused the document", error=str(e))
        return {"error": str(e)}
    except TranscriptionError as e:
        # The vision model failed on every page.
        logger.error("Document conversion failed", error=str(e))
        return {"error": str(e)}
    except Exception as e:  # noqa: BLE001 - reported on the file's node, never raised
        logger.exception("Document conversion failed", error=str(e))
        return {"error": CONVERSION_FAILED}
    finally:
        clear_contextvars()


convert_document_task = ray.remote(convert_and_cache)
