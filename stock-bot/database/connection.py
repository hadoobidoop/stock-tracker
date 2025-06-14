# stock_bot/database/connection.py
# 설명: 데이터베이스 연결 설정(엔진)과 세션 생성을 담당합니다.

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager
from ..config import DATABASE_URL # 루트의 config.py에서 DB URL 가져오기

# DB 엔진은 애플리케이션 전체에서 한번만 생성하는 것이 효율적입니다.
engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@contextmanager
def get_db_session():
    """세션 컨텍스트 매니저를 통해 안정적인 DB 세션을 제공하고 자동 종료를 보장합니다."""
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()
