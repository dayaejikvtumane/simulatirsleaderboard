import logging
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ConversationHandler
from config import BOT_TOKEN, ADMIN_ID
from data.db_session import global_init, create_session
from admin import admin_menu, button_click, handle_admin_message
from telegram import ReplyKeyboardRemove, KeyboardButton, ReplyKeyboardMarkup
from student import register_student_handlers, NAME
from mentors import register_mentor_handlers, MENTOR_NAME, MENTOR_SURNAME, MENTOR_GROUP, MENTOR_CONFIRMATION, \
    mentor_start
from data.users import Mentor, Student
import mentors

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    filename='bot.log'
)
logger = logging.getLogger(__name__)

# Инициализация базы данных
global_init("db/air_quant_15.sqlite")


async def start(update, context):
    telegram_id = update.effective_user.id
    session = create_session()
    if telegram_id == ADMIN_ID:
        admin_check = session.query(Mentor).filter(Mentor.telegram_id == telegram_id).first()
        if admin_check:
            from admin import admin_menu
            await admin_menu(update, context)
        else:
            await update.message.reply_text(
                'Вы идентифицированы как администратор. Давайте зарегистрируем вас как наставника.\n'
                'Введите ваше имя:',
                reply_markup=ReplyKeyboardRemove()
            )
            return MENTOR_NAME
    else:
        student = session.query(Student).filter(Student.telegram_id == telegram_id).first()
        if student:
            keyboard = [
                [KeyboardButton('Добавить результат полёта')],
                [KeyboardButton('Рейтинг')]
            ]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            await update.message.reply_text(
                f'Добро пожаловать, {student.name}!\n'
                'Выберите действие:',
                reply_markup=reply_markup
            )
        else:
            await update.message.reply_text(
                'Привет! Тебя нет в моей базе, давай регистрироваться.\n'
                'Как тебя зовут?',
                reply_markup=ReplyKeyboardRemove(),
            )
            return NAME
    session.close()


def register_admin_handlers(application):
    application.add_handler(CommandHandler("admin", admin_menu, filters.User(ADMIN_ID)))
    application.add_handler(CallbackQueryHandler(button_click, filters.User(ADMIN_ID)))
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.User(ADMIN_ID),
        handle_admin_message
    ))


def main():
    application = Application.builder().token(BOT_TOKEN).build()
    register_student_handlers(application)
    register_mentor_handlers(application)
    register_admin_handlers(application)
    application.add_handler(CommandHandler("start", start))

    application.run_polling()


if __name__ == '__main__':
    main()
