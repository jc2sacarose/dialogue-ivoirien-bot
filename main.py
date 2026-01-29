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
        print(f"Erreur Gemini : {e}")
        return f"C'est propre ! Merci pour ton vocal en {langue}. Ensemble, on protège la racine ! 🇨🇮"

# --- CONFIGURATION GENERALE ---
API_TOKEN = os.environ.get('TELE_TOKEN')
FOLDER_ID = os.environ.get('FOLDER_ID')
ARCHIVE_ID = os.environ.get('ARCHIVE_GROUP_ID')
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

bot = telebot.TeleBot(API_TOKEN, threaded=False)

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
            print("❌ Secret JSON manquant sur Render")
            return
        
        creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        service = build('drive', 'v3', credentials=creds)
        
        metadata = {'name': f"{langue}_{file_name}", 'parents': [FOLDER_ID]}
        media = MediaFileUpload(file_path, mimetype='audio/ogg', resumable=True)
        
        print(f"📡 Tentative d'envoi Drive : {file_name}")
        file = service.files().create(body=metadata, media_body=media, fields='id').execute()
        print(f"✅ Drive Succès ID: {file.get('id')}")
    except Exception as e:
        print(f"⚠️ Drive Erreur Détaillée: {type(e).__name__} - {e}")

@bot.message_handler(commands=['start', 'collecte'])
def start(message):
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    for ligne in MENU_LANGUES:
        markup.add(*ligne)
    bot.send_message(message.chat.id, "🇨🇮 **Archive des Langues Ivoiriennes**\n\nChoisis ta langue :", reply_markup=markup, parse_mode='Markdown')

@bot.message_handler(func=lambda m: any(m.text in ligne for ligne in MENU_LANGUES))
def donner_mission(message):
    langue = message.text
    mission = random.choice(MISSIONS)
    msg = bot.reply_to(message, f"📍 **Langue : {langue}**\n\nTa mission : 👉 *\"{mission}\"*", parse_mode='Markdown')
    bot.register_next_step_handler(msg, lambda m: save_vocal(m, langue, mission))

def save_vocal(message, langue, mission):
    if message.content_type == 'voice':
        status_msg = bot.reply_to(message, "⏳ Enregistrement sécurisé en cours...")
        try:
            file_info = bot.get_file(message.voice.file_id)
            downloaded = bot.download_file(file_info.file_path)
            temp_name = f"{langue}_{int(time.time())}.ogg"
            with open(temp_name, 'wb') as f:
                f.write(downloaded)

            # 1. Archive Telegram
            if ARCHIVE_ID:
                try:
                    with open(temp_name, 'rb') as voice_file:
                        bot.send_voice(chat_id=ARCHIVE_ID, voice=voice_file, caption=f"🎙 {langue} | {mission}")
                except Exception as e:
                    print(f"Erreur Archive Telegram: {e}")

            # 2. Drive
            upload_to_drive(temp_name, temp_name, langue)
            
            # 3. IA Gemini
            reponse_ia = obtenir_reponse_ia(langue, mission, répondre aux questions)
            
            # Nettoyage message d'attente
            try:
                bot.delete_message(message.chat.id, status_msg.message_id)
            except:
                pass
                
            bot.reply_to(message, reponse_ia)
            
            # Suppression fichier local
            if os.path.exists(temp_name):
                os.remove(temp_name)
                
        except Exception as e:
            print(f"Erreur sauvegarde: {e}")
            bot.edit_message_text("✅ Audio bien reçu !", message.chat.id, status_msg.message_id)
    else:
        bot.reply_to(message, "⚠️ Envoie un vocal pour la mission.")

if __name__ == '__main__':
    keep_alive()
    print("Bot démarré et prêt !")
    while True:
        try:
            bot.infinity_polling(timeout=20, skip_pending=True)
        except Exception as e:
            print(f"Polling error: {e}")
            time.sleep(5)
