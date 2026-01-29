import os, telebot, random, time
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from flask import Flask
from threading import Thread
import google.generativeai as genai

# --- CONFIGURATION IA ---
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

def obtenir_reponse_ia(langue, mission):
    prompt = f"Expert Côte d'Ivoire. Félicite l'utilisateur en nouchi pour son vocal en {langue} sur la phrase '{mission}'."
    try:
        return model.generate_content(prompt).text
    except:
        return f"C'est propre ! Merci pour ton vocal en {langue} ! 🇨🇮"

# --- CONFIGURATION GENERALE ---
API_TOKEN = os.environ.get('TELE_TOKEN')
FOLDER_ID = os.environ.get('FOLDER_ID')
ARCHIVE_ID = os.environ.get('ARCHIVE_GROUP_ID')
PORT = int(os.environ.get('PORT', 10000))
SERVICE_ACCOUNT_FILE = '/etc/secrets/service_account.json'
SCOPES = ['https://www.googleapis.com/auth/drive']

app = Flask('')
@app.route('/')
def home(): return "Bot en ligne !"

def run_flask(): app.run(host='0.0.0.0', port=PORT)

bot = telebot.TeleBot(API_TOKEN, threaded=False)

MENU_LANGUES = [['Baoulé', 'Dioula', 'Bété'], ['Yacouba', 'Guéré', 'Attié'], ['Adioukrou', 'Agni', 'Abidji']]
MISSIONS = ["Comment ça va ?", "Le repas est prêt.", "Bonne arrivée chez nous."]

def upload_to_drive(file_path, file_name, langue):
    try:
        if not os.path.exists(SERVICE_ACCOUNT_FILE):
            print("❌ Erreur : Fichier service_account.json absent sur Render")
            return
        creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        service = build('drive', 'v3', credentials=creds)
        metadata = {'name': f"{langue}_{file_name}", 'parents': [FOLDER_ID]}
        media = MediaFileUpload(file_path, mimetype='audio/ogg')
        service.files().create(body=metadata, media_body=media).execute()
        print(f"✅ Drive Succès pour {langue}")
    except Exception as e:
        print(f"⚠️ Erreur Drive : {e}")

@bot.message_handler(commands=['start'])
def start(message):
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    for l in MENU_LANGUES: markup.add(*l)
    bot.send_message(message.chat.id, "Choisis ta langue :", reply_markup=markup)

@bot.message_handler(func=lambda m: any(m.text in l for l in MENU_LANGUES))
def mission(message):
    langue = message.text
    mission_txt = random.choice(MISSIONS)
    msg = bot.reply_to(message, f"Langue : {langue}\nMission : {mission_txt}")
    bot.register_next_step_handler(msg, lambda m: save_vocal(m, langue, mission_txt))

def save_vocal(message, langue, mission):
    if message.content_type == 'voice':
        try:
            file_info = bot.get_file(message.voice.file_id)
            downloaded = bot.download_file(file_info.file_path)
            temp_name = f"vocal_{int(time.time())}.ogg"
            with open(temp_name, 'wb') as f: f.write(downloaded)
            
            if ARCHIVE_ID:
                with open(temp_name, 'rb') as vf:
                    bot.send_voice(ARCHIVE_ID, vf, caption=f"{langue} | {mission}")
            
            upload_to_drive(temp_name, temp_name, langue)
            bot.reply_to(message, obtenir_reponse_ia(langue, mission))
            if os.path.exists(temp_name): os.remove(temp_name)
        except Exception as e: print(f"Erreur : {e}")

if __name__ == '__main__':
    Thread(target=run_flask).start()
    bot.infinity_polling(skip_pending=True)
