"""Database initialization and management utilities"""

from .config.settings import create_db_and_tables, engine, SessionLocal, Base
from .models import *  # 모든 모델을 import


def init_db():
    """데이터베이스와 모든 테이블을 초기화합니다."""
    create_db_and_tables()


def get_db():
    """데이터베이스 세션을 생성하고 반환합니다."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


if __name__ == "__main__":
    init_db() 