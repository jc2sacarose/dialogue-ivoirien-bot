import os
import telebot
import random
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from flask import Flask
from threading import Thread

# --- CONFIGURATION VIA VARIABLES D'ENVIRONNEMENT ---
# On utilise os.environ.get pour plus de sécurité et de flexibilité sur Render
API_TOKEN = os.environ.get('TELE_TOKEN', '8531832542:AAEOejvyJ8vNL3BglMOhtm65lp4LsHLZMm4')
FOLDER_ID = os.environ.get('FOLDER_ID', '1HRWpj38G4GLB2PLHo1Eh0jvKXi1zdoLe')
PORT = int(os.environ.get('PORT', 10000))
SERVICE_ACCOUNT_FILE = '/etc/secrets/service_account.json'
SCOPES = ['https://www.googleapis.com/auth/drive']

# --- SERVEUR WEB (FLASK) POUR RENDER ---
# Indispensable pour éviter l'erreur "No open ports detected"
app = Flask('')

@app.route('/')
def home():
    return "Bot IA Langues Ivoiriennes en cours d'exécution..."

def run_flask():
    app.run(host='0.0.0.0', port=PORT)

def keep_alive():
    t = Thread(target=run_flask)
    t.daemon = True # Le thread s'arrêtera si le programme principal s'arrête
    t.start()

# --- INITIALISATION DU BOT ---
bot = telebot.TeleBot(API_TOKEN)

MENU_LANGUES = [
    ['Baoulé', 'Dioula', 'Bété'],
    ['Yacouba', 'Guéré', 'Attié'],
    ['Adioukrou', 'Agni', 'Abidji'],
    ['Kroumen', 'Gagou', 'Sénoufo'],
    ['Andô', 'Dida', 'Avikam'],
    ['Tagbanan', 'Wobé', 'Ebrié'],
    ['Toura', 'Odiennka'],
    ['Ajoutez votre langue ici'],
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
            print(f"Erreur : Le fichier secret {SERVICE_ACCOUNT_FILE} est introuvable.")
            return
            
        creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        service = build('drive', 'v3', credentials=creds)
        metadata = {'name': f"{langue}_{file_name}", 'parents': [FOLDER_ID]}
        media = MediaFileUpload(file_path, mimetype='audio/ogg')
        service.files().create(body=metadata, media_body=media, fields='id', supportsAllDrives=True).execute()
        print(f"Fichier {file_name} envoyé sur Drive avec succès.")
    except Exception as e:
        print(f"Erreur lors de l'envoi Drive: {e}")

@bot.message_handler(commands=['start', 'collecte'])
def start(message):
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    for ligne in MENU_LANGUES:
        markup.add(*ligne)
    msg = bot.reply_to(message, "🇨🇮 **Archive des Langues Ivoiriennes**\n\nChoisis ta langue maternelle :", reply_markup=markup, parse_mode='Markdown')
    bot.register_next_step_handler(msg, donner_mission)

def donner_mission(message):
    langue = message.text
    mission = random.choice(MISSIONS)
    msg = bot.reply_to(message, f"📍 **Langue : {langue}**\n\nTa mission : Enregistre un vocal en disant :\n\n👉 *\"{mission}\"*", parse_mode='Markdown')
    bot.register_next_step_handler(msg, lambda m: save_vocal(m, langue, mission))

def save_vocal(message, langue, mission):
    if message.content_type == 'voice':
        try:
            bot.reply_to(message, "⏳ Enregistrement sécurisé en cours...")
            
            # 1. Téléchargement du fichier depuis Telegram
            file_info = bot.get_file(message.voice.file_id)
            downloaded = bot.download_file(file_info.file_path)
            
            # Nom propre pour le fichier
            safe_mission = "".join(x for x in mission[:15] if x.isalnum())
            temp_name = f"{langue}_{safe_mission}_{message.date}.ogg"
            
            # Sauvegarde temporaire sur le serveur Render
            with open(temp_name, 'wb') as f:
                f.write(downloaded)

            # --- AJOUT : TRANSFERT VERS LE GROUPE D'ARCHIVE TELEGRAM ---
            # On récupère l'ID du groupe depuis tes variables d'environnement
            archive_id = os.environ.get('ARCHIVE_ID', '-1003561100537') 
            with open(temp_name, 'rb') as voice_file:
                bot.send_voice(
                    chat_id=archive_id, 
                    voice=voice_file, 
                    caption=f"🎙 **Audio {langue} reçu**\n📝 Phrase : {mission}\n👤 Par : @{message.from_user.username or message.from_user.first_name}"
                )

                        # --- TRANSFERT VERS GOOGLE DRIVE ---
            upload_to_drive(temp_name, temp_name, langue)
            

            # Confirmation à l'utilisateur
            bot.reply_to(message, f"✅ Merci ! Ta contribution en **{langue}** est sauvegardée dans l'archive et sur le Drive.", parse_mode='Markdown')
            
            # Nettoyage du fichier temporaire
            if os.path.exists(temp_name):
                os.remove(temp_name)

        except Exception as e:
            print(f"Erreur lors du transfert : {e}")
            bot.reply_to(message, f"❌ Erreur technique : {str(e)}")
    else:
        bot.reply_to(message, "⚠️ Ce n'est pas un vocal. Recommence avec /collecte.")
            
# --- LANCEMENT ---
if __name__ == '__main__':
    # 1. Lancer le serveur Flask en arrière-plan
    keep_alive()
    print(f"Serveur Web activé sur le port {PORT}")
    
    # 2. Lancer le bot Telegram avec infinity_polling (plus stable)
    print("Bot IA Langues Ivoiriennes démarré...")
    bot.infinity_polling(timeout=20, long_polling_timeout=10)
