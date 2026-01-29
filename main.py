import os, telebot, random, time
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from flask import Flask
from threading import Thread
import google.generativeai as genai

# --- CONFIGURATION IA GEMINI ---
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-1.5-flash')

def reponse_ia_ivoirienne(texte_utilisateur, est_vocal=False, langue=None):
    if est_vocal:
        prompt = f"L'utilisateur a envoyé un vocal en {langue}. Félicite-le en nouchi et donne une info culturelle sur cette langue."
    else:
        prompt = f"Tu es un expert des langues de Côte d'Ivoire. Réponds à cette question en nouchi/français ivoirien : {texte_utilisateur}"
    
    try:
        return model.generate_content(prompt).text
    except:
        return "Désolé mon frère, mon réseau a déconné. Mais on est ensemble ! 🇨🇮"

# --- CONFIGURATION GENERALE ---
API_TOKEN = os.environ.get('TELE_TOKEN')
FOLDER_ID = os.environ.get('FOLDER_ID')
SERVICE_ACCOUNT_FILE = '/etc/secrets/service_account.json'

app = Flask('')
@app.route('/')
def home(): return "Bot Ivoirien 2.0 Connecté"

bot = telebot.TeleBot(API_TOKEN, threaded=False)
LANGUES = [['Baoulé', 'Dioula', 'Bété'], ['Yacouba', 'Guéré', 'Attié']]

def upload_to_drive(file_path, file_name, langue):
    try:
        creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=['https://www.googleapis.com/auth/drive'])
        service = build('drive', 'v3', credentials=creds)
        meta = {'name': f"{langue}_{file_name}", 'parents': [FOLDER_ID]}
        media = MediaFileUpload(file_path, mimetype='audio/ogg')
        service.files().create(body=meta, media_body=media).execute()
        print(f"✅ DRIVE OK")
    except Exception as e: print(f"❌ DRIVE ERREUR : {e}")

@bot.message_handler(commands=['start'])
def start(m):
    kb = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    for row in LANGUES: kb.add(*row)
    bot.send_message(m.chat.id, "🇨🇮 **Bot Ivoirien V2**\n\nChoisis une langue pour une mission, ou pose-moi une question directement (ex: 'Comment on dit merci en baoulé ?') !", reply_markup=kb, parse_mode='Markdown')

@bot.message_handler(func=lambda m: any(m.text in row for row in LANGUES))
def mission(m):
    l = m.text
    msg = bot.reply_to(m, f"📍 **Langue : {l}**\nEnvoie un vocal pour que je l'archive sur le Drive !")
    bot.register_next_step_handler(msg, lambda ms: save_vocal(ms, l))

def save_vocal(m, l):
    if m.content_type == 'voice':
        try:
            f_info = bot.get_file(m.voice.file_id)
            data = bot.download_file(f_info.file_path)
            name = f"{l}_{int(time.time())}.ogg"
            with open(name, 'wb') as f: f.write(data)
            upload_to_drive(name, name, l)
            bot.reply_to(m, reponse_ia_ivoirienne("", True, l))
            if os.path.exists(name): os.remove(name)
        except: bot.reply_to(m, "Audio reçu ! 🇨🇮")
    else:
        bot.reply_to(m, reponse_ia_ivoirienne(m.text))

@bot.message_handler(func=lambda m: True)
def chat_libre(m):
    bot.reply_to(m, reponse_ia_ivoirienne(m.text))

if __name__ == '__main__':
    Thread(target=lambda: app.run(host='0.0.0.0', port=10000)).start()
    bot.infinity_polling(skip_pending=True)
