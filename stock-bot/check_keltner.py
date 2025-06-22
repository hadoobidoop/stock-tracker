from infrastructure.db.db_manager import get_db
from infrastructure.db.models.technical_indicator import TechnicalIndicator

def check_keltner_values():
    with get_db() as db:
        indicator = db.query(TechnicalIndicator).filter(
            TechnicalIndicator.ticker == 'AAPL'
        ).order_by(TechnicalIndicator.timestamp_utc.desc()).first()
        
        if indicator:
            print(f'AAPL Keltner Channel values for {indicator.timestamp_utc}:')
            print(f'Middle (kcbe_20_2): {indicator.kcbe_20_2}')
            print(f'Upper (kcue_20_2): {indicator.kcue_20_2}')
            print(f'Lower (kcle_20_2): {indicator.kcle_20_2}')
        else:
            print('No indicator data found for AAPL')

if __name__ == '__main__':
    check_keltner_values() 