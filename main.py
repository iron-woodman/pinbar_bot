from src.binance_api import load_futures_list
import multiprocessing
from binance import Client
from binance.enums import HistoricalKlinesType
import json
import datetime
import time
import os
import src.logger as custom_logging
from src.config_handler import TIMEFRAMES, BINANCE_API_KEY, BINANCE_Secret_KEY
from send_all_signals import process_signal

THREAD_CNT = 1  # 3 потока на ядро
DAY_OPEN_PRICES = dict()

def check_history_bars_for_pinbar_pattern(pair: str, bars: list) -> str:
    """
    Поиск свечного паттерна в барах истории
    :param bars:
    :return:
    """
    if len(bars) < 2:
        print(f'{pair}: Bar count = {len(bars)}.')
        return ""
    _time = []
    cl = []
    op = []
    high = []
    low = []
    vol = []

    for bar in bars:
        value = datetime.datetime.fromtimestamp(bar[0] / 1000)
        # print(value.strftime('%Y-%m-%d %H:%M:%S'))
        _time.append(value.strftime('%Y-%m-%d %H:%M:%S'))
        op.append(float(bar[1]))
        high.append(float(bar[2]))
        low.append(float(bar[3]))
        cl.append(float(bar[4]))
        vol.append(float(bar[5]))

    # проверяем значения на паттерны
    if vol[0] >= vol[1] or op[1] == cl[1]: # объем последней свечи должен быть больше чем объем предудыщей свечи
        return ""
    if cl[1] > op[1] and cl[1] + high[1] > op[1] + low[1] and op[1] + low[1] > op[1] + cl[1] and \
        high[1] + cl[1] > low[1] + cl[1] and low[1] != op[1]  and high[1] > high[0] and cl[0] > op[0]:
        return "Pin Short Green"
    elif cl[1] < op[1] and op[1] + high[1] > cl[1] + low[1] and cl[1] + low[1] > op[1] + cl[1] and \
        high[1] + op[1] > low[1] + op[1] and low[1] != cl[1] and high[1] > high[0] and cl[0] > op[0]:
        return "Pin Short Red"
    elif cl[1] > op[1] and op[1] + low[1] > cl[1] + high[1] and op[1] + low[1] > op[1] + cl[1] and \
        low[1] + op[1] > high[1] + op[1] and high[1] != cl[1] and low[1] < low[0] and cl[0] < op[0]:
        return "Pin Long Green"
    elif cl[1] < op[1] and cl[1] + low[1] > op[1] + high[1] and op[1] + low[1] > op[1] + cl[1] and \
        low[1] + cl[1] > high[1] + cl[1] and high[1] != op[1] and low[1] < low[0] and cl[0] < op[0]:
        return "Pin Long Red"

    return "Pin Test"


def get_day_price_move(pair, last_hour_bar):
    """
    get procent of price movement from open price
    """
    DAY_OPEN_PRICES = load_open_prices()
    if pair in DAY_OPEN_PRICES:
        day_open = DAY_OPEN_PRICES[pair]
        bar_close = float(last_hour_bar[4])
        move = abs(day_open-bar_close) * 100 / day_open
        return move
    return 0




def load_history_bars(task):
    """
    Load historical bars
    :return:
    """
    result = dict()
    pair = task[0]
    api_key = task[1]
    secret_key = task[2]
    all_timeframes = task[3]
    is_spot = task[4]
    client = Client(api_key, secret_key)

    try:
        result['id'] = pair
        for timeframe in all_timeframes:
            if timeframe == '1d':
                st_time = "4 day ago UTC"
            if timeframe == '1h':
                st_time = "2 hour ago UTC"
            else:
                print('Unknown timeframe:', timeframe)
                custom_logging.error(f'Load history bars error: unknown timeframe "{timeframe}"')
                continue

            bars = []
            try:
                if is_spot:
                    bars = client.get_historical_klines(pair, timeframe, st_time, HistoricalKlinesType.SPOT)
                else:
                    bars = client.get_historical_klines(pair, timeframe, st_time,
                                                        klines_type=HistoricalKlinesType.FUTURES)

            except Exception as e:
                print(pair, ':', e)

            if len(bars) == 0:
                print(f" 0 bars has been gathered from server. client.get_historical_klines({pair}, {timeframe}, "
                      f"{st_time})")
                result[timeframe] = 0
                continue
            # ------------ check for different pin bar patterns ----------------------------------------------------------
            check_result = check_history_bars_for_pinbar_pattern(pair, bars)
            result["pattern"] = check_result
            # ----------------------------------------------------------------------------------------------------------
        return result
    except Exception as e:
        print("Exception when calling load_history_bars: ", e)
        return None


def store_signals_to_file(signals_data: dict, pattern_name: str):
    with open(f"signals_{pattern_name}/{datetime.date.today().isoformat()}.txt", 'w', encoding='utf-8') as f:
        json.dump(signals_data, f, ensure_ascii=False, indent=4, separators=(',', ': '))
        print(f'Signals data stored to file "signals_{pattern_name}/{datetime.date.today().isoformat()}.txt".')
        custom_logging.info(
            f'New signals data stored to file "signals_{pattern_name}/{datetime.date.today().isoformat()}.txt".')
        custom_logging.info(
            f'**************************************************************************************')


def load_futures_history_bars_end(responce_list):
    signals_pinbar = dict()

    for responce in responce_list:
        id = responce['id']
        del responce['id']

        if responce['pattern'] != '':
            if responce['pattern'] not in signals_pinbar:
                signals_pinbar[responce['pattern']] = list()
            signals_pinbar[responce['pattern']].append(id)

    try:
        store_signals_to_file(signals_pinbar, "pinbar")

    except Exception as e:
        print("load_futures_history_bars_end exception:", e)
        custom_logging.error(f'load_futures_history_bars_end exception: {e}')


def load_open_prices() -> dict:
    """load open prices from json file"""
    prices = dict()
    for element in os.scandir('day_open_price'):
        if element.is_file():
            if '.txt' in element.name:
                with open(f'day_open_price/{element.name}', 'r', encoding='utf-8') as f:
                    prices = json.load(f)
    return prices


if __name__ == '__main__':
    futures_list = load_futures_list()

    # if len(DAY_OPEN_PRICES) == 0:
    #     custom_logging.error(f"Day open prices not loaded. Script closed.")
    #     exit(1)
    print('Futures count:', len(futures_list))
    tasks = []
    try:
        custom_logging.info('Gathering history candles data...')
        for symbol in futures_list:
            tasks.append((symbol, BINANCE_API_KEY, BINANCE_Secret_KEY, TIMEFRAMES, False))
        with multiprocessing.Pool(multiprocessing.cpu_count() * THREAD_CNT) as pool:
            pool.map_async(load_history_bars, tasks, callback=load_futures_history_bars_end)
            pool.close()
            pool.join()
            cur_date = datetime.date.today().isoformat()
            process_signal('signals_pinbar', cur_date)

    except Exception as ex:
        print("Load history bars exception:", ex)
        custom_logging.error(f"Load history bars exception: {ex}")
