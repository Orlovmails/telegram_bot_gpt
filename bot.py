import logging

from telegram import Update
from telegram.ext import ApplicationBuilder, CallbackQueryHandler, ContextTypes, CommandHandler
from telegram.ext import MessageHandler, filters

from config import BOT_TOKEN
from core import error_handler
from database import init_db
from handlers import (start, random_fact, gpt_mode, talk_mode, quiz_mode,
                      resume_mode, photoai_mode, stats_mode,
                      random_buttons_handler, gpt_finish_handler,
                      talk_buttons_handler, quiz_buttons_handler, quiz_next_handler,
                      resume_finish_handler, photoai_finish_handler,
                      handle_text, handle_photo, TEXT_HANDLERS)
from util import default_callback_handler

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)


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
