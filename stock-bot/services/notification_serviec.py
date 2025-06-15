# stock_bot/services/notification_service.py
# 역할: 텔레그램 등 외부 알림 서비스와의 연동을 책임지는 클래스.

import requests
import logging
from ..config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

logger = logging.getLogger(__name__)

class NotificationService:
    """
    텔레그램 메시지 전송을 담당하는 서비스 클래스입니다.
    """
    def send_telegram_message(self, message: str):
        """텔레그램 봇을 통해 메시지를 전송합니다."""
        if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
            logger.error("Telegram bot token or chat ID is not set. Cannot send message.")
            return

        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}

        try:
            response = requests.post(url, json=payload)
            response.raise_for_status()
            logger.info(f"Telegram message sent successfully.")
        except requests.exceptions.RequestException as e:
            logger.error(f"Error sending Telegram message: {e}")

    def format_signal_message(self, signal_data: dict) -> str:
        """거래 신호 데이터를 텔레그램 메시지 형식으로 변환합니다."""
        ticker = signal_data.get('ticker', 'N/A')
        signal_type = signal_data.get('type', 'N/A')
        score = signal_data.get('score', 0)
        details = signal_data.get('details', [])
        stop_loss = signal_data.get('stop_loss_price')

        message = f"🔔 *{ticker} {signal_type} 신호 감지* (점수: {score})\n\n"
        message += "*감지된 조건:*\n"
        for detail in details[:5]: # 너무 길지 않게 최대 5개만 표시
            message += f"• {detail}\n"

        if stop_loss:
            message += f"\n⚠️ *예상 손절매 가격: ${stop_loss:.2f}*\n"

        message += f"\n💡 기술적 분석에 기반한 신호이며, 신중한 판단이 필요합니다."
        return message

    def format_prediction_message(self, prediction_data: dict) -> str:
        """가격 예측 데이터를 텔레그램 메시지 형식으로 변환합니다."""
        if not prediction_data:
            return "✨ *[일일 예측]* 오늘은 특별한 매수 기회 예측이 없습니다."

        ticker = prediction_data.get('ticker', 'N/A')
        price_type = prediction_data.get('price_type', 'N/A')
        price = prediction_data.get('price', 0.0)

        message = (f"🔮 *[{ticker}] 다음 날 매수 기회 예측!*\n"
                   f"🎯 *예상 지지선: {price_type} 부근 (${price:.2f})*\n")
        # ... 기타 예측 메시지 포맷팅 로직 ...
        return message

