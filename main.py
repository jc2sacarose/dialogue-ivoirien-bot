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

def reponse_ia(texte):
    try:
        # Prompt simplifié pour éviter les refus de l'IA
        prompt = f"Réponds en français ivoirien court à : {texte}"
        return model.generate_content(prompt).text
    except:
        return "C'est propre ! On est ensemble. 🇨🇮"

# --- CONFIG ---
API_TOKEN = os.environ.get('TELE_TOKEN')
FOLDER_ID = os.environ.get('FOLDER_ID')
SERVICE_ACCOUNT_FILE = '/etc/secrets/service_account.json'

app = Flask('')
@app.route('/')
def home(): return "Bot Actif"

bot = telebot.TeleBot(API_TOKEN)
LANGUES = [['Baoulé', 'Dioula', 'Bété'], ['Yacouba', 'Guéré', 'Attié']]

def upload_to_drive(file_path, file_name, langue):
    try:
        creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=['https://www.googleapis.com/auth/drive'])
        service = build('drive', 'v3', credentials=creds)
        meta = {'name': f"{langue}_{file_name}", 'parents': [FOLDER_ID]}
        media = MediaFileUpload(file_path, mimetype='audio/ogg')
        service.files().create(body=meta, media_body=media).execute()
        print("✅ Drive OK")
    except Exception as e:
        print(f"❌ Erreur Drive : {e}")

@bot.message_handler(commands=['start'])
def start(m):
    kb = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    for row in LANGUES: kb.add(*row)
    bot.send_message(m.chat.id, "Pose ta question ou choisis une langue :", reply_markup=kb)

@bot.message_handler(func=lambda m: any(m.text in row for row in LANGUES))
def mission(m):
    l = m.text
    msg = bot.reply_to(m, f"Envoie ton vocal en {l} !")
    bot.register_next_step_handler(msg, lambda ms: save_vocal(ms, l))

def save_vocal(m, l):
    if m.content_type == 'voice':
        f_info = bot.get_file(m.voice.file_id)
        data = bot.download_file(f_info.file_path)
        name = f"{l}_{int(time.time())}.ogg"
        with open(name, 'wb') as f: f.write(data)
        upload_to_drive(name, name, l)
        bot.reply_to(m, "Vocal archivé ! 🇨🇮")
        os.remove(name)
    else:
        bot.reply_to(m, reponse_ia(m.text))

@bot.message_handler(func=lambda m: True)
def chat(m):
    bot.reply_to(m, reponse_ia(m.text))

if __name__ == '__main__':
    Thread(target=lambda: app.run(host='0.0.0.0', port=10000)).start()
    # LE SECRET : skip_pending=True nettoie les erreurs 409
    bot.infinity_polling(skip_pending=True)
