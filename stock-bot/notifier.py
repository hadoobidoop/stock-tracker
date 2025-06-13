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
    SIGNAL_THRESHOLD, PREDICTION_THRESHOLD,
    VOLUME_SURGE_FACTOR, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
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
        "parse_mode": "Markdown"  # 메시지 서식 지정을 위해 Markdown 사용
    }
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()  # HTTP 오류(4xx, 5xx) 발생 시 예외 발생
        logger.info(f"Telegram message sent successfully to chat ID: {TELEGRAM_CHAT_ID}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Error sending Telegram message: {e}")
    except Exception as e:
        logger.error(f"An unexpected error occurred while sending Telegram message: {e}")


def format_signal_message(
        ticker: str,
        signal_type: str,
        signal_score: int,
        signal_details_list: list,
        current_data: pd.Series,
        prev_data: pd.Series,
        stop_loss_price: float = None
) -> str:
    """
    신호 메시지를 포맷팅합니다.
    """
    message = f"🔔 *{ticker} {signal_type} 신호 감지*\n"
    message += f"신호 강도: {signal_score}\n\n"

    if signal_details_list:
        message += "*감지된 조건:*\n"
        for detail in signal_details_list:
            message += f"• {detail}\n"

    if stop_loss_price is not None:
        message += f"\n⚠️ *예상 손절매 가격: ${stop_loss_price:.2f}*\n"

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
    details_list = prediction_data.get('details', [])  # price_predictor에서 전달받은 조건 설명 리스트

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
        message += "- 특정 조건 없음 (점수만으로 발생)\n"  # 모든 조건이 명시되지 않았거나 점수만으로 임계값 초과 시

    message += f"\n📊 이 정보는 예측이며, 투자 결정은 신중하게 하세요!"

    return message
