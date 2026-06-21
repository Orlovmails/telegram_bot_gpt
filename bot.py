import logging
import os
import random
from dotenv import load_dotenv

from telegram import Update
from telegram.ext import ApplicationBuilder, CallbackQueryHandler, ContextTypes, CommandHandler
from telegram.ext import MessageHandler, filters

from gpt import ChatGptService
from database import (init_db, save_user, update_stat, save_quiz_score,
                      get_user_stats, check_rate_limit)
from util import (load_message, send_text, show_main_menu,
                  default_callback_handler, load_prompt, send_text_buttons, send_html,
                  send_image_with_text, send_image_with_text_buttons, load_resume_questions)

RESUME_QUESTIONS = load_resume_questions()

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ChatGPT_TOKEN = os.getenv("CHATGPT_TOKEN")

if not BOT_TOKEN or not ChatGPT_TOKEN:
    raise ValueError(
        "❌ ПОМИЛКА: Токени BOT_TOKEN або CHATGPT_TOKEN не знайдені у файлі .env!\n"
        "Перевірте, чи створили ви файл .env в папці з ботом."
    )

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

QUIZ_TOPICS = ['quiz_prog', 'quiz_math', 'quiz_biology']

TALK_CHARACTERS = {
    'talk_cobain': 'Курт Кобейн 🎸',
    'talk_hawking': 'Стівен Гокінг 🌌',
    'talk_nietzsche': 'Фрідріх Ніцше 🧠',
    'talk_queen': 'Єлизавета II 👑',
    'talk_tolkien': 'Джон Толкін 📖',
}

QUIZ_TOPICS_BTN = {
    'quiz_prog': 'Програмування 💻',
    'quiz_math': 'Математика 🟰',
    'quiz_biology': 'Біологія 🧬',
    'quiz_random': 'Випадкова тема 🎲',
}

QUIZ_NEXT_BTNS = {
    'quiz_more': 'Хочу ще питання',
    'quiz_random_next': 'Випадкова тема 🎲',
    'quiz_change': 'Змінити тему',
    'quiz_finish': 'Закінчити квіз'
}


def get_user_gpt(context: ContextTypes.DEFAULT_TYPE) -> ChatGptService:
    if 'gpt' not in context.user_data:
        context.user_data['gpt'] = ChatGptService(ChatGPT_TOKEN)
    return context.user_data['gpt']


def reset_state(context: ContextTypes.DEFAULT_TYPE):
    context.user_data['gpt'] = ChatGptService(ChatGPT_TOKEN)
    context.user_data['mode'] = None
    context.user_data['quiz_score'] = 0
    context.user_data['quiz_topic_selected'] = False
    context.user_data['quiz_current_topic'] = None
    context.user_data['quiz_waiting_for_action'] = False
    context.user_data['talk_waiting_for_selection'] = False
    context.user_data['resume_data'] = {}


async def rate_limit_check(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int) -> bool:
    if not check_rate_limit(user_id, 'gpt'):
        await send_text(update, context, "⏳ Забагато запитів. Зачекайте хвилину.")
        return True
    return False


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Exception while handling an update: {context.error}", exc_info=context.error)
    if isinstance(update, Update) and update.effective_message:
        await update.effective_message.reply_text("❌ Сталася помилка. Спробуйте пізніше.")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    save_user(user.id, user.username, user.first_name)

    reset_state(context)
    text = load_message('main')
    await send_image_with_text(update, context, 'main', text)
    await show_main_menu(update, context, {
        'start': 'Головне меню',
        'random': 'Дізнатися випадковий цікавий факт 🧠',
        'gpt': 'Задати питання чату GPT 🤖',
        'talk': 'Поговорити з відомою особистістю 👤',
        'quiz': 'Взяти участь у квізі ❓',
        'photoai': 'Розпізнавання зображень 📸',
        'resume': 'Допомога з резюме 📝',
        'stats': 'Моя статистика 📊'
    })


