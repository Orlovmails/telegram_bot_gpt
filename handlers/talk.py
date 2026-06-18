import logging

from telegram import Update
from telegram.ext import ContextTypes

from core import get_user_gpt, reset_state, rate_limit_check
from config import TALK_CHARACTERS
from util import load_message, load_prompt, send_text, send_text_buttons, send_image_with_text_buttons
from handlers.start import start

logger = logging.getLogger(__name__)


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
