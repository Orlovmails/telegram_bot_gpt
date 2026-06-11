import logging
import os                          # ДОДАНО: для роботи з операційною системою (os.getenv)
from dotenv import load_dotenv     # ДОДАНО: для читання файлу .env

from telegram import Update
from telegram.ext import ApplicationBuilder, CallbackQueryHandler, ContextTypes, CommandHandler
from telegram.ext import MessageHandler, filters

from gpt import ChatGptService
from util import (load_message, send_text, send_image, show_main_menu,
                  default_callback_handler, load_prompt, send_text_buttons, send_html)

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ChatGPT_TOKEN = os.getenv("CHATGPT_TOKEN")

# Перевірка для безпеки (якщо забули створити .env файл)
if not BOT_TOKEN or not ChatGPT_TOKEN:
    raise ValueError(
        "❌ ПОМИЛКА: Токени BOT_TOKEN або CHATGPT_TOKEN не знайдені у файлі .env!\n"
        "Перевірте, чи створили ви файл .env в папці з ботом."
    )

# Налаштування логування
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# 2. ІНІЦІАЛІЗАЦІЯ СЕРВІСУ (Замість порожнього None)
chat_gpt = ChatGptService(ChatGPT_TOKEN)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['mode'] = None
    text = load_message('main')
    await send_image(update, context, 'main')
    await send_text(update, context, text)
    await show_main_menu(update, context, {
        'start': 'Головне меню',
        'random': 'Дізнатися випадковий цікавий факт 🧠',
        'gpt': 'Задати питання чату GPT 🤖',
        'talk': 'Поговорити з відомою особистістю 👤',
        'quiz': 'Взяти участь у квізі ❓',
        'photoai': 'Розпізнавання зображень 📸',
        'resume': 'Допомога з резюме 📝'
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

#RESUME
async def resume_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Встановлюємо початковий стан для конструктора резюме
    context.user_data['mode'] = 'resume_education'
    context.user_data['resume_data'] = {} # Тут зберігатимемо відповіді користувача

    await send_image(update, context, 'resume')
    text = load_message('resume')
    await send_text(update, context, text)


async def resume_finish_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    context.user_data['mode'] = None
    context.user_data.pop('resume_data', None)
    await start(update, context)

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
#Додаємо запитання на резюме
    elif mode == 'resume_education':
        context.user_data['resume_data']['education'] = update.message.text

        # Перемикаємо на наступний крок
        context.user_data['mode'] = 'resume_experience'
        await send_text(update, context,
                        "Чудово! Тепер опиши свій досвід роботи (компанії, посади, обов'язки, роки роботи):")

    elif mode == 'resume_experience':
        context.user_data['resume_data']['experience'] = update.message.text

        # Перемикаємо на фінальний крок запитань
        context.user_data['mode'] = 'resume_skills'
        await send_text(update, context,
                        "Зрозуміло. І останнє — перерахуй свої ключові навички та володіння мовами/інструментами:")

    elif mode == 'resume_skills':
        context.user_data['resume_data']['skills'] = update.message.text

        waiting_msg = await send_text(update, context, "Генерую ваше професійне резюме... 🧠📄")

        try:
            # Збираємо всі відповіді докупи
            user_info = (
                f"ОСВІТА:\n{context.user_data['resume_data']['education']}\n\n"
                f"ДОСВІД РОБОТИ:\n{context.user_data['resume_data']['experience']}\n\n"
                f"НАВИЧКИ:\n{context.user_data['resume_data']['skills']}"
            )

            # Завантажуємо HR промпт та надсилаємо запит в GPT
            prompt = load_prompt('resume')
            response = await chat_gpt.send_question(prompt, user_info)

            # Видаляємо маркер початку та кінця кодового блоку Markdown, якщо ШІ його додав
            if response.startswith("```html"):
                response = response.replace("```html", "", 1)
            if response.endswith("```"):
                response = response.rsplit("```", 1)[0]

                # Замінюємо кореневі теги, які ламають парсер Telegram
                response = response.replace("<html>", "").replace("</html>", "")
                response = response.replace("<body>", "").replace("</body>", "")
                response = response.strip()

        except Exception as e:
            logger.error(f"Resume generation error: {e}", exc_info=True)
            response = "❌ Не вдалося згенерувати резюме через технічну помилку ШІ."

        await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=waiting_msg.message_id)

        # Очищуємо режим, бо генерацію завершено
        context.user_data['mode'] = None
        context.user_data.pop('resume_data', None)

        # Використовуємо send_html, оскільки у промпті просимо ШІ використовувати HTML теги (наприклад <b>)
        await send_html(update, context, response)
        await send_text_buttons(update, context, "Бажаєте повернутись у меню?", {'resume_finish': 'Закінчити'})

    else:
        await send_text(update, context, "Будь ласка, оберіть режим у меню або введіть команду.")

#PhotoAI
async def photoai_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Встановлюємо режим користувача, щоб бот знав, що ми чекаємо на фото
    context.user_data['mode'] = 'photoai'

    # Підтягуємо картинку photoai.jpg з resources/images/
    await send_image(update, context, 'photoai')

    # Підтягуємо текст з resources/messages/photoai.txt
    text = load_message('photoai')
    await send_text(update, context, text)


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mode = context.user_data.get('mode')

    # Бот реагує на фото ТІЛЬКИ якщо користувач увійшов у режим photoai
    if mode == 'photoai':
        # Отримуємо фото у найкращій якості
        photo_file = await update.message.photo[-1].get_file()

        # НАДВАЖЛИВО: Отримуємо пряме та валідне HTTP-посилання на файл фотографії
        # Бібліотека python-telegram-bot сама згенерує повну адресу: https://api.telegram.org/...
        photo_url = photo_file.file_path

        waiting_msg = await send_text(update, context, "Аналізую зображення... 🔍")

        try:
            # Завантажуємо системний промпт з файлу
            prompt = load_prompt('photoai')

            # Викликаємо метод (тут await потрібен, бо метод async def)
            response = await chat_gpt.send_image_question(prompt, photo_url)

        except Exception as e:
            logger.error(f"Image analysis error: {e}", exc_info=True)
            response = "❌ Не вдалося розпізнати зображення. Спробуйте пізніше."

        # Видаляємо повідомлення "Аналізую зображення..." та надсилаємо опис користувачу
        await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=waiting_msg.message_id)

        # Додаємо інлайн-кнопку "Закінчити", щоб користувач міг повернутись у головне меню
        await send_text_buttons(update, context, response, {'photoai_finish': 'Закінчити'})
    else:
        # Якщо користувач скинув фото просто так, без увімкненого режиму
        await send_text(update, context, "Будь ласка, спочатку оберіть режим 'Розпізнавання зображень 📸' у меню.")


