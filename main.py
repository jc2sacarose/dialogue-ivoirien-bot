import os
import logging
import nest_asyncio
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler

# Activation pour Render
nest_asyncio.apply()

# Configuration via variables d'environnement
TOKEN = os.getenv("TELEGRAM_TOKEN")
ARCHIVE_ID = os.getenv("ARCHIVE_GROUP_ID") 

CHOIX_LANGUE, ATTENTE_AUDIO = range(2)
MENU_LANGUES = [['Baoulé', 'Dioula'], ['Bété', 'Yacouba']]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🇨🇮 **Dialogue Ivoirien AI**\nAidez-nous à construire l'IA de traduction.\nQuelle langue parlez-vous ?",
        reply_markup=ReplyKeyboardMarkup(MENU_LANGUES, one_time_keyboard=True, resize_keyboard=True)
    )
    return CHOIX_LANGUE

async def langue_choisie(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['langue'] = update.message.text
    await update.message.reply_text(f"Merci ! Envoyez maintenant un vocal en **{update.message.text}**.")
    return ATTENTE_AUDIO

async def reception_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    langue = context.user_data.get('langue')
    user = update.message.from_user
    
    if ARCHIVE_ID:
        # Transfert automatique vers le groupe d'archive
        await context.bot.forward_message(chat_id=ARCHIVE_ID, from_chat_id=update.message.chat_id, message_id=update.message.message_id)
        info = f"🎙 Audio {langue} reçu de @{user.username if user.username else user.id}"
        await context.bot.send_message(chat_id=ARCHIVE_ID, text=info)

    await update.message.reply_text("✅ Enregistrement bien reçu et archivé !")
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
