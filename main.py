import os, telebot, time, google.generativeai as genai
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from flask import Flask
from threading import Thread

# --- IA GEMINI ---
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-1.5-flash')

# --- CONFIG ---
API_TOKEN = os.environ.get('TELE_TOKEN')
FOLDER_ID = os.environ.get('FOLDER_ID')
CHAT_ARCHIVE_ID = os.environ.get('CHAT_ARCHIVE_ID')
SERVICE_ACCOUNT_FILE = '/etc/secrets/Archive-bot-dialogue-d1ab608ab4fb.json'

bot = telebot.TeleBot(API_TOKEN, threaded=False)
app = Flask('')

@app.route('/')
def home(): return "Bot Ivoirien Connecté"

def upload_to_drive(file_path, file_name, langue):
    try:
        if not os.path.exists(SERVICE_ACCOUNT_FILE): return "❌ Fichier secret introuvable"
        creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=['https://www.googleapis.com/auth/drive'])
        service = build('drive', 'v3', credentials=creds)
        meta = {'name': f"{langue}_{file_name}", 'parents': [FOLDER_ID]}
        media = MediaFileUpload(file_path, mimetype='audio/ogg')
        service.files().create(body=meta, media_body=media, supportsAllDrives=True).execute()
        return "✅ OK"
    except Exception as e: return f"❌ {str(e)[:40]}"

@bot.message_handler(commands=['start'])
def start(m):
    kb = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add('Baoulé', 'Dioula', 'Bété', 'Yacouba', 'Guéré', 'Attié')
    bot.send_message(m.chat.id, "🇨🇮 **Archiveur Actif**\nChoisis une langue et envoie ton vocal !", reply_markup=kb)

@bot.message_handler(func=lambda m: m.text in ['Baoulé', 'Dioula', 'Bété', 'Yacouba', 'Guéré', 'Attié'])
def mission(m):
    msg = bot.reply_to(m, f"📍 **{m.text}** : J'attends ton vocal...")
    bot.register_next_step_handler(msg, lambda ms: save_vocal(ms, m.text))

def save_vocal(m, l):
    if m.content_type == 'voice':
        statut = bot.reply_to(m, "🔄 Traitement et archivage...")
        try:
            # 1. Archive Telegram
            if CHAT_ARCHIVE_ID and str(CHAT_ARCHIVE_ID) != "0":
                try: bot.forward_message(CHAT_ARCHIVE_ID, m.chat.id, m.message_id)
                except: pass
            
            # 2. Téléchargement et Drive
            f_info = bot.get_file(m.voice.file_id)
            data = bot.download_file(f_info.file_path)
            name = f"vocal_{int(time.time())}.ogg"
            with open(name, 'wb') as f: f.write(data)
            
            res_drive = upload_to_drive(name, name, l)
            bot.edit_message_text(f"Statut Drive : {res_drive}", m.chat.id, statut.message_id)
            
            # 3. IA Gemini
            prompt = f"L'utilisateur a envoyé un vocal en {l}. Salue-le en nouchi et explique que c'est sauvegardé pour la culture ivoirienne."
            res = model.generate_content(prompt)
            bot.reply_to(m, res.text)
            
            if os.path.exists(name): os.remove(name)
        except Exception as e: bot.reply_to(m, f"❌ Erreur : {str(e)}")
    else:
        bot.reply_to(m, "Envoie un vocal boss !")

@bot.message_handler(func=lambda m: True)
def chat_ecrit(m):
    try:
        res = model.generate_content(f"Tu es l'expert des langues de Côte d'Ivoire. Réponds à : {m.text}")
        bot.reply_to(m, res.text)
    except: bot.reply_to(m, "Je t'entends, mais Gemini est un peu chargé.")

if __name__ == '__main__':
    Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))).start()
    # RÉINITIALISATION FORCÉE
    bot.remove_webhook()
    time.sleep(1)
    print("🚀 Bot lancé...")
    bot.infinity_polling(skip_pending=True)
        
