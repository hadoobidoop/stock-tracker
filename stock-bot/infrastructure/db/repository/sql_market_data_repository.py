"""
시장 데이터 관련 데이터베이스 작업을 담당하는 레포지토리
"""
from datetime import date, datetime, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_

from infrastructure.db.db_manager import get_db
from infrastructure.db.models.market_data import MarketData
from infrastructure.db.models.enums import MarketIndicatorType
from infrastructure.logging import get_logger

logger = get_logger(__name__)


class SQLMarketDataRepository:
    """시장 데이터 SQL 레포지토리"""

    def save_market_data(self, indicator_type: MarketIndicatorType, data_date: date, 
                        value: float, additional_data: str = None) -> bool:
        """
        시장 데이터를 저장합니다. 동일한 날짜와 지표 타입이 있으면 업데이트합니다.
        
        Args:
            indicator_type: 지표 타입
            data_date: 데이터 날짜
            value: 지표 값
            additional_data: 추가 메타데이터 (JSON 문자열)
            
        Returns:
            bool: 저장 성공 여부
        """
        try:
            with get_db() as session:
                # 기존 데이터 확인
                existing = session.query(MarketData).filter(
                    and_(
                        MarketData.date == data_date,
                        MarketData.indicator_type == indicator_type
                    )
                ).first()

                if existing:
                    # 업데이트
                    existing.value = value
                    existing.additional_data = additional_data
                    existing.updated_at = datetime.utcnow()
                    logger.info(f"Updated {indicator_type.value} for date {data_date}: {value}")
                else:
                    # 새로 저장
                    market_data = MarketData(
                        date=data_date,
                        indicator_type=indicator_type,
                        value=value,
                        additional_data=additional_data
                    )
                    session.add(market_data)
                    logger.info(f"Saved new {indicator_type.value} for date {data_date}: {value}")

                session.commit()
                return True

        except Exception as e:
            logger.error(f"Error saving market data: {e}", exc_info=True)
            return False

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