from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from PIL import Image
import pytesseract
import time
import os
import re
import MetaTrader5 as mt5

watched_folder = r'C:\Users\Kristjan\AppData\Local\Packages\5319275A.WhatsAppDesktop_cv1g1gvanyjgm\LocalState\shared\transfers\2025_21'
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

if not mt5.initialize():
    print("MT5 initialization failed, error code =",mt5.last_error())
    quit()
account_info = mt5.account_info()
if account_info is None:
    print("Failed to get acc info")
else:
    print("Connected to account #", account_info.login)

def parse_trade_signal(text):
    lines=text.lower().splitlines()
    trade={}

    symbol_map = {
        'eurusd':'EURUSD',
        'gbpusd': 'GBPUSD',
        'xauusd': 'XAUUSD',
        'btcusd': 'BTCUSD',
        'gold': 'XAUUSD'
    }

    for line in lines:
        if 'buy' in line or 'sell' in line:
            trade['action'] = 'buy' if 'buy' in line else 'sell'
        for key in symbol_map:
            if key in line:
                trade['symbol'] = symbol_map[key]
                break
        if 'tp' in line:
            numbers = re.findall(r'\d+\.?\d*',line)
            if numbers:
                trade['tp'] = float(numbers[0])
        if 'sl' in line:
            numbers = re.findall(r'\d+\.?\d*',line)
            if numbers:
                trade['sl'] = float(numbers[0])

    return trade

def send_trade_to_mt5(trade):
    if not all(k in trade for k in ('action', 'symbol')):
        print("[!] Trade data incomplete:",trade)
        return
    
    symbol = trade['symbol']
    action = trade['action'].lower()

    symbol_info = mt5.symbol_info(symbol)
    if symbol_info is None:
        print(f"[!] Symbol info not found for {symbol}")
        return
    digits = symbol_info.digits
    point = symbol_info.point

    selected = mt5.symbol_select(symbol, True)
    if not selected:
        print(f"[!] Failed to select symbol {symbol}")
        return
    
    lot = 0.01

    price = mt5.symbol_info_tick(symbol).ask if action == 'buy' else mt5.symbol_info_tick(symbol).bid

    request = {
        "action":mt5.TRADE_ACTION_DEAL,
        "symbol":symbol,
        "volume":lot,
        "type":mt5.ORDER_TYPE_BUY if action == 'buy' else mt5.ORDER_TYPE_SELL,
        "price":price,
        "deviation":10,
        "magic":234000,
        "comment": "Trade signal from bot",
        "type_time":mt5.ORDER_TIME_GTC,
        "type_filling":mt5.ORDER_FILLING_RETURN
    }

    if 'tp' in trade:
        try:
            request['tp']= round(float(trade['tp']), digits)
        except ValueError:
            print("[!] Invalid TP values: ",trade['tp'])
    if 'sl' in trade:
        try:
            request['sl']= round(float(trade['sl']), digits)
        except ValueError:
            print("[!] Invalid SL value: ", trade['sl'])

    result = mt5.order_send(request)

    if result.retcode !=mt5.TRADE_RETCODE_DONE:
        print(f"[!] Trade failed, retcode={result.retcode}")
    else:
        print("[+] Trade executed successfully")

class ScreenshotHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.src_path.lower().endswith(('.jpeg', '.jpg', '.png')):
            print(f"[+] New image detected: {event.src_path}")
            try:
                time.sleep(1)
                img = Image.open(event.src_path)
                text = pytesseract.image_to_string(img)
                print("Extracted text: ")
                print(text)

                trade = parse_trade_signal(text)
                print("Parsed Trade Signal: ",trade)
                send_trade_to_mt5(trade)
            
            except Exception as e:
                print(f"[!] Error processing image: {e}")

observer = Observer()
observer.schedule(ScreenshotHandler(), path=watched_folder, recursive=False)
observer.start()

print(f"Watching folder: {watched_folder}")
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    observer.stop()
observer.join()
