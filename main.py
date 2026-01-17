import nest_asyncio
nest_asyncio.apply()
import os
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler

# Ton Token de Dialogue Ivoirien AI
TOKEN = "8531832542:AAHapK1yIHAY6kiQbFdQB1Zvue3kvDjoWfE"
CHOIX_LANGUE, ATTENTE_AUDIO = range(2)
MENU_LANGUES = [['Baoulé', 'Dioula'], ['Bété', 'Yacouba']]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reply_markup = ReplyKeyboardMarkup(MENU_LANGUES, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text("✨ *Akwaba sur Dialogue Ivoirien AI !*\n\nChoisis ta langue :", reply_markup=reply_markup, parse_mode='Markdown')
    return CHOIX_LANGUE

async def langue_choisie(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['langue'] = update.message.text
    await update.message.reply_text(f"Excellent ! Envoie-moi une note vocale en *{update.message.text}*.", parse_mode='Markdown')
    return ATTENTE_AUDIO

async def reception_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Merci ! Ton enregistrement est bien reçu.")
    return ConversationHandler.END

if __name__ == '__main__':
    application = Application.builder().token(TOKEN).build()
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            CHOIX_LANGUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, langue_choisie)],
            ATTENTE_AUDIO: [MessageHandler(filters.VOICE, reception_audio)],
        },
        fallbacks=[CommandHandler('start', start)],
    )
    application.add_handler(conv_handler)
    application.run_polling()
