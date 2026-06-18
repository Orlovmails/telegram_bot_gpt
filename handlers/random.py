import logging

from telegram import Update
from telegram.ext import ContextTypes

from core import get_user_gpt, reset_state, rate_limit_check
from database import update_stat
from util import load_message, load_prompt, send_text, send_text_buttons, send_image_with_text_buttons
from handlers.start import start

logger = logging.getLogger(__name__)


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


async def handle_random_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_text(update, context, "Будь ласка, використовуйте кнопки для керування фактами.")
