import pytest
import pandas as pd
from datetime import datetime, timedelta
from unittest.mock import patch
from indicator_calculator import calculate_daily_indicators, calculate_intraday_indicators
import logging

# 로깅 메시지가 테스트 결과에 영향을 주지 않도록 설정
logging.basicConfig(level=logging.CRITICAL)

@pytest.fixture
def sample_yf_data():
    """yf.download가 반환할 모의 데이터프레임"""
    index = pd.to_datetime(['2023-01-01', '2023-01-02', '2023-01-03'])
    data = {
        'Open': [100, 101, 102],
        'High': [105, 106, 107],
        'Low': [99, 100, 101],
        'Close': [102, 103, 104],
        'Adj Close': [101.5, 102.5, 103.5], # yfinance는 Adj Close도 반환할 수 있음
        'Volume': [1000, 1100, 1200]
    }
    return pd.DataFrame(data, index=index)

@pytest.fixture
def sample_daily_df():
    """일봉 지표 계산을 위한 샘플 DataFrame"""
    # ATR 계산을 위해 최소 14개 이상의 데이터 필요 (ATR_14)
    # 피보나치 룩백 기간(20)보다 길게 설정
    periods = 60 # 충분한 데이터 (FIB_LOOKBACK_DAYS=60이므로)
    data = {
        'Open': [10 + i for i in range(periods)],
        'High': [12 + i for i in range(periods)],
        'Low': [9 + i for i in range(periods)],
        'Close': [11 + i for i in range(periods)],
        'Volume': [100 + i * 10 for i in range(periods)]
    }
    dates = pd.date_range(start='2023-01-01', periods=periods, freq='D')
    return pd.DataFrame(data, index=dates)

@pytest.fixture
def sample_intraday_df():
    """분봉 지표 계산을 위한 샘플 DataFrame (최소 60개 이상)"""
    # 지표 계산에 필요한 최소 데이터 (SMA_60, BB_20, KC_20)
    periods = 100 # 충분한 데이터
    data = {
        'Open': [i + 0.5 for i in range(100, 100 + periods)],
        'High': [i + 1.5 for i in range(100, 100 + periods)],
        'Low': [i - 0.5 for i in range(100, 100 + periods)],
        'Close': [i + 1 for i in range(100, 100 + periods)],
        'Volume': [1000 + i * 10 for i in range(periods)]
    }
    dates = pd.date_range(start='2023-01-01 09:30', periods=periods, freq='1min')
    return pd.DataFrame(data, index=dates)

def test_calculate_daily_indicators(sample_daily_df):
    """일봉 지표 계산 테스트"""
    df_result, extra_indicators = calculate_daily_indicators(sample_daily_df, fib_lookback_days=20)

    assert not df_result.empty
    # ATR 컬럼이 추가되었는지 확인 (컬럼명은 ATR_N_14 등일 수 있음)
    # pandas_ta 0.3.14b0 버전에서는 ATRr_14로 생성될 수 있음
    assert any(col.startswith('ATR') for col in df_result.columns) # 'ATR_' 대신 'ATR'로 시작하는지 확인
    # NaN 값 제거 후에도 데이터가 남아있는지 확인
    assert len(df_result) > 0

    assert 'pivot_points' in extra_indicators
    assert 'fib_retracement' in extra_indicators
    assert 'P' in extra_indicators['pivot_points']
    assert 'S1' in extra_indicators['pivot_points']
    assert 'R1' in extra_indicators['pivot_points']
    assert '23.6%' in extra_indicators['fib_retracement']

    # 값 범위 대략적 확인 (정확한 값은 pandas_ta 구현에 따라 다를 수 있음)
    assert extra_indicators['pivot_points']['P'] > 0
    assert extra_indicators['fib_retracement']['50.0%'] > 0

    # 빈 DataFrame 입력 시 처리
    df_empty, extra_empty = calculate_daily_indicators(pd.DataFrame(), fib_lookback_days=20)
    assert df_empty.empty
    assert not extra_empty # 빈 딕셔너리가 반환되어야 함

def test_calculate_intraday_indicators(sample_intraday_df):
    """분봉 지표 계산 테스트"""
    df_result = calculate_intraday_indicators(sample_intraday_df)

    assert not df_result.empty
    assert len(df_result) <= len(sample_intraday_df) # dropna로 인해 길이가 줄어들 수 있음
    assert len(df_result) > 0 # 데이터가 비어있지 않아야 함

    # 주요 지표 컬럼들이 추가되었는지 확인
    assert 'SMA_5' in df_result.columns
    assert 'SMA_20' in df_result.columns
    assert 'SMA_60' in df_result.columns
    assert 'RSI_14' in df_result.columns
    assert 'MACD_12_26_9' in df_result.columns
    assert 'STOCHk_14_3_3' in df_result.columns
    assert 'STOCHd_14_3_3' in df_result.columns
    assert 'ADX_14' in df_result.columns
    assert 'BBL_20_2.0' in df_result.columns # length=20 명시 후 확인
    # Keltner Channel column names might have 'e' suffix depending on pandas_ta version
    assert 'KCLe_20_2.0' in df_result.columns
    assert 'KCUe_20_2.0' in df_result.columns # KCU_20_2 대신 KCUe_20_2로 변경
    assert 'Volume_SMA_20' in df_result.columns

    # 지표 값들이 NaN이 아닌지 확인 (dropna 후)
    assert not df_result['RSI_14'].isnull().any()
    assert not df_result['MACD_12_26_9'].isnull().any()

    # 빈 DataFrame 입력 시 처리
    df_empty = calculate_intraday_indicators(pd.DataFrame())
    assert df_empty.empty

    # 최소 데이터 개수 미만일 때 처리 (dropna 이후 비어있어야 함)
    df_small = sample_intraday_df.head(10) # 60 미만
    df_small_result = calculate_intraday_indicators(df_small)
    assert df_small_result.empty
