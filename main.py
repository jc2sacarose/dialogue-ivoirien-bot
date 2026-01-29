import os, telebot, random, time
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from flask import Flask
from threading import Thread
import google.generativeai as genai

# CONFIG IA
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

def obtenir_reponse_ia(langue, mission):
    try:
        p = f"Expert Côte d'Ivoire. Félicite en nouchi pour un vocal en {langue} sur '{mission}'."
        return model.generate_content(p).text
    except:
        return f"C'est propre ! Merci pour ton vocal en {langue} ! 🇨🇮"

# CONFIG GENERALE
API_TOKEN = os.environ.get('TELE_TOKEN')
FOLDER_ID = os.environ.get('FOLDER_ID')
ARCHIVE_ID = os.environ.get('ARCHIVE_GROUP_ID')
SERVICE_ACCOUNT_FILE = '/etc/secrets/service_account.json'
SCOPES = ['https://www.googleapis.com/auth/drive']

app = Flask('')
@app.route('/')
def home(): return "Bot Live"

bot = telebot.TeleBot(API_TOKEN, threaded=False)

LANGUES = [['Baoulé', 'Dioula', 'Bété'], ['Yacouba', 'Guéré', 'Attié']]
MISSIONS = ["Comment ça va ?", "Le repas est prêt.", "Bonne arrivée."]

def upload_to_drive(file_path, file_name, langue):
    try:
        if not os.path.exists(SERVICE_ACCOUNT_FILE):
            print("❌ Erreur : Fichier JSON introuvable")
            return
        creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        service = build('drive', 'v3', credentials=creds)
        meta = {'name': f"{langue}_{file_name}", 'parents': [FOLDER_ID]}
        media = MediaFileUpload(file_path, mimetype='audio/ogg')
        service.files().create(body=meta, media_body=media).execute()
        print(f"✅ Drive Succès : {langue}")
    except Exception as e:
        print(f"⚠️ Erreur Drive : {e}")

@bot.message_handler(commands=['start'])
def start(m):
    kb = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    for l in LANGUES: kb.add(*l)
    bot.send_message(m.chat.id, "Choisis ta langue :", reply_markup=kb)

@bot.message_handler(func=lambda m: any(m.text in l for l in LANGUES))
def mission(m):
    l = m.text
    txt = random.choice(MISSIONS)
    msg = bot.reply_to(m, f"Langue : {l}\nMission : {txt}")
    bot.register_next_step_handler(msg, lambda ms: save_vocal(ms, l, txt))

def save_vocal(m, l, txt):
    if m.content_type == 'voice':
        try:
            f_info = bot.get_file(m.voice.file_id)
            data = bot.download_file(f_info.file_path)
            name = f"{l}_{int(time.time())}.ogg"
            with open(name, 'wb') as f: f.write(data)
            if ARCHIVE_ID:
                with open(name, 'rb') as vf: bot.send_voice(ARCHIVE_ID, vf, caption=f"{l} | {txt}")
            upload_to_drive(name, name, l)
            bot.reply_to(m, obtenir_reponse_ia(l, txt))
            if os.path.exists(name): os.remove(name)
        except Exception as e: print(f"Erreur : {e}")

if __name__ == '__main__':
    Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))).start()
    bot.infinity_polling(skip_pending=True)
    
