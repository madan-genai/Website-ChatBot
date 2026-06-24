import redis
import hashlib
import json
import logging

from config2 import REDIS_URL

logger = logging.getLogger("cache")

try:
    _client = redis.from_url(REDIS_URL, decode_responses=True, socket_timeout=2)
    _client.ping()
    REDIS_AVAILABLE = True
    logger.info("Redis connected")
except Exception as e:
    _client = None
    REDIS_AVAILABLE = False
    logger.warning(f"Redis not available — caching disabled: {e}")


def _key(index_id: str, question: str) -> str:
    h = hashlib.sha256(f"{index_id}::{question.strip().lower()}".encode()).hexdigest()
    return f"rag:answer:{h}"


def get_cached(index_id: str, question: str) -> str | None:
    if not REDIS_AVAILABLE:
        return None
    try:
        raw = _client.get(_key(index_id, question))
        if raw:
            data = json.loads(raw)
            logger.info(f"Cache HIT for index={index_id}")
            return data.get("answer")
    except Exception as e:
        logger.warning(f"Cache get error: {e}")
    return None


def set_cached(index_id: str, question: str, answer: str, ttl: int = 3600):
    if not REDIS_AVAILABLE or not answer.strip():
        return
    try:
        _client.setex(
            _key(index_id, question),
            ttl,
            json.dumps({"answer": answer})
        )
        logger.info(f"Cache SET for index={index_id}")
    except Exception as e:
        logger.warning(f"Cache set error: {e}")


def invalidate_index(index_id: str):
    """Delete all cached answers for a given index (on reindex/delete)."""
    if not REDIS_AVAILABLE:
        return
    try:
        pattern = f"rag:answer:*"
        keys = _client.keys(pattern)
        if keys:
            _client.delete(*keys)
        logger.info(f"Cache invalidated for index={index_id}")
    except Exception as e:
        logger.warning(f"Cache invalidate error: {e}")
