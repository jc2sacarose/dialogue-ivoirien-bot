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
        f"Tu es un expert des langues ivoiriennes. L'utilisateur vient d'enregistrer une phrase en {langue} : '{mission}'. "
        f"Réponds-lui de manière très chaleureuse en nouchi ou en français ivoirien. "
        f"Félicite-le pour sa contribution à la sauvegarde du patrimoine et donne-lui une petite anecdote courte sur la langue {langue}."
    )
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Merci beaucoup pour ta contribution en {langue} ! Ton enregistrement est bien sauvegardé. 🇨🇮"

# --- CONFIGURATION ---
API_TOKEN = os.environ.get('TELE_TOKEN', '8531832542:AAG6qRxlYLFZT1vfJsCXqXfPOuvJJdQpvlQ')
FOLDER_ID = os.environ.get('FOLDER_ID', '1HRWpj38G4GLB2PLHo1Eh0jvKXi1zdoLe')
PORT = int(os.environ.get('PORT', 10000))
SERVICE_ACCOUNT_FILE = '/etc/secrets/service_account.json'
SCOPES = ['https://www.googleapis.com/auth/drive.file']

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
    "Viens t'asseoir, on va causer.", "Comment appelle-t-on la mangue ?",
    "Peux-tu me dire comment était le travail ?", "Comment dit-on bonjour ?",
    "Fais passer les enfants et les vieux.", "Je veux comprendre ton problème.",
    "J'ai besoin de ton aide.", "Bon voyage à vous !", "Compte jusqu'à 10.",
    "Combien coûte celui-ci ?", "Je suis à la maison.", "Je suis malade aujourd'hui.",
    "Je ne mange pas beaucoup."
]

def upload_to_drive(file_path, file_name, langue):
    try:
        if not os.path.exists(SERVICE_ACCOUNT_FILE):
            print("Erreur : Secret introuvable.")
            return
        creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        service = build('drive', 'v3', credentials=creds)
        metadata = {'name': f"{langue}_{file_name}", 'parents': [FOLDER_ID]}
        media = MediaFileUpload(file_path, mimetype='audio/ogg')
        service.files().create(body=metadata, media_body=media, fields='id', supportsAllDrives=True).execute()
        print("Fichier envoyé sur Drive.")
    except Exception as e:
        print(f"Erreur Drive: {e}")

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
            
            safe_mission = "".join(x for x in mission[:15] if x.isalnum())
            temp_name = f"{langue}_{safe_mission}_{message.date}.ogg"
            
            with open(temp_name, 'wb') as f:
                f.write(downloaded)

            archive_id = os.environ.get('ARCHIVE_ID', '-1003561100537') 
            with open(temp_name, 'rb') as voice_file:
                bot.send_voice(
                    chat_id=archive_id, 
                    voice=voice_file, 
                    caption=f"🎙 **Audio {langue} reçu**\n📝 Phrase : {mission}\n👤 Par : @{message.from_user.username or message.from_user.first_name}"
                )

            upload_to_drive(temp_name, temp_name, langue)
            
            # --- GÉNÉRATION DE LA RÉPONSE PAR L'IA ---
            reponse_ia = obtenir_reponse_ia(langue, mission)
            bot.reply_to(message, reponse_ia)
            bot.send_message(message.chat.id, "📁 Ton vocal a également été sauvegardé sur Google Drive et dans l'archive.")
            
            if os.path.exists(temp_name):
                os.remove(temp_name)

        except Exception as e:
            bot.reply_to(message, f"❌ Erreur technique : {str(e)}")
    else:
        bot.reply_to(message, "⚠️ Envoie un vocal.")
            
if __name__ == '__main__':
    keep_alive()
    print("Bot démarré...")
    bot.infinity_polling(timeout=20, long_polling_timeout=10, skip_pending=True)