async def random_fact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reset_state(context)
    context.user_data['mode'] = 'random'
    user_id = update.effective_user.id
    if await rate_limit_check(update, context, user_id):
        return

    waiting_msg = await send_text(update, context, load_message('random'))
    try:
        gpt = get_user_gpt(context)
        prompt = load_prompt('random')
        response = await gpt.send_question(prompt, "Розкажи випадковий цікавий факт")
        update_stat(user_id, 'facts_count')
    except Exception as e:
        logger.error(f"GPT error: {e}", exc_info=True)
        response = "❌ Не вдалося отримати факт. Спробуйте пізніше."

    await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=waiting_msg.message_id)
    await send_image_with_text_buttons(update, context, 'random', response, {
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


async def gpt_finish_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await start(update, context)


async def resume_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reset_state(context)
    context.user_data['mode'] = 'resume_education'
    text = load_message('resume')
    await send_image_with_text(update, context, 'resume', text)


async def resume_finish_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await start(update, context)


async def gpt_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reset_state(context)
    gpt = get_user_gpt(context)
    gpt.set_prompt(load_prompt('gpt'))
    context.user_data['mode'] = 'gpt'
    await send_image_with_text(update, context, 'gpt', load_message('gpt'))


async def talk_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reset_state(context)
    context.user_data['mode'] = 'talk'
    context.user_data['talk_waiting_for_selection'] = True
    await send_image_with_text_buttons(update, context, 'talk', load_message('talk'), TALK_CHARACTERS)


async def talk_buttons_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    query = update.callback_query.data

    if query == 'talk_finish':
        await start(update, context)
        return

    context.user_data['talk_waiting_for_selection'] = False

    try:
        gpt = get_user_gpt(context)
        gpt.set_prompt(load_prompt(query))
        await send_text(update, context, "Привіт! Я готовий до розмови з тобою. Запитуй будь-що.")
    except Exception as e:
        logger.error(f"Error loading talk prompt: {e}")
        await send_text(update, context, "❌ Не вдалося завантажити промпт особистості.")


async def quiz_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reset_state(context)
    context.user_data['mode'] = 'quiz'
    await send_image_with_text_buttons(update, context, 'quiz', load_message('quiz'), QUIZ_TOPICS_BTN)


async def quiz_buttons_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    query = update.callback_query.data

    try:
        gpt = get_user_gpt(context)
        gpt.set_prompt(load_prompt('quiz'))
        context.user_data['quiz_topic_selected'] = True

        if query == 'quiz_random':
            query = random.choice(QUIZ_TOPICS)

        context.user_data['quiz_current_topic'] = query
        question = await gpt.add_message(query)
        await send_html(update, context, question)
    except Exception as e:
        logger.error(f"Quiz starting error: {e}", exc_info=True)
        await send_text(update, context, "❌ Не вдалося розпочати квіз. Спробуйте ще раз.")


async def quiz_next_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    query = update.callback_query.data
    context.user_data['quiz_waiting_for_action'] = False

    try:
        gpt = get_user_gpt(context)
        topic = context.user_data.get('quiz_current_topic', QUIZ_TOPICS[0])
        if query == 'quiz_more':
            pass
        elif query == 'quiz_random_next':
            topic = random.choice(QUIZ_TOPICS)
            context.user_data['quiz_current_topic'] = topic
        elif query == 'quiz_change':
            await quiz_mode(update, context)
            return
        elif query == 'quiz_finish':
            user_id = update.effective_user.id
            save_quiz_score(user_id, 'quiz', context.user_data.get('quiz_score', 0))
            update_stat(user_id, 'quiz_games')
            await start(update, context)
            return

        question = await gpt.add_message(topic)
        await send_html(update, context, question)
    except Exception as e:
        logger.error(f"Quiz next error: {e}", exc_info=True)
        await send_text(update, context, "❌ Сталася помилка при генерації наступного питання.")


async def handle_gpt_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if await rate_limit_check(update, context, user_id):
        return

    waiting_msg = await send_text(update, context, "Thinking... 🤖")
    try:
        gpt = get_user_gpt(context)
        response = await gpt.add_message(update.message.text)
        update_stat(user_id, 'gpt_messages')
    except Exception as e:
        logger.error(f"GPT error: {e}")
        response = "❌ Помилка сервісу ШІ."

    await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=waiting_msg.message_id)
    await send_text_buttons(update, context, response, {'gpt_finish': 'Закінчити'})


async def handle_talk_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('talk_waiting_for_selection'):
        await send_image_with_text_buttons(update, context, 'talk',
                                           "Будь ласка, оберіть відому особистість:", TALK_CHARACTERS)
        return

    user_id = update.effective_user.id
    if await rate_limit_check(update, context, user_id):
        return

    try:
        gpt = get_user_gpt(context)
        response = await gpt.add_message(update.message.text)
    except Exception as e:
        logger.error(f"GPT talk error: {e}")
        response = "❌ Тимчасова помилка зв'язку з персонажем."

    await send_text_buttons(update, context, response, {'talk_finish': 'Закінчити'})


async def handle_quiz_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('quiz_waiting_for_action'):
        await send_text_buttons(update, context, "Будь ласка, оберіть що робити далі:", QUIZ_NEXT_BTNS)
        return

    if not context.user_data.get('quiz_topic_selected'):
        await send_image_with_text_buttons(update, context, 'quiz',
                                           "Будь ласка, оберіть тему кнопкою нижче:", QUIZ_TOPICS_BTN)
        return

    user_id = update.effective_user.id
    if await rate_limit_check(update, context, user_id):
        return

    try:
        gpt = get_user_gpt(context)
        result = await gpt.add_message(update.message.text)

        if result and result.startswith("✅"):
            context.user_data['quiz_score'] += 1

        await send_html(update, context, f"{result}\n\n🏆 Ваш поточний рахунок: {context.user_data['quiz_score']}")
        await send_text_buttons(update, context, "Що робимо далі?", QUIZ_NEXT_BTNS)
        context.user_data['quiz_waiting_for_action'] = True
    except Exception as e:
        logger.error(f"Quiz process error: {e}", exc_info=True)
        await send_text(update, context, "❌ Сталася помилка при обробці вашої відповіді.")


async def handle_resume_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mode = context.user_data.get('mode')
    user_id = update.effective_user.id

    if mode == 'resume_education':
        context.user_data['resume_data']['education'] = update.message.text
        context.user_data['mode'] = 'resume_experience'
        await send_text(update, context, RESUME_QUESTIONS['resume_education'])

    elif mode == 'resume_experience':
        context.user_data['resume_data']['experience'] = update.message.text
        context.user_data['mode'] = 'resume_skills'
        await send_text(update, context, RESUME_QUESTIONS['resume_experience'])

    elif mode == 'resume_skills':
        context.user_data['resume_data']['skills'] = update.message.text
        waiting_msg = await send_text(update, context, RESUME_QUESTIONS['resume_skills'])

        try:
            user_info = (
                f"ОСВІТА:\n{context.user_data['resume_data']['education']}\n\n"
                f"ДОСВІД РОБОТИ:\n{context.user_data['resume_data']['experience']}\n\n"
                f"НАВИЧКИ:\n{context.user_data['resume_data']['skills']}"
            )
            gpt = get_user_gpt(context)
            response = await gpt.send_question(load_prompt('resume'), user_info)
            update_stat(user_id, 'resume_count')

            if response.startswith("```html"):
                response = response.replace("```html", "", 1)
            if response.endswith("```"):
                response = response.rsplit("```", 1)[0]
            response = response.replace("<html>", "").replace("</html>", "")
            response = response.replace("<body>", "").replace("</body>", "")
            response = response.strip()
        except Exception as e:
            logger.error(f"Resume generation error: {e}", exc_info=True)
            response = "❌ Не вдалося згенерувати резюме через технічну помилку ШІ."

        context.user_data['mode'] = None
        await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=waiting_msg.message_id)
        await send_html(update, context, response)
        await send_text_buttons(update, context, "Бажаєте повернутись у меню?", {'resume_finish': 'Закінчити'})


