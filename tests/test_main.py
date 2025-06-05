# tests/test_main.py

import pytest
from unittest.mock import patch, MagicMock
import pandas as pd
from datetime import datetime, timedelta
import pytz
from main import (
    run_daily_buy_price_prediction_job,
    run_realtime_signal_detection_job,
    is_market_open,
    get_current_et_time
)
from config import (
    STOCK_SYMBOLS, COLLECTION_INTERVAL_MINUTES, SIGNAL_THRESHOLD, SIGNAL_WEIGHTS,
    DAILY_PREDICTION_HOUR_ET, DAILY_PREDICTION_MINUTE_ET, LOOKBACK_PERIOD_DAYS_FOR_DAILY,
    INTRADAY_INTERVAL, LOOKBACK_PERIOD_MINUTES_FOR_INTRADAY,
    TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, LOG_FILE,
    PREDICTION_THRESHOLD, PREDICTION_SIGNAL_WEIGHTS # 추가: mock_data_for_daily 픽스처에서 사용
)
import logging

# 로깅 레벨 조정 (테스트 중 출력 최소화)
logging.basicConfig(level=logging.CRITICAL)

# config 값 모킹 (실제 텔레그램 전송 방지 및 테스트 환경 설정)
@pytest.fixture(autouse=True)
def mock_config_values():
    with patch('config.TELEGRAM_BOT_TOKEN', 'test_token'), \
            patch('config.TELEGRAM_CHAT_ID', 'test_chat_id'), \
            patch('config.STOCK_SYMBOLS', ['AAPL', 'MSFT']): # 테스트용 소수 종목
        yield

@pytest.fixture
def mock_data_for_realtime():
    """실시간 신호 감지용 모의 데이터프레임"""
    # TypeError: to_datetime() got an unexpected keyword argument 'tz' 해결
    # 먼저 naive DatetimeIndex를 생성한 후 tz_localize를 사용합니다.
    # main.py의 len(df_intraday) < max(20, 60) 조건을 통과하도록 최소 60개 이상으로 늘림
    periods = 100 # 충분한 데이터
    index = pd.to_datetime([
        (datetime(2023, 1, 1, 9, 30) + timedelta(minutes=i)).strftime('%Y-%m-%d %H:%M')
        for i in range(periods)
    ]).tz_localize('America/New_York') # 여기에 시간대 정보 추가

    # 실제 지표 컬럼들을 포함한 충분한 데이터
    data = {
        'Open': [100 + i * 0.1 for i in range(periods)],
        'High': [102 + i * 0.1 for i in range(periods)],
        'Low': [99 + i * 0.1 for i in range(periods)],
        'Close': [101 + i * 0.1 for i in range(periods)],
        'Volume': [1000 + i * 10 for i in range(periods)],
        'SMA_5': [100 + i * 0.1 for i in range(periods)],
        'SMA_20': [99 + i * 0.1 for i in range(periods)],
        'SMA_60': [98 + i * 0.1 for i in range(periods)],
        'RSI_14': [50 + i * 0.1 for i in range(periods)],
        'MACD_12_26_9': [0 + i * 0.01 for i in range(periods)],
        'MACDh_12_26_9': [0 + i * 0.005 for i in range(periods)],
        'MACDs_12_26_9': [0 + i * 0.008 for i in range(periods)],
        'STOCHk_14_3_3': [50 + i * 0.2 for i in range(periods)],
        'STOCHd_14_3_3': [40 + i * 0.2 for i in range(periods)],
        'ADX_14': [20 + i * 0.1 for i in range(periods)],
        'DMP_14': [15 + i * 0.15 for i in range(periods)],
        'DMN_14': [10 - i * 0.05 for i in range(periods)],
        'BBL_20_2.0': [98 + i * 0.1 for i in range(periods)],
        'BBM_20_2.0': [100 + i * 0.1 for i in range(periods)],
        'BBU_20_2.0': [102 + i * 0.1 for i in range(periods)],
        'KCLe_20_2.0': [98.5 + i * 0.1 for i in range(periods)], # 컬럼명 변경
        'KCMe_20_2.0': [100.5 + i * 0.1 for i in range(periods)], # 컬럼명 변경
        'KCUe_20_2.0': [102.5 + i * 0.1 for i in range(periods)], # 컬럼명 변경
        'Volume_SMA_20': [900 + i * 5 for i in range(periods)],
        'ATR_14': [1.0 + i * 0.01 for i in range(periods)] # ATR 컬럼 추가된 점 고려
    }
    df = pd.DataFrame(data, index=index)
    # 마지막 데이터에 골든 크로스 신호 포함
    df.loc[df.index[-1], 'SMA_5'] = 105.0
    df.loc[df.index[-1], 'SMA_20'] = 104.0
    # 임계값을 낮춰서 테스트에 성공하도록
    with patch('config.SIGNAL_THRESHOLD', 4): # golden_cross_sma 가중치가 4이므로
        yield df

