import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# .env 파일에서 환경 변수 로드
load_dotenv()

# 데이터베이스 URL 설정
DATABASE_URL = os.getenv("DATABASE_URL", "mysql+pymysql://user:password@localhost/stock_tracker")

# SQLAlchemy 엔진 및 세션 설정
engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def create_db_and_tables():
    """데이터베이스와 테이블을 생성합니다."""
    Base.metadata.create_all(bind=engine)
    print("Database and tables checked/created successfully for MySQL.")
