"""
데이터베이스 연결 및 세션 관리, 테이블 생성 등
데이터베이스 관련 로직을 총괄하는 모듈입니다.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from contextlib import contextmanager

# 설정 파일에서 DATABASE_URL을 가져옵니다.
from infrastructure.db.config.settings import DATABASE_URL

# --- 데이터베이스 엔진 및 세션 설정 ---
engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def create_db_and_tables():
    """
    데이터베이스와 Base에 등록된 모든 테이블을 생성합니다.
    이 함수를 호출하기 전에 모든 모델이 import 되어 Base.metadata에 등록되어 있어야 합니다.
    """
    # models 패키지 내의 모든 모듈을 import하여 테이블이 Base에 등록되도록 합니다.
    # 이 과정이 없으면 Base.metadata.create_all()이 테이블을 찾지 못할 수 있습니다.
    from infrastructure.db import models
    Base.metadata.create_all(bind=engine)
    print("Database and tables checked/created successfully for MySQL.")


def init_db():
    """데이터베이스와 모든 테이블을 초기화합니다."""
    create_db_and_tables()


@contextmanager
def get_db():
    """데이터베이스 세션을 생성하고 반환하는 제너레이터입니다."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


if __name__ == "__main__":
    print("Initializing database...")
    init_db()
    print("Database initialization complete.") 