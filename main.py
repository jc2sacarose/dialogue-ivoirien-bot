import os, telebot, time, google.generativeai as genai
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from flask import Flask
from threading import Thread

# --- CONFIGURATION IA GEMINI ---
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
# Instruction système pour forcer l'IA à être un expert en langues ivoiriennes
model = genai.GenerativeModel(
    model_name='gemini-1.5-flash',
    system_instruction="Tu es l'expert n°1 des langues de Côte d'Ivoire (Baoulé, Dioula, Bété, etc.). Ton but est de traduire, expliquer les significations en français et discuter en nouchi. Sois chaleureux et authentique."
)

def reponse_ia(texte, est_vocal=False, langue=None):
    try:
        if est_vocal:
            prompt = f"L'utilisateur vient d'envoyer un vocal en {langue}. Salue-le chaleureusement et dis-lui que son message est bien archivé pour la postérité."
        else:
            prompt = f"Réponds à ceci en expliquant si nécessaire la signification en français : {texte}"
        return model.generate_content(prompt).text
    except:
        return "Petit souci de connexion avec Gemini, mais on est ensemble ! 🇨🇮"

# --- CONFIGURATION SERVICES ---
API_TOKEN = os.environ.get('TELE_TOKEN')
FOLDER_ID = os.environ.get('FOLDER_ID')
CHAT_ARCHIVE_ID = os.environ.get('CHAT_ARCHIVE_ID') # ID type -100...
SERVICE_ACCOUNT_FILE = '/etc/secrets/Archive-bot-dialogue-d1ab608ab4fb.json'

bot = telebot.TeleBot(API_TOKEN, threaded=False)
app = Flask('')

@app.route('/')
def home(): return "Bot Ivoirien Actif"

LANGUES = [['Baoulé', 'Dioula', 'Bété'], ['Yacouba', 'Guéré', 'Attié'], ['ajoutez votre langue']]

def upload_to_drive(file_path, file_name, langue):
    try:
        if not os.path.exists(SERVICE_ACCOUNT_FILE): return "Erreur: Fichier JSON introuvable"
        creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=['https://www.googleapis.com/auth/drive'])
        service = build('drive', 'v3', credentials=creds)
        meta = {'name': f"{langue}_{file_name}", 'parents': [FOLDER_ID]}
        media = MediaFileUpload(file_path, mimetype='audio/ogg')
        service.files().create(body=meta, media_body=media).execute()
        return "OK"
    except Exception as e: return str(e)

@bot.message_handler(commands=['start'])
def start(m):
    kb = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    for row in LANGUES: kb.add(*row)
    bot.send_message(m.chat.id, "🇨🇮 **Bienvenue sur Dialogue Ivoirien AI**\nJe traduis vos langues et j'archive notre culture. Choisissez ou ajoutez une langue ou posez-moi une question !", reply_markup=kb)

@bot.message_handler(func=lambda m: any(m.text in row for row in LANGUES))
def mission(m):
    msg = bot.reply_to(m, f"📍 **{m.text}** : J'écoute ton vocal...")
    bot.register_next_step_handler(msg, lambda ms: save_vocal(ms, m.text))

def save_vocal(m, l):
    if m.content_type == 'voice':
        statut = bot.reply_to(m, "🔄 Traitement en cours...")
        try:
            # 1. Archive Telegram (On essaie, mais on ne bloque pas si ça rate)
            try:
                if CHAT_ARCHIVE_ID and str(CHAT_ARCHIVE_ID) != "0":
                    bot.forward_message(CHAT_ARCHIVE_ID, m.chat.id, m.message_id)
            except: pass 

            # 2. Téléchargement
            f_info = bot.get_file(m.voice.file_id)
            data = bot.download_file(f_info.file_path)
            name = f"{l}_{int(time.time())}.ogg"
            with open(name, 'wb') as f: f.write(data)
            
            # 3. Drive
            res = upload_to_drive(name, name, l)
            msg_final = "✅ Archivé sur Drive !" if res == "OK" else f"⚠️ Drive Erreur: {res}"
            bot.edit_message_text(msg_final, m.chat.id, statut.message_id)

            # 4. IA
            bot.reply_to(m, reponse_ia("", True, l))
            if os.path.exists(name): os.remove(name)
        except Exception as e:
            bot.reply_to(m, f"❌ Erreur: {str(e)}")
    else:
        bot.reply_to(m, "Envoie un vocal après avoir choisi la langue, ou pose une question par écrit.")

@bot.message_handler(func=lambda m: True)
def chat_ecrit(m):
    bot.reply_to(m, reponse_ia(m.text))

if __name__ == '__main__':
    Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))).start()
    bot.remove_webhook()
    print("🚀 Bot lancé...")
    bot.infinity_polling(skip_pending=True)