async def handle_random_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_text(update, context, "Будь ласка, використовуйте кнопки для керування фактами.")


TEXT_HANDLERS = {
    'gpt': handle_gpt_text,
    'talk': handle_talk_text,
    'quiz': handle_quiz_text,
    'random': handle_random_text,
    'resume_education': handle_resume_text,
    'resume_experience': handle_resume_text,
    'resume_skills': handle_resume_text,
}


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mode = context.user_data.get('mode')
    handler = TEXT_HANDLERS.get(mode)
    if handler:
        await handler(update, context)
    else:
        await send_text(update, context, "Будь ласка, оберіть режим у меню або введіть команду.")


async def photoai_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reset_state(context)
    context.user_data['mode'] = 'photoai'
    await send_image_with_text(update, context, 'photoai', load_message('photoai'))


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('mode') != 'photoai':
        await send_text(update, context, "Будь ласка, спочатку оберіть режим 'Розпізнавання зображень 📸' у меню.")
        return

    photo_file = await update.message.photo[-1].get_file()
    waiting_msg = await send_text(update, context, "Аналізую зображення... 🔍")

    try:
        gpt = get_user_gpt(context)
        response = await gpt.send_image_question(load_prompt('photoai'), photo_file.file_path)
    except Exception as e:
        logger.error(f"Image analysis error: {e}", exc_info=True)
        response = "❌ Не вдалося розпізнати зображення. Спробуйте пізніше."

    await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=waiting_msg.message_id)
    await send_text_buttons(update, context, response, {'photoai_finish': 'Закінчити'})


