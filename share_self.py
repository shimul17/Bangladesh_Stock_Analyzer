# ========================================================
# DSE Top 20 Stock Scanner
# Features:
# - Analyzes top 20 DSE stocks
# - Buy/Sell decision using RSI, MACD, MA9/MA21, Bollinger Bands
# - Volume Status (BUYERS ACTIVE / SELLERS DOMINATING / MARKET NEUTRAL)
# - Calculates Sell Target and Stop Loss
# - VS Code-friendly horizontal output
# - Optional Telegram alerts for STRONG BUY / STRONG SELL
# ========================================================

import pandas as pd
from bdshare import get_historical_data
import numpy as np
from datetime import datetime
import requests

# ------------------ Telegram Setup ------------------
TELEGRAM_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"  # Replace with your bot token
CHAT_ID = "YOUR_CHAT_ID"                    # Replace with your chat id

def send_telegram_message(message):
    """Send message to Telegram for strong signals."""
    if TELEGRAM_TOKEN and CHAT_ID:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {"chat_id": CHAT_ID, "text": message}
        try:
            requests.post(url, data=payload)
        except:
            pass

# ------------------ Top 20 DSE Stocks ------------------
stocks = ["BDTHAI","BEXIMCO","GP","SQURPHARMA","BATBC",
          "RENATA","BRACBANK","ACI","OLYMPIC","WALTONHIL",
          "IFICBANK","DBH","MARICO","ONEBANK","NBL",
          "FUWANGCER","EXIMBANK","MONNOSTAF","LHBL","IPDC"]

start_date = "2024-01-01"
end_date = datetime.today().strftime('%Y-%m-%d')

# ------------------ Stock Analysis Function ------------------
def analyze_stock(symbol):
    """Analyze a single stock and return summary dictionary."""
    try:
        df = get_historical_data(start_date,end_date,symbol)
    except:
        return None
    if df is None or df.empty:
        return None

    df = df.reset_index()
    df.columns = [c.lower() for c in df.columns]
    df['close'] = pd.to_numeric(df['close'], errors='coerce')
    df['volume'] = pd.to_numeric(df['volume'], errors='coerce')
    df = df.dropna()

    # ------------------ Indicators ------------------
    # Moving averages
    df['ma9'] = df['close'].rolling(9).mean()
    df['ma21'] = df['close'].rolling(21).mean()

    # MACD
    df['ema12'] = df['close'].ewm(span=12, adjust=False).mean()
    df['ema26'] = df['close'].ewm(span=26, adjust=False).mean()
    df['macd'] = df['ema12'] - df['ema26']
    df['signal'] = df['macd'].ewm(span=9, adjust=False).mean()

    # RSI
    delta = df['close'].diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = -delta.clip(upper=0).rolling(14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))

    # Bollinger Bands
    df['sma20'] = df['close'].rolling(20).mean()
    df['std20'] = df['close'].rolling(20).std()
    df['lower_b'] = df['sma20'] - 2*df['std20']
    df['upper_b'] = df['sma20'] + 2*df['std20']

    # ------------------ Latest Values ------------------
    price = df['close'].iloc[-1]
    prev_price = df['close'].iloc[-2]
    lower_b = df['lower_b'].iloc[-1]
    upper_b = df['upper_b'].iloc[-1]
    ma9 = df['ma9'].iloc[-1]
    ma21 = df['ma21'].iloc[-1]
    macd = df['macd'].iloc[-1]
    signal = df['signal'].iloc[-1]
    rsi = df['rsi'].iloc[-1]

    # ------------------ Volume Status ------------------
    vol_avg = df['volume'].tail(10).mean()
    curr_vol = df['volume'].iloc[-1]
    vol_ratio = curr_vol / vol_avg if vol_avg>0 else 1
    if price > prev_price and vol_ratio > 1.2:
        vol_status = "BUYERS ACTIVE"
    elif price < prev_price and vol_ratio > 1.2:
        vol_status = "SELLERS DOMINATING"
    else:
        vol_status = "MARKET NEUTRAL"

    # ------------------ Decision ------------------
    if (price <= lower_b or rsi < 35) and price > prev_price:
        decision = "STRONG BUY"
    elif macd > signal and ma9 > ma21:
        decision = "BUY / HOLD"
    elif rsi > 80 or price >= upper_b:
        decision = "STRONG SELL"
    elif ma9 < ma21 or macd < signal:
        decision = "SELL / AVOID"
    else:
        decision = "WAIT"

    # ------------------ Sell Target & Stop Loss ------------------
    sell_target = upper_b if decision in ["STRONG BUY","BUY / HOLD"] else lower_b
    stop_loss = lower_b if decision in ["STRONG BUY","BUY / HOLD"] else upper_b

    # ------------------ Telegram Alert ------------------
    if decision in ["STRONG BUY","STRONG SELL"]:
        msg = f"{symbol} -> {decision}\nPrice: {round(price,2)}\nTarget: {round(sell_target,2)}\nStop Loss: {round(stop_loss,2)}\nVolume: {vol_status}"
        send_telegram_message(msg)

    return {
        "Stock": symbol,
        "Price": round(price,2),
        "Volume_Status": vol_status,
        "Decision": decision,
        "Sell_Target": round(sell_target,2),
        "Stop_Loss": round(stop_loss,2)
    }

# ------------------ Run Top 20 Scanner ------------------
results = []
for stock in stocks:
    res = analyze_stock(stock)
    if res:
        results.append(res)

df_result = pd.DataFrame(results)

# ------------------ VS Code Horizontal Display ------------------
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 120)
pd.set_option('display.colheader_justify', 'center')

print("\n====== DSE Top 20 Scanner (Horizontal + Telegram Alerts) ======\n")
print(df_result.to_string(index=False))
