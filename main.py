import os
import telebot
import random
import time
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from flask import Flask
from threading import Thread
import google.generativeai as genai

# --- CONFIGURATION IA GEMINI ---
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

def obtenir_reponse_ia(langue, mission):
    prompt = (
        f"Tu es un expert en culture de Côte d'Ivoire. Un utilisateur vient de t'envoyer un vocal en {langue} "
        f"pour la phrase : '{mission}'. Réponds-lui en nouchi ou en français de Moussa. "
        f"Félicite-le chaleureusement et donne-lui une petite anecdote rapide sur la langue {langue}."
    )
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"Erreur Gemini détaillée: {e}")
        return f"C'est propre ! Merci pour ton vocal en {langue}. Ensemble, on protège la racine ! 🇨🇮"

# --- CONFIGURATION GENERALE ---
API_TOKEN = os.environ.get('TELE_TOKEN')
FOLDER_ID = os.environ.get('FOLDER_ID')
ARCHIVE_ID = os.environ.get('ARCHIVE_ID') # Assure-toi que c'est bien mis dans Render
PORT = int(os.environ.get('PORT', 10000))
SERVICE_ACCOUNT_FILE = '/etc/secrets/service_account.json'
SCOPES = ['https://www.googleapis.com/auth/drive']

app = Flask('')

@app.route('/')
def home():
    return "Le Bot Ivoirien est bien réveillé !"

def run_flask():
    app.run(host='0.0.0.0', port=PORT)

def keep_alive():
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()

bot = telebot.TeleBot(API_TOKEN)

MENU_LANGUES = [
    ['Baoulé', 'Dioula', 'Bété'], ['Yacouba', 'Guéré', 'Attié'],
    ['Adioukrou', 'Agni', 'Abidji'], ['Kroumen', 'Gagou', 'Sénoufo'],
    ['Andô', 'Dida', 'Avikam'], ['Tagbanan', 'Wobé', 'Ebrié'],
    ['Toura', 'Odiennka'], ['Ajoutez votre langue ici']
]

MISSIONS = [
    "Comment ça va aujourd'hui ?", "Le repas est prêt, viens manger.",
    "Où se trouve le marché le plus proche ?", "Bonne arrivée chez nous.",
    "Je cherche un taxi pour aller en ville.", "Il faut pardonner, c'est Dieu qui donne.",
    "On dit quoi ? La famille va bien ?", "Le travail finit par payer.",
    "Viens t'asseoir, on va causer."
]

def upload_to_drive(file_path, file_name, langue):
    try:
        if not os.path.exists(SERVICE_ACCOUNT_FILE):
            print(f"❌ Fichier secret introuvable à : {SERVICE_ACCOUNT_FILE}")
            return
        
        creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        service = build('drive', 'v3', credentials=creds)
        
        metadata = {'name': f"{langue}_{file_name}", 'parents': [FOLDER_ID]}
        media = MediaFileUpload(file_path, mimetype='audio/ogg')
        
        # Correction ici : retrait de supportsAllDrives pour plus de compatibilité
        file = service.files().create(body=metadata, media_body=media, fields='id').execute()
        print(f"✅ Drive : Fichier {file.get('id')} envoyé.")
    except Exception as e:
        print(f"⚠️ Erreur Drive : {e}")

@bot.message_handler(commands=['start', 'collecte'])
def start(message):
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    for ligne in MENU_LANGUES:
        markup.add(*ligne)
    bot.send_message(message.chat.id, "🇨🇮 **Archive des Langues Ivoiriennes**\n\nChoisis ta langue pour commencer :", reply_markup=markup, parse_mode='Markdown')

@bot.message_handler(func=lambda m: any(m.text in ligne for ligne in MENU_LANGUES))
def donner_mission(message):
    langue = message.text
    mission = random.choice(MISSIONS)
    msg = bot.reply_to(message, f"📍 **Langue : {langue}**\n\nTa mission : Enregistre ce qui suit :\n👉 *\"{mission}\"*", parse_mode='Markdown')
    bot.register_next_step_handler(msg, lambda m: save_vocal(m, langue, mission))

def save_vocal(message, langue, mission):
    if message.content_type == 'voice':
        try:
            bot.send_chat_action(message.chat.id, 'upload_voice')
            file_info = bot.get_file(message.voice.file_id)
            downloaded = bot.download_file(file_info.file_path)
            
            temp_name = f"{langue}_{int(time.time())}.ogg"
            with open(temp_name, 'wb') as f:
                f.write(downloaded)

            # Archive Telegram
            if ARCHIVE_ID:
                with open(temp_name, 'rb') as voice_file:
                    bot.send_voice(chat_id=ARCHIVE_ID, voice=voice_file, caption=f"🎙 Audio {langue}\n📝 Phrase : {mission}")

            # Envoi Drive
            upload_to_drive(temp_name, temp_name, langue)
            
            # IA Gemini
            reponse_ia = obtenir_reponse_ia(langue, mission)
            bot.reply_to(message, reponse_ia)
            
            if os.path.exists(temp_name):
                os.remove(temp_name)
        except Exception as e:
            print(f"Erreur générale : {e}")
            bot.reply_to(message, "Petit souci technique, mais l'audio est bien reçu !")
    else:
        bot.reply_to(message, "⚠️ Pardon, envoie un message vocal pour la mission.")

if __name__ == '__main__':
    keep_alive()
    print("Bot démarré et prêt !")
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
            
