from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from urllib.parse import quote_plus

from models2 import Base, Index, ChatHistory
from config2 import (
    MYSQL_USER, MYSQL_PASSWORD,
    MYSQL_HOST, MYSQL_DATABASE, MYSQL_PORT
)

password     = quote_plus(MYSQL_PASSWORD)
DATABASE_URL = (
    f"mysql+pymysql://{MYSQL_USER}:{password}"
    f"@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}"
)

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600
)

# Auto-create tables on startup
Base.metadata.create_all(bind=engine)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── Index helpers ──────────────────────────────────────────────────────────
def save_index(
    index_id: str,
    url: str,
    collection_name: str,
    status: str,
    db: Session,
    pages_crawled: int = 0,
    chunks_created: int = 0,
    error_message: str = None,
):
    url    = str(url).strip()
    record = db.query(Index).filter(Index.index_id == index_id).first()

    if record:
        record.url             = url
        record.collection_name = collection_name
        record.status          = status
        record.pages_crawled   = pages_crawled
        record.chunks_created  = chunks_created
        record.error_message   = error_message
    else:
        record = Index(
            index_id=index_id,
            url=url,
            collection_name=collection_name,
            status=status,
            pages_crawled=pages_crawled,
            chunks_created=chunks_created,
            error_message=error_message,
        )
        db.add(record)

    db.commit()
    db.refresh(record)
    return record


def get_index(index_id: str, db: Session):
    return db.query(Index).filter(Index.index_id == index_id).first()


def get_index_by_url(url: str, db: Session):
    url = str(url).strip()
    return db.query(Index).filter(Index.url == url).first()


def delete_index(index_id: str, db: Session) -> bool:
    record = db.query(Index).filter(Index.index_id == index_id).first()
    if not record:
        return False
    db.delete(record)
    db.commit()
    return True


# ── Chat history helpers ───────────────────────────────────────────────────
def save_message(
    index_id: str,
    session_id: str,
    role: str,
    content: str,
    db: Session,
):
    msg = ChatHistory(
        index_id=index_id,
        session_id=session_id,
        role=role,
        content=content,
    )
    db.add(msg)
    db.commit()
    return msg


def get_chat_history(
    index_id: str,
    session_id: str,
    db: Session,
    limit: int = 50,
) -> list[ChatHistory]:
    return (
        db.query(ChatHistory)
        .filter(
            ChatHistory.index_id   == index_id,
            ChatHistory.session_id == session_id,
        )
        .order_by(ChatHistory.created_at.asc())
        .limit(limit)
        .all()
    )


def delete_chat_history(index_id: str, session_id: str, db: Session):
    db.query(ChatHistory).filter(
        ChatHistory.index_id   == index_id,
        ChatHistory.session_id == session_id,
    ).delete()
    db.commit()


def delete_all_chat_history(index_id: str, db: Session):
    db.query(ChatHistory).filter(
        ChatHistory.index_id == index_id
    ).delete()
    db.commit()
