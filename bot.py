import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CallbackQueryHandler, ContextTypes, CommandHandler
from telegram.ext import MessageHandler, filters

from gpt import ChatGptService
from util import (load_message, send_text, send_image, show_main_menu,
                  default_callback_handler, load_prompt, send_text_buttons, send_html)
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

#КВІЗ
async def quiz_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['mode'] = 'quiz'
    context.user_data['quiz_score'] = 0
    await send_image(update, context, 'quiz')

    # Повертаємо 'quiz_more' для теми "Схожа тема", як прописано у твоєму quiz.txt
    await send_text_buttons(update, context, "Обери тему для квізу:", {
        'quiz_prog': 'Програмування 💻',
        'quiz_math': 'Математика 🟰',
        'quiz_biology': 'Біологія 🧬',
        'quiz_more': 'Схожа тема 👉',
    })

async def quiz_buttons_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    query = update.callback_query.data  # Отримуємо 'quiz_prog', 'quiz_math' тощо

    try:
        # 1. Завантажуємо системний промпт та ініціалізуємо ШІ
        prompt = load_prompt('quiz')
        chat_gpt.set_prompt(prompt)

        # 2. НАДВИЖЛИВО: Передаємо в ШІ саме команду 'quiz_prog' або 'quiz_math'
        # Тепер ШІ точно зорієнтується по твоїй інструкції з файлу quiz.txt!
        question = await chat_gpt.add_message(query)

        await send_html(update, context, question)
    except Exception as e:
        logger.error(f"Quiz starting error: {e}", exc_info=True)
        await send_text(update, context, "❌ Не вдалося розпочати квіз. Спробуйте ще раз.")


async def quiz_next_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    query = update.callback_query.data  # 'quiz_more', 'quiz_change' або 'quiz_finish'

    try:
        if query == 'quiz_more':
            # Коли користувач хоче ще питання, ми надсилаємо йому команду "quiz_more"
            question = await chat_gpt.add_message("quiz_more")
            await send_html(update, context, question)
        elif query == 'quiz_change':
            await quiz_mode(update, context)
        elif query == 'quiz_finish':
            context.user_data['mode'] = None
            await start(update, context)
    except Exception as e:
        logger.error(f"Quiz next error: {e}", exc_info=True)
        await send_text(update, context, "❌ Сталася помилка при генерації наступного питання.")

#Тут вже об'єднуємо gpt та talk режим + квіз
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
#Додаємо КВІЗ
    elif mode == 'quiz':
        answer = update.message.text
        try:
            result = await chat_gpt.add_message(answer)

            # Валідація результату ШІ
            if result and "правильно" in result.lower() and "неправильно" not in result.lower():
                context.user_data['quiz_score'] += 1

            score = context.user_data['quiz_score']

            # Надсилаємо відповідь через HTML, щоб захистити текст від невалідного Markdown
            await send_html(update, context, f"{result}\n\n🏆 Ваш поточний рахунок: {score}")

            await send_text_buttons(update, context, "Що робимо далі?", {
                'quiz_more': 'Хочу ще питання на цю ж тему',
                'quiz_change': 'Змінити тему',
                'quiz_finish': 'Закінчити квіз'
            })
        except Exception as e:
            logger.error(f"Quiz process error: {e}", exc_info=True)
            await send_text(update, context, "❌ Сталася помилка при обробці вашої відповіді.")

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
    app.add_handler(CommandHandler('quiz', quiz_mode))

    # Реєстрація кнопок вибору персонажів та завершення розмови
    app.add_handler(CallbackQueryHandler(talk_buttons_handler, pattern='^talk_(cobain|hawking|nietzsche|queen|tolkien)'))
    app.add_handler(CallbackQueryHandler(talk_finish_handler, pattern='^talk_finish$'))

    app.add_handler(CallbackQueryHandler(quiz_buttons_handler, pattern='^quiz_(prog|math|biology|other)'))
    app.add_handler(CallbackQueryHandler(quiz_next_handler, pattern='^quiz_(more|change|finish)'))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(CallbackQueryHandler(random_buttons_handler, pattern='^random_.*'))
    app.add_handler(CallbackQueryHandler(default_callback_handler))

    logger.info("🚀 Bot started")
    app.run_polling()

if __name__ == "__main__":
    main()