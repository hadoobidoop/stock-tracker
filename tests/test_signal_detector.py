# tests/test_signal_detector.py

import pytest
import pandas as pd
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from signal_detector import detect_weighted_signals
from config import SIGNAL_THRESHOLD, SIGNAL_WEIGHTS, VOLUME_SURGE_FACTOR
import logging

# 로깅 메시지가 테스트 결과에 영향을 주지 않도록 설정
logging.basicConfig(level=logging.CRITICAL)

@pytest.fixture
def mock_intraday_data_base():
    """
    기본적인 분봉 데이터 (지표 계산 후 컬럼명 포함).
    대부분의 지표는 중립적인 상태로 설정하여, 각 테스트에서 특정 신호를 유도할 때만 변경되도록 합니다.
    """
    periods = 100 # 충분한 데이터 (SMA_60, BB_20, KC_20 등의 지표 계산을 위해)
    index = pd.to_datetime([
        (datetime(2023, 1, 1, 9, 30) + timedelta(minutes=i)).strftime('%Y-%m-%d %H:%M')
        for i in range(periods)
    ])
    data = {
        'Open': [100.0 + i * 0.01 for i in range(periods)],
        'High': [100.5 + i * 0.01 for i in range(periods)],
        'Low': [99.5 + i * 0.01 for i in range(periods)],
        'Close': [100.2 + i * 0.01 for i in range(periods)],
        'Volume': [1000 + i for i in range(periods)],
        # Neutral SMA values initially (no cross)
        'SMA_5': [100.2 + i * 0.01 for i in range(periods)],
        'SMA_20': [100.2 + i * 0.01 for i in range(periods)],
        'SMA_60': [100.2 + i * 0.01 for i in range(periods)],
        # Neutral RSI
        'RSI_14': [50.0 for _ in range(periods)],
        # Neutral MACD (no cross, close to zero)
        'MACD_12_26_9': [0.0 for _ in range(periods)],
        'MACDh_12_26_9': [0.0 for _ in range(periods)],
        'MACDs_12_26_9': [0.0 for _ in range(periods)],
        # Neutral Stochastic (no cross, middle range)
        'STOCHk_14_3_3': [50.0 for _ in range(periods)],
        'STOCHd_14_3_3': [50.0 for _ in range(periods)],
        # Neutral ADX (below 25, +DI approx = -DI)
        'ADX_14': [20.0 for _ in range(periods)],
        'DMP_14': [20.0 for _ in range(periods)],
        'DMN_14': [20.0 for _ in range(periods)],
        # Neutral Bollinger Bands (close to price, no squeeze/expansion)
        'BBL_20_2.0': [99.0 + i * 0.01 for i in range(periods)],
        'BBM_20_2.0': [100.0 + i * 0.01 for i in range(periods)],
        'BBU_20_2.0': [101.0 + i * 0.01 for i in range(periods)],
        # Neutral Keltner Channels (close to price, no squeeze/expansion)
        'KCLe_20_2.0': [99.2 + i * 0.01 for i in range(periods)], # 컬럼명 변경
        'KCMe_20_2.0': [100.2 + i * 0.01 for i in range(periods)], # 컬럼명 변경
        'KCUe_20_2.0': [101.2 + i * 0.01 for i in range(periods)], # 컬럼명 변경
        # Neutral Volume SMA (current volume not surging)
        'Volume_SMA_20': [1000.0 for _ in range(periods)],
        'ATR_14': [1.0 + i * 0.01 for i in range(periods)] # ATR 컬럼 추가된 점 고려
    }
    df = pd.DataFrame(data, index=index)
    yield df

def test_detect_weighted_signals_buy_golden_cross(mock_intraday_data_base):
    """SMA 골든 크로스 매수 신호 테스트"""
    df = mock_intraday_data_base.copy()
    # 골든 크로스 유도
    df.loc[df.index[-2], 'SMA_5'] = 99.0
    df.loc[df.index[-2], 'SMA_20'] = 100.0
    df.loc[df.index[-1], 'SMA_5'] = 105.0
    df.loc[df.index[-1], 'SMA_20'] = 104.0
    df.loc[df.index[-1], 'Close'] = 105.5 # Ensure close is above SMA_5 and SMA_20

    expected_score = SIGNAL_WEIGHTS["golden_cross_sma"] # 다른 조건은 만족하지 않게 함
    # 임계값을 낮춰서 테스트
    with patch('config.SIGNAL_THRESHOLD', expected_score):
        signal = detect_weighted_signals(df, 'TEST')
        assert signal is not None # 빈 딕셔너리가 아닌지 확인
        assert signal['type'] == 'BUY'
        assert signal['score'] == expected_score
        # Check if '골든 크로스' is a substring of any detail
        assert any("골든 크로스" in detail for detail in signal['details'])

