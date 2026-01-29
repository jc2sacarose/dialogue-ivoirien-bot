import os, telebot, random, time
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from flask import Flask
from threading import Thread
import google.generativeai as genai

# --- CONFIGURATION IA GEMINI ---
# On s'assure que la clé est bien lue
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-1.5-flash')

def reponse_ia_ivoirienne(texte_utilisateur, est_vocal=False, langue=None):
    if est_vocal:
        prompt = f"Un utilisateur a envoyé un vocal en {langue}. Félicite-le chaleureusement en nouchi (ivoirien) et donne une info culturelle rapide sur cette ethnie."
    else:
        prompt = f"Tu es un expert des langues de Côte d'Ivoire. Réponds à cette question en nouchi/français ivoirien de manière courte : {texte_utilisateur}"
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"Erreur Gemini: {e}")
        return "C'est propre ! On est ensemble pour la culture. 🇨🇮"

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
    except Exception as e: 
        print(f"❌ DRIVE ERREUR : {e}")

@bot.message_handler(commands=['start'])
def start(m):
    kb = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    for row in LANGUES: kb.add(*row)
    text = "🇨🇮 **Bot Ivoirien V2**\n\nPose-moi une question (ex: 'Manger en Yacouba') ou choisis une langue pour envoyer un vocal !"
    bot.send_message(m.chat.id, text, reply_markup=kb, parse_mode='Markdown')

@bot.message_handler(func=lambda m: any(m.text in row for row in LANGUES))
def mission(m):
    l = m.text
    msg = bot.reply_to(m, f"📍 **Langue : {l}**\nEnvoie ton vocal maintenant pour l'archive !")
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
        except: 
            bot.reply_to(m, "Vocal reçu et archivé ! 🇨🇮")
    else:
        bot.reply_to(m, reponse_ia_ivoirienne(m.text))

@bot.message_handler(func=lambda m: True)
def chat_libre(m):
    # Cette fonction permet de répondre à "Comment on dit manger en Yacouba ?"
    bot.reply_to(m, reponse_ia_ivoirienne(m.text))

if __name__ == '__main__':
    t = Thread(target=lambda: app.run(host='0.0.0.0', port=10000))
    t.start()
    bot.infinity_polling(skip_pending=True)
