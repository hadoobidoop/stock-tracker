# tests/test_database.py

import pytest
import os

from sqlalchemy import text
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.ext.asyncio import engine


# `main.py`와 동일한 레벨에서 `database.py`를 찾을 수 있도록 경로 설정이 필요할 수 있습니다.
# pytest를 프로젝트 루트 디렉터리에서 실행하면通常적으로 자동 처리됩니다.

# 이 테스트는 실제 DB에 연결하므로, 통합 테스트로 표시합니다.
@pytest.mark.integration
def test_database_connection():
    """
    설정된 DATABASE_URL을 사용하여 실제 데이터베이스 연결을 테스트합니다.
    이 테스트는 통합 테스트이며, 실행 전에 데이터베이스가 실행 중이고 접근 가능해야 합니다.
    또한, DATABASE_URL 환경 변수가 정확하게 설정되어 있어야 합니다.
    """
    # DATABASE_URL이 설정되지 않았다면 테스트를 건너뜁니다.
    if not os.getenv("DATABASE_URL"):
        pytest.skip("DATABASE_URL 환경 변수가 설정되지 않아 테스트를 건너뜁니다.")

    try:
        # engine.connect()는 커넥션 풀에서 실제 연결을 가져옵니다.
        connection = engine.connect()

        # 간단한 쿼리를 실행하여 연결이 활성 상태인지 확인합니다.
        connection.execute(text("SELECT 1"))

        # 여기까지 오류 없이 실행되었다면 연결은 성공한 것입니다.
        # 사용한 연결을 커넥션 풀에 반환합니다.
        connection.close()

        print("\nDatabase connection successful!")

    except OperationalError as e:
        # OperationalError는 호스트, 포트, 자격 증명 오류 등 연결 자체의 실패 시 발생합니다.
        pytest.fail(
            f"데이터베이스 연결에 실패했습니다. DATABASE_URL 환경 변수, DB 상태, 네트워크 접근 권한을 확인하세요.\n"
            f"Error: {e}"
        )
    except ProgrammingError as e:
        # ProgrammingError는 연결은 되었으나 DB가 없거나 권한이 없는 경우에 발생할 수 있습니다.
        pytest.fail(
            f"데이터베이스에 프로그래밍 오류가 발생했습니다. DB가 존재하지 않거나 사용자 권한이 부족할 수 있습니다.\n"
            f"Error: {e}"
        )
    except Exception as e:
        # 그 외 예기치 않은 예외를 처리합니다.
        pytest.fail(f"데이터베이스 연결 테스트 중 예기치 않은 오류가 발생했습니다: {e}")