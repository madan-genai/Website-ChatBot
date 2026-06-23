from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from models import Index
from config import MYSQL_USER, MYSQL_PASSWORD, MYSQL_HOST, MYSQL_DATABASE, MYSQL_PORT
from urllib.parse import quote_plus
password = quote_plus(MYSQL_PASSWORD)

DATABASE_URL = (
    f"mysql+pymysql://{MYSQL_USER}:{password}"
    f"@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}"
)

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def save_index(
    index_id: str,
    url: str,
    collection_name: str,
    status: str,
    db: Session
):
    record = db.query(Index).filter(
        Index.index_id == index_id
    ).first()

    if record:
        record.url = url
        record.collection_name = collection_name
        record.status = status
    else:
        record = Index(
            index_id=index_id,
            url=url,
            collection_name=collection_name,
            status=status
        )
        db.add(record)

    db.commit()
    db.refresh(record)
    return record


def get_index(index_id: str, db: Session):
    return db.query(Index).filter(
        Index.index_id == index_id
    ).first()

def get_index_by_url(url: str, db):
    return db.query(Index).filter(
        Index.url == url
    ).first()