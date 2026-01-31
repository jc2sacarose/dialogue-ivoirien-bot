import os, telebot, time
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from flask import Flask
from threading import Thread
import google.generativeai as genai

# --- IA GEMINI ---
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-1.5-flash')

def reponse_ia(texte, est_vocal=False, langue=None):
    try:
        if est_vocal:
            prompt = f"Un utilisateur a envoyé un vocal en {langue}. Salue-le en nouchi et dis-lui que c'est archivé."
        else:
            prompt = f"Réponds en nouchi ivoirien : {texte}"
        response = model.generate_content(prompt)
        return response.text
    except:
        return "C'est propre ! On est ensemble pour la culture. 🇨🇮"

# --- CONFIGURATION SERVICES ---
API_TOKEN = os.environ.get('TELE_TOKEN')
FOLDER_ID = os.environ.get('FOLDER_ID')
CHAT_ARCHIVE_ID = os.environ.get('CHAT_ARCHIVE_ID')
# Chemin vers ton fichier JSON secret sur Render
SERVICE_ACCOUNT_FILE = '/etc/secrets/Archive-bot-dialogue-d1ab608ab4fb.json'

app = Flask('')
@app.route('/')
def home(): return "Bot Actif"

bot = telebot.TeleBot(API_TOKEN, threaded=False)
LANGUES = [['Baoulé', 'Dioula', 'Bété'], ['Yacouba', 'Guéré', 'Attié']]

def upload_to_drive(file_path, file_name, langue):
    try:
        if not os.path.exists(SERVICE_ACCOUNT_FILE):
            return "Fichier JSON introuvable sur Render"
        creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=['https://www.googleapis.com/auth/drive'])
        service = build('drive', 'v3', credentials=creds)
        meta = {'name': f"{langue}_{file_name}", 'parents': [FOLDER_ID]}
        media = MediaFileUpload(file_path, mimetype='audio/ogg')
        service.files().create(body=meta, media_body=media).execute()
        return "OK"
    except Exception as e:
        return str(e)

@bot.message_handler(commands=['start'])
def start(m):
    kb = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    for row in LANGUES: kb.add(*row)
    bot.send_message(m.chat.id, "🇨🇮 **Archiveur Ivoirien**\nChoisis une langue et envoie ton vocal !", reply_markup=kb)

@bot.message_handler(func=lambda m: any(m.text in row for row in LANGUES))
def mission(m):
    msg = bot.reply_to(m, f"📍 **{m.text}** : J'attends ton vocal...")
    bot.register_next_step_handler(msg, lambda ms: save_vocal(ms, m.text))

def save_vocal(m, l):
    if m.content_type == 'voice':
        statut = bot.reply_to(m, "🔄 En cours d'archivage...")
        try:
            # 1. Archive Telegram
            if CHAT_ARCHIVE_ID:
                bot.forward_message(CHAT_ARCHIVE_ID, m.chat.id, m.message_id)
            
            # 2. Téléchargement temporaire
            f_info = bot.get_file(m.voice.file_id)
            data = bot.download_file(f_info.file_path)
            name = f"{l}_{int(time.time())}.ogg"
            with open(name, 'wb') as f:
                f.write(data)
            
            # 3. Archive Drive
            result_drive = upload_to_drive(name, name, l)
            
            if result_drive == "OK":
                bot.edit_message_text("✅ Archivé sur Drive et Telegram !", m.chat.id, statut.message_id)
            else:
                bot.edit_message_text(f"⚠️ Telegram OK, mais Drive Erreur : {result_drive}", m.chat.id, statut.message_id)
            
            # 4. Réponse IA
            bot.reply_to(m, reponse_ia("", True, l))
            
            if os.path.exists(name): os.remove(name)
        except Exception as e:
            bot.edit_message_text(f"❌ Erreur critique : {str(e)}", m.chat.id, statut.message_id)
    else:
        bot.reply_to(m, reponse_ia(m.text))

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    Thread(target=lambda: app.run(host='0.0.0.0', port=port)).start()
    bot.remove_webhook()
    print("🚀 Le Bot est lancé...")
    bot.infinity_polling(skip_pending=True)
