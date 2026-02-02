import os, telebot, time, google.generativeai as genai
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from flask import Flask
from threading import Thread

# --- IA GEMINI ---
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-1.5-flash')

def reponse_ia(texte, est_vocal=False, langue=None):
    try:
        if est_vocal:
            prompt = f"L'utilisateur a envoyé un vocal en {langue}. Salue-le en nouchi et dis-lui que c'est bien archivé pour la Côte d'Ivoire !"
        else:
            prompt = f"Tu es un expert des langues ivoiriennes. Réponds à ceci en expliquant les mots si besoin : {texte}"
        return model.generate_content(prompt).text
    except: return "On est ensemble ! 🇨🇮"

# --- CONFIG ---
API_TOKEN = os.environ.get('TELE_TOKEN')
FOLDER_ID = os.environ.get('FOLDER_ID')
CHAT_ARCHIVE_ID = os.environ.get('CHAT_ARCHIVE_ID')
SERVICE_ACCOUNT_FILE = '/etc/secrets/Archive-bot-dialogue-d1ab608ab4fb.json'

bot = telebot.TeleBot(API_TOKEN, threaded=False)
app = Flask('')

@app.route('/')
def home(): return "Bot Actif"

def upload_to_drive(file_path, file_name, langue):
    try:
        if not os.path.exists(SERVICE_ACCOUNT_FILE): return "Fichier JSON manquant sur Render"
        creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=['https://www.googleapis.com/auth/drive'])
        service = build('drive', 'v3', credentials=creds)
        meta = {'name': f"{langue}_{file_name}", 'parents': [FOLDER_ID]}
        media = MediaFileUpload(file_path, mimetype='audio/ogg')
        service.files().create(body=meta, media_body=media, supportsAllDrives=True).execute()
        return "✅ OK"
    except Exception as e: return f"❌ Erreur: {str(e)}"

@bot.message_handler(commands=['start'])
def start(m):
    kb = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add('Baoulé', 'Dioula', 'Bété', 'Yacouba', 'Guéré', 'Attié', 'Ajoutez votre langue')
    bot.send_message(m.chat.id, "🇨🇮 **Dialogue Ivoirien AI**\nChoisis une langue et envoie ton vocal !", reply_markup=kb)

@bot.message_handler(func=lambda m: m.text in ['Baoulé', 'Dioula', 'Bété', 'Yacouba', 'Guéré', 'Attié'])
def mission(m):
    msg = bot.reply_to(m, f"📍 **{m.text}** : J'attends ton vocal...")
    bot.register_next_step_handler(msg, lambda ms: save_vocal(ms, m.text))

def save_vocal(m, l):
    if m.content_type == 'voice':
        statut = bot.reply_to(m, "🔄 Archivage en cours...")
        try:
            # 1. Archive Telegram
            if CHAT_ARCHIVE_ID and str(CHAT_ARCHIVE_ID) != "0":
                try: bot.forward_message(CHAT_ARCHIVE_ID, m.chat.id, m.message_id)
                except: pass
            
            # 2. Drive
            f_info = bot.get_file(m.voice.file_id)
            data = bot.download_file(f_info.file_path)
            name = f"{l}_{int(time.time())}.ogg"
            with open(name, 'wb') as f: f.write(data)
            
            res_drive = upload_to_drive(name, name, l)
            bot.edit_message_text(f"Détails Drive : {res_drive}", m.chat.id, statut.message_id)
            
            # 3. IA
            bot.reply_to(m, reponse_ia("", True, l))
            if os.path.exists(name): os.remove(name)
        except Exception as e: bot.reply_to(m, f"❌ Erreur : {str(e)}")
    else:
        bot.reply_to(reponse_ia(m.text))

if __name__ == '__main__':
    Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))).start()
    bot.remove_webhook()
    bot.infinity_polling(skip_pending=True)
