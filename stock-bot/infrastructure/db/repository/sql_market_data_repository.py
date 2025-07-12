"""
시장 데이터 관련 데이터베이스 작업을 담당하는 레포지토리
"""
from datetime import date, datetime, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_

from contextlib import contextmanager

from infrastructure.db.db_manager import get_db
from infrastructure.db.models.market_data import MarketData
from infrastructure.db.models.enums import MarketIndicatorType
from infrastructure.logging import get_logger

logger = get_logger(__name__)


from domain.analysis.repository.analysis_repository import MarketDataRepository

class SQLMarketDataRepository(MarketDataRepository):
    """시장 데이터 SQL 레포지토리"""

    @contextmanager
    def transaction(self):
        """데이터베이스 트랜잭션 컨텍스트를 제공합니다."""
        with get_db() as session:
            try:
                yield session
                session.commit()
                logger.debug("Transaction committed successfully.")
            except Exception as e:
                logger.error(f"Transaction failed, rolling back. Error: {e}", exc_info=True)
                session.rollback()
                raise

    def save_market_data_batch(self, records: List[Dict[str, Any]], session: Session) -> bool:
        """
        여러 시장 데이터를 배치로 저장합니다. 트랜잭션 내에서 호출되어야 합니다.
        
        Args:
            records: 저장할 데이터 딕셔너리의 리스트.
            session: 활성 SQLAlchemy 세션.
        """
        if not records:
            return True
        try:
            # 딕셔너리 리스트를 MarketData 객체 리스트로 변환
            market_data_objects = [MarketData(**record) for record in records]

            # bulk_save_objects를 사용하여 객체 리스트를 저장
            session.bulk_save_objects(market_data_objects)
            logger.info(f"Successfully batched {len(records)} records for insertion.")
            return True
        except Exception as e:
            logger.error(f"Error during batch save: {e}", exc_info=True)
            # 트랜잭션 롤백을 위해 예외를 다시 발생시킴
            raise

    def get_all_market_data_in_range(self, start_date: date, end_date: date) -> Dict[date, Dict[str, Any]]:
        """
        지정된 기간 내의 모든 일별 시장 지표를 가져옵니다.
        """
        try:
            with get_db() as session:
                records = session.query(MarketData).filter(
                    and_(
                        MarketData.date >= start_date,
                        MarketData.date <= end_date
                    )
                ).order_by(MarketData.date).all()

                data_by_date = {}
                for record in records:
                    day = record.date
                    if day not in data_by_date:
                        data_by_date[day] = {}
                    data_by_date[day][record.indicator_type.value.lower()] = record.value
                
                return data_by_date
        except Exception as e:
            logger.error(f"Error getting all market data in range: {e}", exc_info=True)
            return {}

    def save_market_data(self, indicator_type: MarketIndicatorType, data_date: date, 
                        value: float, additional_data: str = None, session: Optional[Session] = None) -> bool:
        """
        시장 데이터를 저장하거나 업데이트합니다.
        외부 세션을 주입받아 트랜잭션의 일부로 실행하거나, 자체 세션을 생성하여 실행할 수 있습니다.
        """
        if session:
            return self._save_market_data_internal(indicator_type, data_date, value, additional_data, session)
        else:
            try:
                with self.transaction() as new_session:
                    return self._save_market_data_internal(indicator_type, data_date, value, additional_data, new_session)
            except Exception as e:
                logger.error(f"Error in self-managed session for save_market_data: {e}", exc_info=True)
                return False

    def _save_market_data_internal(self, indicator_type: MarketIndicatorType, data_date: date, 
                                   value: float, additional_data: Optional[str], session: Session) -> bool:
        """save_market_data의 핵심 로직. 반드시 활성 세션과 함께 호출되어야 합니다."""
        existing = session.query(MarketData).filter(
            MarketData.date == data_date,
            MarketData.indicator_type == indicator_type
        ).first()

        if existing:
            if self._is_data_identical(existing, value, additional_data, indicator_type):
                return True
            
            old_value = existing.value
            existing.value = value
            existing.additional_data = additional_data
            existing.updated_at = datetime.utcnow()
            
            if self._is_significant_change(old_value, value, indicator_type):
                logger.warning(f"Significant change for {indicator_type.value} on {data_date}: {old_value:.2f} → {value:.2f}")
        else:
            market_data = MarketData(
                date=data_date,
                indicator_type=indicator_type,
                value=value,
                additional_data=additional_data
            )
            session.add(market_data)
            logger.info(f"Saved new {indicator_type.value} for date {data_date}: {value}")
        
        return True

    def _is_data_identical(self, existing: MarketData, new_value: float, new_additional_data: str = None, indicator_type: MarketIndicatorType = None) -> bool:
        """
        기존 데이터와 새로운 데이터가 동일한지 확인합니다.
        
        Args:
            existing: 기존 데이터베이스 레코드
            new_value: 새로운 값
            new_additional_data: 새로운 추가 데이터
            indicator_type: 지표 타입 (비교 로직 분기용)
            
        Returns:
            bool: 데이터가 동일한지 여부
        """
        # 값 비교 (소수점 6자리까지 비교)
        value_tolerance = 1e-6
        try:
            # 두 값 모두 float으로 변환하여 안전하게 비교
            if abs(float(existing.value) - float(new_value)) > value_tolerance:
                return False
        except (TypeError, ValueError):
             # 하나라도 float으로 변환할 수 없으면 다른 것으로 간주
            return False
        
        # 추가 데이터 비교
        existing_additional = existing.additional_data or ""
        new_additional = new_additional_data or ""
        
        if existing_additional != new_additional:
            # JSON 데이터인 경우 파싱해서 비교
            if existing_additional.startswith('{') and new_additional.startswith('{'):
                try:
                    import json
                    existing_json = json.loads(existing_additional)
                    new_json = json.loads(new_additional)
                    
                    # PUT_CALL_RATIO의 경우, all_ratios 딕셔너리만 비교
                    if indicator_type == MarketIndicatorType.PUT_CALL_RATIO:
                        existing_ratios = existing_json.get('all_ratios', {})
                        new_ratios = new_json.get('all_ratios', {})
                        return existing_ratios == new_ratios

                    # 버핏 지수의 경우, 중요한 필드만 비교
                    important_fields = ['data_source', 'calculation_method', 'market_cap_billions', 'gdp_billions']
                    
                    for field in important_fields:
                        if existing_json.get(field) != new_json.get(field):
                            return False
                    
                    return True
                except (json.JSONDecodeError, KeyError):
                    # JSON 파싱 실패 시 문자열 직접 비교
                    return existing_additional == new_additional
            else:
                return existing_additional == new_additional
        
        return True

    def _is_significant_change(self, old_value: float, new_value: float, indicator_type: MarketIndicatorType) -> bool:
        """
        값의 변화가 유의미한 수준인지 확인합니다.
        
        Args:
            old_value: 기존 값
            new_value: 새로운 값
            indicator_type: 지표 타입
            
        Returns:
            bool: 유의미한 변화인지 여부
        """
        if old_value == 0:
            return new_value != 0
        
        # 지표별 임계값 설정
        thresholds = {
            MarketIndicatorType.BUFFETT_INDICATOR: 5.0,    # 5% 이상 변화
            MarketIndicatorType.VIX: 10.0,                 # 10% 이상 변화  
            MarketIndicatorType.US_10Y_TREASURY_YIELD: 5.0  # 5% 이상 변화
        }
        
        threshold = thresholds.get(indicator_type, 5.0)  # 기본 5%
        change_percent = abs((new_value - old_value) / old_value * 100)
        
        return change_percent >= threshold

    def get_latest_market_data(self, indicator_type: MarketIndicatorType) -> Optional[MarketData]:
        """
        특정 지표의 최신 데이터를 가져옵니다.
        
        Args:
            indicator_type: 지표 타입
            
        Returns:
            MarketData 또는 None
        """
        try:
            with get_db() as session:
                return session.query(MarketData).filter(
                    MarketData.indicator_type == indicator_type
                ).order_by(desc(MarketData.date)).first()
        except Exception as e:
            logger.error(f"Error getting latest market data: {e}", exc_info=True)
            return None

    def get_latest_indicator_date(self, indicator_type: MarketIndicatorType) -> Optional[date]:
        """
        특정 지표의 가장 최신 데이터 날짜를 가져옵니다.
        
        Args:
            indicator_type: 지표 타입
            
        Returns:
            date 또는 None
        """
        latest_data = self.get_latest_market_data(indicator_type)
        return latest_data.date if latest_data else None

    def get_recent_market_data(self, indicator_type: MarketIndicatorType, limit: int = 10) -> List[MarketData]:
        """
        특정 지표의 최근 데이터를 가져옵니다.
        
        Args:
            indicator_type: 지표 타입
            limit: 가져올 데이터 개수
            
        Returns:
            MarketData 리스트 (최신 순)
        """
        try:
            with get_db() as session:
                return session.query(MarketData).filter(
                    MarketData.indicator_type == indicator_type
                ).order_by(desc(MarketData.date)).limit(limit).all()
        except Exception as e:
            logger.error(f"Error getting recent market data: {e}", exc_info=True)
            return []

    def get_market_data_by_date_range(self, indicator_type: MarketIndicatorType, 
                                     start_date: date, end_date: date) -> List[MarketData]:
        """
        특정 지표의 날짜 범위 데이터를 가져옵니다.
        
        Args:
            indicator_type: 지표 타입
            start_date: 시작 날짜
            end_date: 종료 날짜
            
        Returns:
            MarketData 리스트
        """
        try:
            with get_db() as session:
                return session.query(MarketData).filter(
                    and_(
                        MarketData.indicator_type == indicator_type,
                        MarketData.date >= start_date,
                        MarketData.date <= end_date
                    )
                ).order_by(MarketData.date).all()
        except Exception as e:
            logger.error(f"Error getting market data by date range: {e}", exc_info=True)
            return []

    def get_market_data_by_date(self, indicator_type: MarketIndicatorType, target_date: date) -> Optional[MarketData]:
        """
        특정 날짜와 지표 타입에 정확히 일치하는 데이터를 가져옵니다.

        Args:
            indicator_type: 지표 타입
            target_date: 대상 날짜

        Returns:
            MarketData 또�� None
        """
        try:
            with get_db() as session:
                return session.query(MarketData).filter(
                    and_(
                        MarketData.indicator_type == indicator_type,
                        MarketData.date == target_date
                    )
                ).first()
        except Exception as e:
            logger.error(f"Error getting market data by date: {e}", exc_info=True)
            return None

    def get_existing_dates(self, indicator_type: MarketIndicatorType, start_date: date) -> set:
        """
        특정 시작 날짜 이후로 특정 지표에 대해 데이터가 이미 존재하는 날짜들의 집합을 반환합니다.
        백필링 시 중복 저장을 방지하기 위해 사용됩니다.

        Args:
            indicator_type: 지표 타입
            start_date: 조회 시작 날짜

        Returns:
            날짜(date) 객체들의 집합(set)
        """
        try:
            with get_db() as session:
                results = session.query(MarketData.date).filter(
                    and_(
                        MarketData.indicator_type == indicator_type,
                        MarketData.date >= start_date
                    )
                ).all()
                return {result.date for result in results}
        except Exception as e:
            logger.error(f"Error getting existing dates: {e}", exc_info=True)
            return set()

    def get_market_data_by_date_with_forward_fill(self, indicator_type: MarketIndicatorType,
                                                  target_date: date) -> Optional[MarketData]:
        """
        특정 날짜의 데이터를 가져오되, 데이터가 없으면 그 이전 가장 최신 데이터를 가져옵니다 (Forward Fill).
        백테스팅 시점에 특정 날짜의 데이터가 없는 경우를 처리하기 위해 사용됩니다.

        Args:
            indicator_type: 지표 타입
            target_date: 대상 날짜

        Returns:
            MarketData 또는 None
        """
        try:
            with get_db() as session:
                return session.query(MarketData).filter(
                    and_(
                        MarketData.indicator_type == indicator_type,
                        MarketData.date <= target_date
                    )
                ).order_by(desc(MarketData.date)).first()
        except Exception as e:
            logger.error(f"Error getting market data with forward fill: {e}", exc_info=True)
            return None

    def get_all_indicators_for_date(self, target_date: date) -> List[MarketData]:
        """
        특정 날짜의 모든 지표 데이터를 가져옵니다.
        
        Args:
            target_date: 대상 날짜
            
        Returns:
            MarketData 리스트
        """
        try:
            with get_db() as session:
                return session.query(MarketData).filter(
                    MarketData.date == target_date
                ).all()
        except Exception as e:
            logger.error(f"Error getting all indicators for date: {e}", exc_info=True)
            return []

    def delete_old_data(self, indicator_type: MarketIndicatorType, days_to_keep: int = 365) -> bool:
        """
        오래된 데이터를 삭제합니다.
        
        Args:
            indicator_type: 지표 타입
            days_to_keep: 보관할 일수
            
        Returns:
            bool: 삭제 성공 여부
        """
        try:
            cutoff_date = date.today() - timedelta(days=days_to_keep)
            with get_db() as session:
                deleted_count = session.query(MarketData).filter(
                    and_(
                        MarketData.indicator_type == indicator_type,
                        MarketData.date < cutoff_date
                    )
                ).delete()
                
                session.commit()
                logger.info(f"Deleted {deleted_count} old records for {indicator_type.value}")
                return True

        except Exception as e:
            logger.error(f"Error deleting old data: {e}", exc_info=True)
            return False 