@pytest.fixture
def mock_data_for_daily():
    """일일 예측용 모의 데이터프레임"""
    periods = LOOKBACK_PERIOD_DAYS_FOR_DAILY + 5 # 충분한 데이터
    data = {
        'Open': [100 + i for i in range(periods)],
        'High': [102 + i for i in range(periods)],
        'Low': [99 + i for i in range(periods)],
        'Close': [101 + i for i in range(periods)],
        'Volume': [1000 + i * 10 for i in range(periods)]
    }
    dates = pd.date_range(start='2023-01-01', periods=periods, freq='D')
    df = pd.DataFrame(data, index=dates)
    df['ATR_14'] = 1.0 # ATR 값 추가
    df['RSI_14'] = 50.0 # RSI 값 추가

    # 예측이 발생하도록 데이터 조정
    # S1 (98.0) 근처, RSI 과매도 (28.0), ATR 합리적 (2.0 / 100.0 = 0.02 < 0.05)
    df.loc[df.index[-1], 'Close'] = 98.0 + 0.1
    df.loc[df.index[-1], 'RSI_14'] = 28.0
    df.loc[df.index[-1], 'ATR_14'] = 2.0

    # predict_next_day_buy_price가 사용할 extra_indicators 모의
    mock_extra_indicators = {
        'pivot_points': {'P': 100.0, 'S1': 98.0, 'S2': 96.0, 'R1': 102.0, 'R2': 104.0},
        'fib_retracement': {
            '23.6%': 105.0, '38.2%': 98.0, '50.0%': 95.0, '61.8%': 92.0, '78.6%': 88.0
        }
    }
    # 예측 점수가 임계값을 넘도록 설정 (pivot_s1_near + rsi_oversold_daily + atr_reasonable_daily)
    expected_score = (PREDICTION_SIGNAL_WEIGHTS["pivot_s1_near"] +
                      PREDICTION_SIGNAL_WEIGHTS["rsi_oversold_daily"] +
                      PREDICTION_SIGNAL_WEIGHTS["atr_reasonable_daily"])
    with patch('config.PREDICTION_THRESHOLD', expected_score):
        yield df, mock_extra_indicators


# --------------------
# 헬퍼 함수 테스트
# --------------------
def test_get_current_et_time():
    """ET 시간 반환 테스트"""
    et_timezone = pytz.timezone('America/New_York')
    current_time_et = get_current_et_time()
    # 시간대 객체 자체를 비교하는 대신, zone 이름을 비교하여 견고성 향상
    assert current_time_et.tzinfo.zone == et_timezone.zone
    assert current_time_et.hour >= 0 and current_time_et.hour <= 23

def test_is_market_open_during_hours():
    """장 중 시간 테스트"""
    # 월요일 오전 10시 00분 ET
    market_open_time = datetime(2023, 10, 23, 10, 0, 0, tzinfo=pytz.timezone('America/New_York'))
    assert is_market_open(market_open_time)

def test_is_market_open_before_open():
    """장 시작 전 시간 테스트"""
    # 월요일 오전 9시 00분 ET
    before_open_time = datetime(2023, 10, 23, 9, 0, 0, tzinfo=pytz.timezone('America/New_York'))
    assert not is_market_open(before_open_time)

def test_is_market_open_after_close():
    """장 마감 후 시간 테스트"""
    # 월요일 오후 4시 01분 ET
    after_close_time = datetime(2023, 10, 23, 16, 1, 0, tzinfo=pytz.timezone('America/New_York'))
    assert not is_market_open(after_close_time)

def test_is_market_open_weekend():
    """주말 시간 테스트"""
    # 토요일 오전 10시 00분 ET
    saturday = datetime(2023, 10, 21, 10, 0, 0, tzinfo=pytz.timezone('America/New_York'))
    assert not is_market_open(saturday)
    # 일요일 오전 10시 00분 ET
    sunday = datetime(2023, 10, 22, 10, 0, 0, tzinfo=pytz.timezone('America/New_York'))
    assert not is_market_open(sunday)

# --------------------
# 주요 작업 함수 테스트
# --------------------

