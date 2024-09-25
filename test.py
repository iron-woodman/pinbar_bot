from src.binance_api import load_futures_list
from src.telegram_api import send_signal
from src.config_handler import TLG_TOKEN, TLG_CHANNEL_ID


futures_list = load_futures_list()
send_signal(f"Загружен список фьючерсов ({len(futures_list)} шт.)", TLG_TOKEN, TLG_CHANNEL_ID)
