import os, telebot, time, google.generativeai as genai
from flask import Flask
from threading import Thread

# Config ultra-simple
API_TOKEN = os.environ.get('TELE_TOKEN')
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-1.5-flash')

bot = telebot.TeleBot(API_TOKEN, threaded=False)
app = Flask('')

@app.route('/')
def home(): return "Bot en ligne"

@bot.message_handler(commands=['start'])
def start(m):
    bot.send_message(m.chat.id, "🇨🇮 **Le Bot est réveillé !**\nDis-moi quelque chose pour tester.")

@bot.message_handler(func=lambda m: True)
def chat(m):
    try:
        res = model.generate_content(f"Réponds en nouchi court : {m.text}")
        bot.reply_to(m, res.text)
    except Exception as e:
        bot.reply_to(m, "Problème avec Gemini, mais je t'entends !")

if __name__ == '__main__':
    Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))).start()
    bot.remove_webhook()
    print("Lancement...")
    bot.infinity_polling(skip_pending=True)
    
