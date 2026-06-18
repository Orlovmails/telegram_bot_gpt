import logging

from telegram import Update
from telegram.ext import ContextTypes

from gpt import ChatGptService
from config import ChatGPT_TOKEN
from database import check_rate_limit
from util import send_text, send_html

logger = logging.getLogger(__name__)


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