async def photoai_finish_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await start(update, context)


async def stats_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    stats = get_user_stats(update.effective_user.id)
    await send_html(update, context, (
        f"📊 <b>Ваша статистика:</b>\n\n"
        f"🧠 Випадкових фактів: <b>{stats['facts_count']}</b>\n"
        f"🤖 Повідомлень з GPT: <b>{stats['gpt_messages']}</b>\n"
        f"❓ Ігор у квіз: <b>{stats['quiz_games']}</b>\n"
        f"🏆 Найкращий рахунок: <b>{stats['quiz_best_score']}</b>\n"
        f"📝 Резюме згенеровано: <b>{stats['resume_count']}</b>"
    ))


def main():
    init_db()
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_error_handler(error_handler)

    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('random', random_fact))
    app.add_handler(CommandHandler('gpt', gpt_mode))
    app.add_handler(CommandHandler('talk', talk_mode))
    app.add_handler(CommandHandler('quiz', quiz_mode))
    app.add_handler(CommandHandler('photoai', photoai_mode))
    app.add_handler(CommandHandler('resume', resume_mode))
    app.add_handler(CommandHandler('stats', stats_mode))

    app.add_handler(CallbackQueryHandler(talk_buttons_handler, pattern='^talk_'))
    app.add_handler(CallbackQueryHandler(quiz_buttons_handler, pattern='^quiz_(prog|math|biology|random)$'))
    app.add_handler(CallbackQueryHandler(quiz_next_handler, pattern='^quiz_(more|random_next|change|finish)$'))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    app.add_handler(CallbackQueryHandler(resume_finish_handler, pattern='^resume_finish$'))
    app.add_handler(CallbackQueryHandler(photoai_finish_handler, pattern='^photoai_finish$'))
    app.add_handler(CallbackQueryHandler(gpt_finish_handler, pattern='^gpt_finish$'))
    app.add_handler(CallbackQueryHandler(random_buttons_handler, pattern='^random_.*'))
    app.add_handler(CallbackQueryHandler(default_callback_handler))

    logger.info("🚀 Bot started")
    app.run_polling()


if __name__ == "__main__":
    main()
