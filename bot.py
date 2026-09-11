import telebot
import re
import os

TOKEN = os.environ.get("BOT_TOKEN")
OWNER_ID = int(os.environ.get("OWNER_ID", 0))

# Mengaktifkan bot secara agresif
bot = telebot.TeleBot(TOKEN, threaded=False)

# PEMBERSIHAN SEKALI LAGI
try:
    bot.remove_webhook()
    bot.delete_webhook(drop_pending_updates=True)
    print("Jalur Telegram dibersihkan secara total!")
except Exception as e:
    print(f"Error clean: {e}")

group_members = {}       
partner_database = {}    

def record_activity(chat_id, user):
    if user.is_bot:
        return
    if chat_id not in group_members:
        group_members[chat_id] = {}
    group_members[chat_id][user.id] = user.first_name

@bot.message_handler(content_types=['new_chat_members'])
def handle_new_member(message):
    for member in message.new_chat_members:
        record_activity(message.chat.id, member)

@bot.message_handler(func=lambda message: message.chat.type != "private", content_types=['text', 'photo', 'video', 'sticker'])
def track_active_members(message):
    record_activity(message.chat.id, message.from_user)

# ==================== PERINTAH UTAMA (PASTI DIRESPOND TELEGRAM) ====================

@bot.message_handler(commands=['start'])
def send_welcome(message):
    teks = (
        "👋 **Bot Tagall Broadcast Aktif!**\n\n"
        "**Cara Kirim Broadcast Tagall:**\n"
        "Ketik kata-kata Anda langsung di chat ini dan **wajib masukkan link grup partner**.\n\n"
        "Atau jika teks biasa tidak merespon, gunakan perintah:\n"
        "`/broadcast kata-kata Anda beserta https://t.me`"
    )
    bot.reply_to(message, teks, parse_mode="Markdown")

@bot.message_handler(commands=['addpartner'])
def add_partner_link(message):
    if message.from_user.id != OWNER_ID:
        bot.reply_to(message, "❌ Hanya untuk Owner Bot!")
        return
    command_parts = message.text.split(" ", 1)
    if len(command_parts) < 2:
        bot.reply_to(message, "💡 **Cara pakai:** `/addpartner [LINK_GRUP]`")
        return
    link_target = command_parts[1].strip()
    if not group_members:
        bot.reply_to(message, "❌ **Gagal Mendaftar!** Bot belum merekam aktivitas grup aktif.\n\nKetik sepatah kata dulu di grup Anda!")
        return
    last_active_chat_id = list(group_members.keys())[-1]
    partner_database[link_target] = last_active_chat_id
    bot.reply_to(message, f"✅ **Link Sukses Terdaftar!**\n🔗 {link_target}")

@bot.message_handler(commands=['listpartner'])
def list_partner_links(message):
    if message.from_user.id != OWNER_ID:
        return
    if not partner_database:
        bot.reply_to(message, "ℹ️ Belum ada link terdaftar.")
        return
    teks = "📋 **Daftar Link Terdaftar:**\n\n"
    for idx, link in enumerate(partner_database.keys(), 1):
        teks += f"{idx}. {link}\n"
    bot.reply_to(message, teks)

# ==================== PROSES SIARAN (DUA JALUR: TEKS BIASA & COMMAND) ====================

def proses_tagall(message, teks_sumber):
    links_found = re.findall(r'(https?://[^\s]+)', teks_sumber)
    target_chat_id = None
    for link in links_found:
        if link in partner_database:
            target_chat_id = partner_database[link]
            break
            
    if not target_chat_id:
        bot.reply_to(message, "❌ **Ditolak!** Wajib menyertakan link grup partner yang terdaftar!")
        return

    bot.reply_to(message, "🔄 Mengirim tagall emoji ke grup...")
    mentions = f"📢 **PENGUMUMAN BARU**\n\n{teks_sumber}\n\n"
    count = 0
    
    for user_id in group_members[target_chat_id].keys():
        mentions += f"[👤](tg://user?id={user_id}) "
        count += 1
        if count % 10 == 0:
            try:
                bot.send_message(target_chat_id, mentions, parse_mode="Markdown", disable_web_page_preview=False)
            except Exception:
                pass
            mentions = f"📢 **PENGUMUMAN BARU (Lanjutan)**\n\n"
            
    if count % 10 != 0:
        try:
            bot.send_message(target_chat_id, mentions, parse_mode="Markdown", disable_web_page_preview=False)
        except Exception:
            pass
    bot.reply_to(message, f"✅ Sukses melakukan tagall!")

# Jalur Alternatif 1: Menggunakan awalan /broadcast
@bot.message_handler(commands=['broadcast'])
def handle_command_broadcast(message):
    command_parts = message.text.split(" ", 1)
    if len(command_parts) < 2:
        bot.reply_to(message, "💡 Format salah. Gunakan `/broadcast teks Anda beserta link`")
        return
    proses_tagall(message, command_parts[1].strip())

# Jalur Alternatif 2: Menggunakan teks biasa di PM
@bot.message_handler(func=lambda message: message.chat.type == "private", content_types=['text'])
def handle_pm_text_broadcast(message):
    if message.text.startswith('/'):
        return
    proses_tagall(message, message.text)

print("Bot Tagall Aktif di Railway...")
bot.infinity_polling()

