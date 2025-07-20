# --- 공통 로거 설정 ---
import argparse
import sys
from pathlib import Path

# 프로젝트 루트를 Python path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from domain.services import StrategyService
# from domain.signals.config.signals.service.signal_detection_service import SignalDetectionService
# from domain.signals.models.enums import StrategyType
# --- 새로운 전략 시스템 추가 ---
from infrastructure.db.db_manager import create_db_and_tables
from infrastructure.logging import setup_logging, get_logger
from infrastructure.scheduler.jobs import update_stock_metadata_job
from infrastructure.scheduler.scheduler_manager import setup_scheduler, start_scheduler

# 애플리케이션 시작 시 로깅 설정
setup_logging()
logger = get_logger(__name__)

# 전역 전략 서비스 인스턴스 (Phase 4: 새로운 services 계층)
yaml_strategy_service: StrategyService = None
# legacy_strategy_service: SignalDetectionService = None  # 비활성화

def parse_arguments():
    """명령행 인수 파싱"""
    parser = argparse.ArgumentParser(description='Stock Analyzer Bot with Strategy Selection')
    
    # YAML 전략 목록 가져오기
    try:
        # 임시로 YAML 전략 서비스 사용
        definitions_path = project_root / "domain" / "strategies" / "definitions"
        temp_strategy_service = StrategyService(definitions_path)
        available_strategies = temp_strategy_service.get_strategy_names()
    except Exception:
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
    

    
    parser.add_argument('--list-strategies', 
                       action='store_true',
                       help='사용 가능한 전략 목록 출력 후 종료')
    
    return parser.parse_args()

def list_available_strategies():
    """사용 가능한 YAML 전략 목록 출력"""
    print("\n🎯 사용 가능한 YAML 전략 목록:")
    print("="*80)
    
    try:
        definitions_path = project_root / "domain" / "strategies" / "definitions"
        strategy_service = StrategyService(definitions_path)
        strategies = strategy_service.get_all_strategies()
        
        print("\n📊 YAML 기반 전략들:")
        print("-" * 60)
        for name, strategy_def in strategies.items():
            print(f"• {name}: {strategy_def.strategy_name}")
            print(f"  📊 매수 규칙: {len(strategy_def.buy_rules)}개")
            print(f"  📊 매도 규칙: {len(strategy_def.sell_rules)}개")
            print(f"  💰 포트폴리오: {strategy_def.portfolio.get('order_size', 'N/A')}")
            print()
        
        print(f"\n총 {len(strategies)}개 전략 사용 가능")
        
    except Exception as e:
        print(f"전략 목록 조회 실패: {e}")
        print("\n기본 전략들:")
        print("• conservative: 보수적 전략")
        print("• balanced: 균형 전략")
        print("• aggressive: 공격적 전략")

def initialize_strategy_system(args) -> bool:
    """전략 시스템 초기화 (Phase 4: YAML 전략만 사용)"""
    global yaml_strategy_service
    
    logger.info("Phase 4: YAML 전략 시스템 초기화 중...")
    
    try:
        # YAML 전략 서비스 초기화
        definitions_path = project_root / "domain" / "strategies" / "definitions"
        yaml_strategy_service = StrategyService(definitions_path)
        yaml_strategies = yaml_strategy_service.get_strategy_names()
        logger.info(f"YAML 전략 {len(yaml_strategies)}개 로드 완료: {', '.join(yaml_strategies)}")
        
        # 기본 전략 설정 (YAML 기반)
        default_strategy = args.strategy or 'conservative'
        if default_strategy in yaml_strategies:
            strategy = yaml_strategy_service.get_strategy(default_strategy)
            if strategy:
                logger.info(f"기본 전략 '{default_strategy}' 설정 완료: {strategy.strategy_name}")
            else:
                logger.warning(f"전략 '{default_strategy}' 로드 실패")
        else:
            logger.warning(f"요청된 전략 '{default_strategy}'을 찾을 수 없음. 사용 가능한 전략: {yaml_strategies}")
        
        return True
        
    except Exception as e:
        logger.error(f"YAML 전략 시스템 초기화 실패: {e}")
        return False

def get_strategy_service() -> StrategyService:
    """전역 YAML 전략 서비스 인스턴스 반환 (Phase 4)"""
    return yaml_strategy_service



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
