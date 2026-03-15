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
import time 

# ------------------ Telegram Setup ------------------
TELEGRAM_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN" 
CHAT_ID = "YOUR_CHAT_ID"

def send_telegram_message(message):
    if TELEGRAM_TOKEN != "YOUR_TELEGRAM_BOT_TOKEN":
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {"chat_id": CHAT_ID, "text": message}
        try:
            requests.post(url, data=payload, timeout=5)
        except:
            pass

# ------------------ Top 20 DSE Stocks ------------------
stocks = ["BDTHAI","BEXIMCO","GP","SQURPHARMA","BATBC",
          "RENATA","BRACBANK","ACI","OLYMPIC","WALTONHIL",
          "IFICBANK","DBH","MARICO","ONEBANK","NBL",
          "FUWANGCER","EXIMBANK","MONNOSTAF","LHBL","IPDC"]

start_date = "2024-01-01"
end_date = datetime.today().strftime('%Y-%m-%d')

def analyze_stock(symbol):
    try:
        df = get_historical_data(start_date, end_date, symbol)
        if df is None or df.empty: return None
        
        df = df.reset_index()
        df.columns = [c.lower() for c in df.columns]
        df['close'] = pd.to_numeric(df['close'], errors='coerce')
        df['volume'] = pd.to_numeric(df['volume'], errors='coerce')
        df = df.sort_values('date').dropna(subset=['close', 'volume'])
        
        if len(df) < 30: return None

        # --- Indicators ---
        df['ma9'] = df['close'].rolling(9).mean()
        df['ma21'] = df['close'].rolling(21).mean()
        
        # MACD
        df['ema12'] = df['close'].ewm(span=12, adjust=False).mean()
        df['ema26'] = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = df['ema12'] - df['ema26']
        df['signal'] = df['macd'].ewm(span=9, adjust=False).mean()

        # RSI (Safe Calculation)
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        df['rsi'] = 100 - (100 / (1 + (gain / (loss + 1e-9)))) # 1e-9 added to avoid div by zero

        # Bollinger Bands
        df['sma20'] = df['close'].rolling(20).mean()
        df['std20'] = df['close'].rolling(20).std()
        df['lower_b'] = df['sma20'] - 2*df['std20']
        df['upper_b'] = df['sma20'] + 2*df['std20']

        # --- Latest Values ---
        curr = df.iloc[-1]
        prev = df.iloc[-2]
        price, rsi, macd, sig = curr['close'], curr['rsi'], curr['macd'], curr['signal']
        ma9, ma21, lower_b, upper_b = curr['ma9'], curr['ma21'], curr['lower_b'], curr['upper_b']

        # --- Volume Status ---
        vol_avg = df['volume'].tail(10).mean()
        vol_ratio = curr['volume'] / vol_avg if vol_avg > 0 else 1
        
        if price > prev['close'] and vol_ratio > 1.2:
            vol_status = "BUYERS ACTIVE"
        elif price < prev['close'] and vol_ratio > 1.2:
            vol_status = "SELLERS DOMINATING"
        else:
            vol_status = "NEUTRAL"

        # --- Decision Engine ---
        decision = "WAIT"
        if (price <= lower_b or rsi < 35) and price > prev['close']:
            decision = "STRONG BUY"
        elif macd > sig and ma9 > ma21:
            decision = "BUY / HOLD"
        elif rsi > 75 or price >= upper_b:
            decision = "STRONG SELL"
        elif ma9 < ma21 or macd < sig:
            decision = "SELL / AVOID"

        # --- Target & Stop Loss ---
        
        sell_target = round(upper_b, 2) if decision in ["STRONG BUY", "BUY / HOLD"] else round(lower_b, 2)
        stop_loss = round(lower_b, 2) if decision in ["STRONG BUY", "BUY / HOLD"] else round(upper_b, 2)

        # Telegram Alert for strong signals
        if decision in ["STRONG BUY", "STRONG SELL"]:
            alert = f"🚨 {symbol} -> {decision}\n💰 Price: {price}\n🎯 Target: {sell_target}\n📉 SL: {stop_loss}\n📊 Vol: {vol_status}"
            send_telegram_message(alert)

        return {
            "Stock": symbol,
            "Price": price,
            "RSI": round(rsi, 2),
            "Vol_Status": vol_status,
            "Decision": decision,
            "Target": sell_target,
            "StopLoss": stop_loss
        }
    except Exception as e:
        print(f"Error analyzing {symbol}: {e}")
        return None

# --- Main Run ---
print("\nScanning DSE Top 20 Stocks... Please wait.\n")
results = []
for s in stocks:
    analysis = analyze_stock(s)
    if analysis:
        results.append(analysis)
    time.sleep(0.5) 

df_result = pd.DataFrame(results)

# Display Formatting
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 1000)

print("="*100)
print(df_result.to_string(index=False))
print("="*100)

