import os, telebot, time
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
        prompt = f"Un utilisateur a envoyé un vocal en {langue}. Félicite-le chaleureusement en nouchi (ivoirien) et donne une info culturelle rapide sur cette langue."
    else:
        prompt = f"Tu es un expert des langues de Côte d'Ivoire. Réponds à cette question en nouchi (ivoirien) : {texte_utilisateur}"
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"Erreur Gemini: {e}")
        return "C'est propre ! On est ensemble pour la culture. 🇨🇮"

# --- CONFIGURATION DES IDS ET TOKENS ---
API_TOKEN = os.environ.get('TELE_TOKEN')
FOLDER_ID = os.environ.get('FOLDER_ID')
CHAT_ARCHIVE_ID = os.environ.get('CHAT_ARCHIVE_ID') # Ton fameux code -100
SERVICE_ACCOUNT_FILE = '/etc/secrets/service_account.json'

app = Flask('')
@app.route('/')
def home(): return "Bot en ligne !"

bot = telebot.TeleBot(API_TOKEN, threaded=False)
LANGUES = [['Baoulé', 'Dioula', 'Bété'], ['Yacouba', 'Guéré', 'Attié']]

def upload_to_drive(file_path, file_name, langue):
    try:
        if not os.path.exists(SERVICE_ACCOUNT_FILE):
            print("❌ Erreur : Fichier service_account.json manquant")
            return
        creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=['https://www.googleapis.com/auth/drive'])
        service = build('drive', 'v3', credentials=creds)
        meta = {'name': f"{langue}_{file_name}", 'parents': [FOLDER_ID]}
        media = MediaFileUpload(file_path, mimetype='audio/ogg')
        service.files().create(body=meta, media_body=media).execute()
        print(f"✅ DRIVE OK : {file_name}")
    except Exception as e: 
        print(f"❌ DRIVE ERREUR : {e}")

@bot.message_handler(commands=['start'])
def start(m):
    kb = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    for row in LANGUES: kb.add(*row)
    text = "🇨🇮 **Dialogue Ivoirien AI V2**\n\nChoisis une langue pour envoyer un vocal ou pose-moi une question sur une ethnie !"
    bot.send_message(m.chat.id, text, reply_markup=kb, parse_mode='Markdown')

@bot.message_handler(func=lambda m: any(m.text in row for row in LANGUES))
def mission(m):
    l = m.text
    msg = bot.reply_to(m, f"📍 **Langue choisie : {l}**\nEnvoie ton vocal maintenant, je l'archive tout de suite !")
    bot.register_next_step_handler(msg, lambda ms: save_vocal(ms, l))

def save_vocal(m, l):
    if m.content_type == 'voice':
        try:
            # 1. Archive Telegram (le fameux groupe -100)
            if CHAT_ARCHIVE_ID:
                bot.forward_message(CHAT_ARCHIVE_ID, m.chat.id, m.message_id)
            
            # 2. Téléchargement du vocal
            f_info = bot.get_file(m.voice.file_id)
            data = bot.download_file(f_info.file_path)
            name = f"{l}_{int(time.time())}.ogg"
            with open(name, 'wb') as f: f.write(data)
            
            # 3. Archive Google Drive
            upload_to_drive(name, name, l)
            
            # 4. Réponse de l'IA
            bot.reply_to(m, reponse_ia_ivoirienne("", True, l))
            
            if os.path.exists(name): os.remove(name)
        except Exception as e:
            print(f"Erreur : {e}")
            bot.reply_to(m, "Vocal bien reçu et archivé ! 🇨🇮")
    else:
        bot.reply_to(m, reponse_ia_ivoirienne(m.text))

@bot.message_handler(func=lambda m: True)
def chat_libre(m):
    bot.reply_to(m, reponse_ia_ivoirienne(m.text))

if __name__ == '__main__':
    # Le skip_pending=True permet au bot d'ignorer les messages envoyés 
    # pendant qu'il était déconnecté, ce qui évite de saturer la connexion au démarrage.
    bot.infinity_polling(skip_pending=True)
    