def test_detect_weighted_signals_buy_multiple_conditions(mock_intraday_data_base):
    """여러 매수 조건 만족 시 테스트"""
    df = mock_intraday_data_base.copy()
    # 골든 크로스
    df.loc[df.index[-2], 'SMA_5'] = 99.0
    df.loc[df.index[-2], 'SMA_20'] = 100.0
    df.loc[df.index[-1], 'SMA_5'] = 105.0
    df.loc[df.index[-1], 'SMA_20'] = 104.0
    df.loc[df.index[-1], 'Close'] = 105.5 # Ensure close is above SMAs

    # MACD 골든 크로스
    df.loc[df.index[-2], 'MACD_12_26_9'] = -0.1
    df.loc[df.index[-2], 'MACDs_12_26_9'] = 0.0
    df.loc[df.index[-1], 'MACD_12_26_9'] = 0.1
    df.loc[df.index[-1], 'MACDs_12_26_9'] = 0.05

    # 거래량 급증
    df.loc[df.index[-1], 'Volume'] = df.loc[df.index[-1], 'Volume_SMA_20'] * (VOLUME_SURGE_FACTOR + 0.5)

    # RSI 과매도 탈출
    df.loc[df.index[-2], 'RSI_14'] = 25.0
    df.loc[df.index[-1], 'RSI_14'] = 35.0

    # ADX 강한 상승 추세 (ADX > 25 이고 +DI > -DI)
    df.loc[df.index[-1], 'ADX_14'] = 30.0
    df.loc[df.index[-1], 'DMP_14'] = 35.0
    df.loc[df.index[-1], 'DMN_14'] = 10.0

    expected_score = (SIGNAL_WEIGHTS["golden_cross_sma"] +
                      SIGNAL_WEIGHTS["macd_cross"] +
                      SIGNAL_WEIGHTS["volume_surge"] +
                      SIGNAL_WEIGHTS["rsi_bounce_drop"] +
                      SIGNAL_WEIGHTS["adx_strong_trend"])

    with patch('config.SIGNAL_THRESHOLD', expected_score):
        signal = detect_weighted_signals(df, 'TEST')
        assert signal is not None
        assert signal['type'] == 'BUY'
        assert signal['score'] == expected_score
        assert len(signal['details']) == 5
        assert any("골든 크로스" in detail for detail in signal['details'])
        assert any("MACD 골든 크로스" in detail for detail in signal['details'])
        assert any("거래량 급증" in detail for detail in signal['details'])
        assert any("RSI 과매도 탈출" in detail for detail in signal['details'])
        assert any("ADX 강한 상승 추세" in detail for detail in signal['details'])


def test_detect_weighted_signals_sell_dead_cross(mock_intraday_data_base):
    """SMA 데드 크로스 매도 신호 테스트"""
    df = mock_intraday_data_base.copy()
    # 데드 크로스 유도
    df.loc[df.index[-2], 'SMA_5'] = 100.0
    df.loc[df.index[-2], 'SMA_20'] = 99.0
    df.loc[df.index[-1], 'SMA_5'] = 104.0
    df.loc[df.index[-1], 'SMA_20'] = 105.0
    df.loc[df.index[-1], 'Close'] = 103.5 # Ensure close is below SMA_5 and SMA_20

    expected_score = SIGNAL_WEIGHTS["golden_cross_sma"]
    with patch('config.SIGNAL_THRESHOLD', expected_score):
        signal = detect_weighted_signals(df, 'TEST')
        assert signal is not None
        assert signal['type'] == 'SELL'
        assert signal['score'] == expected_score
        assert any("데드 크로스" in detail for detail in signal['details'])

def test_detect_weighted_signals_no_signal(mock_intraday_data_base):
    """신호 임계값 미달 시 테스트"""
    df = mock_intraday_data_base.copy()
    # 어떤 조건도 만족하지 않거나, 만족하더라도 임계값 미달
    signal = detect_weighted_signals(df, 'TEST')
    assert not signal # 빈 딕셔너리 반환 확인

def test_detect_weighted_signals_insufficient_data():
    """데이터 부족 시 테스트"""
    df_empty = pd.DataFrame()
    signal = detect_weighted_signals(df_empty, 'TEST')
    assert not signal

    df_one_row = pd.DataFrame({'Close': [100]}, index=[datetime.now()])
    signal = detect_weighted_signals(df_one_row, 'TEST')
    assert not signal

def test_detect_weighted_signals_missing_required_columns(mock_intraday_data_base): # 픽스처 인자로 추가
    """필수 지표 컬럼 누락 시 테스트"""
    df = mock_intraday_data_base.drop(columns=['RSI_14']) # RSI_14 컬럼 제거
    signal = detect_weighted_signals(df, 'TEST')
    assert not signal