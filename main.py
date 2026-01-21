import os
import random
import nest_asyncio
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler

nest_asyncio.apply()

TOKEN = os.getenv("TELEGRAM_TOKEN")
ARCHIVE_ID = os.getenv("ARCHIVE_GROUP_ID") 

CHOIX_LANGUE, ATTENTE_AUDIO = range(2)
# J'ai ajouté les langues de tes boutons sur la capture
MENU_LANGUES = [['Baoulé', 'Dioula'], ['Bété', 'Yacouba']]

# Banque de phrases pour faire parler les gens
MISSIONS = [
    "Comment se porte la famille ce matin ?",
    "Le marché est-il ouvert aujourd'hui ?",
    "Bonne arrivée chez nous.",
    "Où puis-je trouver de l'eau ?",
    "Merci pour votre aide."
]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🇨🇮 **Dialogue Ivoirien AI**\nAidez-nous à construire l'IA de traduction.\nQuelle langue parlez-vous ?",
        reply_markup=ReplyKeyboardMarkup(MENU_LANGUES, one_time_keyboard=True, resize_keyboard=True)
    )
    return CHOIX_LANGUE

async def langue_choisie(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['langue'] = update.message.text
    # On choisit une mission au hasard
    phrase = random.choice(MISSIONS)
    context.user_data['phrase_source'] = phrase
    
    await update.message.reply_text(
        f"🎯 **Mission {update.message.text}**\n\nTraduisez et dites en vocal :\n« _{phrase}_ »"
    )
    return ATTENTE_AUDIO

async def reception_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    langue = context.user_data.get('langue')
    phrase = context.user_data.get('phrase_source')
    user = update.message.from_user
    
    if ARCHIVE_ID:
        # Envoi de l'audio + les infos précises à l'archive
        info = f"🎙 **{langue}**\n📝 Phrase: {phrase}\n👤 Par: @{user.username if user.username else user.id}"
        await context.bot.send_voice(chat_id=ARCHIVE_ID, voice=update.message.voice.file_id, caption=info)

    await update.message.reply_text("✅ Enregistrement bien reçu et archivé ! Merci Boss.")
    return ConversationHandler.END

def main():
    # Suppression de l'utilisation de port pour éviter les erreurs Render
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
