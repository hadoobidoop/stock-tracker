# notifier.py

import requests
import logging
import pandas as pd
from datetime import datetime
# config에서 직접 임포트하므로, `main.py`에서 `config`를 로드하고
# `send_telegram_message`, `format_signal_message`, `format_prediction_message`를 호출할 때
# `config`의 값들을 매개변수로 전달해야 합니다.
# 여기서는 `config.py`의 값을 직접 임포트하여 사용하도록 변경합니다.
from config import (
    TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID,
    SIGNAL_THRESHOLD, PREDICTION_THRESHOLD,
    VOLUME_SURGE_FACTOR
)

logger = logging.getLogger(__name__)

def send_telegram_message(message: str):
    """
    텔레그램 봇을 통해 메시지를 전송합니다.
    """
    # 텔레그램 봇 토큰이나 채팅 ID가 설정되지 않았다면 메시지 전송을 시도하지 않습니다.
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.error("Telegram bot token or chat ID is not set in config.py. Cannot send message.")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown" # 메시지 서식 지정을 위해 Markdown 사용
    }
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status() # HTTP 오류(4xx, 5xx) 발생 시 예외 발생
        logger.info(f"Telegram message sent successfully to chat ID: {TELEGRAM_CHAT_ID}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Error sending Telegram message: {e}")
    except Exception as e:
        logger.error(f"An unexpected error occurred while sending Telegram message: {e}")


def format_signal_message(
        ticker: str,
        signal_type: str,
        signal_score: int, # signal_detector에서 계산된 최종 점수
        signal_details_list: list, # signal_detector에서 온 상세 조건 목록
        current_data: pd.Series, # 현재 데이터 (마지막 봉)
        prev_data: pd.Series, # 이전 데이터 (바로 이전 봉)
        stop_loss_price: float = None # ATR 기반 손절매 가격 추가
) -> str:
    """
    실시간 매수/매도 신호 알림 메시지를 포맷합니다.
    모든 필요한 지표 값과 조건이 메시지에 포함됩니다.
    """
    # 현재 봉의 타임스탬프를 사용하여 메시지 시간 표시
    timestamp = current_data.name.strftime('%Y-%m-%d %H:%M:%S')

    emoji = "🔥" if signal_type == "BUY" else "📉"
    action_text = "매수" if signal_type == "BUY" else "매도"

    # 켈트너 채널 중간선 (KCMe_20_2)이 없을 경우 BBM_20_2.0 (볼린저 밴드 중간선) 사용
    # indicator_calculator에서 KCMe_20_2가 생성되지 않으므로 BBM_20_2.0을 기본값으로 사용
    keltner_middle = current_data.get('KCMe_20_2', current_data.get('BBM_20_2.0', 0.0))

    message = (
        f"{emoji} *[{ticker}] {action_text} 신호 발생!* {emoji}\n"
        f"🗓️ 시간: `{timestamp}`\n"
        f"💰 현재 종가: *${current_data['Close']:.2f}*\n"
        f"⭐ *신호 점수: {signal_score} / {SIGNAL_THRESHOLD} (임계값)* ⭐\n"
        f"\n"
        f"*--- 지표 상세 ---*\n"
        f"📊 SMA (5/20/60): {current_data['SMA_5']:.2f} / {current_data['SMA_20']:.2f} / {current_data['SMA_60']:.2f}\n"
        f"📈 RSI (14): {current_data['RSI_14']:.2f}\n"
        f"📉 MACD / Signal: {current_data['MACD_12_26_9']:.2f} / {current_data['MACDs_12_26_9']:.2f}\n"
        f"📊 STOCH (%K/%D): {current_data['STOCHk_14_3_3']:.2f} / {current_data['STOCHd_14_3_3']:.2f}\n"
        f"💪 ADX (14): {current_data['ADX_14']:.2f} (+DI:{current_data['DMP_14']:.2f}, -DI:{current_data['DMN_14']:.2f})\n" # ADX는 DMP, DMN도 함께 표시하여 방향성 확인
        f"📈 거래량: {current_data['Volume']:,} (20일 평균: {current_data['Volume_SMA_20']:.0f})\n" # 현재 거래량과 평균 거래량 함께 표시
        f"📈 볼린저 밴드 (상/중/하): {current_data['BBU_20_2.0']:.2f} / {current_data['BBM_20_2.0']:.2f} / {current_data['BBL_20_2.0']:.2f}\n"
        f"📈 켈트너 채널 (상/중/하): {current_data.get('KCUe_20_2', 0.0):.2f} / {keltner_middle:.2f} / {current_data.get('KCLe_20_2', 0.0):.2f}\n" # KCLe, KCUe도 get()으로 안전하게 접근
        f"\n"
    )

    message += f"*--- 신호 발생 조건 ---*\n"
    # signal_details_list는 signal_detector에서 조건이 충족될 때 추가한 상세 설명 문자열 리스트입니다.
    if signal_details_list:
        for detail in signal_details_list:
            message += f"- ✅ {detail}\n"
    else:
        message += "- 특정 조건 없음 (점수만으로 발생)\n" # 모든 조건이 명시되지 않았거나 점수만으로 임계값 초과 시

    # --- 손절매 가격 정보 추가 ---
    if stop_loss_price is not None:
        message += f"\n⚠️ *예상 손절매 가격: ${stop_loss_price:.2f}*\n"
    # --- 손절매 가격 정보 추가 끝 ---

    message += f"\n💡 기술적 분석에 기반한 신호이며, 신중한 판단이 필요합니다."

    return message

def format_prediction_message(prediction_data: dict) -> str:
    """
    텔레그램 알림 메시지를 포맷합니다. (일일 예측 신호)
    """
    if not prediction_data:
        return "✨ *[일일 예측 알림]*\n\n오늘은 특별한 매수 기회 예측이 없습니다."

    ticker = prediction_data.get('ticker', 'N/A')
    price_type = prediction_data.get('price_type', 'N/A')
    price = prediction_data.get('price', 0.0)
    range_low = prediction_data.get('range_low', 0.0)
    range_high = prediction_data.get('range_high', 0.0)
    reason = prediction_data.get('reason', '지정된 예측 기준 충족')
    score = prediction_data.get('score', 0)
    details_list = prediction_data.get('details', []) # price_predictor에서 전달받은 조건 설명 리스트

    # main.py에서 주입된 정보 (전일 종가 및 예측 실행 시점)
    prev_day_close = prediction_data.get('prev_day_close', 0.0)
    prediction_timestamp = prediction_data.get('prediction_timestamp', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))


    message = (
        f"🔮 *[{ticker}] 다음 날 매수 기회 예측!* 🔮\n"
        f"🗓️ 예측 시간: `{prediction_timestamp}`\n"
        f"📈 전일 종가: *${prev_day_close:.2f}*\n"
        f"🎯 *예상 매수 구간: {price_type} 부근 (${price:.2f})*\n"
        f"  (범위: ${range_low:.2f} ~ ${range_high:.2f})\n"
        f"⭐ *예측 점수: {score} / {PREDICTION_THRESHOLD} (임계값)* ⭐\n"
        f"\n"
        f"*--- 예측 조건 ---*\n"
    )

    # details_list에 담긴 조건 설명을 모두 출력
    if details_list:
        for detail in details_list:
            message += f"- ✅ {detail}\n"
    else:
        message += "- 특정 조건 없음 (점수만으로 발생)\n" # 모든 조건이 명시되지 않았거나 점수만으로 임계값 초과 시

    message += f"\n📊 이 정보는 예측이며, 투자 결정은 신중하게 하세요!"

    return message
