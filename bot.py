import telebot
import re
import os

# Mengambil kredensial secara aman dari sistem Environment Variables di Railway
TOKEN = os.environ.get("BOT_TOKEN")
OWNER_ID = int(os.environ.get("OWNER_ID", 0))

bot = telebot.TeleBot(TOKEN, threaded=False)

# Database sederhana dalam memori
group_members = {}       # Menyimpan data anggota aktif per grup
partner_database = {}    # Menyimpan data: {LINK_GRUP: CHAT_ID_GRUP}

# Fungsi otomatis mencatat ID Grup dan Anggotanya saat ada aktivitas
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

@bot.message_handler(func=lambda message: True, content_types=['text', 'photo', 'video', 'sticker'])
def track_active_members(message):
    if message.chat.type != "private":
        # Otomatis merekam ID Grup secara diam-diam saat grup aktif
        record_activity(message.chat.id, message.from_user)

# ==================== MANAGEMEN PARTNER (DI PM OWNER) ====================

# Cara pakai di PM Owner: /addpartner https://t.me
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
    
    # Cari ID Grup yang aktif terakhir kali dari database sementara
    if not group_members:
        bot.reply_to(message, "❌ **Gagal Mendaftar!** Bot belum merekam grup aktif apa pun.\n\n"
                              "Silakan ketik teks apa saja di dalam grup Anda terlebih dahulu agar bot mengenali grupnya!")
        return
        
    last_active_chat_id = list(group_members.keys())[-1]
    partner_database[link_target] = last_active_chat_id
    bot.reply_to(message, f"✅ **Link Sukses Terdaftar!**\n🔗 {link_target}")

# Cara pakai di PM Owner: /delpartner https://t.me
@bot.message_handler(commands=['delpartner'])
def remove_partner_link(message):
    if message.from_user.id != OWNER_ID:
        return
    command_parts = message.text.split(" ", 1)
    if len(command_parts) >= 2:
        link_target = command_parts[1].strip()
        if link_target in partner_database:
            del partner_database[link_target]
            bot.reply_to(message, "⚠️ Link partner berhasil dihapus.")
            return
    bot.reply_to(message, "❌ Link tidak ditemukan.")

# Melihat daftar link yang terdaftar lewat PM Owner: /listpartner
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

# ==================== PROSES SIARAN PM (VERIFIKASI LINK + EMOJI) ====================

@bot.message_handler(commands=['start'])
def send_welcome(message):
    if message.chat.type == "private":
        teks = (
            "👋 **Selamat datang di Bot Tagall Broadcast!**\n\n"
            "Silakan kirimkan kata-kata Anda **wajib menyertakan link grup partner** yang valid di dalam pesannya.\n\n"
            "⚠️ Jika link grup salah atau tidak terdaftar, permintaan broadcast akan otomatis ditolak!"
        )
        bot.reply_to(message, teks, parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.chat.type == "private", content_types=['text'])
def handle_pm_broadcast(message):
    if message.text.startswith('/'):
        return

    pesan_user = message.text
    
    # Mencari apakah ada teks berformat link di dalam pesan user
    links_found = re.findall(r'(https?://[^\s]+)', pesan_user)
    
    target_chat_id = None
    for link in links_found:
        if link in partner_database:
            target_chat_id = partner_database[link]
            break
            
    if not target_chat_id:
        bot.reply_to(message, "❌ **Ditolak!** Teks Anda wajib menyertakan link grup partner yang sudah terdaftar!")
        return

    bot.reply_to(message, "🔄 Link cocok! Mengirim tagall emoji ke grup...")

    mentions = f"📢 **PENGUMUMAN BARU**\n\n{pesan_user}\n\n"
    count = 0
    
    # Ambil data anggota grup tujuan
    for user_id in group_members[target_chat_id].keys():
        mentions += f"[👤](tg://user?id={user_id}) "
        count += 1
        
        # Kirim per 10 emoji agar chat grup tetap rapi
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

    bot.reply_to(message, f"✅ Sukses melakukan tagall ke grup partner!")

# Otomatis menghapus antrean pesan sampah saat bot dinyalakan ulang
bot.delete_webhook(drop_pending_updates=True)

print("Bot Tagall Jarak Jauh siap berjalan di Railway...")
bot.infinity_polling()
