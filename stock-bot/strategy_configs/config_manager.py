#!/usr/bin/env python3
"""
전략 설정 관리 유틸리티

새로운 조직화된 전략 설정 구조를 관리하는 CLI 도구
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Any

from config_loader import get_strategy_config_loader


def list_strategies():
    """모든 사용 가능한 전략을 카테고리별로 나열합니다."""
    loader = get_strategy_config_loader()
    
    print("\n🎯 조직화된 전략 설정 구조")
    print("=" * 80)
    
    # 인덱스 파일에서 카테고리별 정보 가져오기
    try:
        with open(loader.index_file, 'r', encoding='utf-8') as f:
            index_data = json.load(f)
        
        strategies = index_data.get("strategies", {})
        
        for category, strategy_list in strategies.items():
            if category == "archived_files":
                continue
                
            print(f"\n📂 {category.replace('_', ' ').title()}")
            print("-" * 60)
            
            for strategy in strategy_list:
                risk_level = strategy.get("risk_level", "Unknown")
                print(f"• {strategy['name']}")
                print(f"  📝 {strategy['description']}")
                print(f"  📊 위험도: {risk_level}")
                print(f"  📁 파일: {strategy['file_path']}")
                print()
                
    except FileNotFoundError:
        print("❌ 인덱스 파일을 찾을 수 없습니다. 전략 설정이 올바르게 조직화되었는지 확인하세요.")
    except Exception as e:
        print(f"❌ 오류 발생: {e}")


def show_strategy_details(strategy_name: str):
    """특정 전략의 상세 정보를 표시합니다."""
    loader = get_strategy_config_loader()
    config = loader.load_strategy_config(strategy_name)
    
    if not config:
        print(f"❌ 전략 '{strategy_name}'을 찾을 수 없습니다.")
        return
    
    print(f"\n🎯 전략 상세 정보: {strategy_name}")
    print("=" * 80)
    
    # 기본 정보
    print(f"📝 이름: {config.get('name', 'N/A')}")
    print(f"📄 설명: {config.get('description', 'N/A')}")
    print(f"⚡ 신호 임계값: {config.get('signal_threshold', 'N/A')}")
    print(f"💰 거래당 리스크: {config.get('risk_per_trade', 'N/A')}")
    print(f"🏗️ 구현 클래스: {config.get('implementation_class', 'N/A')}")
    
    # 포지션 관리
    position_mgmt = config.get('position_management', {})
    if position_mgmt:
        print(f"\n📈 포지션 관리:")
        print(f"  최대 포지션: {position_mgmt.get('max_positions', 'N/A')}")
        print(f"  타임아웃(시간): {position_mgmt.get('position_timeout_hours', 'N/A')}")
    
    # 시장 필터
    market_filters = config.get('market_filters', {})
    if market_filters:
        print(f"\n🔍 시장 필터:")
        for key, value in market_filters.items():
            print(f"  {key}: {value}")
    
    # 탐지기 설정
    detectors = config.get('detectors', [])
    if detectors:
        print(f"\n🎛️ 탐지기 설정:")
        for detector in detectors:
            print(f"  • {detector.get('detector_class', 'N/A')} (가중치: {detector.get('weight', 'N/A')})")
    
    # 탐지기 가중치
    detector_weights = config.get('detector_weights', {})
    if detector_weights:
        print(f"\n⚖️ 탐지기 가중치:")
        for detector, weight in detector_weights.items():
            print(f"  {detector}: {weight}")
    
    # 메타데이터
    metadata = config.get('metadata', {})
    if metadata:
        print(f"\n📋 메타데이터:")
        print(f"  생성일: {metadata.get('created_at', 'N/A')}")
        print(f"  소스: {metadata.get('source_file', 'N/A')}")


def validate_config_structure():
    """설정 구조의 유효성을 검사합니다."""
    loader = get_strategy_config_loader()
    
    print("\n🔍 설정 구조 유효성 검사")
    print("=" * 80)
    
    errors = []
    warnings = []
    
    # 인덱스 파일 검사
    if not loader.index_file.exists():
        errors.append("인덱스 파일이 없습니다: index.json")
    else:
        print("✅ 인덱스 파일 존재")
    
    # 전략 디렉토리 검사
    if not loader.strategies_path.exists():
        errors.append("전략 디렉토리가 없습니다: strategies/")
    else:
        print("✅ 전략 디렉토리 존재")
        
        # 각 카테고리 디렉토리 검사
        expected_categories = ['basic', 'momentum', 'trend', 'reversion', 'advanced']
        for category in expected_categories:
            category_path = loader.strategies_path / category
            if category_path.exists():
                print(f"✅ 카테고리 디렉토리 존재: {category}/")
            else:
                warnings.append(f"카테고리 디렉토리가 없습니다: {category}/")
    
    # 개별 전략 파일 검사
    available_strategies = loader.get_available_strategies()
    print(f"\n📊 발견된 전략: {len(available_strategies)}개")
    
    for strategy_name in available_strategies:
        config = loader.load_strategy_config(strategy_name)
        if config:
            # 필수 필드 검사
            required_fields = ['name', 'description', 'signal_threshold', 'risk_per_trade']
            missing_fields = [field for field in required_fields if field not in config]
            
            if missing_fields:
                errors.append(f"전략 '{strategy_name}'에 필수 필드가 없습니다: {missing_fields}")
            else:
                print(f"✅ 전략 '{strategy_name}' 유효")
        else:
            errors.append(f"전략 '{strategy_name}' 로드 실패")
    
    # 아카이브 디렉토리 검사
    if loader.archived_path.exists():
        archived_files = list(loader.archived_path.glob("*.json"))
        print(f"📦 아카이브된 파일: {len(archived_files)}개")
    
    # 결과 출력
    print(f"\n📋 검사 결과:")
    print(f"  ✅ 성공: 구조가 올바르게 조직화되었습니다" if not errors else f"  ❌ 오류: {len(errors)}개")
    print(f"  ⚠️ 경고: {len(warnings)}개")
    
    if errors:
        print(f"\n❌ 오류 목록:")
        for error in errors:
            print(f"  • {error}")
    
    if warnings:
        print(f"\n⚠️ 경고 목록:")
        for warning in warnings:
            print(f"  • {warning}")
    
    return len(errors) == 0


def migrate_legacy_config(legacy_file: str, output_dir: str = None):
    """레거시 설정 파일을 새로운 구조로 마이그레이션합니다."""
    if not Path(legacy_file).exists():
        print(f"❌ 레거시 파일을 찾을 수 없습니다: {legacy_file}")
        return
    
    print(f"\n🔄 레거시 설정 마이그레이션: {legacy_file}")
    print("=" * 80)
    
    try:
        with open(legacy_file, 'r', encoding='utf-8') as f:
            legacy_configs = json.load(f)
        
        migrated_count = 0
        
        for strategy_name, config in legacy_configs.items():
            # 전략 카테고리 결정 (간단한 휴리스틱)
            category = _determine_strategy_category(strategy_name, config)
            
            # 출력 디렉토리 결정
            if output_dir:
                output_path = Path(output_dir) / "strategies" / category
            else:
                output_path = Path("strategies") / category
            
            output_path.mkdir(parents=True, exist_ok=True)
            
            # 개별 파일로 저장
            output_file = output_path / f"{strategy_name}_config.json"
            
            # 메타데이터 추가
            config_with_metadata = {
                **config,
                "metadata": {
                    "created_at": "2025-07-19T12:00:00Z",
                    "source_file": legacy_file,
                    "migrated": True,
                    "category": category
                }
            }
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(config_with_metadata, f, indent=2, ensure_ascii=False)
            
            print(f"✅ 마이그레이션 완료: {strategy_name} → {output_file}")
            migrated_count += 1
        
        print(f"\n📊 마이그레이션 완료: {migrated_count}개 전략")
        
    except Exception as e:
        print(f"❌ 마이그레이션 실패: {e}")


def _determine_strategy_category(strategy_name: str, config: Dict[str, Any]) -> str:
    """전략 이름과 설정을 기반으로 카테고리를 결정합니다."""
    name_lower = strategy_name.lower()
    description = config.get('description', '').lower()
    
    if any(keyword in name_lower for keyword in ['conservative', 'balanced', 'aggressive']):
        return 'basic'
    elif any(keyword in name_lower for keyword in ['momentum', 'rsi', 'stoch']):
        return 'momentum'
    elif any(keyword in name_lower for keyword in ['trend', 'sma', 'macd', 'pullback']):
        return 'trend'
    elif any(keyword in name_lower for keyword in ['mean', 'reversion', 'bollinger']):
        return 'reversion'
    else:
        return 'advanced'


def main():
    parser = argparse.ArgumentParser(description='전략 설정 관리 도구')
    subparsers = parser.add_subparsers(dest='command', help='사용 가능한 명령어')
    
    # list 명령어
    list_parser = subparsers.add_parser('list', help='모든 전략 나열')
    
    # show 명령어
    show_parser = subparsers.add_parser('show', help='특정 전략 상세 정보')
    show_parser.add_argument('strategy_name', help='전략 이름')
    
    # validate 명령어
    validate_parser = subparsers.add_parser('validate', help='설정 구조 유효성 검사')
    
    # migrate 명령어
    migrate_parser = subparsers.add_parser('migrate', help='레거시 설정 마이그레이션')
    migrate_parser.add_argument('legacy_file', help='레거시 설정 파일 경로')
    migrate_parser.add_argument('--output-dir', help='출력 디렉토리 (기본값: 현재 디렉토리)')
    
    args = parser.parse_args()
    
    if args.command == 'list':
        list_strategies()
    elif args.command == 'show':
        show_strategy_details(args.strategy_name)
    elif args.command == 'validate':
        valid = validate_config_structure()
        sys.exit(0 if valid else 1)
    elif args.command == 'migrate':
        migrate_legacy_config(args.legacy_file, args.output_dir)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()