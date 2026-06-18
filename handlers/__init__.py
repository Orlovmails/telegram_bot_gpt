from telegram import Update
from telegram.ext import ContextTypes

from handlers.start import start, stats_mode
from handlers.random import random_fact, random_buttons_handler, handle_random_text
from handlers.gpt import gpt_mode, handle_gpt_text, gpt_finish_handler
from handlers.talk import talk_mode, talk_buttons_handler, handle_talk_text
from handlers.quiz import quiz_mode, quiz_buttons_handler, quiz_next_handler, handle_quiz_text
from handlers.resume import resume_mode, handle_resume_text, resume_finish_handler
from handlers.photoai import photoai_mode, handle_photo, photoai_finish_handler
from util import send_text

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
