import logging

from telegram import Update
from telegram.ext import ContextTypes

from core import get_user_gpt, reset_state, rate_limit_check
from database import update_stat
from util import load_message, load_prompt, send_text, send_text_buttons, send_image_with_text
from handlers.start import start

logger = logging.getLogger(__name__)


async def gpt_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reset_state(context)
    gpt = get_user_gpt(context)
    gpt.set_prompt(load_prompt('gpt'))
    context.user_data['mode'] = 'gpt'
    await send_image_with_text(update, context, 'gpt', load_message('gpt'))


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


async def gpt_finish_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await start(update, context)
