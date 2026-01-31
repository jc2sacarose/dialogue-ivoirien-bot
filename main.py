import os, telebot, time
from flask import Flask
from threading import Thread
import google.generativeai as genai

# --- IA GEMINI ---
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-1.5-flash')

# --- CONFIGURATION ---
API_TOKEN = os.environ.get('TELE_TOKEN')
app = Flask('')

@app.route('/')
def home(): return "Bot en ligne"

bot = telebot.TeleBot(API_TOKEN)

# --- REPONSE IA ---
def parler_ia(message_texte):
    try:
        response = model.generate_content(f"Réponds en nouchi ivoirien très court : {message_texte}")
        return response.text
    except Exception as e:
        return "Petit souci technique, mais on est ensemble ! 🇨🇮"

@bot.message_handler(commands=['start'])
def send_welcome(m):
    bot.reply_to(m, "C'est propre ! Je suis réveillé. Envoie-moi un message pour voir.")

@bot.message_handler(func=lambda m: True)
def echo_all(m):
    reponse = parler_ia(m.text)
    bot.reply_to(m, reponse)

# --- LANCEMENT ---
if __name__ == '__main__':
    Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))).start()
    bot.remove_webhook()
    print("🚀 Bot prêt !")
    bot.infinity_polling(skip_pending=True)
