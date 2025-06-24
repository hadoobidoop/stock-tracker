# --- 공통 로거 설정 ---
from infrastructure.logging import setup_logging, get_logger
from infrastructure.db.db_manager import create_db_and_tables
from infrastructure.scheduler.jobs import update_stock_metadata_job
from infrastructure.scheduler.scheduler_manager import setup_scheduler, start_scheduler

# --- 새로운 전략 시스템 추가 ---
from domain.analysis.service.signal_detection_service import EnhancedSignalDetectionService
from domain.analysis.config.strategy_settings import StrategyType, STRATEGY_CONFIGS
import argparse
import sys

# 애플리케이션 시작 시 로깅 설정
setup_logging()
logger = get_logger(__name__)

# 전역 전략 서비스 인스턴스 (스케줄러 작업에서 사용)
strategy_service: EnhancedSignalDetectionService = None

def parse_arguments():
    """명령행 인수 파싱"""
    parser = argparse.ArgumentParser(description='Stock Analyzer Bot with Strategy Selection')
    
    parser.add_argument('--strategy', 
                       choices=[st.value for st in StrategyType], 
                       default=StrategyType.MOMENTUM.value,
                       help='기본 사용할 전략 (기본값: momentum)')
    
    parser.add_argument('--strategy-mix', 
                       choices=['balanced_mix', 'conservative_mix', 'aggressive_mix'],
                       help='전략 조합 사용 (단일 전략 대신 조합 사용)')
    
    parser.add_argument('--auto-strategy', 
                       action='store_true',
                       help='시장 상황에 따른 자동 전략 선택 활성화')
    
    parser.add_argument('--load-strategies', 
                       type=str,
                       help='파일에서 전략 설정 로드')
    
    parser.add_argument('--list-strategies', 
                       action='store_true',
                       help='사용 가능한 전략 목록 출력 후 종료')
    
    return parser.parse_args()

def list_available_strategies():
    """사용 가능한 전략 목록 출력"""
    print("\n🎯 사용 가능한 전략 목록:")
    print("="*60)
    
    for strategy_type, config in STRATEGY_CONFIGS.items():
        print(f"\n전략 타입: {strategy_type.value}")
        print(f"이름: {config.name}")
        print(f"설명: {config.description}")
        print(f"임계값: {config.signal_threshold}")
        print(f"리스크: {config.risk_per_trade * 100:.1f}%")
        print("-" * 40)
    
    print("\n🔀 사용 가능한 전략 조합:")
    print("- balanced_mix: 균형잡힌 조합 (balanced + momentum + trend_following)")
    print("- conservative_mix: 보수적 조합 (conservative + trend_following + swing)")
    print("- aggressive_mix: 공격적 조합 (aggressive + momentum + scalping)")

def initialize_strategy_system(args) -> bool:
    """전략 시스템 초기화"""
    global strategy_service
    
    logger.info("전략 시스템 초기화 중...")
    
    try:
        # 전략 서비스 생성
        strategy_service = EnhancedSignalDetectionService()
        
        # 파일에서 전략 설정 로드 (우선순위)
        if args.load_strategies:
            logger.info(f"파일에서 전략 설정 로드: {args.load_strategies}")
            if strategy_service.load_strategy_configs(args.load_strategies):
                logger.info("파일에서 전략 설정 로드 성공")
            else:
                logger.error("파일에서 전략 설정 로드 실패, 기본 설정 사용")
                if not strategy_service.initialize():
                    return False
        else:
            # 기본 전략들 초기화
            if not strategy_service.initialize():
                logger.error("전략 시스템 초기화 실패")
                return False
        
        # 전략 조합 설정 (우선순위)
        if args.strategy_mix:
            logger.info(f"전략 조합 설정: {args.strategy_mix}")
            if strategy_service.set_strategy_mix(args.strategy_mix):
                logger.info(f"전략 조합 '{args.strategy_mix}' 설정 완료")
            else:
                logger.error(f"전략 조합 '{args.strategy_mix}' 설정 실패")
                return False
                
        # 단일 전략 설정
        elif args.strategy:
            strategy_type = StrategyType(args.strategy)
            logger.info(f"단일 전략 설정: {strategy_type.value}")
            if strategy_service.switch_strategy(strategy_type):
                logger.info(f"전략 '{strategy_type.value}' 설정 완료")
            else:
                logger.error(f"전략 '{strategy_type.value}' 설정 실패")
                return False
        
        # 자동 전략 선택 설정
        if args.auto_strategy:
            logger.info("자동 전략 선택 활성화")
            strategy_service.enable_auto_strategy_selection(True)
        
        # 현재 전략 정보 로깅
        current_strategy = strategy_service.get_current_strategy_info()
        logger.info(f"현재 활성 전략: {current_strategy}")
        
        # 사용 가능한 전략 목록 로깅
        available_strategies = strategy_service.get_available_strategies()
        logger.info(f"로드된 전략 수: {len(available_strategies)}")
        
        return True
        
    except Exception as e:
        logger.error(f"전략 시스템 초기화 실패: {e}")
        return False

def get_strategy_service() -> EnhancedSignalDetectionService:
    """전역 전략 서비스 인스턴스 반환 (스케줄러 작업에서 사용)"""
    return strategy_service

def save_startup_strategy_config():
    """시작 시 전략 설정을 파일로 저장"""
    if strategy_service:
        try:
            from datetime import datetime
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            config_file = f"./strategy_configs/startup_config_{timestamp}.json"
            
            import os
            os.makedirs("./strategy_configs", exist_ok=True)
            
            strategy_service.save_strategy_configs(config_file)
            logger.info(f"시작 시 전략 설정 저장: {config_file}")
            
        except Exception as e:
            logger.warning(f"전략 설정 저장 실패: {e}")

if __name__ == "__main__":
    # 명령행 인수 파싱
    args = parse_arguments()
    
    # 전략 목록 출력 모드
    if args.list_strategies:
        list_available_strategies()
        sys.exit(0)
    
    logger.info("========================================")
    logger.info("  Starting Stock Analyzer Bot")
    logger.info("========================================")

    try:
        # 1. 데이터베이스 테이블 확인 및 생성
        logger.info("Step 1: Initializing database...")
        create_db_and_tables()

        # 2. 전략 시스템 초기화 (새로 추가)
        logger.info("Step 2: Initializing strategy system...")
        if not initialize_strategy_system(args):
            logger.error("전략 시스템 초기화 실패. 프로그램을 종료합니다.")
            sys.exit(1)
        
        # 시작 시 전략 설정 저장
        save_startup_strategy_config()

        # 3. 프로그램 시작 시 메타데이터 즉시 업데이트
        logger.info("Step 3: Performing initial metadata update...")
        update_stock_metadata_job()

        # 4. 스케줄러 설정 및 시작
        logger.info("Step 4: Setting up and starting the scheduler...")
        scheduler = setup_scheduler()
        start_scheduler(scheduler)

    except KeyboardInterrupt:
        logger.info("프로그램이 사용자에 의해 중단되었습니다.")
        sys.exit(0)
    except Exception as e:
        logger.error(f"프로그램 실행 중 오류 발생: {e}")
        sys.exit(1)
