"""测试公共配置和 fixtures。"""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.src.db.database import Base


@pytest.fixture()
def db() -> Session:  # type: ignore[misc]
    """提供一个内存中的 SQLite 数据库会话，每个测试用例独立。"""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()
