"""
시장 지표 분석 유틸리티
VIX, 버핏 지수 등 시장 전체 지표를 분석하는 함수들
"""
from typing import Dict, Optional, Tuple, List, Any
from datetime import datetime, timedelta
import pandas as pd
from infrastructure.db.models.enums import MarketIndicatorType
from infrastructure.db.repository.sql_market_data_repository import SQLMarketDataRepository
from infrastructure.logging import get_logger

logger = get_logger(__name__)


class MarketIndicatorAnalyzer:
    """시장 지표 분석기"""
    
    def __init__(self):
        self.repository = SQLMarketDataRepository()
    
    def get_vix_analysis(self, lookback_days: int = 30) -> Dict:
        """
        VIX 분석 결과를 반환합니다.
        
        Args:
            lookback_days: 분석할 과거 기간 (일)
            
        Returns:
            Dict: VIX 분석 결과
        """
        try:
            # 최근 VIX 데이터 가져오기
            recent_vix_data = self.repository.get_recent_market_data(
                MarketIndicatorType.VIX, 
                limit=lookback_days
            )
            
            if not recent_vix_data:
                logger.warning("No VIX data available")
                return {}
            
            # VIX 값들 추출
            vix_values = [data.value for data in recent_vix_data]
            vix_dates = [data.date for data in recent_vix_data]
            
            current_vix = vix_values[0]  # 최신 값
            
            # VIX 통계 계산
            vix_mean = sum(vix_values) / len(vix_values)
            vix_std = (sum((x - vix_mean) ** 2 for x in vix_values) / len(vix_values)) ** 0.5
            
            # VIX 레벨 분류
            fear_level = self._classify_vix_level(current_vix)
            
            # VIX 변화율 계산
            if len(vix_values) >= 2:
                prev_vix = vix_values[1]
                vix_change_pct = ((current_vix - prev_vix) / prev_vix) * 100
            else:
                vix_change_pct = 0.0
            
            # VIX 트렌드 분석
            trend = self._analyze_vix_trend(vix_values)
            
            # 거래 신호 생성
            trading_signal = self._generate_vix_trading_signal(
                current_vix, vix_change_pct, trend, fear_level
            )
            
            return {
                'current_vix': current_vix,
                'vix_mean': vix_mean,
                'vix_std': vix_std,
                'vix_change_pct': vix_change_pct,
                'fear_level': fear_level,
                'trend': trend,
                'trading_signal': trading_signal,
                'confidence': trading_signal.get('confidence', 0.0),
                'last_updated': vix_dates[0] if vix_dates else None
            }
            
        except Exception as e:
            logger.error(f"Error analyzing VIX: {e}")
            return {}
    
    def _classify_vix_level(self, vix_value: float) -> str:
        """VIX 레벨을 분류합니다."""
        if vix_value >= 40:
            return "EXTREME_FEAR"  # 극도의 공포
        elif vix_value >= 30:
            return "HIGH_FEAR"  # 높은 공포
        elif vix_value >= 20:
            return "MODERATE_FEAR"  # 보통 공포
        elif vix_value >= 12:
            return "LOW_FEAR"  # 낮은 공포
        else:
            return "COMPLACENCY"  # 안심/자만
    
    def _analyze_vix_trend(self, vix_values: List[float]) -> str:
        """VIX 트렌드를 분석합니다."""
        if len(vix_values) < 3:
            return "NEUTRAL"
        
        # 최근 3일간의 변화율 계산
        recent_change = ((vix_values[0] - vix_values[2]) / vix_values[2]) * 100
        
        if recent_change > 15:
            return "RAPIDLY_RISING"  # 급상승
        elif recent_change > 5:
            return "RISING"  # 상승
        elif recent_change < -15:
            return "RAPIDLY_FALLING"  # 급하락
        elif recent_change < -5:
            return "FALLING"  # 하락
        else:
            return "NEUTRAL"  # 중립
    
    def _generate_vix_trading_signal(self, current_vix: float, vix_change_pct: float, 
                                   trend: str, fear_level: str) -> Dict:
        """VIX 기반 거래 신호를 생성합니다."""
        signal: Dict[str, Any] = {
            'type': None,
            'strength': 0.0,
            'confidence': 0.0,
            'reason': []
        }
        
        # 극도의 공포 시 매수 신호
        if fear_level == "EXTREME_FEAR":
            signal['type'] = 'BUY'
            signal['strength'] = 8.0
            signal['confidence'] = 0.85
            signal['reason'].append(f"VIX 극도 공포 레벨 ({current_vix:.1f})")
            
        elif fear_level == "HIGH_FEAR":
            signal['type'] = 'BUY'
            signal['strength'] = 6.0
            signal['confidence'] = 0.75
            signal['reason'].append(f"VIX 높은 공포 레벨 ({current_vix:.1f})")
            
        elif fear_level == "COMPLACENCY":
            signal['type'] = 'SELL'
            signal['strength'] = 5.0
            signal['confidence'] = 0.65
            signal['reason'].append(f"VIX 안심/자만 레벨 ({current_vix:.1f})")
        
        # 트렌드에 따른 조정
        if trend == "RAPIDLY_RISING" and signal['type'] == 'BUY':
            signal['strength'] += 1.0
            signal['confidence'] += 0.05
            signal['reason'].append("VIX 급상승으로 신호 강화")
            
        elif trend == "RAPIDLY_FALLING" and signal['type'] == 'SELL':
            signal['strength'] += 1.0
            signal['confidence'] += 0.05
            signal['reason'].append("VIX 급하락으로 신호 강화")
        
        # 변화율에 따른 조정
        if abs(vix_change_pct) > 20:
            signal['strength'] += 0.5
            signal['reason'].append(f"VIX 큰 변화 ({vix_change_pct:+.1f}%)")
        
        return signal
    
    def get_buffett_indicator_analysis(self) -> Dict:
        """버핏 지수 분석 결과를 반환합니다."""
        try:
            latest_data = self.repository.get_latest_market_data(MarketIndicatorType.BUFFETT_INDICATOR)
            
            if not latest_data:
                return {}
            
            buffett_value = latest_data.value
            
            # 버핏 지수 레벨 분류
            if buffett_value >= 200:
                level = "SEVERELY_OVERVALUED"
                signal_type = "SELL"
                confidence = 0.8
            elif buffett_value >= 150:
                level = "OVERVALUED"
                signal_type = "SELL"
                confidence = 0.6
            elif buffett_value >= 100:
                level = "FAIRLY_VALUED"
                signal_type = None
                confidence = 0.0
            elif buffett_value >= 75:
                level = "UNDERVALUED"
                signal_type = "BUY"
                confidence = 0.5
            else:
                level = "SEVERELY_UNDERVALUED"
                signal_type = "BUY"
                confidence = 0.8
            
            return {
                'current_value': buffett_value,
                'level': level,
                'signal_type': signal_type,
                'confidence': confidence,
                'last_updated': latest_data.date
            }
            
        except Exception as e:
            logger.error(f"Error analyzing Buffett Indicator: {e}")
            return {}
    
    def get_combined_market_sentiment(self) -> Dict:
        """VIX와 버핏 지수를 결합한 시장 심리 분석"""
        try:
            vix_analysis = self.get_vix_analysis()
            buffett_analysis = self.get_buffett_indicator_analysis()
            
            # 결합된 신호 생성
            combined_signal = self._combine_market_signals(vix_analysis, buffett_analysis)
            
            return {
                'vix_analysis': vix_analysis,
                'buffett_analysis': buffett_analysis,
                'combined_signal': combined_signal,
                'market_sentiment': self._determine_market_sentiment(vix_analysis, buffett_analysis)
            }
            
        except Exception as e:
            logger.error(f"Error analyzing combined market sentiment: {e}")
            return {}
    
    def _combine_market_signals(self, vix_analysis: Dict, buffett_analysis: Dict) -> Dict:
        """VIX와 버핏 지수 신호를 결합합니다."""
        if not vix_analysis or not buffett_analysis:
            return {}
        
        vix_signal = vix_analysis.get('trading_signal', {})
        buffett_signal = buffett_analysis
        
        # 신호 일치 여부 확인
        vix_type = vix_signal.get('type')
        buffett_type = buffett_signal.get('signal_type')
        
        if vix_type == buffett_type and vix_type is not None:
            # 신호가 일치하는 경우
            combined_strength = (vix_signal.get('strength', 0) + 
                               (buffett_signal.get('confidence', 0) * 10)) / 2
            combined_confidence = min(0.95, 
                                    (vix_signal.get('confidence', 0) + 
                                     buffett_signal.get('confidence', 0)) / 2 + 0.1)
            
            return {
                'type': vix_type,
                'strength': combined_strength,
                'confidence': combined_confidence,
                'reason': [f"VIX와 버핏 지수 신호 일치 ({vix_type})"]
            }
        else:
            # 신호가 상충하거나 한쪽만 있는 경우
            if vix_type and not buffett_type:
                return vix_signal
            elif buffett_type and not vix_type:
                return {
                    'type': buffett_type,
                    'strength': buffett_signal.get('confidence', 0) * 5,
                    'confidence': buffett_signal.get('confidence', 0),
                    'reason': ["버핏 지수 단독 신호"]
                }
            else:
                return {
                    'type': None,
                    'strength': 0.0,
                    'confidence': 0.0,
                    'reason': ["상충하는 시장 신호"]
                }
    
    def _determine_market_sentiment(self, vix_analysis: Dict, buffett_analysis: Dict) -> str:
        """전체적인 시장 심리를 판단합니다."""
        if not vix_analysis:
            return "UNKNOWN"
        
        fear_level = vix_analysis.get('fear_level', 'MODERATE_FEAR')
        
        if fear_level in ['EXTREME_FEAR', 'HIGH_FEAR']:
            return "FEARFUL"
        elif fear_level == 'COMPLACENCY':
            return "GREEDY"
        else:
            return "NEUTRAL"


def get_market_indicator_analysis() -> Dict:
    """현재 시장 지표 분석 결과를 반환하는 편의 함수"""
    analyzer = MarketIndicatorAnalyzer()
    return analyzer.get_combined_market_sentiment()


def get_vix_for_strategy() -> Optional[float]:
    """전략에서 사용할 현재 VIX 값을 반환하는 편의 함수"""
    try:
        analyzer = MarketIndicatorAnalyzer()
        vix_analysis = analyzer.get_vix_analysis()
        return vix_analysis.get('current_vix')
    except Exception as e:
        logger.error(f"Error getting VIX for strategy: {e}")
        return None 