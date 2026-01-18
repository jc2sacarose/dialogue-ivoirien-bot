import logging
import nest_asyncio
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler

# Activation pour Render
nest_asyncio.apply()

# --- CONFIGURATION ---
TOKEN = "8531832542:AAHapK1y_HkS7994D-iWn7-S1v-4S7S7S7S" 
ID_GROUPE_ARCHIVE = -1007266887518 

CHOIX_LANGUE, ATTENTE_AUDIO = range(2)
MENU_LANGUES = [['Baoulé', 'Dioula'], ['Bété', 'Yacouba'], ['Français/Nouchi']]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reply_markup = ReplyKeyboardMarkup(MENU_LANGUES, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text("✨ *Akwaba sur Dialogue Ivoirien !*\nChoisis ta langue :", 
                                   reply_markup=reply_markup, parse_mode='Markdown')
    return CHOIX_LANGUE

async def langue_choisie(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['langue'] = update.message.text
    await update.message.reply_text(f"Parfait ! Envoie maintenant ton vocal en *{update.message.text}*.", parse_mode='Markdown')
    return ATTENTE_AUDIO

async def reception_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    langue = context.user_data.get('langue', 'Inconnue')
    user = update.message.from_user.first_name
    await update.message.reply_text(f"✅ Merci {user} ! C'est bien reçu.")
    
    # ENVOI AUTOMATIQUE DANS TON GROUPE D'ARCHIVES
    info = f"🎤 *Nouveau vocal reçu !*\n👤 Nom : {user}\n🌍 Langue : {langue}"
    await context.bot.send_message(chat_id=ID_GROUPE_ARCHIVE, text=info, parse_mode='Markdown')
    await context.bot.forward_message(chat_id=ID_GROUPE_ARCHIVE, from_chat_id=update.message.chat_id, message_id=update.message.message_id)
    
    return ConversationHandler.END

def main():
    app = Application.builder().token(TOKEN).build()
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            CHOIX_LANGUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, langue_choisie)],
            ATTENTE_AUDIO: [MessageHandler(filters.VOICE | filters.AUDIO, reception_audio)],
        },
        fallbacks=[CommandHandler('start', start)],
    )
    app.add_handler(conv_handler)
    app.run_polling()

if __name__ == '__main__':
    main()
