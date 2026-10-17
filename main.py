import os
import subprocess
import telebot

# التوكن والآيدي الخاص بك مباشرة
TOKEN = "8700445121:AAEe49qNIV_uh3atuSaqt4EXv8RrhVZskE4"
ADMIN_CHAT_ID = 8134363644

bot = telebot.TeleBot(TOKEN)


@bot.message_handler(commands=["start"])
def send_welcome(message):
  if message.from_user.id != ADMIN_CHAT_ID:
    bot.reply_to(message, "⚠️ عذراً، هذا البوت خاص ولا يمكنك استخدامه.")
    return
  bot.reply_to(
      message,
      "☁️ أهلاً بك! البوت يعمل الآن على الاستضافة السحابية بنجاح.\nيمكنك"
      " إرسال أي أمر للتحكم بالسيرفر.",
  )


@bot.message_handler(func=lambda message: True)
def execute_command(message):
  if message.from_user.id != ADMIN_CHAT_ID:
    return

  command = message.text

  try:
    # تنفيذ الأمر في شل السيرفر
    result = subprocess.run(
        command, shell=True, capture_output=True, text=True, timeout=120
    )
    output = result.stdout + result.stderr

    if not output.strip():
      output = "✅ تم تنفيذ الأمر بنجاح (لا توجد مخرجات)."

    # تقسيم الرسالة إذا تجاوزت الحد الأقصى للتليجرام
    if len(output) > 4000:
      for x in range(0, len(output), 4000):
        bot.send_message(message.chat.id, output[x : x + 4000])
    else:
      bot.send_message(
          message.chat.id, f"```bash\n{output}\n```", parse_mode="Markdown"
      )

  except Exception as e:
    bot.send_message(
        message.chat.id, f"❌ حدث خطأ:\n`{str(e)}`", parse_mode="Markdown"
    )


if __name__ == "__main__":
  print("[*] Cloud Bot is running...")
  bot.infinity_polling()

