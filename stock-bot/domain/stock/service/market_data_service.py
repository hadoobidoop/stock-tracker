"""
시장 데이터 수집 및 관리 서비스
버핏 지수, VIX, 공포지수 등 다양한 시장 지표를 수집합니다.
"""
import pandas as pd
import pandas_datareader.data as web
import yfinance as yf
import requests
from datetime import datetime, date, timedelta
from typing import Optional, Dict, Any, Tuple, List
import json
import time
import random

from infrastructure.db.repository.sql_market_data_repository import SQLMarketDataRepository
from infrastructure.db.models.enums import MarketIndicatorType
from infrastructure.logging import get_logger

logger = get_logger(__name__)


class MarketDataService:
    """시장 데이터 수집 및 관리 서비스"""

    def __init__(self):
        self.repository = SQLMarketDataRepository()
        # API 호출 제한 방지를 위한 설정
        self.yahoo_request_delay = 30.0  # Yahoo API 호출 간 지연 시간 (초) - 단건 호출 시
        self.yahoo_batch_delay = 2.0  # 배치 작업 시 지연 시간 (초)
        self.yahoo_retry_count = 3  # Yahoo API 재시도 횟수
        self.fred_preferred = True  # FRED를 우선 사용
        self.is_batch_mode = False  # 배치 모드 여부

    def _delay_for_yahoo_api(self, is_batch: bool = None):
        """
        Yahoo API 호출 제한을 피하기 위한 지연
        
        Args:
            is_batch: 배치 모드인지 여부. None이면 self.is_batch_mode 사용
        """
        if is_batch is None:
            is_batch = self.is_batch_mode

        if is_batch:
            # 배치 모드: 짧은 지연 (2-3초)
            delay = self.yahoo_batch_delay + random.uniform(-0.5, 1.0)
            logger.debug(f"Yahoo API batch delay: {delay:.1f}s")
        else:
            # 단건 모드: 긴 지연 (30초)
            delay = self.yahoo_request_delay + random.uniform(-2.0, 2.0)
            logger.info(f"Yahoo API single request delay: {delay:.1f}s")

        time.sleep(delay)

    def _fetch_yahoo_data_with_retry(self, symbol: str, period: str = "5d", is_batch: bool = None) -> Optional[Any]:
        """
        Yahoo Finance에서 데이터를 가져오되 재시도 로직 포함
        
        Args:
            symbol: Yahoo Finance 심볼
            period: 데이터 기간 ("5d", "1mo", "3mo" 등)
            is_batch: 배치 모드 여부. None이면 self.is_batch_mode 사용
            
        Returns:
            Yahoo Finance 데이터 또는 None
        """
        if is_batch is None:
            is_batch = self.is_batch_mode

        for attempt in range(self.yahoo_retry_count):
            try:
                self._delay_for_yahoo_api(is_batch)
                ticker = yf.Ticker(symbol)
                data = ticker.history(period=period)

                if not data.empty:
                    logger.info(f"Successfully fetched Yahoo data for {symbol} (attempt {attempt + 1})")
                    return data
                else:
                    logger.warning(f"Empty data from Yahoo for {symbol} (attempt {attempt + 1})")

            except Exception as e:
                logger.warning(f"Yahoo API error for {symbol} (attempt {attempt + 1}): {e}")

                if attempt < self.yahoo_retry_count - 1:
                    # 재시도 전 추가 지연
                    time.sleep(2 ** attempt)  # 지수적 백오프

        logger.error(f"Failed to fetch Yahoo data for {symbol} after {self.yahoo_retry_count} attempts")
        return None

    def update_buffett_indicator(self) -> bool:
        """
        Federal Reserve Z.1 Financial Accounts 데이터를 우선 사용하고,
        실패 시 Yahoo Finance ^W5000을 백업으로 사용하여 버핏 지수를 계산합니다.
        
        Returns:
            bool: 업데이트 성공 여부
        """
        logger.info("Starting Buffett Indicator update...")

        # 1. Fed Z.1 데이터로 시도 (기본 방식)
        if self.fred_preferred and self._update_buffett_with_fed_data():
            logger.info("Buffett Indicator updated successfully using Fed Z.1 data")
            return True

        # 2. Yahoo Finance ^W5000으로 백업 시도
        logger.info("Attempting Buffett Indicator update using Yahoo Finance ^W5000...")
        return self._update_buffett_with_yahoo_data()

    def _update_buffett_with_fed_data(self) -> bool:
        """Fed Z.1 데이터를 사용한 버핏 지수 업데이트 (기존 로직)"""
        try:
            # GDP 데이터 가져오기 (FRED)
            start_date = datetime.now() - timedelta(days=365)  # 1년 범위
            end_date = datetime.now()

            gdp = web.DataReader('GDP', 'fred', start_date, end_date)

            if gdp.empty:
                logger.warning("No GDP data received from FRED")
                return False

            gdp_clean = gdp['GDP'].dropna()
            if gdp_clean.empty:
                logger.warning("No valid GDP data available")
                return False

            latest_gdp = gdp_clean.iloc[-1]  # billion USD
            logger.info(f"Latest GDP: ${latest_gdp:.2f} billion USD")

            # Federal Reserve Z.1 Financial Accounts 데이터 가져오기
            market_data = web.DataReader('NCBEILQ027S', 'fred', start_date, end_date)

            if market_data.empty:
                logger.warning("No market cap data received from Fed Z.1")
                return False

            market_clean = market_data['NCBEILQ027S'].dropna()
            if market_clean.empty:
                logger.warning("No valid market cap data available")
                return False

            # Fed Z.1 데이터는 백만 달러 단위이므로 십억 달러로 변환
            latest_market_cap_millions = market_clean.iloc[-1]
            latest_market_cap_billions = latest_market_cap_millions / 1000

            logger.info(f"Latest Market Cap: ${latest_market_cap_billions:.1f} billion USD")

            # 최근 5일간의 데이터로 버핏 지수 계산
            for i in range(min(5, len(market_clean))):
                market_date = market_clean.index[-1 - i].date()
                market_cap_millions = market_clean.iloc[-1 - i]
                market_cap_billions = market_cap_millions / 1000  # 백만 달러 → 십억 달러

                buffett_ratio = (market_cap_billions / latest_gdp) * 100

                additional_data = json.dumps({
                    "market_cap_billions": float(market_cap_billions),
                    "market_cap_trillions": float(market_cap_billions / 1000),
                    "gdp_billions": float(latest_gdp),
                    "gdp_trillions": float(latest_gdp / 1000),
                    "calculation_method": "fed_z1_market_cap_to_gdp",
                    "data_source": "Federal Reserve Z.1 (NCBEILQ027S) + FRED (GDP)",
                    "note": "Fed Z.1: Nonfinancial corporate business; corporate equities; liability, Level"
                })

                success = self.repository.save_market_data(
                    indicator_type=MarketIndicatorType.BUFFETT_INDICATOR,
                    data_date=market_date,
                    value=buffett_ratio,
                    additional_data=additional_data
                )

                if success:
                    logger.info(f"Saved Buffett Indicator for {market_date}: {buffett_ratio:.1f}%")

            return True

        except Exception as e:
            logger.error(f"Error updating Buffett Indicator with Fed data: {e}", exc_info=True)
            return False

    def _update_buffett_with_yahoo_data(self) -> bool:
        """Yahoo Finance ^W5000 데이터를 사용한 버핏 지수 업데이트 (백업 방식)"""
        try:
            # 1. GDP 데이터 (FRED에서 여전히 가져오기)
            start_date = datetime.now() - timedelta(days=365)
            gdp = web.DataReader('GDP', 'fred', start_date, datetime.now())

            if gdp.empty:
                logger.warning("No GDP data for Yahoo-based Buffett calculation")
                return False

            gdp_clean = gdp['GDP'].dropna()
            latest_gdp = gdp_clean.iloc[-1]  # billion USD
            logger.info(f"GDP for Yahoo calculation: ${latest_gdp:.2f} billion USD")

            # 2. Yahoo Finance ^W5000 데이터 가져오기 (API 호출 제한 고려)
            wilshire_data = self._fetch_yahoo_data_with_retry("^W5000", period="1mo")

            if wilshire_data is None or wilshire_data.empty:
                logger.error("Failed to fetch Wilshire 5000 data from Yahoo Finance")
                return False

            # 3. Wilshire 5000 포인트를 시가총액으로 변환
            # 일반적으로 1 포인트 ≈ 1.05-1.1 billion USD (2024년 기준)
            conversion_factor = 1.08  # 보수적 추정치

            # 최근 5일간의 데이터 처리 (API 호출 최소화)
            recent_data = wilshire_data.tail(5)

            for i, (date_idx, row) in enumerate(recent_data.iterrows()):
                market_date = date_idx.date()
                wilshire_value = row['Close']

                # 시가총액 계산 (billion USD)
                estimated_market_cap = wilshire_value * conversion_factor

                # 버핏 지수 계산
                buffett_ratio = (estimated_market_cap / latest_gdp) * 100

                additional_data = json.dumps({
                    "wilshire_5000_points": float(wilshire_value),
                    "conversion_factor": conversion_factor,
                    "market_cap_billions": float(estimated_market_cap),
                    "market_cap_trillions": float(estimated_market_cap / 1000),
                    "gdp_billions": float(latest_gdp),
                    "gdp_trillions": float(latest_gdp / 1000),
                    "calculation_method": "yahoo_w5000_to_gdp",
                    "data_source": "Yahoo Finance (^W5000) + FRED (GDP)",
                    "note": f"Wilshire 5000 converted using factor {conversion_factor}x"
                })

                success = self.repository.save_market_data(
                    indicator_type=MarketIndicatorType.BUFFETT_INDICATOR,
                    data_date=market_date,
                    value=buffett_ratio,
                    additional_data=additional_data
                )

                if success:
                    logger.info(f"Saved Yahoo-based Buffett Indicator for {market_date}: {buffett_ratio:.1f}% "
                                f"(Wilshire: {wilshire_value:.0f} pts, Market Cap: ${estimated_market_cap:.1f}B)")

            return True

        except Exception as e:
            logger.error(f"Error updating Buffett Indicator with Yahoo data: {e}", exc_info=True)
            return False

    def update_vix(self) -> bool:
        """
        FRED에서 VIX 데이터를 우선 가져오고, 실패 시 Yahoo Finance에서 백업으로 가져옵니다.
        
        Returns:
            bool: 업데이트 성공 여부
        """
        logger.info("Starting VIX update...")

        # 1. FRED에서 VIX 데이터 시도 (기본 방식)
        if self.fred_preferred and self._update_vix_with_fred():
            logger.info("VIX updated successfully using FRED data")
            return True

        # 2. Yahoo Finance에서 VIX 백업 시도
        logger.info("Attempting VIX update using Yahoo Finance...")
        return self._update_vix_with_yahoo()

    def _update_vix_with_fred(self) -> bool:
        """FRED에서 VIX 데이터 업데이트 (기존 로직)"""
        try:
            # 최근 7일간의 데이터 가져오기
            start_date = datetime.now() - timedelta(days=7)
            end_date = datetime.now()

            # FRED에서 VIX 데이터 가져오기
            vix_data = web.DataReader('VIXCLS', 'fred', start_date, end_date)

            if vix_data.empty:
                logger.warning("No VIX data received from FRED")
                return False

            vix_clean = vix_data['VIXCLS'].dropna()

            # 최근 데이터들 저장
            for i in range(min(5, len(vix_clean))):
                vix_date = vix_clean.index[-1 - i].date()
                vix_value = vix_clean.iloc[-1 - i]

                additional_data = json.dumps({
                    "data_source": "FRED (VIXCLS)",
                    "note": "Federal Reserve Economic Data"
                })

                success = self.repository.save_market_data(
                    indicator_type=MarketIndicatorType.VIX,
                    data_date=vix_date,
                    value=vix_value,
                    additional_data=additional_data
                )

                if success:
                    logger.info(f"Saved FRED VIX for {vix_date}: {vix_value:.2f}")

            return True

        except Exception as e:
            logger.error(f"Error updating VIX with FRED: {e}", exc_info=True)
            return False

    def _update_vix_with_yahoo(self) -> bool:
        """Yahoo Finance에서 VIX 데이터 업데이트 (백업 방식)"""
        try:
            # Yahoo Finance ^VIX 데이터 가져오기 (API 호출 제한 고려)
            vix_data = self._fetch_yahoo_data_with_retry("^VIX", period="5d")

            if vix_data is None or vix_data.empty:
                logger.error("Failed to fetch VIX data from Yahoo Finance")
                return False

            # 최근 5일간의 데이터 처리
            recent_data = vix_data.tail(5)

            for i, (date_idx, row) in enumerate(recent_data.iterrows()):
                vix_date = date_idx.date()
                vix_value = row['Close']

                additional_data = json.dumps({
                    "data_source": "Yahoo Finance (^VIX)",
                    "note": "Yahoo Finance backup data"
                })

                success = self.repository.save_market_data(
                    indicator_type=MarketIndicatorType.VIX,
                    data_date=vix_date,
                    value=vix_value,
                    additional_data=additional_data
                )

                if success:
                    logger.info(f"Saved Yahoo VIX for {vix_date}: {vix_value:.2f}")

            return True

        except Exception as e:
            logger.error(f"Error updating VIX with Yahoo: {e}", exc_info=True)
            return False

    def update_treasury_yield(self) -> bool:
        """
        FRED에서 10년 국채 수익률을 가져와 저장합니다.
        
        Returns:
            bool: 업데이트 성공 여부
        """
        logger.info("Starting 10-Year Treasury Yield update...")

        try:
            # 최근 7일간의 데이터 가져오기
            start_date = datetime.now() - timedelta(days=7)
            end_date = datetime.now()

            # FRED에서 10년 국채 수익률 가져오기
            treasury_data = web.DataReader('DGS10', 'fred', start_date, end_date)

            if treasury_data.empty:
                logger.warning("No Treasury yield data received from FRED")
                return False

            treasury_clean = treasury_data['DGS10'].dropna()

            # 최근 데이터들 저장
            for i in range(min(5, len(treasury_clean))):
                treasury_date = treasury_clean.index[-1 - i].date()
                treasury_value = treasury_clean.iloc[-1 - i]

                success = self.repository.save_market_data(
                    indicator_type=MarketIndicatorType.US_10Y_TREASURY_YIELD,
                    data_date=treasury_date,
                    value=treasury_value
                )

                if success:
                    logger.info(f"Saved 10Y Treasury Yield for {treasury_date}: {treasury_value:.2f}%")

            return True

        except Exception as e:
            logger.error(f"Error updating Treasury yield: {e}", exc_info=True)
            return False

    def update_gold_price(self) -> bool:
        """
        Yahoo Finance에서 금 선물(GC=F) 가격을 가져와 저장합니다.
        
        Returns:
            bool: 업데이트 성공 여부
        """
        logger.info("Starting Gold Price (GC=F) update...")

        try:
            # Yahoo Finance GC=F 데이터 가져오기
            gold_data = self._fetch_yahoo_data_with_retry("GC=F", period="5d")

            if gold_data is None or gold_data.empty:
                logger.error("Failed to fetch Gold price data from Yahoo Finance")
                return False

            # 최근 5일간의 데이터 처리
            recent_data = gold_data.tail(5)

            for i, (date_idx, row) in enumerate(recent_data.iterrows()):
                gold_date = date_idx.date()
                gold_price = row['Close']

                additional_data = json.dumps({
                    "data_source": "Yahoo Finance (GC=F)",
                    "currency": "USD",
                    "unit": "per troy ounce",
                    "note": "Gold futures continuous contract"
                })

                success = self.repository.save_market_data(
                    indicator_type=MarketIndicatorType.GOLD_PRICE,
                    data_date=gold_date,
                    value=gold_price,
                    additional_data=additional_data
                )

                if success:
                    logger.info(f"Saved Gold price for {gold_date}: ${gold_price:.2f}")

            return True

        except Exception as e:
            logger.error(f"Error updating Gold price: {e}", exc_info=True)
            return False

    def update_crude_oil_price(self) -> bool:
        """
        Yahoo Finance에서 원유 선물(CL=F) 가격을 가져와 저장합니다.
        
        Returns:
            bool: 업데이트 성공 여부
        """
        logger.info("Starting Crude Oil Price (CL=F) update...")

        try:
            # Yahoo Finance CL=F 데이터 가져오기
            oil_data = self._fetch_yahoo_data_with_retry("CL=F", period="5d")

            if oil_data is None or oil_data.empty:
                logger.error("Failed to fetch Crude Oil price data from Yahoo Finance")
                return False

            # 최근 5일간의 데이터 처리
            recent_data = oil_data.tail(5)

            for i, (date_idx, row) in enumerate(recent_data.iterrows()):
                oil_date = date_idx.date()
                oil_price = row['Close']

                additional_data = json.dumps({
                    "data_source": "Yahoo Finance (CL=F)",
                    "currency": "USD",
                    "unit": "per barrel",
                    "note": "WTI Crude Oil futures continuous contract"
                })

                success = self.repository.save_market_data(
                    indicator_type=MarketIndicatorType.CRUDE_OIL_PRICE,
                    data_date=oil_date,
                    value=oil_price,
                    additional_data=additional_data
                )

                if success:
                    logger.info(f"Saved Crude Oil price for {oil_date}: ${oil_price:.2f}")

            return True

        except Exception as e:
            logger.error(f"Error updating Crude Oil price: {e}", exc_info=True)
            return False

    def update_sp500_index(self) -> bool:
        """
        Yahoo Finance에서 S&P 500 지수(^GSPC)를 가져와 저장합니다.
        
        Returns:
            bool: 업데이트 성공 여부
        """
        logger.info("Starting S&P 500 Index (^GSPC) update...")

        try:
            # Yahoo Finance ^GSPC 데이터 가져오기
            sp500_data = self._fetch_yahoo_data_with_retry("^GSPC", period="5d")

            if sp500_data is None or sp500_data.empty:
                logger.error("Failed to fetch S&P 500 data from Yahoo Finance")
                return False

            # 최근 5일간의 데이터 처리
            recent_data = sp500_data.tail(5)

            for i, (date_idx, row) in enumerate(recent_data.iterrows()):
                sp500_date = date_idx.date()
                sp500_value = row['Close']

                additional_data = json.dumps({
                    "data_source": "Yahoo Finance (^GSPC)",
                    "note": "Standard & Poor's 500 Index",
                    "market": "US Stock Market"
                })

                success = self.repository.save_market_data(
                    indicator_type=MarketIndicatorType.SP500_INDEX,
                    data_date=sp500_date,
                    value=sp500_value,
                    additional_data=additional_data
                )

                if success:
                    logger.info(f"Saved S&P 500 for {sp500_date}: {sp500_value:.2f}")

            return True

        except Exception as e:
            logger.error(f"Error updating S&P 500 index: {e}", exc_info=True)
            return False

    def update_put_call_ratio(self) -> bool:
        """
        CBOE JSON API에서 Put/Call 비율을 가져와 저장합니다.
        
        Returns:
            bool: 업데이트 성공 여부
        """
        logger.info("Starting Put/Call Ratio update...")

        try:
            import requests
            from datetime import datetime, timedelta

            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'en-US,en;q=0.5',
                'Referer': 'https://www.cboe.com/',
                'Origin': 'https://www.cboe.com',
                'Connection': 'keep-alive',
            }

            # 최근 며칠간의 데이터 시도 (오늘부터 역순으로)
            dates_to_try = []
            for i in range(5):  # 최근 5일
                target_date = date.today() - timedelta(days=5) - timedelta(days=i)
                dates_to_try.append(target_date)

            for target_date in dates_to_try:
                try:
                    # CBOE JSON API URL 생성
                    date_str = target_date.strftime('%Y-%m-%d')
                    api_url = f"https://cdn.cboe.com/data/us/options/market_statistics/daily/{date_str}_daily_options"

                    logger.info(f"Fetching Put/Call data from CBOE API: {date_str}")
                    response = requests.get(api_url, headers=headers, timeout=10)

                    if response.status_code == 200:
                        data = response.json()

                        # Put/Call 비율 데이터 파싱
                        if 'ratios' in data:
                            all_ratios = {}  # 모든 비율을 저장할 딕셔너리
                            total_put_call_ratio = None

                            # 먼저 모든 비율을 수집
                            for ratio_item in data['ratios']:
                                ratio_name = ratio_item.get('name', '')
                                ratio_value = ratio_item.get('value')

                                try:
                                    ratio_float = float(ratio_value)

                                    if 0.0 < ratio_float <= 10.0:  # 유효한 범위 확인
                                        all_ratios[ratio_name] = ratio_float

                                        # TOTAL PUT/CALL RATIO를 primary value로 설정
                                        if ratio_name == 'TOTAL PUT/CALL RATIO':
                                            total_put_call_ratio = ratio_float

                                except (ValueError, TypeError) as e:
                                    logger.warning(f"Invalid ratio value for {ratio_name}: {ratio_value}")

                            # TOTAL PUT/CALL RATIO가 있으면 저장
                            if total_put_call_ratio is not None and all_ratios:
                                # additional_data에는 모든 비율과 메타데이터 저장
                                additional_data = json.dumps({
                                    "data_source": f"CBOE JSON API ({api_url})",
                                    "data_date": date_str,
                                    "api_response_status": "200",
                                    "note": "Official CBOE Put/Call ratios data",
                                    "total_ratios_count": len(all_ratios),
                                    "all_ratios": all_ratios,
                                    "primary_ratio": "TOTAL PUT/CALL RATIO"
                                })

                                success = self.repository.save_market_data(
                                    indicator_type=MarketIndicatorType.PUT_CALL_RATIO,
                                    data_date=target_date,
                                    value=total_put_call_ratio,
                                    additional_data=additional_data
                                )

                                if success:
                                    logger.info(
                                        f"Saved CBOE TOTAL PUT/CALL RATIO for {date_str}: {total_put_call_ratio:.3f}")
                                    logger.info(f"Stored {len(all_ratios)} total Put/Call ratios in additional_data")
                                    logger.info(f"All ratios: {list(all_ratios.keys())}")
                                    return True
                                else:
                                    logger.error(f"Failed to save Put/Call ratios for {date_str}")
                            else:
                                logger.warning(f"TOTAL PUT/CALL RATIO not found in CBOE data for {date_str}")

                        else:
                            logger.warning(f"No 'ratios' data found in CBOE API response for {date_str}")

                    elif response.status_code == 404:
                        logger.info(f"No CBOE data available for {date_str} (404)")
                        continue

                    else:
                        logger.warning(f"CBOE API returned status {response.status_code} for {date_str}")
                        continue

                except requests.RequestException as e:
                    logger.warning(f"Request failed for CBOE API {date_str}: {e}")
                    continue
                except json.JSONDecodeError as e:
                    logger.warning(f"Invalid JSON response from CBOE API {date_str}: {e}")
                    continue

            # API가 모두 실패했을 경우 대체 방법
            logger.warning("CBOE API failed for all recent dates, using VIX-based estimation")

            latest_vix = self.get_latest_vix()
            if latest_vix:
                # VIX 기반 추정 공식 (실제 데이터와 비교하여 조정됨)
                estimated_pc_ratio = 0.6 + (latest_vix - 20) * 0.015
                estimated_pc_ratio = max(0.4, min(1.5, estimated_pc_ratio))

                additional_data = json.dumps({
                    "data_source": "VIX-based estimation (CBOE API fallback)",
                    "vix_value": latest_vix,
                    "estimation_formula": "0.6 + (VIX - 20) * 0.015",
                    "note": "Estimated Put/Call ratio when CBOE API unavailable"
                })

                success = self.repository.save_market_data(
                    indicator_type=MarketIndicatorType.PUT_CALL_RATIO,
                    data_date=date.today(),
                    value=estimated_pc_ratio,
                    additional_data=additional_data
                )

                if success:
                    logger.info(f"Saved estimated Put/Call Ratio: {estimated_pc_ratio:.3f} (VIX-based)")
                    return True

            return False

        except Exception as e:
            logger.error(f"Error updating Put/Call ratio: {e}", exc_info=True)
            return False

    def set_yahoo_settings(self, single_delay: float = 30.0, batch_delay: float = 2.0,
                           retry_count: int = 3, prefer_fred: bool = True):
        """
        Yahoo Finance API 설정을 조정합니다.
        
        Args:
            single_delay: 단건 호출 시 Yahoo API 호출 간 지연 시간 (초)
            batch_delay: 배치 호출 시 Yahoo API 호출 간 지연 시간 (초)
            retry_count: 재시도 횟수
            prefer_fred: FRED를 우선 사용할지 여부
        """
        self.yahoo_request_delay = single_delay
        self.yahoo_batch_delay = batch_delay
        self.yahoo_retry_count = retry_count
        self.fred_preferred = prefer_fred
        logger.info(f"Yahoo settings updated: single_delay={single_delay}s, batch_delay={batch_delay}s, "
                    f"retry={retry_count}, prefer_fred={prefer_fred}")

    def set_batch_mode(self, is_batch: bool):
        """
        배치 모드를 설정합니다.
        
        Args:
            is_batch: 배치 모드 여부
        """
        self.is_batch_mode = is_batch
        logger.info(f"Batch mode set to: {is_batch}")

    def update_all_indicators(self) -> Dict[str, bool]:
        """
        모든 지표를 업데이트합니다.
        배치 모드로 실행되어 Yahoo API 호출 간 지연을 줄입니다.
        
        Returns:
            Dict[str, bool]: 각 지표별 업데이트 성공 여부
        """
        logger.info("Starting update of all market indicators (batch mode)...")

        # 배치 모드 활성화
        original_batch_mode = self.is_batch_mode
        self.is_batch_mode = True

        try:
            results = {}

            # 버핏 지수 업데이트 (Fed Z.1 우선, Yahoo 백업)
            results['buffett_indicator'] = self.update_buffett_indicator()

            # API 호출 제한 방지를 위한 지연
            if not self.fred_preferred:  # Yahoo 모드일 때만 지연
                logger.info("Delaying between indicator updates to respect API limits...")
                time.sleep(2.0)

            # VIX 업데이트 (FRED 우선, Yahoo 백업)
            results['vix'] = self.update_vix()

            # 추가 지연 (Yahoo 모드)
            if not self.fred_preferred:
                time.sleep(1.0)

            # 10년 국채 수익률 업데이트 (FRED만 사용)
            results['treasury_yield'] = self.update_treasury_yield()

            # 금 가격 업데이트 (Yahoo Finance) - 배치 모드 지연
            results['gold_price'] = self.update_gold_price()

            # 원유 가격 업데이트 (Yahoo Finance) - 배치 모드 지연
            results['crude_oil_price'] = self.update_crude_oil_price()

            # S&P 500 지수 업데이트 (Yahoo Finance) - 배치 모드 지연
            results['sp500_index'] = self.update_sp500_index()

            # Put/Call 비율 업데이트 (CBOE 웹 스크래핑)
            results['put_call_ratio'] = self.update_put_call_ratio()

            # 공포탐욕지수 업데이트 (CNN API)
            results['fear_greed_index'] = self.update_fear_greed_index()

            # 달러 인덱스(DXY) 업데이트 (Yahoo Finance)
            results['dxy_index'] = self.update_dxy_index()

            # S&P 500 200일 이동평균 업데이트 (파생 데이터)
            # S&P 500 지수 업데이트가 성공했을 경우에만 실행
            if results.get('sp500_index', False):
                results['sp500_sma_200'] = self.update_sp500_sma()
            else:
                results['sp500_sma_200'] = False
                logger.warning("Skipping S&P 500 SMA calculation due to index update failure.")

            success_count = sum(results.values())
            total_count = len(results)

            # API 사용 통계 로깅
            yahoo_used = any(
                'yahoo' in str(self.repository.get_latest_market_data(MarketIndicatorType.BUFFETT_INDICATOR)) for _ in
                [0])
            logger.info(f"Market indicators update completed: {success_count}/{total_count} successful")
            logger.info(
                f"Data sources used: FRED={self.fred_preferred}, Yahoo_backup={'potentially' if not self.fred_preferred else 'if_needed'}")

            return results

        finally:
            # 배치 모드 복원
            self.is_batch_mode = original_batch_mode

    def get_data_source_stats(self) -> Dict[str, int]:
        """
        최근 데이터의 소스별 통계를 반환합니다.
        
        Returns:
            Dict[str, int]: 데이터 소스별 개수
        """
        stats = {
            'fred_buffett': 0,
            'yahoo_buffett': 0,
            'fred_vix': 0,
            'yahoo_vix': 0,
            'fred_treasury': 0
        }

        try:
            # 최근 10개 데이터 확인
            for indicator_type in [MarketIndicatorType.BUFFETT_INDICATOR, MarketIndicatorType.VIX,
                                   MarketIndicatorType.US_10Y_TREASURY_YIELD]:
                recent_data = self.repository.get_recent_market_data(indicator_type, limit=10)

                for data in recent_data:
                    if data.additional_data:
                        source_info = json.loads(data.additional_data)
                        source = source_info.get('data_source', '')

                        if indicator_type == MarketIndicatorType.BUFFETT_INDICATOR:
                            if 'FRED' in source or 'Fed' in source:
                                stats['fred_buffett'] += 1
                            elif 'Yahoo' in source:
                                stats['yahoo_buffett'] += 1
                        elif indicator_type == MarketIndicatorType.VIX:
                            if 'FRED' in source:
                                stats['fred_vix'] += 1
                            elif 'Yahoo' in source:
                                stats['yahoo_vix'] += 1
                        elif indicator_type == MarketIndicatorType.US_10Y_TREASURY_YIELD:
                            stats['fred_treasury'] += 1

        except Exception as e:
            logger.warning(f"Error getting data source stats: {e}")

        return stats

    def get_latest_buffett_indicator(self) -> Optional[float]:
        """최신 버핏 지수를 가져옵니다."""
        latest_data = self.repository.get_latest_market_data(MarketIndicatorType.BUFFETT_INDICATOR)
        return latest_data.value if latest_data else None

    def get_latest_vix(self) -> Optional[float]:
        """최신 VIX를 가져옵니다."""
        latest_data = self.repository.get_latest_market_data(MarketIndicatorType.VIX)
        return latest_data.value if latest_data else None

    def get_latest_gold_price(self) -> Optional[float]:
        """최신 금 가격을 가져옵니다."""
        latest_data = self.repository.get_latest_market_data(MarketIndicatorType.GOLD_PRICE)
        return latest_data.value if latest_data else None

    def get_latest_crude_oil_price(self) -> Optional[float]:
        """최신 원유 가격을 가져옵니다."""
        latest_data = self.repository.get_latest_market_data(MarketIndicatorType.CRUDE_OIL_PRICE)
        return latest_data.value if latest_data else None

    def get_latest_sp500_index(self) -> Optional[float]:
        """최신 S&P 500 지수를 가져옵니다."""
        latest_data = self.repository.get_latest_market_data(MarketIndicatorType.SP500_INDEX)
        return latest_data.value if latest_data else None

    def get_latest_treasury_yield(self) -> Optional[float]:
        """최신 10년 국채 수익률을 가져옵니다."""
        latest_data = self.repository.get_latest_market_data(MarketIndicatorType.US_10Y_TREASURY_YIELD)
        return latest_data.value if latest_data else None

    def get_latest_put_call_ratio(self) -> Optional[float]:
        """최신 Put/Call 비율을 가져옵니다 (첫 번째 값)."""
        latest_data = self.repository.get_latest_market_data(MarketIndicatorType.PUT_CALL_RATIO)
        return latest_data.value if latest_data else None

    def update_fear_greed_index(self) -> bool:
        """CNN 공포탐욕지수를 업데이트합니다."""
        try:
            logger.info("Starting Fear & Greed Index update...")

            # 오늘 날짜 기준으로 최근 5일간 시도
            today = datetime.now().date()

            for days_back in range(5):
                target_date = today - timedelta(days=days_back)
                date_str = target_date.strftime('%Y-%m-%d')

                # CNN API URL (시작 날짜를 지정하면 오늘까지의 데이터를 가져옴)
                api_url = f"https://production.dataviz.cnn.io/index/fearandgreed/graphdata/{date_str}"

                logger.info(f"Fetching Fear & Greed Index from CNN API: {date_str}")

                # User-Agent 헤더 추가 (API 차단 방지)
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                    'Accept': 'application/json, text/plain, */*',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                }

                try:
                    response = requests.get(api_url, headers=headers, timeout=30)

                    if response.status_code == 200:
                        data = response.json()

                        # 공포탐욕지수 데이터 파싱
                        if 'fear_and_greed_historical' in data and 'data' in data['fear_and_greed_historical']:
                            historical_data = data['fear_and_greed_historical']['data']

                            if historical_data:
                                # 가장 최근 데이터 사용
                                latest_data = historical_data[-1]

                                # Unix timestamp (milliseconds)를 datetime으로 변환
                                timestamp_ms = int(float(latest_data['x']))
                                data_date = datetime.fromtimestamp(timestamp_ms / 1000).date()
                                fear_greed_value = float(latest_data['y'])

                                # 유효한 범위 확인 (0-100)
                                if 0 <= fear_greed_value <= 100:
                                    additional_data = json.dumps({
                                        "data_source": f"CNN Fear & Greed API ({api_url})",
                                        "data_date": data_date.strftime('%Y-%m-%d'),
                                        "api_response_status": "200",
                                        "note": "Official CNN Fear & Greed Index data",
                                        "timestamp_ms": timestamp_ms,
                                        "total_data_points": len(historical_data)
                                    })

                                    success = self.repository.save_market_data(
                                        indicator_type=MarketIndicatorType.FEAR_GREED_INDEX,
                                        data_date=data_date,
                                        value=fear_greed_value,
                                        additional_data=additional_data
                                    )

                                    if success:
                                        logger.info(f"Saved CNN Fear & Greed Index for {data_date}: {fear_greed_value}")
                                        return True
                                    else:
                                        logger.error(f"Failed to save Fear & Greed Index for {data_date}")
                                else:
                                    logger.warning(
                                        f"Invalid Fear & Greed Index value: {fear_greed_value} (must be 0-100)")
                            else:
                                logger.warning(f"No historical data found in CNN API response for {date_str}")
                        else:
                            logger.warning(f"Unexpected CNN API response structure for {date_str}")

                    elif response.status_code == 403:
                        logger.warning(f"CNN API returned status 403 for {date_str}")
                        continue

                    elif response.status_code == 404:
                        logger.warning(f"CNN API returned status 404 for {date_str}")
                        continue

                    else:
                        logger.warning(f"CNN API returned status {response.status_code} for {date_str}")
                        continue

                except requests.exceptions.RequestException as e:
                    logger.warning(f"Request failed for CNN Fear & Greed API ({date_str}): {e}")
                    continue

            # 모든 날짜에서 실패한 경우 - VIX 기반 추정치 사용
            logger.warning("Failed to get Fear & Greed Index from CNN API, using VIX-based estimation")

            try:
                vix_value = self.get_latest_vix()
                if vix_value:
                    # VIX 기반 공포탐욕지수 추정 (0-100 범위)
                    # VIX가 낮을수록 탐욕(높은 값), 높을수록 공포(낮은 값)
                    estimated_fg = max(0, min(100, 100 - (vix_value - 10) * 3))

                    additional_data = json.dumps({
                        "data_source": "VIX-based estimation",
                        "note": "Estimated Fear & Greed Index based on VIX",
                        "vix_value": vix_value,
                        "estimation_formula": "100 - (VIX - 10) * 3"
                    })

                    success = self.repository.save_market_data(
                        indicator_type=MarketIndicatorType.FEAR_GREED_INDEX,
                        data_date=today,
                        value=estimated_fg,
                        additional_data=additional_data
                    )

                    if success:
                        logger.info(f"Saved estimated Fear & Greed Index for {today}: {estimated_fg:.1f}")
                        return True

            except Exception as e:
                logger.error(f"Failed to create VIX-based Fear & Greed estimate: {e}")

            logger.error("Failed to update Fear & Greed Index from all sources")
            return False

        except Exception as e:
            logger.error(f"Error updating Fear & Greed Index: {e}", exc_info=True)
            return False

    def get_latest_fear_greed_index(self) -> Optional[float]:
        """최신 공포탐욕지수를 가져옵니다."""
        latest_data = self.repository.get_latest_market_data(MarketIndicatorType.FEAR_GREED_INDEX)
        return latest_data.value if latest_data else None

    def update_dxy_index(self) -> bool:
        """Yahoo Finance에서 달러 인덱스(DXY)를 가져와 저장합니다."""
        logger.info("Starting DXY Index (DX-Y.NYB) update...")
        try:
            dxy_data = self._fetch_yahoo_data_with_retry("DX-Y.NYB", period="5d")
            if dxy_data is None or dxy_data.empty:
                logger.error("Failed to fetch DXY data from Yahoo Finance")
                return False

            for date_idx, row in dxy_data.iterrows():
                dxy_date = date_idx.date()
                dxy_value = row['Close']
                additional_data = json.dumps({"data_source": "Yahoo Finance (DX-Y.NYB)"})
                success = self.repository.save_market_data(
                    indicator_type=MarketIndicatorType.DXY,
                    data_date=dxy_date,
                    value=dxy_value,
                    additional_data=additional_data
                )
                if success:
                    logger.info(f"Saved DXY for {dxy_date}: {dxy_value:.2f}")
            return True
        except Exception as e:
            logger.error(f"Error updating DXY index: {e}", exc_info=True)
            return False

    def update_sp500_sma(self, window: int = 200) -> bool:
        """DB의 S&P 500 데이터를 기반으로 SMA를 계산하고 저장합니다."""
        logger.info(f"Starting S&P 500 {window}-day SMA calculation...")
        try:
            # SMA 계산에 필요한 충분한 데이터 조회 (window + 버퍼)
            sp500_data = self.repository.get_recent_market_data(MarketIndicatorType.SP500_INDEX, limit=window + 50)
            if len(sp500_data) < window:
                logger.warning(f"Not enough S&P 500 data to calculate {window}-day SMA. Found {len(sp500_data)} points.")
                return False

            # DataFrame으로 변환
            df = pd.DataFrame([(d.date, d.value) for d in sp500_data], columns=['Date', 'Close']).set_index('Date')
            df.sort_index(inplace=True)

            # SMA 계산
            sma_series = df['Close'].rolling(window=window).mean().dropna()

            if sma_series.empty:
                logger.warning("SMA calculation resulted in an empty series.")
                return False

            # 최근 5일치 SMA 값 저장
            for sma_date, sma_value in sma_series.tail(5).items():
                additional_data = json.dumps({
                    "data_source": "Calculated from SP500_INDEX in DB",
                    "calculation_window": window
                })
                success = self.repository.save_market_data(
                    indicator_type=MarketIndicatorType.SP500_SMA_200,
                    data_date=sma_date,
                    value=sma_value,
                    additional_data=additional_data
                )
                if success:
                    logger.info(f"Saved S&P 500 {window}-day SMA for {sma_date}: {sma_value:.2f}")
            return True
        except Exception as e:
            logger.error(f"Error calculating S&P 500 SMA: {e}", exc_info=True)
            return False

    # --- Backtesting Support Methods with Forward Fill ---

    def get_vix_by_date(self, target_date: date) -> Optional[float]:
        """특정 날짜의 VIX를 가져옵니다 (Forward Fill 적용)."""
        data = self.repository.get_market_data_by_date_with_forward_fill(MarketIndicatorType.VIX, target_date)
        if data:
            logger.debug(f"VIX for {target_date} (found on {data.date}): {data.value}")
            return data.value
        logger.warning(f"No VIX data found on or before {target_date}")
        return None

    def get_treasury_yield_by_date(self, target_date: date) -> Optional[float]:
        """특정 날짜의 10년 국채 수익률을 가져옵니다 (Forward Fill 적용)."""
        data = self.repository.get_market_data_by_date_with_forward_fill(MarketIndicatorType.US_10Y_TREASURY_YIELD, target_date)
        if data:
            logger.debug(f"Treasury yield for {target_date} (found on {data.date}): {data.value}")
            return data.value
        logger.warning(f"No Treasury yield data found on or before {target_date}")
        return None

    def get_buffett_indicator_by_date(self, target_date: date) -> Optional[float]:
        """특정 날짜의 버핏 지수를 가져옵니다 (Forward Fill 적용)."""
        data = self.repository.get_market_data_by_date_with_forward_fill(MarketIndicatorType.BUFFETT_INDICATOR, target_date)
        if data:
            logger.debug(f"Buffett indicator for {target_date} (found on {data.date}): {data.value}")
            return data.value
        logger.warning(f"No Buffett indicator data found on or before {target_date}")
        return None

    def get_put_call_ratio_by_date(self, target_date: date) -> Optional[float]:
        """특정 날짜의 Put/Call 비율을 가져옵니다 (Forward Fill 적용)."""
        data = self.repository.get_market_data_by_date_with_forward_fill(MarketIndicatorType.PUT_CALL_RATIO, target_date)
        if data:
            logger.debug(f"Put/Call ratio for {target_date} (found on {data.date}): {data.value}")
            return data.value
        logger.warning(f"No Put/Call ratio data found on or before {target_date}")
        return None

    def get_fear_greed_index_by_date(self, target_date: date) -> Optional[float]:
        """특정 날짜의 공포탐욕지수를 가져옵니다 (Forward Fill 적용)."""
        data = self.repository.get_market_data_by_date_with_forward_fill(MarketIndicatorType.FEAR_GREED_INDEX, target_date)
        if data:
            logger.debug(f"Fear & Greed Index for {target_date} (found on {data.date}): {data.value}")
            return data.value
        logger.warning(f"No Fear & Greed Index data found on or before {target_date}")
        return None

    def get_all_put_call_ratios(self, limit: int = 1) -> Dict[str, Dict]:
        """
        모든 Put/Call 비율들을 조회합니다.
        
        Args:
            limit: 조회할 최근 데이터 개수
            
        Returns:
            Dict[str, Dict]: 날짜별 모든 Put/Call 비율 데이터
        """
        try:
            recent_data = self.repository.get_recent_market_data(MarketIndicatorType.PUT_CALL_RATIO, limit=limit)
            result = {}

            for data in recent_data:
                date_str = data.date.strftime('%Y-%m-%d')

                # 기본 정보 설정
                result[date_str] = {
                    'total_put_call_ratio': data.value,  # value 필드에 저장된 TOTAL PUT/CALL RATIO
                    'data_source': 'Unknown',
                    'all_ratios': {},
                    'ratios_count': 0
                }

                # additional_data에서 모든 비율 정보 추출
                if data.additional_data:
                    try:
                        additional_info = json.loads(data.additional_data)

                        result[date_str]['data_source'] = additional_info.get('data_source', 'Unknown')
                        result[date_str]['ratios_count'] = additional_info.get('total_ratios_count', 0)
                        result[date_str]['primary_ratio'] = additional_info.get('primary_ratio', 'TOTAL PUT/CALL RATIO')

                        # 모든 비율 정보
                        all_ratios = additional_info.get('all_ratios', {})
                        if all_ratios:
                            result[date_str]['all_ratios'] = all_ratios

                    except json.JSONDecodeError:
                        logger.warning(f"Failed to parse additional_data for {date_str}")

            return result

        except Exception as e:
            logger.error(f"Error getting all Put/Call ratios: {e}", exc_info=True)
            return {}

    def get_macro_data_for_date(self, target_date: date, required_indicators: List[str]) -> Dict[str, Any]:
        """
        특정 날짜와 요구되는 지표 목록을 기반으로, 모든 거시 경제 지표를 조회하고
        'Last Known Value' 정책을 적용하여 완결된 딕셔너리를 반환합니다.

        Args:
            target_date: 데이터를 조회할 기준 날짜
            required_indicators: 필요한 거시 지표의 이름 목록 (예: ['VIX', 'FEAR_GREED_INDEX'])

        Returns:
            Dict[str, Any]: 조회된 거시 지표 데이터 딕셔너리.
                           데이터가 없는 경우에도 키는 존재하되 값은 None이 됩니다.
        """
        macro_data = {}
        
        # 각 지표에 대한 조회 함수 매핑
        indicator_fetch_map = {
            'VIX': self.get_vix_by_date,
            'US_10Y_TREASURY_YIELD': self.get_treasury_yield_by_date,
            'BUFFETT_INDICATOR': self.get_buffett_indicator_by_date,
            'PUT_CALL_RATIO': self.get_put_call_ratio_by_date,
            'FEAR_GREED_INDEX': self.get_fear_greed_index_by_date,
            'DXY': lambda d: self.repository.get_market_data_by_date_with_forward_fill(MarketIndicatorType.DXY, d).value if self.repository.get_market_data_by_date_with_forward_fill(MarketIndicatorType.DXY, d) else None,
            'SP500_SMA_200': lambda d: self.repository.get_market_data_by_date_with_forward_fill(MarketIndicatorType.SP500_SMA_200, d).value if self.repository.get_market_data_by_date_with_forward_fill(MarketIndicatorType.SP500_SMA_200, d) else None,
            # S&P500, 금, 유가 등 다른 지표도 필요 시 여기에 추가
            'SP500_INDEX': lambda d: self.repository.get_market_data_by_date_with_forward_fill(MarketIndicatorType.SP500_INDEX, d).value if self.repository.get_market_data_by_date_with_forward_fill(MarketIndicatorType.SP500_INDEX, d) else None,
            'GOLD_PRICE': lambda d: self.repository.get_market_data_by_date_with_forward_fill(MarketIndicatorType.GOLD_PRICE, d).value if self.repository.get_market_data_by_date_with_forward_fill(MarketIndicatorType.GOLD_PRICE, d) else None,
            'CRUDE_OIL_PRICE': lambda d: self.repository.get_market_data_by_date_with_forward_fill(MarketIndicatorType.CRUDE_OIL_PRICE, d).value if self.repository.get_market_data_by_date_with_forward_fill(MarketIndicatorType.CRUDE_OIL_PRICE, d) else None,
        }

        logger.debug(f"Fetching macro data for {target_date} with required indicators: {required_indicators}")

        for indicator_name in required_indicators:
            fetch_function = indicator_fetch_map.get(indicator_name)
            if fetch_function:
                macro_data[indicator_name] = fetch_function(target_date)
            else:
                logger.warning(f"No fetch function defined for required indicator: {indicator_name}")
                macro_data[indicator_name] = None
        
        return macro_data


if __name__ == '__main__':
    """테스트용 실행"""
    from infrastructure.logging import setup_logging

    setup_logging()

    service = MarketDataService()
    results = service.update_all_indicators()
    print("Update results:", results)
