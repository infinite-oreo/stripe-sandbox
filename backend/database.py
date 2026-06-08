"""
[INPUT]: 依赖 sqlalchemy 的 create_engine/sessionmaker
[OUTPUT]: 对外提供 engine, SessionLocal, Base, get_db
[POS]: 数据层底座，所有 model 和 router 的依赖注入源头
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

SQLALCHEMY_DATABASE_URL = "sqlite:///./stripe_mock.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
