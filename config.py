import os

from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ChatGPT_TOKEN = os.getenv("CHATGPT_TOKEN")

if not BOT_TOKEN or not ChatGPT_TOKEN:
    raise ValueError(
        "❌ ПОМИЛКА: Токени BOT_TOKEN або CHATGPT_TOKEN не знайдені у файлі .env!\n"
        "Перевірте, чи створили ви файл .env в папці з ботом."
    )

QUIZ_TOPICS = ['quiz_prog', 'quiz_math', 'quiz_biology']

TALK_CHARACTERS = {
    'talk_cobain': 'Курт Кобейн 🎸',
    'talk_hawking': 'Стівен Гокінг 🌌',
    'talk_nietzsche': 'Фрідріх Ніцше 🧠',
    'talk_queen': 'Єлизавета II 👑',
    'talk_tolkien': 'Джон Толкін 📖',
}

QUIZ_TOPICS_BTN = {
    'quiz_prog': 'Програмування 💻',
    'quiz_math': 'Математика 🟰',
    'quiz_biology': 'Біологія 🧬',
    'quiz_random': 'Випадкова тема 🎲',
}

QUIZ_NEXT_BTNS = {
    'quiz_more': 'Хочу ще питання',
    'quiz_random_next': 'Випадкова тема 🎲',
    'quiz_change': 'Змінити тему',
    'quiz_finish': 'Закінчити квіз'
}

from util import load_resume_questions

RESUME_QUESTIONS = load_resume_questions()
