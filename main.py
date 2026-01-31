import os, telebot, time
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from flask import Flask
from threading import Thread
import google.generativeai as genai

# --- CONFIGURATION IA ---
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-1.5-flash')

def reponse_ia(texte, est_vocal=False, langue=None):
    try:
        prompt = f"Réponds en nouchi : {texte}"
        if est_vocal: prompt = f"Vocal en {langue} reçu. Salue-le en nouchi !"
        return model.generate_content(prompt).text
    except: return "C'est propre ! On est ensemble. 🇨🇮"

# --- CONFIGURATION SERVICES ---
API_TOKEN = os.environ.get('TELE_TOKEN')
FOLDER_ID = os.environ.get('FOLDER_ID')
SERVICE_ACCOUNT_FILE = '/etc/secrets/service_account.json'

app = Flask('')
@app.route('/')
def home(): return "Bot Actif"

bot = telebot.TeleBot(API_TOKEN, threaded=False)
LANGUES = [['Baoulé', 'Dioula', 'Bété'], ['Yacouba', 'Guéré', 'Attié']]

def upload_to_drive(file_path, file_name, langue):
    try:
        creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=['https://www.googleapis.com/auth/drive'])
        service = build('drive', 'v3', credentials=creds)
        meta = {'name': f"{langue}_{file_name}", 'parents': [FOLDER_ID]}
        media = MediaFileUpload(file_path, mimetype='audio/ogg')
        service.files().create(body=meta, media_body=media).execute()
        print(f"✅ ARCHIVE OK")
    except Exception as e: print(f"❌ DRIVE ERROR: {e}")

@bot.message_handler(commands=['start'])
def start(m):
    kb = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    for row in LANGUES: kb.add(*row)
    bot.send_message(m.chat.id, "🇨🇮 **Dialogue Ivoirien AI**\nChoisis une langue !", reply_markup=kb)

@bot.message_handler(func=lambda m: any(m.text in row for row in LANGUES))
def mission(m):
    msg = bot.reply_to(m, f"📍 **{m.text}** : Envoie ton vocal !")
    bot.register_next_step_handler(msg, lambda ms: save_vocal(ms, m.text))

def save_vocal(m, l):
    if m.content_type == 'voice':
        try:
            f_info = bot.get_file(m.voice.file_id)
            data = bot.download_file(f_info.file_path)
            name = f"{l}_{int(time.time())}.ogg"
            with open(name, 'wb') as f: f.write(data)
            upload_to_drive(name, name, l)
            bot.reply_to(m, reponse_ia("", True, l))
            if os.path.exists(name): os.remove(name)
        except Exception as e: print(f"Erreur: {e}")
    else: bot.reply_to(m, reponse_ia(m.text))

@bot.message_handler(func=lambda m: True)
def chat_libre(m):
    bot.reply_to(m, reponse_ia(m.text))

if __name__ == '__main__':
    t = Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000))))
    t.start()
    
    bot.remove_webhook()
    time.sleep(1)
    print("🚀 Bot démarré...")
    bot.infinity_polling(skip_pending=True)
    
