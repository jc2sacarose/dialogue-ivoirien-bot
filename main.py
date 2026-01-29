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

def obtenir_reponse_ia(langue, mission):
    prompt = (
        f"Tu es un expert des langues de Côte d'Ivoire. Un utilisateur vient de t'envoyer un vocal en {langue} "
        f"pour la phrase : '{mission}'. Réponds-lui de manière très chaleureuse en mélangeant français et nouchi. "
        f"Félicite-le et donne une petite anecdote rapide sur la culture {langue}."
    )
    try:
        response = model.generate_content(prompt)
        return response.text
    except:
        return f"C'est propre ! Merci pour ton vocal en {langue}. On ensemble pour la culture ! 🇨🇮"

# --- CONFIGURATION GENERALE ---
API_TOKEN = os.environ.get('TELE_TOKEN')
FOLDER_ID = os.environ.get('FOLDER_ID')
ARCHIVE_ID = os.environ.get('ARCHIVE_GROUP_ID')
SERVICE_ACCOUNT_FILE = '/etc/secrets/service_account.json'

app = Flask('')
@app.route('/')
def home(): return "Bot Ivoirien 2.0 Connecté"

bot = telebot.TeleBot(API_TOKEN, threaded=False)
LANGUES = [['Baoulé', 'Dioula', 'Bété'], ['Yacouba', 'Guéré', 'Attié'], ['Adioukrou', 'Agni', 'Abidji']]
MISSIONS = ["Comment ça va ?", "Le repas est prêt, viens manger.", "Bonne arrivée chez nous."]

def upload_to_drive(file_path, file_name, langue):
    try:
        creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=['https://www.googleapis.com/auth/drive'])
        service = build('drive', 'v3', credentials=creds)
        meta = {'name': f"{langue}_{file_name}", 'parents': [FOLDER_ID]}
        media = MediaFileUpload(file_path, mimetype='audio/ogg')
        service.files().create(body=meta, media_body=media).execute()
        print(f"✅ DRIVE OK : {langue}")
    except Exception as e: print(f"❌ DRIVE ERREUR : {e}")

@bot.message_handler(commands=['start'])
def start(m):
    kb = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    for row in LANGUES: kb.add(*row)
    bot.send_message(m.chat.id, "🇨🇮 **Bienvenue sur la V2 !**\n\nL'IA ivoirienne t'écoute. Choisis ta langue pour commencer :", reply_markup=kb, parse_mode='Markdown')

@bot.message_handler(func=lambda m: any(m.text in row for row in LANGUES))
def mission(m):
    l = m.text
    txt = random.choice(MISSIONS)
    msg = bot.reply_to(m, f"📍 **Langue choisie : {l}**\n👉 Ta mission : *\"{txt}\"*\n\nEnregistre un vocal en {l} pour traduire cette phrase !")
    bot.register_next_step_handler(msg, lambda ms: save_vocal(ms, l, txt))

def save_vocal(m, l, txt):
    if m.content_type == 'voice':
        status_msg = bot.reply_to(m, "⏳ *L'IA analyse ton vocal...*", parse_mode='Markdown')
        try:
            f_info = bot.get_file(m.voice.file_id)
            data = bot.download_file(f_info.file_path)
            name = f"{l}_{int(time.time())}.ogg"
            with open(name, 'wb') as f: f.write(data)
            
            # Archive Telegram
            if ARCHIVE_ID:
                with open(name, 'rb') as vf: bot.send_voice(ARCHIVE_ID, vf, caption=f"🎙 {l} | {txt}")
            
            # Envoi Drive
            upload_to_drive(name, name, l)
            
            # Réponse IA
            ia_txt = obtenir_reponse_ia(l, txt)
            bot.edit_message_text(ia_txt, m.chat.id, status_msg.message_id)
            
            if os.path.exists(name): os.remove(name)
        except Exception as e:
            print(f"Erreur : {e}")
            bot.edit_message_text("✅ Audio reçu avec succès !", m.chat.id, status_msg.message_id)
    else:
        bot.reply_to(m, "⚠️ Pardon, il faut envoyer un vocal pour que l'IA puisse t'écouter.")

if __name__ == '__main__':
    Thread(target=lambda: app.run(host='0.0.0.0', port=10000)).start()
    bot.infinity_polling(skip_pending=True)
        
