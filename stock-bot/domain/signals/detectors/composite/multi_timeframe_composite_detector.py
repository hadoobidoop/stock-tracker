# MultiTimeframeCompositeDetector (다중 시간대 복합 Detector)
# =========================================================
# - 일봉/시간봉 데이터를 동시에 분석하여, 추세 컨센서스와 신호 강도를 산출하는 복합 신호 감지기
# - 단일 Detector로 일봉/시간봉 컨펌, 신뢰도 계산, 신호 강도(점수) 산출까지 일괄 처리
# - 신호 컨펌/강도 산출 로직을 커스터마이즈하거나, 추가 필터/지표를 결합해 확장 가능
# - MultiTimeframeStrategy에서 직접 사용하며, config에서 가중치/임계값 등 조정 가능
#
# [주요 기능]
#   - _validate_multi_timeframe_data: 입력 데이터(일봉/시간봉) 유효성 검증
#   - _analyze_multi_timeframe_trends: 일봉/시간봉 추세 및 컨센서스 분석
#   - _calculate_signal_strength: 컨센서스/지표 기반 신호 강도(점수) 산출
#   - detect_signals: 전체 분석 및 신호/점수/근거 반환 (전략에서 호출)
#
# [확장/유지보수 포인트]
#   - 신호 컨펌/강도 산출 로직(_analyze_multi_timeframe_trends, _calculate_signal_strength) 커스터마이즈 가능
#   - 신규 지표/필터 추가, 근거 메시지 포맷 확장 등 용이
#
# [사용 예시]
#   detector = MultiTimeframeCompositeDetector(weight=7.0)
#   buy_score, sell_score, buy_details, sell_details = detector.detect_signals(df, market_trend, long_term_trend, daily_extra_indicators)

from typing import Dict, List, Tuple

import pandas as pd

from domain.signals.detectors.signal_detector import SignalDetector
from domain.signals.analysis.multi_timeframe import analyze_multi_timeframe_signals
from infrastructure.db.models.enums import TrendType
from infrastructure.logging import get_logger

logger = get_logger(__name__)

class MultiTimeframeCompositeDetector(SignalDetector):
    """
    다중 시간대 복합 신호 감지기
    - 일봉/시간봉 데이터를 동시에 분석하여, 추세 컨센서스와 신호 강도를 산출
    - 단일 Detector로 일봉/시간봉 컨펌, 신뢰도 계산, 신호 강도(점수) 산출까지 일괄 처리
    - 신호 컨펌/강도 산출 로직을 커스터마이즈하거나, 추가 필터/지표를 결합해 확장 가능
    """
    def __init__(self, weight: float, name: str = None):
        """
        MultiTimeframeCompositeDetector 생성자
        Args:
            weight (float): Detector 가중치(최종 점수에 곱해짐)
            name (str, optional): Detector 이름(미지정 시 기본값)
        """
        super().__init__(weight, name or "MultiTimeframe_Composite_Detector")

    def detect_signals(self, 
                      df: pd.DataFrame, 
                      market_trend: TrendType = TrendType.NEUTRAL,
                      long_term_trend: TrendType = TrendType.NEUTRAL,
                      daily_extra_indicators: Dict = None) -> Tuple[float, float, List[str], List[str]]:
        """
        일봉/시간봉 동시 분석 및 신호/점수/근거 반환
        Args:
            df (pd.DataFrame): 시간봉 데이터
            market_trend (TrendType): 시장 추세
            long_term_trend (TrendType): 장기 추세
            daily_extra_indicators (dict, optional): 일봉 데이터 등 추가 지표
        Returns:
            Tuple[float, float, List[str], List[str]]: (매수점수, 매도점수, 매수근거, 매도근거)
        """
        daily_df = daily_extra_indicators.get('daily_data') if daily_extra_indicators else None
        if daily_df is None or daily_df.empty:
            logger.warning("No daily data available for multi-timeframe analysis")
            return 0.0, 0.0, [], []
        
        try:
            # analysis 모듈의 함수 사용
            signal_strength, buy_details, sell_details = analyze_multi_timeframe_signals(daily_df, df)
            
            # 가중치 적용하여 점수 계산
            buy_score = self.weight * signal_strength['buy_strength'] if signal_strength['buy_strength'] > 0.5 else 0.0
            sell_score = self.weight * signal_strength['sell_strength'] if signal_strength['sell_strength'] > 0.5 else 0.0
            
            return buy_score, sell_score, buy_details, sell_details
        except Exception as e:
            logger.error(f"Error in multi-timeframe analysis: {e}")
            return 0.0, 0.0, [], [] 