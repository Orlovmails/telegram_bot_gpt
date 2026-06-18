from telegram import Update
from telegram.ext import ContextTypes

from core import reset_state
from database import save_user, get_user_stats
from util import load_message, send_html, send_image_with_text, show_main_menu


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
