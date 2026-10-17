from datetime import datetime
import os
import re
import socket
import subprocess
import telebot

# التوكن والآيدي الخاص بك مباشرة
TOKEN = "8700445121:AAEe49qNIV_uh3atuSaqt4EXv8RrhVZskE4"
ADMIN_CHAT_ID = 8134363644

bot = telebot.TeleBot(TOKEN)


def get_connection_type():
  """دالة لمعرفة هل الجهاز متصل بـ Wi-Fi أو بيانات خلوية واسم الشبكة/الشركة"""
  try:
    # محاولة فحص الاتصال عبر أدوات Linux القياسية (nmcli / iwgetid)
    # فحص الواي فاي أولاً
    wifi_name = subprocess.check_output(
        "iwgetid -r 2>/dev/null || nmcli -t -f active,ssid dev wifi | grep '^yes' | cut -d: -f2",
        shell=True,
    ).decode("utf-8").strip()

    if wifi_name:
      return f"📶 واي فاي (Wi-Fi): `{wifi_name}`"

    # فحص إذا كان هناك واجهة بيانات خلوية (rmnet, ppp0, wwan)
    interfaces = subprocess.check_output(
        "ip route show | grep default", shell=True
    ).decode("utf-8")
    if "wwan" in interfaces or "rmnet" in interfaces or "ppp" in interfaces:
      # محاولة جلب اسم مشغل البيانات إن أمكن
      operator = subprocess.check_output(
          "mmcli -m 2>/dev/null | grep 'operator name' | awk -F': ' '{print $2}'",
          shell=True,
      ).decode("utf-8").strip()
      op_name = f" ({operator})" if operator else ""
      return f"📱 بيانات الهاتف (Cellular){op_name}"

    return "🌐 اتصال سلكي / شبكة عامة (Ethernet/Other)"
  except Exception:
    return "🌐 غير قادر على تحديد نوع الشبكة بدقة"


def get_network_info():
  """دالة لاستخراج عنوان IP و MAC Address والشبكة الوقت"""
  # الحصول على IP الداخلي
  try:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    local_ip = s.getsockname()[0]
    s.close()
  except Exception:
    local_ip = "غير معروف"

  # الحصول على IP الخارجي
  try:
    public_ip = (
        subprocess.check_output(
            "curl -s --max-time 3 https://api.ipify.org || wget -qO- --timeout=3 https://api.ipify.org",
            shell=True,
        )
        .decode("utf-8")
        .strip()
    )
    if not public_ip:
      public_ip = "غير معروف"
  except Exception:
    public_ip = "غير معروف"

  # الحصول على MAC Address
  try:
    mac_output = subprocess.check_output(
        "ip link || ifconfig", shell=True
    ).decode("utf-8")
    mac_addresses = re.findall(
        r"(?:[0-9a-fA-F]{2}[:-]){5}[0-9a-fA-F]{2}", mac_output
    )
    # تصفية الـ MAC الوهمي المتكرر إن وجد
    unique_macs = [
        m for m in set(mac_addresses) if not m.startswith("00:00:00")
    ]
    mac_str = (
        "\n".join([f"`{mac}`" for mac in unique_macs])
        if unique_macs
        else "لم يتم العثور عليه"
    )
  except Exception:
    mac_str = "غير معروف"

  # الوقت والتاريخ الحالي
  current_time = datetime.now().strftime("%Y-%m-%d | %I:%M:%S %p")

  # نوع الاتصال والشبكة
  connection_info = get_connection_type()

  return (
      f"⏰ **الوقت الحالي:** `{current_time}`\n"
      f"🌐 **IP الداخلي:** `{local_ip}`\n"
      f"🌍 **IP الخارجي:** `{public_ip}`\n"
      f"📌 **الـ MAC Address:**\n{mac_str}\n"
      f"📡 **حالة الاتصال:** {connection_info}"
  )


def initial_setup():
  print("[*] جاري تحديث الحزم وتثبيت الأدوات اللازمة في الخلفية...")
  try:
    subprocess.run(
        "apt update && apt install wget git curl wireless-tools -y",
        shell=True,
        check=True,
    )
    print("[!] تم التحديث والتثبيت بنجاح.")
  except Exception as e:
    print(f"[-] ملاحظة أثناء التحديث التلقائي: {e}")


@bot.message_handler(commands=["start", "info"])
def send_welcome(message):
  if message.from_user.id != ADMIN_CHAT_ID:
    bot.reply_to(message, "⚠️ عذراً، هذا البوت خاص ولا يمكنك استخدامه.")
    return

  current_dir = os.getcwd()
  net_info = get_network_info()

  msg_text = (
      f"👋 **مرحباً بك!**\n\n"
      f"{net_info}\n\n"
      f"📁 **المسار الحالي:**\n`{current_dir}`\n\n"
      f"💡 *يمكنك إرسال أي أمر تيرمنال للتحكم بالسيرفر مباشرة.*"
  )

  bot.reply_to(message, msg_text, parse_mode="Markdown")


@bot.message_handler(func=lambda message: True)
def execute_command(message):
  if message.from_user.id != ADMIN_CHAT_ID:
    return

  command = message.text.strip()

  try:
    # دعم أمر الانتقال بين المجلدات (cd)
    if command.startswith("cd "):
      new_dir = command[3:].strip()
      os.chdir(new_dir)
      current_dir = os.getcwd()
      bot.send_message(
          message.chat.id,
          f"📁 تم تغيير المسار إلى:\n`{current_dir}`",
          parse_mode="Markdown",
      )
      return

    # تنفيذ الأوامر في شل السيرفر
    result = subprocess.run(
        command, shell=True, capture_output=True, text=True, timeout=120
    )
    output = result.stdout + result.stderr

    if not output.strip():
      output = "✅ تم تنفيذ الأمر بنجاح (لا توجد مخرجات)."

    # تقسيم الرسالة إذا تجاوزت الحد الأقصى للتليجرام (4000 حرف)
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


if __name__ == "__main__":
  initial_setup()
  print("[*] Cloud Bot is running...")
  bot.infinity_polling()
