import os
import telebot
import random
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from flask import Flask
from threading import Thread
import google.generativeai as genai

# --- CONFIGURATION IA GEMINI ---
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-1.5-flash')

def obtenir_reponse_ia(langue, mission):
    prompt = (
        f"Tu es un expert en culture de Côte d'Ivoire. Un utilisateur vient de t'envoyer un vocal en {langue} "
        f"pour la phrase : '{mission}'. Réponds-lui en nouchi ou en français de Moussa. "
        f"Félicite-le chaudement et donne-lui une anecdote sur la langue {langue}."
    )
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"Erreur Gemini: {e}")
        return f"Merci pour ta contribution en {langue} ! C'est ensemble qu'on protège nos racines. 🇨🇮"

# --- CONFIGURATION ---
API_TOKEN = os.environ.get('TELE_TOKEN')
FOLDER_ID = os.environ.get('FOLDER_ID')
PORT = int(os.environ.get('PORT', 10000))
SERVICE_ACCOUNT_FILE = '/etc/secrets/service_account.json'
# Scope élargi pour éviter les erreurs de permission
SCOPES = ['https://www.googleapis.com/auth/drive']

app = Flask('')

@app.route('/')
def home():
    return "Bot IA Langues Ivoiriennes en ligne"

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
            print(f"❌ Erreur : Le fichier {SERVICE_ACCOUNT_FILE} est introuvable !")
            return
        
        creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        service = build('drive', 'v3', credentials=creds)
        
        metadata = {'name': f"{langue}_{file_name}", 'parents': [FOLDER_ID]}
        media = MediaFileUpload(file_path, mimetype='audio/ogg')
        
        service.files().create(body=metadata, media_body=media, fields='id', supportsAllDrives=True).execute()
        print(f"✅ Succès : {file_name} envoyé sur Drive.")
    except Exception as e:
        print(f"⚠️ Erreur Drive précise : {type(e).__name__} - {e}")

@bot.message_handler(commands=['start', 'collecte'])
def start(message):
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    for ligne in MENU_LANGUES:
        markup.add(*ligne)
    msg = bot.reply_to(message, "🇨🇮 **Archive des Langues Ivoiriennes**\n\nChoisis ta langue :", reply_markup=markup, parse_mode='Markdown')
    bot.register_next_step_handler(msg, donner_mission)

def donner_mission(message):
    langue = message.text
    mission = random.choice(MISSIONS)
    msg = bot.reply_to(message, f"📍 **Langue : {langue}**\n\nMission : Enregistre :\n👉 *\"{mission}\"*", parse_mode='Markdown')
    bot.register_next_step_handler(msg, lambda m: save_vocal(m, langue, mission))

def save_vocal(message, langue, mission):
    if message.content_type == 'voice':
        try:
            bot.reply_to(message, "⏳ Enregistrement sécurisé en cours...")
            file_info = bot.get_file(message.voice.file_id)
            downloaded = bot.download_file(file_info.file_path)
            
            temp_name = f"{langue}_{message.date}.ogg"
            with open(temp_name, 'wb') as f:
                f.write(downloaded)

            # Archive Telegram
            archive_id = os.environ.get('ARCHIVE_ID', '-1003561100537') 
            with open(temp_name, 'rb') as voice_file:
                bot.send_voice(chat_id=archive_id, voice=voice_file, caption=f"🎙 Audio {langue}\n📝 Phrase : {mission}")

            # Envoi Drive
            upload_to_drive(temp_name, temp_name, langue)
            
            # IA Gemini
            reponse_ia = obtenir_reponse_ia(langue, mission)
            bot.reply_to(message, reponse_ia)
            
            if os.path.exists(temp_name):
                os.remove(temp_name)
        except Exception as e:
            bot.reply_to(message, f"❌ Erreur : {str(e)}")
    else:
        bot.reply_to(message, "⚠️ Envoie un vocal.")
            
if __name__ == '__main__':
    keep_alive()
    print("Bot démarré et prêt !")
    bot.infinity_polling(skip_pending=True)
    
