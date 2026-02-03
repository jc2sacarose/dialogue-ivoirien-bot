import os, telebot, time
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from flask import Flask
from threading import Thread
import google.generativeai as genai

# --- CONFIGURATION IA GEMINI ---
# Utilise la nouvelle clé AI Studio que tu as générée
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-1.5-flash')

def reponse_ia_ivoirienne(texte_utilisateur, est_vocal=False, langue=None):
    if est_vocal:
        prompt = f"Un utilisateur a envoyé un vocal en {langue}. Félicite-le chaleureusement en nouchi (ivoirien) et donne une info culturelle rapide sur cette langue."
    else:
        prompt = f"Tu es un expert des langues de Côte d'Ivoire. Réponds à cette question en nouchi/français ivoirien : {texte_utilisateur}"
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"Erreur Gemini: {e}")
        return "C'est propre mon frère ! On est ensemble pour la culture. 🇨🇮"

# --- CONFIGURATION SERVICES ---
API_TOKEN = os.environ.get('TELE_TOKEN')
FOLDER_ID = os.environ.get('FOLDER_ID')
SERVICE_ACCOUNT_FILE = '/etc/secrets/Archive-bot-dialogue-d1ab608ab4fb.json'
app = Flask('')
@app.route('/')
def home(): return "Le Bot est en mouvement !"

bot = telebot.TeleBot(API_TOKEN, threaded=False)
LANGUES = [['Baoulé', 'Dioula', 'Bété'], ['Yacouba', 'Guéré', 'Attié'], ['Ajoutez votre langue']]

def upload_to_drive(file_path, file_name, langue):
    try:
        creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=['https://www.googleapis.com/auth/drive'])
        service = build('drive', 'v3', credentials=creds)
        meta = {'name': f"{langue}_{file_name}", 'parents': [FOLDER_ID]}
        media = MediaFileUpload(file_path, mimetype='audio/ogg')
        service.files().create(body=meta, media_body=media, supportsAllDrives=True).execute()
        return "✅ OK"
    except Exception as e: return f"❌ Erreur: {str(e)[:20]}"

@bot.message_handler(content_types=['voice'])
def handle_vocal(m):
    # On détecte la langue par défaut ou via le texte précédent
    statut = bot.reply_to(m, "🔄 Archivage en cours...")
    try:
        f_info = bot.get_file(m.voice.file_id)
        data = bot.download_file(f_info.file_path)
        name = f"vocal_{int(time.time())}.ogg"
        with open(name, 'wb') as f: f.write(data)
        res = upload_to_drive(name, name, "Vocal")
        bot.edit_message_text(f"Drive: {res}", m.chat.id, statut.message_id)
        bot.reply_to(m, model.generate_content("Dis bonjour en nouchi").text)
        os.remove(name)
    except Exception as e: bot.reply_to(m, f"Erreur: {e}")
        
@bot.message_handler(commands=['start'])
def start(m):
    bot.send_message(m.chat.id, "🇨🇮 **Bot Réveillé !**\nChoisis ta langue et envoie un vocal.")

@bot.message_handler(content_types=['voice'])
def handle_vocal(m):
    # On détecte la langue par défaut ou via le texte précédent
    statut = bot.reply_to(m, "🔄 Archivage en cours...")
    try:
        f_info = bot.get_file(m.voice.file_id)
        data = bot.download_file(f_info.file_path)
        name = f"vocal_{int(time.time())}.ogg"
        with open(name, 'wb') as f: f.write(data)
        res = upload_to_drive(name, name, "Vocal")
        bot.edit_message_text(f"Drive: {res}", m.chat.id, statut.message_id)
        bot.reply_to(m, model.generate_content("Dis bonjour en nouchi").text)
        os.remove(name)
    except Exception as e: bot.reply_to(m, f"Erreur: {e}")

@bot.message_handler(func=lambda m: True)
def chat(m):
    try:
        res = model.generate_content(m.text)
        bot.reply_to(m, res.text)
    except: bot.reply_to(m, "Je t'entends !")

if __name__ == '__main__':
    Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))).start()
    bot.remove_webhook() # Étape cruciale pour débloquer la ligne
    time.sleep(1)
    print("🚀 Lancement du bot...")
    bot.infinity_polling(skip_pending=True)
