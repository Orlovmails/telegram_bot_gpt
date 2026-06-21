import logging
import random

from telegram import Update
from telegram.ext import ContextTypes

from core import get_user_gpt, reset_state, rate_limit_check
from config import QUIZ_TOPICS, QUIZ_TOPICS_BTN, QUIZ_NEXT_BTNS
from database import save_quiz_score, update_stat
from util import load_message, load_prompt, send_text, send_html, send_text_buttons, send_image_with_text_buttons
from handlers.start import start

logger = logging.getLogger(__name__)


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
