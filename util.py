from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Message, \
    BotCommand, MenuButtonCommands, BotCommandScopeChat, MenuButtonDefault
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes


async def send_text(update: Update, context: ContextTypes.DEFAULT_TYPE,
                    text: str) -> Message:
    if text.count('_') % 2 != 0:
        message = f"Рядок '{text}' є невалідним з точки зору markdown. Скористайтеся методом send_html()"
        print(message)
        return await context.bot.send_message(chat_id=update.effective_chat.id, text=message)

    text = text.encode('utf16', errors='surrogatepass').decode('utf16')
    return await context.bot.send_message(chat_id=update.effective_chat.id,
                                          text=text,
                                          parse_mode=ParseMode.MARKDOWN)


async def send_html(update: Update, context: ContextTypes.DEFAULT_TYPE,
                    text: str) -> Message:
    text = text.encode('utf16', errors='surrogatepass').decode('utf16')
    return await context.bot.send_message(chat_id=update.effective_chat.id,
                                          text=text, parse_mode=ParseMode.HTML)


async def send_text_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE,
                            text: str, buttons: dict) -> Message:
    text = text.encode('utf16', errors='surrogatepass').decode('utf16')
    keyboard = []
    for key, value in buttons.items():
        button = InlineKeyboardButton(str(value), callback_data=str(key))
        keyboard.append([button])
    reply_markup = InlineKeyboardMarkup(keyboard)
    return await context.bot.send_message(
        update.effective_message.chat_id,
        text=text, reply_markup=reply_markup,
        message_thread_id=update.effective_message.message_thread_id)


async def send_image(update: Update, context: ContextTypes.DEFAULT_TYPE,
                     name: str) -> Message:
    with open(f'resources/images/{name}.jpg', 'rb') as image:
        return await context.bot.send_photo(chat_id=update.effective_chat.id,
                                            photo=image)


async def send_image_with_text(update: Update, context: ContextTypes.DEFAULT_TYPE,
                               name: str, text: str) -> Message:
    text = text.encode('utf16', errors='surrogatepass').decode('utf16')
    with open(f'resources/images/{name}.jpg', 'rb') as image:
        return await context.bot.send_photo(chat_id=update.effective_chat.id,
                                            photo=image,
                                            caption=text,
                                            parse_mode=ParseMode.HTML)


async def send_image_with_text_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE,
                                       name: str, text: str, buttons: dict) -> Message:
    text = text.encode('utf16', errors='surrogatepass').decode('utf16')
    keyboard = []
    for key, value in buttons.items():
        button = InlineKeyboardButton(str(value), callback_data=str(key))
        keyboard.append([button])
    reply_markup = InlineKeyboardMarkup(keyboard)
    with open(f'resources/images/{name}.jpg', 'rb') as image:
        return await context.bot.send_photo(chat_id=update.effective_chat.id,
                                            photo=image,
                                            caption=text,
                                            reply_markup=reply_markup,
                                            parse_mode=ParseMode.HTML)


async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE,
                         commands: dict):
    command_list = [BotCommand(key, value) for key, value in commands.items()]
    await context.bot.set_my_commands(command_list, scope=BotCommandScopeChat(
        chat_id=update.effective_chat.id))
    await context.bot.set_chat_menu_button(menu_button=MenuButtonCommands(),
                                           chat_id=update.effective_chat.id)


def load_message(name):
    with open("resources/messages/" + name + ".txt", "r",
              encoding="utf8") as file:
        return file.read()


def load_prompt(name):
    with open("resources/prompts/" + name + ".txt", "r",
              encoding="utf8") as file:
        return file.read()


def load_resume_questions():
    questions = {}
    with open("resources/messages/resume_questions.txt", "r", encoding="utf8") as file:
        for line in file:
            line = line.strip()
            if '=' in line:
                key, value = line.split('=', 1)
                questions[key] = value
    return questions


async def default_callback_handler(update: Update,
                                   context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    query = update.callback_query.data
    await send_html(update, context, f'You have pressed button with {query} callback')