async def photoai_finish_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    context.user_data['mode'] = None
    await start(update, context)

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
    app.add_handler(CommandHandler('photoai', photoai_mode))
    app.add_handler(CommandHandler('resume', resume_mode))

    # Реєстрація кнопок вибору персонажів та завершення розмови
    app.add_handler(CallbackQueryHandler(talk_buttons_handler, pattern='^talk_(cobain|hawking|nietzsche|queen|tolkien)'))
    app.add_handler(CallbackQueryHandler(talk_finish_handler, pattern='^talk_finish$'))

    app.add_handler(CallbackQueryHandler(quiz_buttons_handler, pattern='^quiz_(prog|math|biology|other)'))
    app.add_handler(CallbackQueryHandler(quiz_next_handler, pattern='^quiz_(more|change|finish)'))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    app.add_handler(CallbackQueryHandler(resume_finish_handler, pattern='^resume_finish$'))

    app.add_handler(CallbackQueryHandler(photoai_finish_handler, pattern='^photoai_finish$'))
    app.add_handler(CallbackQueryHandler(random_buttons_handler, pattern='^random_.*'))
    app.add_handler(CallbackQueryHandler(default_callback_handler))

    logger.info("🚀 Bot started")
    app.run_polling()

if __name__ == "__main__":
    main()