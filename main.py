import logging
from telegram.ext import Application
from config import BOT_TOKEN
from data.db_session import global_init, create_session
from telegram import ReplyKeyboardRemove, KeyboardButton, ReplyKeyboardMarkup
from student import register_student_handlers, NAME
from data.users import Mentor, Student

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    filename='bot.log'
)
logger = logging.getLogger(__name__)

global_init("db/air_quant_15.sqlite")

async def start(update, context):
    telegram_id = update.effective_user.id
    session = create_session()
    student = session.query(Student).filter(Student.telegram_id == telegram_id).first()
    if student:
        keyboard = [
            [KeyboardButton('Добавить результат полёта')],
            [KeyboardButton('Рейтинг')]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text(
            f'Добро пожаловать, {student.name}!\nВыберите действие:',
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            'Привет! Тебя нет в моей базе, давай регистрироваться.\nКак тебя зовут?',
            reply_markup=ReplyKeyboardRemove(),
        )
        return NAME
    session.close()

def main():
    application = Application.builder().token(BOT_TOKEN).build()
    register_student_handlers(application)
    application.run_polling()

if __name__ == '__main__':
    main()