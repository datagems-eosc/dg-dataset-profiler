"""Centralized, fault-tolerant Ray client connection management.

The Ray head node is memory capped (4Gi) and occasionally gets OOMKilled and
replaced. The API process must therefore tolerate Ray being unavailable at
startup and tolerate the Ray head being restarted while the API is running,
*without* crashing and *without* deregistering the pod from the Kubernetes
Service.

This module centralizes every Ray connection concern:

* ``ensure_connection`` connects lazily and reconnects on demand if the
  existing client connection went stale (e.g. after a Ray head restart). It
  performs ONE clean reconnect (``ray.shutdown`` then ``ray.init``) rather than
  stacking a second client, which would raise the ``allow_multiple=True`` error.
* ``health_status`` reports Ray status using a lightweight read on the EXISTING
  connection. It never raises and never lets a Ray outage propagate as an HTTP
  error.
* ``connect_with_retry`` is used by the FastAPI startup hook to attempt an
  initial connection with backoff, but it never raises -- a Ray outage must not
  crash the web server.

A short cooldown guards against every request/health call paying the full
~30s Ray client connect timeout while the cluster is down: once an attempt
fails, subsequent calls report "degraded" immediately until the cooldown
elapses.
"""

import os
import threading
import time

# Make a dropped client connection fail fast (default grace period is 30s).
# We handle reconnection ourselves via a clean ray.shutdown()+ray.init(), so we
# don't want Ray's built-in reconnect logic to block calls for half a minute.
os.environ.setdefault("RAY_CLIENT_RECONNECT_GRACE_PERIOD", "5")

import ray

from dataset_profiler.configs.config_logging import logger


RAY_ADDRESS = os.getenv("RAY_ADDRESS", "ray://ray-head:10001")

# After a failed connection attempt, skip further blocking connect attempts for
# this many seconds and report Ray as degraded immediately. Keeps the health
# endpoint and request path responsive during a sustained Ray outage.
_CONNECT_COOLDOWN_SEC = float(os.getenv("RAY_CONNECT_COOLDOWN_SEC", "10"))

# Serialize all ray.init / ray.shutdown transitions. ray.init is not safe to
# call concurrently, and we never want two threads racing a reconnect.
_lock = threading.Lock()
_last_failure_ts = 0.0


def _ray_init() -> None:
    """(Re)connect the Ray client. Caller must hold ``_lock``."""
    ray.init(
        address=RAY_ADDRESS,
        ignore_reinit_error=True,
        log_to_driver=False,
        logging_level="error",
    )


def _ping() -> list:
    """Lightweight read against the live connection. Raises if stale/unreachable."""
    nodes = ray.nodes()
    return [n for n in nodes if n.get("Alive")]


def _reconnect() -> None:
    """Tear down a stale client and establish a fresh one. Caller must hold ``_lock``."""
    try:
        ray.shutdown()
    except Exception as ex:  # pragma: no cover - shutdown should not raise, but be safe
        logger.warning("ray.shutdown during reconnect raised", error=str(ex))
    _ray_init()


def _in_cooldown() -> bool:
    return (time.monotonic() - _last_failure_ts) < _CONNECT_COOLDOWN_SEC


def _note_failure() -> None:
    global _last_failure_ts
    _last_failure_ts = time.monotonic()


def _note_success() -> None:
    global _last_failure_ts
    _last_failure_ts = 0.0


def _connect_and_probe():
    """Probe-and-reconnect logic shared by callers. Caller must hold ``_lock``.

    Returns the list of alive Ray nodes if Ray ends up connected and reachable,
    or ``None`` otherwise. Never raises.
    """
    if ray.is_initialized():
        # We hold a client object, but the head may have been replaced and the
        # connection may be stale. Probe it cheaply.
        try:
            alive = _ping()
            _note_success()
            return alive
        except Exception as ex:
            logger.warning("Ray connection appears stale, reconnecting", error=str(ex))
            if _in_cooldown():
                return None
            try:
                _reconnect()
                alive = _ping()
                _note_success()
                logger.info("Ray reconnected after stale connection")
                return alive
            except Exception as reconnect_ex:
                logger.error("Ray reconnect failed", error=str(reconnect_ex))
                _note_failure()
                return None

    # No connection yet -- establish one (unless we just failed and are cooling down).
    if _in_cooldown():
        return None
    try:
        _ray_init()
        alive = _ping()
        _note_success()
        return alive
    except Exception as ex:
        logger.error("Ray connection attempt failed", error=str(ex))
        _note_failure()
        return None


def ensure_connection() -> bool:
    """Guarantee a usable Ray connection, reconnecting once if it went stale.

    Returns ``True`` if Ray is connected and reachable, ``False`` otherwise.
    Never raises -- callers decide how to surface an unavailable cluster.
    """
    with _lock:
        return _connect_and_probe() is not None


def connect_with_retry(max_attempts: int = 5, base_backoff: float = 1.0) -> bool:
    """Attempt to connect to Ray with exponential backoff. Never raises.

    Used by the FastAPI startup hook. A Ray outage at startup must not crash the
    web server; the API stays up and reconnects lazily later.
    """
    for attempt in range(1, max_attempts + 1):
        # Bypass the cooldown for the deliberate startup retry loop.
        with _lock:
            _note_success()  # reset so each startup attempt actually tries
            connected = _connect_and_probe() is not None
        if connected:
            logger.info("Connected to Ray cluster", ray_address=RAY_ADDRESS, attempt=attempt)
            return True
        if attempt < max_attempts:
            backoff = base_backoff * (2 ** (attempt - 1))
            logger.warning(
                "Ray not reachable yet, will retry",
                ray_address=RAY_ADDRESS,
                attempt=attempt,
                max_attempts=max_attempts,
                backoff_seconds=backoff,
            )
            time.sleep(backoff)

    logger.warning(
        "Could not connect to Ray on startup; API will serve and reconnect lazily",
        ray_address=RAY_ADDRESS,
    )
    return False


def health_status() -> dict:
    """Report Ray health using the EXISTING connection -- never calls a bare ray.init().

    Performs a lightweight read against the live connection. If the connection is
    stale, does ONE clean reconnect rather than stacking a second client. Always
    returns a dict (never raises, never the ``allow_multiple=True`` error), so the
    caller can keep the pod Ready and merely report Ray as degraded.
    """
    config = {"ray_address": RAY_ADDRESS}
    with _lock:
        alive_nodes = _connect_and_probe()
        if alive_nodes is None:
            return {
                "status": "degraded",
                "message": "Ray cluster is not reachable.",
                "config": config,
            }
        if alive_nodes:
            return {
                "status": "healthy",
                "message": f"Ray cluster reachable with {len(alive_nodes)} alive node(s).",
            }
        return {
            "status": "degraded",
            "message": "No alive Ray nodes detected.",
            "config": config,
        }
