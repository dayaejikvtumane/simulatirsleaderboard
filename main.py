import logging
from telegram import ReplyKeyboardRemove, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler
from student import register_name, register_surname, register_group, register_birth_date, confirm_registration, \
    register_student_handlers, NAME, SURNAME, GROUP, BIRTH_DATE, CONFIRM
from rating import register_rating_handlers
from asynchronous import async_handler
from config import BOT_TOKEN, ADMIN_ID
from data.db_session import global_init, create_session
from data.users import Student, Mentor
from mentor import MENTOR_NAME, MENTOR_SURNAME, MENTOR_GROUP, register_mentor_name, register_mentor_surname, \
    register_mentor_group, cancel_mentor_registration, register_mentor_handlers
# настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    filename='bot.log'
)
logger = logging.getLogger(__name__)
# подключение к бд
global_init("db/air_quant_15.sqlite")


# проверка на наставника из txt
def is_mentor(telegram_id):
    try:
        with open("admin.txt", "r") as f:
            admin_ids = [line.strip() for line in f.readlines() if line.strip()]
            return str(telegram_id) in admin_ids or telegram_id == ADMIN_ID
    except FileNotFoundError:
        return telegram_id == ADMIN_ID


@async_handler
async def start(update, context):
    try:
        telegram_id = update.effective_user.id
        session = create_session()
        # проверка на студента если зареган
        student = session.query(Student).filter(Student.telegram_id == telegram_id).first()
        if student:
            keyboard = [
                [KeyboardButton('Добавить результат полёта')],
                [KeyboardButton('Рейтинг')],
                [KeyboardButton('Все мои результаты')]
            ]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            await update.message.reply_text(
                f'Добро пожаловать, {student.name}!\nВыберите действие:',
                reply_markup=reply_markup
            )
            session.close()
            return ConversationHandler.END
        # проверка наставника если зареган
        if is_mentor(telegram_id):
            mentor = session.query(Mentor).filter(Mentor.telegram_id == telegram_id).first()
            if mentor:
                keyboard = [
                    [KeyboardButton('Проверить результаты учеников')],
                    [KeyboardButton('Рейтинг')],
                    [KeyboardButton('Добавить наставника')],
                    [KeyboardButton('Мои группы')]
                ]
                reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
                await update.message.reply_text(
                    f'Добро пожаловать, наставник {mentor.name} {mentor.surname}!\n'
                    'Выберите действие:',
                    reply_markup=reply_markup
                )
                session.close()
                return ConversationHandler.END
            else:
                # если наставник незареган
                await update.message.reply_text(
                    'Привет, наставник! Давайте зарегистрируем вас в системе.\n'
                    'Введите ваше имя:',
                    reply_markup=ReplyKeyboardRemove()
                )
                session.close()
                return MENTOR_NAME
        else:
            # если ученик незареган
            await update.message.reply_text(
                'Привет! Тебя нет в моей базе, давай регистрироваться.\n'
                'Как тебя зовут?',
                reply_markup=ReplyKeyboardRemove(),
            )
            session.close()
            return NAME
    except Exception as e:
        logger.error(f"Ошибка в обработчике start: {str(e)}")
        await update.message.reply_text(
            'Произошла ошибка. Пожалуйста, попробуйте позже.',
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END
    finally:
        # если в бд что-то есть
        if 'session' in locals():
            session.close()


def register_handlers(application: Application):
    start_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, register_name)],
            SURNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, register_surname)],
            GROUP: [MessageHandler(filters.TEXT & ~filters.COMMAND, register_group)],
            BIRTH_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, register_birth_date)],
            CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_registration)],
            MENTOR_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, register_mentor_name)],
            MENTOR_SURNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, register_mentor_surname)],
            MENTOR_GROUP: [MessageHandler(filters.TEXT & ~filters.COMMAND, register_mentor_group)],
        },
        fallbacks=[CommandHandler('cancel', cancel_mentor_registration)],
    )
    application.add_handler(start_handler)
    register_student_handlers(application)
    register_mentor_handlers(application, ADMIN_ID)
    register_rating_handlers(application)


def main():
    try:
        application = Application.builder().token(BOT_TOKEN).build()
        register_handlers(application)
        application.run_polling()
    except Exception as e:
        logger.critical(f"Ошибка при запуске бота: {str(e)}")
        raise


if __name__ == '__main__':
    main()
