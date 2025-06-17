import sys
if sys.version_info >= (3, 13):
    raise RuntimeError("⛔ Python 3.13 detected — imghdr will break telegram bot. Use Python 3.11 instead.")

try:
    import imghdr
except ImportError:
    imghdr = None


import os
import json
import time
import threading
import pandas as pd
from datetime import datetime
from flask import Flask, request
from binance.client import Client
from telegram import Bot, Update
from telegram.ext import Dispatcher, CommandHandler
from dotenv import load_dotenv
import requests

load_dotenv()
BINANCE_API_KEY = os.getenv("BINANCE_API_KEY")
BINANCE_SECRET = os.getenv("BINANCE_SECRET")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

bot = Bot(token=TELEGRAM_TOKEN)
client = Client(BINANCE_API_KEY, BINANCE_SECRET)
app = Flask(__name__)
dispatcher = Dispatcher(bot, None, use_context=True)

STATE_FILE = "state.json"
LOG_FILE = "trades_log.csv"
DAILY_REPORT_HOUR = 22

state = {
    "live": True,
    "paused": False,
    "scalp_active": False,
    "positions": []
}

if os.path.exists(STATE_FILE):
    with open(STATE_FILE, 'r') as f:
        state.update(json.load(f))

def save_state():
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=4)

def send(msg):
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=msg)
        print("Telegram error:", e)

@app.route("/")
def home():
    return "Bot je aktivan!", 200

@app.route("/oraclebot", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return "OK", 200

def start_live(update, context):
    state["live"] = True
    save_state()
    update.message.reply_text("✅ Live režim uključen.")

def pause(update, context):
    state["paused"] = True
    save_state()
    update.message.reply_text("⏸ Bot pauziran.")

def resume(update, context):
    state["paused"] = False
    save_state()
    update.message.reply_text("▶ Bot nastavlja rad.")

def status(update, context):
    update.message.reply_text(f"Live: {state['live']} | Paused: {state['paused']} | Scalping: {state['scalp_active']} | Pozicija: {len(state['positions'])}")

def scalp_on(update, context):
    state["scalp_active"] = True
    save_state()
    update.message.reply_text("⚡ Scalping uključen.")

def scalp_off(update, context):
    state["scalp_active"] = False
    save_state()
    update.message.reply_text("🔕 Scalping isključen.")

def daily_report():
    while True:
        now = datetime.utcnow()
        if now.hour == DAILY_REPORT_HOUR and now.minute < 2:
                if os.path.exists(LOG_FILE):
                    df = pd.read_csv(LOG_FILE)
                    df["timestamp"] = pd.to_datetime(df["timestamp"])
                    df_today = df[df["timestamp"].dt.date == now.date()]
                    profit = df_today["pnl"].sum() if "pnl" in df_today.columns else 0
                    wins = (df_today["pnl"] > 0).sum() if "pnl" in df_today.columns else 0
                    losses = (df_today["pnl"] < 0).sum() if "pnl" in df_today.columns else 0
                    send(f"🧾 Dnevni izveštaj\n📈 Ulaza: {len(df_today)}\n✅ Dobitaka: {wins} ❌ Gubitaka: {losses}\n💰 PnL: {profit:.2f} USDT")
                else:
                    send("🧾 Nema podataka za današnji dan.")
                print("Report error:", e)
    time.sleep(120)
    time.sleep(30)

def keep_alive():
    while True:
            requests.get(WEBHOOK_URL)
            print("Ping error:", e)
    time.sleep(600)

dispatcher.add_handler(CommandHandler("start_live", start_live))
dispatcher.add_handler(CommandHandler("pause", pause))
dispatcher.add_handler(CommandHandler("resume", resume))
dispatcher.add_handler(CommandHandler("status", status))
dispatcher.add_handler(CommandHandler("scalp_on", scalp_on))
dispatcher.add_handler(CommandHandler("scalp_off", scalp_off))

threading.Thread(target=daily_report, daemon=True).start()
threading.Thread(target=keep_alive, daemon=True).start()

if __name__ == "__main__":
    bot.delete_webhook()
    bot.set_webhook(WEBHOOK_URL)
    app.run(host="0.0.0.0", port=443)