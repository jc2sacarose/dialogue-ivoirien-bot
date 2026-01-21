import os
import logging
import random
import nest_asyncio
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler

# Activation pour Render
nest_asyncio.apply()

# Configuration
TOKEN = os.getenv("TELEGRAM_TOKEN")
ARCHIVE_ID = os.getenv("ARCHIVE_GROUP_ID") 

CHOIX_LANGUE, ATTENTE_AUDIO = range(2)
MENU_LANGUES = [['Baoulé', 'Dioula'], ['Bété', 'Sénoufo']] # Mis à jour

# --- BANQUE DE PHRASES POUR L'IA ---
MISSIONS = [
    "Comment ça va aujourd'hui ?",
    "Le repas est prêt, viens manger.",
    "Où se trouve le marché le plus proche ?",
    "Bonne arrivée dans notre village.",
    "Le respect est le chemin de la sagesse.",
    "Je cherche un taxi pour aller en ville."
]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🇨🇮 **Dialogue Ivoirien AI**\nPrêt pour une mission linguistique ?\nQuelle langue parlez-vous ?",
        reply_markup=ReplyKeyboardMarkup(MENU_LANGUES, one_time_keyboard=True, resize_keyboard=True, parse_mode='Markdown')
    )
    return CHOIX_LANGUE

async def langue_choisie(update: Update, context: ContextTypes.DEFAULT_TYPE):
    langue = update.message.text
    context.user_data['langue'] = langue
    
    # Sélection d'une phrase aléatoire pour le défi
    phrase_mission = random.choice(MISSIONS)
    context.user_data['phrase_source'] = phrase_mission
    
    await update.message.reply_text(
        f"🎯 **Mission {langue}**\n\nTraduisez et dites en vocal :\n« _{phrase_mission}_ »",
        parse_mode='Markdown'
    )
    return ATTENTE_AUDIO

async def reception_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    langue = context.user_data.get('langue')
    phrase = context.user_data.get('phrase_source')
    user = update.message.from_user
    
    if ARCHIVE_ID:
        # 1. Transfert de l'audio
        await context.bot.forward_message(chat_id=ARCHIVE_ID, from_chat_id=update.message.chat_id, message_id=update.message.message_id)
        
        # 2. Envoi des précisions (pour faciliter le futur tri vers Drive)
        info = (f"🆔 **NOUVELLE DONNÉE**\n"
                f"🌍 Langue : {langue}\n"
                f"📝 Phrase source : {phrase}\n"
                f"👤 Par : @{user.username if user.username else user.id}")
        
        await context.bot.send_message(chat_id=ARCHIVE_ID, text=info, parse_mode='Markdown')

    await update.message.reply_text("✅ Enregistrement reçu ! Votre contribution aide l'IA à comprendre nos langues. Merci !")
    return ConversationHandler.END

def main():
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
