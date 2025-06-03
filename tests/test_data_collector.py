import pytest
import pandas as pd
from unittest.mock import patch
from data_collector import get_ohlcv_data
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

def test_get_ohlcv_data_success(sample_yf_data):
    """유효한 데이터가 성공적으로 반환되는지 테스트"""
    with patch('yfinance.download', return_value=sample_yf_data) as mock_download:
        df = get_ohlcv_data('AAPL', '5d', '1d')

        mock_download.assert_called_once_with(
            'AAPL', period='5d', interval='1d', progress=False
        )
        assert not df.empty
        assert isinstance(df, pd.DataFrame)
        assert all(col in df.columns for col in ['Open', 'High', 'Low', 'Close', 'Volume'])
        assert isinstance(df.index, pd.DatetimeIndex)
        assert df.iloc[0]['Close'] == 102
        assert df.iloc[-1]['Volume'] == 1200

def test_get_ohlcv_data_empty_return():
    """yfinance.download가 빈 DataFrame을 반환할 때의 처리 테스트"""
    with patch('yfinance.download', return_value=pd.DataFrame()) as mock_download:
        df = get_ohlcv_data('NONEXISTENT', '1d', '1m')
        assert df.empty
        mock_download.assert_called_once()

def test_get_ohlcv_data_missing_column(sample_yf_data):
    """필수 컬럼이 누락된 경우의 처리 테스트"""
    malformed_data = sample_yf_data.drop(columns=['Close'])
    with patch('yfinance.download', return_value=malformed_data) as mock_download:
        df = get_ohlcv_data('AAPL', '5d', '1d')
        assert df.empty
        mock_download.assert_called_once()

def test_get_ohlcv_data_exception():
    """yfinance.download에서 예외 발생 시의 처리 테스트"""
    with patch('yfinance.download', side_effect=Exception('Test error')) as mock_download:
        df = get_ohlcv_data('AAPL', '5d', '1d')
        assert df.empty
        mock_download.assert_called_once()

# 컬럼명 대소문자 변환 테스트
def test_get_ohlcv_data_column_capitalization():
    index = pd.to_datetime(['2023-01-01'])
    data = {
        'open': [100], 'high': [101], 'low': [99],
        'close': [100.5], 'volume': [1000], 'adj close': [99.5]
    }
    mock_df_lower = pd.DataFrame(data, index=index)

    with patch('yfinance.download', return_value=mock_df_lower):
        df = get_ohlcv_data('TEST', '1d', '1d')
        assert 'Open' in df.columns and 'open' not in df.columns
        assert 'Volume' in df.columns and 'volume' not in df.columns
        assert df.iloc[0]['Open'] == 100