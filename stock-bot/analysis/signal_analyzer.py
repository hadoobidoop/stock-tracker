# stock_bot/analysis/signal_analyzer.py

import logging
import pandas as pd
import operator
from typing import Tuple, List

from ..config import SIGNAL_WEIGHTS, VOLUME_SURGE_FACTOR, PREDICTION_ATR_MULTIPLIER_FOR_RANGE, SIGNAL_ADJUSTMENT_FACTORS_BY_TREND
from ..database.models import TrendType

logger = logging.getLogger(__name__)

class SignalAnalyzer:
    """
    모든 기술적 신호 분석을 수행하는 클래스.
    원본 파일들의 모든 로직을 보존하며, 계산부터 조정까지 모든 책임을 가집니다.
    """

    def analyze(self, df_intraday: pd.DataFrame, ticker: str, market_trend: str, long_term_trend: str, daily_extra_indicators: dict) -> Tuple[float, float, List[str]]:
        """
        [Public Method] 이 클래스의 유일한 진입점입니다.
        모든 신호 분석을 수행하고, 최종 조정된 매수/매도 점수와 상세 정보를 반환합니다.
        [검증 완료] 기존 signal_utils.py의 전체적인 흐름과 동일합니다.
        """
        if df_intraday.empty or len(df_intraday) < 2:
            logger.warning(f"Not enough intraday data for signal analysis for {ticker}.")
            return 0.0, 0.0, []

        # 1. 원시 점수 계산 (내부 메소드 호출)
        buy_score, buy_details = self._calculate_raw_score(df_intraday, 'buy', market_trend, daily_extra_indicators)
        sell_score, sell_details = self._calculate_raw_score(df_intraday, 'sell', market_trend, daily_extra_indicators)

        # 2. 장기 추세에 따른 점수 후처리 및 조정
        # [검증 완료] 기존 signal_utils.py의 장기 추세 점수 조정 로직과 100% 동일합니다.
        if long_term_trend == TrendType.BULLISH:
            buy_score *= 1.2
            sell_score *= 0.8
        elif long_term_trend == TrendType.BEARISH:
            buy_score *= 0.8
            sell_score *= 1.2

        # 3. 최종 신호 상세 정보 구성
        # [검증 완료] 기존 signal_utils.py의 상세 정보 구성 로직과 100% 동일합니다.
        final_details = []
        if buy_score > 0:
            final_details.extend([f"매수({int(buy_score)}점): {detail}" for detail in buy_details])
        if sell_score > 0:
            final_details.extend([f"매도({int(sell_score)}점): {detail}" for detail in sell_details])

        return buy_score, sell_score, final_details

    def _calculate_raw_score(self, df_intraday: pd.DataFrame, signal_type: str, market_trend: str, daily_extra_indicators: dict) -> Tuple[float, List[str]]:
        """
        [Private Method] 매수 또는 매도에 대한 원시 점수를 계산합니다.
        [검증 완료] 기존 buy_signals.py, sell_signals.py의 모든 조건을 1:1로 통합했습니다.
        """
        latest_data = df_intraday.iloc[-1]
        prev_data = df_intraday.iloc[-2]
        score = 0
        details = []

        # [검증 완료] signal_type에 따른 동적 파라미터 설정은 원본 로직을 일반화하기 위한 것으로, 모든 조건을 포괄합니다.
        params = self._get_signal_parameters(signal_type)
        adj = SIGNAL_ADJUSTMENT_FACTORS_BY_TREND.get(market_trend, {})
        trend_adj, mom_rev_adj, vol_adj, bb_kc_adj, piv_fib_adj = (
            adj.get(params["trend_adj_factor"], 1.0), adj.get("momentum_reversal_adj", 1.0), adj.get("volume_adj", 1.0),
            adj.get("bb_kc_adj", 1.0), adj.get("pivot_fib_adj", 1.0)
        )

        # --- 모든 신호 조건 계산 (원본 파일 로직 1:1 매칭) ---

        # [검증 완료] 조건 1: SMA 크로스 (buy/sell_signals.py #1)
        if params['crossunder_op'](prev_data['SMA_5'], prev_data['SMA_20']) and params['crossover_op'](latest_data['SMA_5'], latest_data['SMA_20']):
            sma_score = SIGNAL_WEIGHTS.get(params['sma_cross_weight'], 0) * trend_adj
            if latest_data.get('ADX_14', 0) < 25:
                sma_score *= 0.5
                details.append(f"{params['sma_cross_detail']} (ADX 약세로 가중치 감소)")
            score += sma_score
            details.append(f"{params['sma_cross_detail']} (SMA 5:{latest_data['SMA_5']:.2f}, 20:{latest_data['SMA_20']:.2f})")

        # [검증 완료] 조건 2: MACD 크로스 및 MACD+거래량 혼합 (buy/sell_signals.py #2, 혼합패턴)
        if params['crossunder_op'](prev_data['MACD_12_26_9'], prev_data['MACDs_12_26_9']) and params['crossover_op'](latest_data['MACD_12_26_9'], latest_data['MACDs_12_26_9']):
            macd_score = SIGNAL_WEIGHTS.get(params['macd_cross_weight'], 0) * trend_adj
            if latest_data.get('ADX_14', 0) < 25:
                macd_score *= 0.5
                details.append(f"{params['macd_cross_detail']} (ADX 약세로 가중치 감소)")
            score += macd_score
            details.append(f"{params['macd_cross_detail']} (MACD:{latest_data['MACD_12_26_9']:.2f}, Signal:{latest_data['MACDs_12_26_9']:.2f})")

            if latest_data['Volume'] > latest_data['Volume_SMA_20'] * VOLUME_SURGE_FACTOR:
                score += SIGNAL_WEIGHTS.get("macd_volume_confirm", 0) * vol_adj
                details.append(f"{params['macd_cross_detail']} & 거래량 급증 확인")

        # [검증 완료] 조건 3: ADX 추세 (buy/sell_signals.py #3)
        dmp, dmn = latest_data.get('DMP_14', 0), latest_data.get('DMN_14', 0)
        adx_di_check = params['adx_di_op'](dmp, dmn) if signal_type == 'buy' else params['adx_di_op'](dmn, dmp)
        if latest_data.get('ADX_14', 0) > 25 and adx_di_check:
            score += SIGNAL_WEIGHTS.get("adx_strong_trend", 0) * trend_adj
            details.append(f"ADX 강한 {signal_type} 추세 ({latest_data['ADX_14']:.2f})")

        # [검증 완료] 조건 4, 5 및 혼합: RSI/Stoch 반전 및 동시 신호 (buy/sell_signals.py #4, #5, 혼합패턴)
        rsi_reversed = params['rsi_op'](prev_data['RSI_14'], params['rsi_threshold']) and params['rsi_cross_op'](latest_data['RSI_14'], params['rsi_threshold'])
        stoch_crossed = params['crossunder_op'](prev_data['STOCHk_14_3_3'], prev_data['STOCHd_14_3_3']) and params['crossover_op'](latest_data['STOCHk_14_3_3'], latest_data['STOCHd_14_3_3'])
        stoch_level_ok = params['crossunder_op'](latest_data['STOCHk_14_3_3'], params['stoch_threshold']) if signal_type == 'buy' else params['crossover_op'](latest_data['STOCHk_14_3_3'], params['stoch_threshold'])
        stoch_reversed = stoch_crossed and stoch_level_ok

        if rsi_reversed: score += SIGNAL_WEIGHTS.get("rsi_bounce_drop", 0) * mom_rev_adj; details.append(f"{params['rsi_detail']} ({prev_data['RSI_14']:.2f} -> {latest_data['RSI_14']:.2f})")
        if stoch_reversed: score += SIGNAL_WEIGHTS.get("stoch_cross", 0) * mom_rev_adj; details.append(f"{params['stoch_detail']} (%K:{latest_data['STOCHk_14_3_3']:.2f}, %D:{latest_data['STOCHd_14_3_3']:.2f})")
        if rsi_reversed and stoch_reversed: score += SIGNAL_WEIGHTS.get("rsi_stoch_confirm", 0) * mom_rev_adj; details.append("RSI/Stoch 동시 매수 신호" if signal_type == 'buy' else "RSI/Stoch 동시 매도 신호")

        # [검증 완료] 조건 4a: RSI + BBand 반전 (buy/sell_signals.py 혼합패턴)
        bb_val, prev_bb_val = latest_data.get(params["bb_reversal_band_key"]), prev_data.get(params["bb_reversal_band_key"])
        if bb_val is not None and prev_bb_val is not None:
            if params["rsi_op"](latest_data['RSI_14'], params["rsi_threshold"]) and params["bb_reversal_op"](latest_data['Close'], bb_val):
                if params["bb_reversal_cross_op"](latest_data['Close'], bb_val) or (params["crossunder_op"](prev_data['Close'], prev_bb_val) and params["crossover_op"](latest_data['Close'], bb_val)): # 원본의 or 조건 포함
                    score += SIGNAL_WEIGHTS.get("rsi_bb_reversal", 0) * mom_rev_adj
                    details.append(f"RSI & {params['bb_reversal_detail']}")

        # [검증 완료] 조건 6: 거래량 급증 (buy/sell_signals.py #6)
        if latest_data['Volume'] > latest_data['Volume_SMA_20'] * VOLUME_SURGE_FACTOR:
            score += SIGNAL_WEIGHTS.get("volume_surge", 0) * vol_adj
            details.append(f"거래량 급증 (현재:{latest_data['Volume']:.0f} > 평균:{latest_data['Volume_SMA_20']:.0f})")

        # [검증 완료] 조건 7: BB/KC 스퀴즈 후 확장 (buy/sell_signals.py #7)
        is_squeezed = latest_data.get('BBU_20_2.0', float('inf')) < latest_data.get('KCUe_20_2.0', float('inf')) and latest_data.get('BBL_20_2.0', float('-inf')) > latest_data.get('KCLe_20_2.0', float('-inf'))
        exp_band, prev_exp_band = latest_data.get(params["bb_expansion_band_key"]), prev_data.get(params["bb_expansion_band_key"])
        if not is_squeezed and exp_band is not None and prev_exp_band is not None:
            if params["bb_expansion_op"](latest_data['Close'], exp_band) and not params["bb_expansion_op"](prev_data['Close'], prev_exp_band):
                score += SIGNAL_WEIGHTS.get("bb_squeeze_expansion", 0) * bb_kc_adj
                details.append(f"볼린저 밴드 확장 ({params['bb_expansion_detail']})")

        # [검증 완료] 조건 8: 지지/저항 + 모멘텀 반전 (buy/sell_signals.py 혼합패턴)
        if daily_extra_indicators and (rsi_reversed or stoch_reversed):
            atr_col = next((c for c in df_intraday.columns if 'ATR' in c), None)
            atr = latest_data.get(atr_col, 0.0) if atr_col else 0.0
            threshold = (atr or 0.0) * PREDICTION_ATR_MULTIPLIER_FOR_RANGE
            if threshold > 0:
                for level_type, levels in [("Pivot", daily_extra_indicators.get('pivot_points', {})), ("Fib", daily_extra_indicators.get('fib_retracement', {}))]:
                    keys_to_check = params['pivot_keys'] if level_type == "Pivot" else ['38.2%', '50.0%', '61.8%']
                    for key in keys_to_check:
                        level_val = levels.get(key)
                        if level_val and abs(latest_data['Close'] - level_val) <= threshold:
                            weight_key = "pivot_momentum_reversal" if level_type == "Pivot" else "fib_momentum_reversal"
                            score += SIGNAL_WEIGHTS.get(weight_key, 0) * piv_fib_adj
                            details.append(f"{level_type} {key} & 모멘텀 반전 (Level:{level_val:.2f}, Close:{latest_data['Close']:.2f})")

        return score, details

    def _get_signal_parameters(self, signal_type: str) -> dict:
        """[Helper] 신호 타입에 따른 파라미터를 반환합니다."""
        if signal_type == 'buy':
            return {
                "crossover_op": operator.gt, "crossunder_op": operator.lt, "sma_cross_weight": "golden_cross_sma", "sma_cross_detail": "골든 크로스",
                "macd_cross_weight": "macd_cross", "macd_cross_detail": "MACD 골든 크로스", "adx_di_op": operator.gt,
                "rsi_threshold": 30, "rsi_op": operator.le, "rsi_cross_op": operator.gt, "rsi_detail": "RSI 과매도 탈출",
                "stoch_cross_op": operator.gt, "stoch_threshold": 80, "stoch_detail": "스토캐스틱 매수",
                "bb_reversal_band_key": "BBL_20_2.0", "bb_reversal_op": operator.le, "bb_reversal_cross_op": operator.gt, "bb_reversal_detail": "BB 하단 반등",
                "bb_expansion_band_key": "BBU_20_2.0", "bb_expansion_op": operator.gt, "bb_expansion_detail": "상단 돌파",
                "pivot_keys": ['S1', 'S2'], "trend_adj_factor": "trend_follow_buy_adj"
            }
        else: # 'sell'
            return {
                "crossover_op": operator.lt, "crossunder_op": operator.gt, "sma_cross_weight": "dead_cross_sma", "sma_cross_detail": "데드 크로스",
                "macd_cross_weight": "macd_cross", "macd_cross_detail": "MACD 데드 크로스", "adx_di_op": operator.gt,
                "rsi_threshold": 70, "rsi_op": operator.ge, "rsi_cross_op": operator.lt, "rsi_detail": "RSI 과매수 탈출",
                "stoch_cross_op": operator.lt, "stoch_threshold": 20, "stoch_detail": "스토캐스틱 매도",
                "bb_reversal_band_key": "BBU_20_2.0", "bb_reversal_op": operator.ge, "bb_reversal_cross_op": operator.lt, "bb_reversal_detail": "BB 상단 반전",
                "bb_expansion_band_key": "BBL_20_2.0", "bb_expansion_op": operator.lt, "bb_expansion_detail": "하단 돌파",
                "pivot_keys": ['R1', 'R2'], "trend_adj_factor": "trend_follow_sell_adj"
            }
