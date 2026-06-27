import time
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import OperationalError
from sqlalchemy.dialects.mysql import insert as mysql_insert
from urllib.parse import quote_plus, urlparse, urlunparse
from typing import Generator

from models2 import Base, Index, ChatHistory
from config2 import (
    MYSQL_USER, MYSQL_PASSWORD,
    MYSQL_HOST, MYSQL_DATABASE, MYSQL_PORT
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Database URL
# ---------------------------------------------------------------------------

password = quote_plus(MYSQL_PASSWORD)
DATABASE_URL = (
    f"mysql+pymysql://{MYSQL_USER}:{password}"
    f"@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}"
)


# ---------------------------------------------------------------------------
# Engine with retry
# ---------------------------------------------------------------------------

def _create_engine_with_retry(
    url: str,
    retries: int = 10,
    delay: float = 3.0,
) -> object:
    """
    Create a SQLAlchemy engine with retry logic.

    Retries the connection until MySQL is ready or retries are exhausted.
    Uses a fixed delay between attempts (suitable for container startup).

    Args:
        url: SQLAlchemy database URL.
        retries: Maximum number of connection attempts.
        delay: Seconds to wait between attempts.

    Returns:
        A connected SQLAlchemy Engine instance.

    Raises:
        RuntimeError: If all retry attempts are exhausted.
    """
    for attempt in range(1, retries + 1):
        try:
            _engine = create_engine(
                url,
                pool_pre_ping=True,   # validates connections before use
                pool_recycle=3600,    # recycle connections every 1 hour
            )
            # create_engine() is lazy — force an actual TCP connection
            with _engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("MySQL connection established successfully.")
            return _engine
        except OperationalError as e:
            logger.warning(
                f"MySQL not ready (attempt {attempt}/{retries}). "
                f"Retrying in {delay}s... Error: {e}"
            )
            time.sleep(delay)

    raise RuntimeError(
        f"MySQL unavailable after {retries} attempts. "
        "Check DATABASE_URL and MySQL container health."
    )


engine = _create_engine_with_retry(DATABASE_URL)
Base.metadata.create_all(bind=engine)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# ---------------------------------------------------------------------------
# Dependency
# ---------------------------------------------------------------------------

def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that yields a database session.

    Commits on success, rolls back on any exception,
    and always closes the session.
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# ---------------------------------------------------------------------------
# URL utilities
# ---------------------------------------------------------------------------

def normalize_url(url: str) -> str:
    """
    Normalize a URL for consistent storage and deduplication.

    - Strips whitespace
    - Adds http:// if scheme is missing
    - Lowercases scheme and netloc
    - Removes www. prefix
    - Strips trailing slashes from path
    - Removes query strings and fragments

    Args:
        url: Raw URL string from user input.

    Returns:
        Normalized URL string.
    """
    url = str(url).strip()
    if not url:
        return url

    if not url.startswith(("http://", "https://")):
        url = "http://" + url

    parsed = urlparse(url)
    netloc = parsed.netloc.lower().replace("www.", "")
    path = parsed.path.rstrip("/") or "/"

    cleaned = parsed._replace(
        scheme=parsed.scheme.lower(),
        netloc=netloc,
        path=path,
        query="",
        fragment="",
    )
    return urlunparse(cleaned)


# ---------------------------------------------------------------------------
# Index operations
# ---------------------------------------------------------------------------

def save_index(
    index_id: str,
    url: str,
    collection_name: str,
    status: str,
    db: Session,
    pages_crawled: int = 0,
    chunks_created: int = 0,
    error_message: str | None = None,
) -> Index:
    """
    Atomically insert or update an Index record.

    Uses MySQL ON DUPLICATE KEY UPDATE to avoid race conditions
    under concurrent requests with the same index_id.

    Args:
        index_id: Unique identifier for the index.
        url: URL that was indexed (will be normalized).
        collection_name: Qdrant collection name.
        status: Current status (e.g. 'pending', 'complete', 'failed').
        db: Active SQLAlchemy session.
        pages_crawled: Number of pages crawled.
        chunks_created: Number of vector chunks created.
        error_message: Error detail if status is 'failed'.

    Returns:
        The saved or updated Index ORM instance.
    """
    url = normalize_url(url)

    stmt = mysql_insert(Index).values(
        index_id=index_id,
        url=url,
        collection_name=collection_name,
        status=status,
        pages_crawled=pages_crawled,
        chunks_created=chunks_created,
        error_message=error_message,
    )
    stmt = stmt.on_duplicate_key_update(
        url=stmt.inserted.url,
        collection_name=stmt.inserted.collection_name,
        status=stmt.inserted.status,
        pages_crawled=stmt.inserted.pages_crawled,
        chunks_created=stmt.inserted.chunks_created,
        error_message=stmt.inserted.error_message,
    )
    db.execute(stmt)
    db.commit()

    return db.query(Index).filter(Index.index_id == index_id).first()


def get_index(index_id: str, db: Session) -> Index | None:
    """
    Fetch an Index record by its ID.

    Args:
        index_id: Unique index identifier.
        db: Active SQLAlchemy session.

    Returns:
        Index instance or None if not found.
    """
    return db.query(Index).filter(Index.index_id == index_id).first()


def get_index_by_url(url: str, db: Session) -> Index | None:
    """
    Fetch an Index record by normalized URL.

    Args:
        url: Raw URL to look up (will be normalized before query).
        db: Active SQLAlchemy session.

    Returns:
        Index instance or None if not found.
    """
    url = normalize_url(url)
    return db.query(Index).filter(Index.url == url).first()


def delete_index(index_id: str, db: Session) -> bool:
    """
    Delete an Index record by ID.

    Args:
        index_id: Unique index identifier.
        db: Active SQLAlchemy session.

    Returns:
        True if deleted, False if record did not exist.
    """
    record = db.query(Index).filter(Index.index_id == index_id).first()
    if not record:
        logger.warning(f"delete_index: index_id={index_id} not found.")
        return False
    db.delete(record)
    db.commit()
    logger.info(f"Deleted index record: index_id={index_id}")
    return True


# ---------------------------------------------------------------------------
# Chat history operations
# ---------------------------------------------------------------------------

def save_message(
    index_id: str,
    session_id: str,
    role: str,
    content: str,
    db: Session,
) -> ChatHistory:
    """
    Persist a single chat message to history.

    Args:
        index_id: Index the conversation belongs to.
        session_id: Unique session identifier.
        role: Message role ('user' or 'assistant').
        content: Message text content.
        db: Active SQLAlchemy session.

    Returns:
        The saved ChatHistory ORM instance.
    """
    msg = ChatHistory(
        index_id=index_id,
        session_id=session_id,
        role=role,
        content=content,
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    logger.debug(f"Saved message: session_id={session_id} role={role}")
    return msg


def get_chat_history(
    index_id: str,
    session_id: str,
    db: Session,
    limit: int = 50,
) -> list[ChatHistory]:
    """
    Retrieve chat history for a session, ordered oldest-first.

    Args:
        index_id: Index the conversation belongs to.
        session_id: Unique session identifier.
        db: Active SQLAlchemy session.
        limit: Maximum number of messages to return.

    Returns:
        List of ChatHistory instances ordered by created_at ascending.
    """
    return (
        db.query(ChatHistory)
        .filter(
            ChatHistory.index_id == index_id,
            ChatHistory.session_id == session_id,
        )
        .order_by(ChatHistory.created_at.asc())
        .limit(limit)
        .all()
    )


def delete_chat_history(
    index_id: str,
    session_id: str,
    db: Session,
) -> int:
    """
    Delete all chat history for a specific session.

    Args:
        index_id: Index the conversation belongs to.
        session_id: Unique session identifier.
        db: Active SQLAlchemy session.

    Returns:
        Number of rows deleted.
    """
    deleted = (
        db.query(ChatHistory)
        .filter(
            ChatHistory.index_id == index_id,
            ChatHistory.session_id == session_id,
        )
        .delete()
    )
    db.commit()
    logger.info(
        f"Deleted {deleted} messages: "
        f"index_id={index_id} session_id={session_id}"
    )
    return deleted


def delete_all_chat_history(
    index_id: str,
    db: Session,
) -> int:
    """
    Delete all chat history across all sessions for an index.

    Used when an index is fully deleted to clean up orphaned messages.

    Args:
        index_id: Index whose history should be purged.
        db: Active SQLAlchemy session.

    Returns:
        Number of rows deleted.
    """
    deleted = (
        db.query(ChatHistory)
        .filter(ChatHistory.index_id == index_id)
        .delete()
    )
    db.commit()
    logger.info(
        f"Purged all chat history: index_id={index_id} "
        f"rows_deleted={deleted}"
    )
    return deleted