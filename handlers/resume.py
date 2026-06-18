import logging

from telegram import Update
from telegram.ext import ContextTypes

from core import get_user_gpt, reset_state
from config import RESUME_QUESTIONS
from database import update_stat
from util import load_message, load_prompt, send_text, send_html, send_text_buttons, send_image_with_text
from handlers.start import start

logger = logging.getLogger(__name__)


async def resume_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reset_state(context)
    context.user_data['mode'] = 'resume_education'
    text = load_message('resume')
    await send_image_with_text(update, context, 'resume', text)


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


async def resume_finish_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await start(update, context)
