import logging

from telegram import Update
from telegram.ext import ContextTypes

from core import get_user_gpt, reset_state
from util import load_message, load_prompt, send_text, send_text_buttons, send_image_with_text
from handlers.start import start

logger = logging.getLogger(__name__)


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
