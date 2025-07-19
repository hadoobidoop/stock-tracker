# --- 공통 로거 설정 ---
from infrastructure.logging import setup_logging, get_logger
from infrastructure.db.db_manager import create_db_and_tables
from infrastructure.scheduler.jobs import update_stock_metadata_job
from infrastructure.scheduler.scheduler_manager import setup_scheduler, start_scheduler

# --- 새로운 전략 시스템 추가 ---
from domain.analysis.service.signal_detection_service import SignalDetectionService
from domain.analysis.base.models.enums import StrategyType, StrategyMode
from domain.analysis.strategy.configs.static_strategies import STRATEGY_CONFIGS
from domain.analysis.utils.strategy_selector import strategy_selector, list_all_strategies
import argparse
import sys

# 애플리케이션 시작 시 로깅 설정
setup_logging()
logger = get_logger(__name__)

# 전역 전략 서비스 인스턴스 (스케줄러 작업에서 사용)
strategy_service: SignalDetectionService = None

def parse_arguments():
    """명령행 인수 파싱"""
    parser = argparse.ArgumentParser(description='Stock Analyzer Bot with Strategy Selection')
    
    # 동적으로 사용 가능한 전략 목록 가져오기
    try:
        from common.config.settings import get_available_static_strategies
        available_strategies = [st.lower() for st in get_available_static_strategies()]
    except ImportError:
        # 폴백: 기본 전략들
        available_strategies = ['conservative', 'balanced', 'aggressive']
    
    parser.add_argument('--strategy', 
                       choices=available_strategies,
                       default='momentum',
                       help='기본 사용할 전략 (기본값: momentum)')
    
    parser.add_argument('--strategy-mix', 
                       choices=['balanced_mix', 'conservative_mix', 'aggressive_mix'],
                       help='Static Strategy Mix 사용 (단일 전략 대신 조합 사용)')
    
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
    print("\n🎯 전체 사용 가능한 전략 목록:")
    print("="*80)
    
    strategies = list_all_strategies()
    
    # 정적 전략
    print("\n📊 정적 전략 (Static Strategies):")
    print("-" * 60)
    for strategy in strategies["static_strategies"]:
        print(f"• {strategy['name']}: {strategy['display_name']}")
        print(f"  📝 {strategy['description']}")
        print(f"  ⚡ 임계값: {strategy['signal_threshold']}, 💰 리스크: {strategy['risk_per_trade']*100:.1f}%")
        print()
    
    # 동적 전략
    print("\n🧠 동적 전략 (Dynamic Strategies):")
    print("-" * 60)
    for strategy in strategies["dynamic_strategies"]:
        print(f"• {strategy['name']}: {strategy['display_name']}")
        print(f"  📝 {strategy['description']}")
        print(f"  ⚡ 임계값: {strategy['signal_threshold']}, 💰 리스크: {strategy['risk_per_trade']*100:.1f}%")
        print(f"  🔧 모디파이어: {strategy['modifiers_count']}개")
        print()
    
    # Static Strategy Mix
    print("\n🔀 Static Strategy Mix:")
    print("-" * 60)
    for strategy in strategies["static_mix"]:
        print(f"• {strategy['name']}: {strategy['display_name']}")
        print(f"  📝 {strategy['description']}")
        print()
    
    # 환경변수 설정 안내
    print("\n⚙️ 환경변수로 기본 전략 설정:")
    print("export STRATEGY_MODE=dynamic          # 기본 모드: static, dynamic, static_mix")
    print("export STATIC_STRATEGY=BALANCED       # 정적 전략 기본값")
    print("export DYNAMIC_STRATEGY=dynamic_weight_strategy  # 동적 전략 기본값") 
    print("export STRATEGY_MIX=balanced_mix      # Static Strategy Mix 기본값")

def initialize_strategy_system(args) -> bool:
    """전략 시스템 초기화"""
    global strategy_service
    
    logger.info("전략 시스템 초기화 중...")
    
    try:
        # 전략 서비스 생성
        strategy_service = SignalDetectionService()
        
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
        
        # Static Strategy Mix 설정 (우선순위)
        if args.strategy_mix:
            logger.info(f"Static Strategy Mix 설정: {args.strategy_mix}")
            if strategy_service.set_strategy_mix(args.strategy_mix):
                logger.info(f"Static Strategy Mix '{args.strategy_mix}' 설정 완료")
            else:
                logger.error(f"Static Strategy Mix '{args.strategy_mix}' 설정 실패")
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

def get_strategy_service() -> SignalDetectionService:
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
            
            strategy_service.strategy_manager.save_strategies_to_file(config_file)
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
