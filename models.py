from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import Column, String, TIMESTAMP, Integer, Text, text


class Base(DeclarativeBase):
    pass


class Index(Base):
    __tablename__ = "indexes"

    index_id = Column(String(255), primary_key=True, nullable=False)

    url = Column(Text, nullable=False)

    collection_name = Column(String(255), nullable=False)

    status = Column(
        String(50),
        nullable=False,
        default="processing",
        server_default=text("'processing'")
    )

    pages_crawled = Column(
        Integer,
        default=0,
        server_default=text("0")
    )

    chunks_created = Column(
        Integer,
        default=0,
        server_default=text("0")
    )

    error_message = Column(Text, nullable=True)

    created_at = Column(
        TIMESTAMP,
        server_default=text("CURRENT_TIMESTAMP")
    )