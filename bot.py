import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CallbackQueryHandler, ContextTypes, CommandHandler
from telegram.ext import MessageHandler, filters

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
#Random_fact
async def random_fact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_image(update, context, 'random')
    try:
        prompt = load_prompt('random')
        response = await chat_gpt.send_question(prompt, "Розкажи випадковий цікавий факт")
    except Exception as e:
        logger.error(f"GPT error: {e}", exc_info=True)
        response = "❌ Не вдалося отримати факт. Спробуйте пізніше."

    await send_text_buttons(update, context, response, {
        'random_finish': 'Закінчити',
        'random_one_more': 'Хочу ще факт'
    })

async def random_buttons_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    query = update.callback_query.data
    if query == 'random_finish':
        await start(update, context)
    elif query == 'random_one_more':
        await random_fact(update, context)

#ChatGPT інтерфейс
async def gpt_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['mode'] = 'gpt'  # Встановлюємо режим
    await send_image(update, context, 'gpt')
    text = load_message('gpt')
    await send_text(update, context, text)

#Dialog_famous
async def talk_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['mode'] = 'talk'
    await send_image(update, context, 'talk')
    text = load_message('talk')
    await send_text_buttons(update, context, text, {
        'talk_cobain': 'Курт Кобейн 🎸',
        'talk_hawking': 'Стівен Гокінг 🌌',
        'talk_nietzsche': 'Фрідріх Ніцше 🧠',
        'talk_queen': 'Єлизавета II 👑',
        'talk_tolkien': 'Джон Толкін 📖',
    })

async def talk_buttons_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    query = update.callback_query.data # Передає 'talk_hawking' тощо

    try:
        # Шукаємо файл за повною назвою кнопки, щоб уникнути помилки No such file
        prompt = load_prompt(query)
        chat_gpt.set_prompt(prompt) # Задаємо системну роль ШІ
        await send_text(update, context, f"Привіт! Я готовий до розмови з тобою. Запитуй будь-що.")
    except Exception as e:
        logger.error(f"Error loading talk prompt: {e}")
        await send_text(update, context, "❌ Не вдалося завантажити промпт особистості.")

async def talk_finish_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    context.user_data['mode'] = None
    await start(update, context)

#Тут вже об'єднуємо gpt та talk режим
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mode = context.user_data.get('mode')

    if mode == 'gpt':
        waiting_msg = await send_text(update, context, "Thinking... 🤖")
        try:
            response = await chat_gpt.add_message(update.message.text)
        except Exception as e:
            logger.error(f"GPT error: {e}")
            response = "❌ Помилка сервісу ШІ."

        await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=waiting_msg.message_id)
        await send_text(update, context, response)
#Додаємо блок розмови
    elif mode == 'talk':
        try:
            # Надсилаємо повідомлення користувача до ШІ персонажу
            response = await chat_gpt.add_message(update.message.text)
        except Exception as e:
            logger.error(f"GPT talk error: {e}")
            response = "❌ Тимчасова помилка зв'язку з персонажем."

        # Додаємо кнопку завершення розмови
        await send_text_buttons(update, context, response, {'talk_finish': 'Закінчити'})

    else:
        await send_text(update, context, "Будь ласка, оберіть режим у меню або введіть команду.")

def main():
    global chat_gpt
    chat_gpt = ChatGptService(ChatGPT_TOKEN)

    app = ApplicationBuilder().token(BOT_TOKEN).build()

# Зареєструвати обробник команди можна так:
# app.add_handler(CommandHandler('command', handler_func))

# Зареєструвати обробник колбеку можна так:
# app.add_handler(CallbackQueryHandler(app_button, pattern='^app_.*'))
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('random', random_fact))
    app.add_handler(CommandHandler('gpt', gpt_mode))
    app.add_handler(CommandHandler('talk', talk_mode))

    # Реєстрація кнопок вибору персонажів та завершення розмови
    app.add_handler(CallbackQueryHandler(talk_buttons_handler, pattern='^talk_(cobain|hawking|nietzsche|queen|tolkien)'))
    app.add_handler(CallbackQueryHandler(talk_finish_handler, pattern='^talk_finish$'))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(CallbackQueryHandler(random_buttons_handler, pattern='^random_.*'))
    app.add_handler(CallbackQueryHandler(default_callback_handler))

    logger.info("🚀 Bot started")
    app.run_polling()

if __name__ == "__main__":
    main()