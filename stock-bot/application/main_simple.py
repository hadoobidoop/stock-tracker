#!/usr/bin/env python3
"""
Stock Analyzer Bot - Phase 4 간소화 버전

새로운 services 계층을 테스트하기 위한 간단한 진입점
"""
import argparse
import sys
from pathlib import Path

# 프로젝트 루트를 Python path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from domain.services import StrategyService, TradingService
from infrastructure.logging import setup_logging, get_logger
from infrastructure.db.db_manager import create_db_and_tables

# 애플리케이션 시작 시 로깅 설정
setup_logging()
logger = get_logger(__name__)


def parse_arguments():
    """명령행 인수 파싱"""
    parser = argparse.ArgumentParser(description='Stock Analyzer Bot - Phase 4 Services Layer Test')
    
    parser.add_argument('--list-strategies', 
                       action='store_true',
                       help='사용 가능한 YAML 전략 목록 출력')
    
    parser.add_argument('--test-strategy', 
                       help='특정 전략 테스트 (예: conservative)')
    
    return parser.parse_args()


def list_yaml_strategies():
    """YAML 전략 목록 출력"""
    print("\n🎯 Phase 4: YAML 전략 목록:")
    print("="*60)
    
    try:
        definitions_path = Path("domain/strategies/definitions")
        strategy_service = StrategyService(definitions_path)
        strategies = strategy_service.get_all_strategies()
        
        print(f"\n📊 {len(strategies)}개 YAML 전략 로드 완료:")
        print("-" * 40)
        for name, strategy_def in strategies.items():
            print(f"• {name}: {strategy_def.strategy_name}")
            print(f"  📈 매수 규칙: {len(strategy_def.buy_rules)}개")
            print(f"  📉 매도 규칙: {len(strategy_def.sell_rules)}개")
            print(f"  💰 포트폴리오: {strategy_def.portfolio.get('order_size', 'N/A')}")
            print()
        
        print("🎉 Services 계층이 정상 동작 중입니다!")
        
    except Exception as e:
        logger.error(f"YAML 전략 로드 실패: {e}")
        print(f"❌ 오류: {e}")


def test_strategy(strategy_name: str):
    """전략 테스트"""
    print(f"\n🧪 전략 테스트: {strategy_name}")
    print("="*60)
    
    try:
        definitions_path = Path("domain/strategies/definitions")
        strategy_service = StrategyService(definitions_path)
        
        # 전략 조회
        strategy = strategy_service.get_strategy(strategy_name)
        if not strategy:
            print(f"❌ 전략 '{strategy_name}'을 찾을 수 없습니다.")
            return
        
        print(f"✅ 전략 '{strategy_name}' 로드 성공!")
        print(f"   이름: {strategy.strategy_name}")
        print(f"   매수 규칙: {len(strategy.buy_rules)}개")
        print(f"   매도 규칙: {len(strategy.sell_rules)}개")
        print(f"   감지기: {len(strategy.detectors)}개")
        
        # TradingService 초기화 (데이터 리포지토리 없이 테스트)
        trading_service = TradingService(strategy_service, None)
        print("✅ TradingService 초기화 성공!")
        
        print("\n🎉 전략과 서비스가 정상 동작합니다!")
        
    except Exception as e:
        logger.error(f"전략 테스트 실패: {e}")
        print(f"❌ 오류: {e}")


def main():
    """메인 실행 함수"""
    args = parse_arguments()
    
    logger.info("========================================")
    logger.info("  Phase 4: Services Layer Test")
    logger.info("========================================")
    
    try:
        # 데이터베이스 초기화 (간단히)
        logger.info("데이터베이스 초기화...")
        create_db_and_tables()
        
        if args.list_strategies:
            list_yaml_strategies()
        elif args.test_strategy:
            test_strategy(args.test_strategy)
        else:
            print("사용법:")
            print("  --list-strategies: YAML 전략 목록 보기")
            print("  --test-strategy <name>: 특정 전략 테스트")
            print("\n예시:")
            print("  python application/main_simple.py --list-strategies")
            print("  python application/main_simple.py --test-strategy conservative")
    
    except KeyboardInterrupt:
        logger.info("프로그램이 사용자에 의해 중단되었습니다.")
        sys.exit(0)
    except Exception as e:
        logger.error(f"프로그램 실행 중 오류 발생: {e}")
        print(f"❌ 오류: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()