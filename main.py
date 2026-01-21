import os
import random
import nest_asyncio
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler

# Activation pour Render
nest_asyncio.apply()

# Configuration
TOKEN = os.getenv("TELEGRAM_TOKEN")
ARCHIVE_ID = os.getenv("ARCHIVE_GROUP_ID") 

CHOIX_LANGUE, ATTENTE_AUDIO = range(2)
MENU_LANGUES = [
    ['Baoulé', 'Dioula', 'Bété'],
    ['Yacouba', 'Guéré', 'Attié'],
    ['Adioukrou', 'Agni', 'Abidji'],
    ['Kroumen', 'Gagou', 'Sénoufo'],
    ['Andô', 'Dida', 'Avikam'],
    ['Tagbanan', 'Wobé', 'Ebrié'],
    ['Toura', 'Odiennka']
]

# --- BANQUE DE MISSIONS POUR L'IA ---
MISSIONS = [
    "Comment ça va aujourd'hui ?",
    "Le repas est prêt, viens manger.",
    "Où se trouve le marché le plus proche ?",
    "Bonne arrivée chez nous.",
    "Je cherche un taxi pour aller en ville.",
    "Il faut pardonner, c'est Dieu qui donne.",
    "On dit quoi ? La famille va bien ?",
    "Le travail finit par payer.",
    "Viens t'asseoir, on va causer.",
    "Comment appelle-t-on la mangue ?",
    "Peux-tu me dire comment était le travail ?",
    "Comment dit-on bonjour ?",
    "Fais passer les enfants et les vieux.",
    "Je veux comprendre ton problème.",
    "J'ai besoin de ton aide.",
    "Bon voyage à vous !",
    "Compte jusqu'à 10.",
    "Combien coûte celui-ci ?",
    "Je suis à la maison.",
    "Je suis malade aujourd'hui.",
    "Je ne mange pas beaucoup."
]



# --- PETIT SERVEUR POUR RENDER (Évite l'erreur de Port) ---
class FakeServer(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running")

def run_fake_server():
    server = HTTPServer(('0.0.0.0', int(os.environ.get('PORT', 10000))), FakeServer)
    server.serve_forever()

# --- LOGIQUE DU BOT ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🇨🇮 **Dialogue Ivoirien AI**\nPrêt pour une mission ?\nQuelle langue parlez-vous ?",
        reply_markup=ReplyKeyboardMarkup(MENU_LANGUES, one_time_keyboard=True, resize_keyboard=True)
    )
    return CHOIX_LANGUE

async def langue_choisie(update: Update, context: ContextTypes.DEFAULT_TYPE):
    langue = update.message.text
    context.user_data['langue'] = langue
    phrase = random.choice(MISSIONS)
    context.user_data['phrase_source'] = phrase
    
    await update.message.reply_text(
        f"🎯 **Mission {langue}**\n\nTraduisez et dites en vocal :\n« _{phrase}_ »"
    )
    return ATTENTE_AUDIO

async def reception_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    langue = context.user_data.get('langue')
    phrase = context.user_data.get('phrase_source')
    user = update.message.from_user
    
    if ARCHIVE_ID:
        info = f"🎙 **{langue}**\n📝 Phrase: {phrase}\n👤 Par: @{user.username if user.username else user.id}"
        await context.bot.send_voice(chat_id=ARCHIVE_ID, voice=update.message.voice.file_id, caption=info)

    await update.message.reply_text("✅ Enregistrement reçu ! Merci Boss.")
    return ConversationHandler.END

def main():
    # Lancer le serveur bidon en arrière-plan pour Render
    threading.Thread(target=run_fake_server, daemon=True).start()
    
    app = Application.builder().token(TOKEN).build()
    conv = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            CHOIX_LANGUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, langue_choisie)],
            ATTENTE_AUDIO: [MessageHandler(filters.VOICE, reception_audio)],
        },
        fallbacks=[CommandHandler('start', start)],
    )
    app.add_handler(conv)
    app.run_polling()

if __name__ == '__main__':
    main()
  