@patch('main.get_ohlcv_data')
@patch('main.calculate_intraday_indicators')
@patch('main.detect_weighted_signals')
@patch('main.send_telegram_message')
@patch('main.format_signal_message')
@patch('main.is_market_open', return_value=True) # 항상 장이 열려있다고 가정
def test_run_realtime_signal_detection_job_success(
        mock_is_market_open, mock_format_signal_message, mock_send_telegram_message,
        mock_detect_weighted_signals, mock_calculate_intraday_indicators, mock_get_ohlcv_data,
        mock_data_for_realtime # pytest fixture
):
    """실시간 신호 감지 작업 성공 테스트"""
    # get_ohlcv_data의 반환 값 설정
    mock_get_ohlcv_data.return_value = mock_data_for_realtime

    # calculate_intraday_indicators의 반환 값 설정 (원본 DataFrame 그대로)
    mock_calculate_intraday_indicators.return_value = mock_data_for_realtime

    # detect_weighted_signals의 반환 값 설정 (신호가 감지된 경우)
    mock_detect_weighted_signals.return_value = {
        'type': 'BUY', 'score': 10, 'details': ['test detail'],
        'current_price': mock_data_for_realtime.iloc[-1]['Close'],
        'timestamp': mock_data_for_realtime.index[-1].strftime('%Y-%m-%d %H:%M')
    }
    mock_format_signal_message.return_value = "Formatted BUY message"

    run_realtime_signal_detection_job()

    # 각 함수들이 올바르게 호출되었는지 확인
    assert mock_is_market_open.called
    assert mock_get_ohlcv_data.call_count == len(STOCK_SYMBOLS) * 2 # 시장 지수 + 각 종목
    assert mock_calculate_intraday_indicators.call_count == len(STOCK_SYMBOLS)
    assert mock_detect_weighted_signals.call_count == len(STOCK_SYMBOLS)
    assert mock_format_signal_message.call_count == len(STOCK_SYMBOLS)
    assert mock_send_telegram_message.call_count == len(STOCK_SYMBOLS)
    mock_send_telegram_message.assert_called_with("Formatted BUY message")


@patch('main.get_ohlcv_data')
@patch('main.predict_next_day_buy_price')
@patch('main.send_telegram_message')
@patch('main.format_prediction_message')
@patch('main.is_market_open', return_value=False) # 일일 예측은 장 마감 후이므로
def test_run_daily_buy_price_prediction_job_success(
        mock_is_market_open, mock_format_prediction_message, mock_send_telegram_message,
        mock_predict_next_day_buy_price, mock_get_ohlcv_data, mock_data_for_daily
):
    """일일 예측 작업 성공 테스트"""
    df_daily, mock_extra_indicators = mock_data_for_daily
    mock_get_ohlcv_data.return_value = df_daily

    # predict_next_day_buy_price의 반환 값 설정
    mock_predict_next_day_buy_price.return_value = {
        'ticker': 'AAPL', 'price_type': 'Pivot S1', 'price': 98.0,
        'range_low': 97.0, 'range_high': 99.0, 'reason': 'test reason',
        'score': PREDICTION_THRESHOLD + 1, 'details': ['test detail']
    }
    mock_format_prediction_message.return_value = "Formatted PREDICTION message"

    run_daily_buy_price_prediction_job()

    assert mock_get_ohlcv_data.call_count == len(STOCK_SYMBOLS)
    assert mock_predict_next_day_buy_price.call_count == len(STOCK_SYMBOLS)
    assert mock_format_prediction_message.call_count == len(STOCK_SYMBOLS)
    assert mock_send_telegram_message.call_count == len(STOCK_SYMBOLS)
    mock_send_telegram_message.assert_called_with("Formatted PREDICTION message")

@patch('main.is_market_open', return_value=False)
@patch('main.get_ohlcv_data')
@patch('main.calculate_intraday_indicators')
@patch('main.detect_weighted_signals')
@patch('main.send_telegram_message')
def test_run_realtime_signal_detection_job_market_closed(
        mock_send_telegram_message, mock_detect_weighted_signals,
        mock_calculate_intraday_indicators, mock_get_ohlcv_data, mock_is_market_open
):
    """장이 닫혔을 때 실시간 신호 감지 작업이 실행되지 않는지 테스트"""
    run_realtime_signal_detection_job()
    assert mock_is_market_open.called
    mock_get_ohlcv_data.assert_not_called()
    mock_calculate_intraday_indicators.assert_not_called()
    mock_detect_weighted_signals.assert_not_called()
    mock_send_telegram_message.assert_not_called()

@patch('main.get_ohlcv_data', return_value=pd.DataFrame()) # 빈 데이터 반환
@patch('main.predict_next_day_buy_price')
@patch('main.send_telegram_message')
def test_run_daily_buy_price_prediction_job_no_data(
        mock_send_telegram_message, mock_predict_next_day_buy_price, mock_get_ohlcv_data
):
    """일일 예측 작업에서 데이터가 없을 때 예측이 스킵되는지 테스트"""
    run_daily_buy_price_prediction_job()
    assert mock_get_ohlcv_data.call_count == len(STOCK_SYMBOLS)
    mock_predict_next_day_buy_price.assert_not_called()
    mock_send_telegram_message.assert_not_called()