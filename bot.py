import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CallbackQueryHandler, ContextTypes, CommandHandler

from gpt import ChatGptService
from util import (load_message, send_text, send_image, show_main_menu,
                  default_callback_handler, load_prompt, send_text_buttons)
from credentials import ChatGPT_TOKEN, BOT_TOKEN

# Налаштування логування
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

chat_gpt = None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = load_message('main')
    await send_image(update, context, 'main')
    await send_text(update, context, text)
    await show_main_menu(update, context, {
        'start': 'Головне меню',
        'random': 'Дізнатися випадковий цікавий факт 🧠',
        'gpt': 'Задати питання чату GPT 🤖',
        'talk': 'Поговорити з відомою особистістю 👤',
        'quiz': 'Взяти участь у квізі ❓'
        # Додати команду в меню можна так:
        # 'command': 'button text'

    })

def main():
    global chat_gpt
    chat_gpt = ChatGptService(ChatGPT_TOKEN)

    app = ApplicationBuilder().token(BOT_TOKEN).build()

# Зареєструвати обробник команди можна так:
# app.add_handler(CommandHandler('command', handler_func))

# Зареєструвати обробник колбеку можна так:
# app.add_handler(CallbackQueryHandler(app_button, pattern='^app_.*'))
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CallbackQueryHandler(default_callback_handler))

    logger.info("🚀 Bot started")
    app.run_polling()

if __name__ == "__main__":
    main()