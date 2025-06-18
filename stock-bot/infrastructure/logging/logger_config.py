import logging
import logging.config
import sys

def setup_logging(log_level: str = 'INFO'):
    """
    애플리케이션 전반에 걸쳐 사용할 표준 로깅을 설정합니다.
    - 레벨: INFO
    - 포맷: %(asctime)s - %(name)s - %(levelname)s - %(message)s
    - 핸들러: 콘솔 출력 (StreamHandler)
    """
    # 루트 로거의 핸들러를 모두 제거하여 중복 로깅을 방지합니다.
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

    # 기본 로깅 설정
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    logging.info("Standard logging configured.")

def get_logger(name: str) -> logging.Logger:
    """지정된 이름으로 로거 인스턴스를 가져옵니다."""
    return logging.getLogger(name)
