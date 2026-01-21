import os
import telebot
import random
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# --- CONFIGURATION ---
API_TOKEN = '8531832542:AAEOejvyJ8vNL3BglMOhtm65lp4LsHLZMm4' 
FOLDER_ID = '1HRWpj38G4GLB2PLHo1Eh0jvKXi1zdoLe'
# ---------------------

bot = telebot.TeleBot(API_TOKEN)
SERVICE_ACCOUNT_FILE = '/etc/secrets/service_account.json'
SCOPES = ['https://www.googleapis.com/auth/drive.file']

# --- TES DONNÉES ---
MENU_LANGUES = [
    ['Baoulé', 'Dioula', 'Bété'],
    ['Yacouba', 'Guéré', 'Attié'],
    ['Adioukrou', 'Agni', 'Abidji'],
    ['Kroumen', 'Gagou', 'Sénoufo'],
    ['Andô', 'Dida', 'Avikam'],
    ['Tagbanan', 'Wobé', 'Ebrié'],
    ['Toura', 'Odiennka']
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
    creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    service = build('drive', 'v3', credentials=creds)
    
    metadata = {
        'name': f"{langue}_{file_name}", 
        'parents': [FOLDER_ID]
    }
    
    media = MediaFileUpload(file_path, mimetype='audio/ogg')
    
    # On ajoute supportsAllDrives pour que Google accepte d'utiliser ton stockage
    service.files().create(
        body=metadata, 
        media_body=media, 
        fields='id',
        supportsAllDrives=True 
    ).execute()
    
    
    # On précise bien que le dossier parent est TON dossier
    metadata = {
        'name': f"{langue}_{file_name}", 
        'parents': [FOLDER_ID]
    }
    
    media = MediaFileUpload(file_path, mimetype='audio/ogg')
    
    # On ajoute supportsAllDrives pour autoriser le transfert vers ton espace
    service.files().create(
        body=metadata, 
        media_body=media, 
        fields='id',
        supportsAllDrives=True 
    ).execute()
    

@bot.message_handler(commands=['start', 'collecte'])
def start(message):
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    for ligne in MENU_LANGUES:
        markup.add(*ligne)
    
    msg = bot.reply_to(message, "🇨🇮 **Archive des Langues Ivoiriennes**\n\nChoisis ta langue maternelle pour commencer la mission :", reply_markup=markup, parse_mode='Markdown')
    bot.register_next_step_handler(msg, donner_mission)

def donner_mission(message):
    langue = message.text
    mission = random.choice(MISSIONS)
    msg = bot.reply_to(message, f"📍 **Langue : {langue}**\n\nTa mission : Enregistre un vocal en disant la phrase suivante dans ta langue :\n\n👉 *\"{mission}\"*", parse_mode='Markdown')
    bot.register_next_step_handler(msg, lambda m: save_vocal(m, langue, mission))

def save_vocal(message, langue, mission):
    if message.content_type == 'voice':
        try:
            bot.reply_to(message, "⏳ Enregistrement sécurisé sur le Drive...")
            file_info = bot.get_file(message.voice.file_id)
            downloaded = bot.download_file(file_info.file_path)
            
            # Nom : Langue_Mission_Date.ogg
            safe_mission = "".join(x for x in mission[:15] if x.isalnum())
            temp_name = f"{langue}_{safe_mission}_{message.date}.ogg"
            
            with open(temp_name, 'wb') as f:
                f.write(downloaded)
            
            upload_to_drive(temp_name, temp_name, langue)
            bot.reply_to(message, f"✅ Merci ! Ta contribution en **{langue}** a été ajoutée à l'archive.", parse_mode='Markdown')
            os.remove(temp_name)
        except Exception as e:
            bot.reply_to(message, f"❌ Erreur : {str(e)}")
    else:
        bot.reply_to(message, "⚠️ Annulé. Tu dois envoyer un vocal pour cette mission.")

bot.polling()
  
