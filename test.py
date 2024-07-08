import json
import os
from send_all_signals import process_signal
import datetime


def load_open_prices():
    open_prices = dict()
    for element in os.scandir('day_open_price'):
        if element.is_file():
            if '.txt' in element.name:
                with open(f'day_open_price/{element.name}', 'r', encoding='utf-8') as f:
                    open_prices = json.load(f)
    return open_prices


cur_date = datetime.date.today().isoformat()
process_signal('signals_pinbar', cur_date)
