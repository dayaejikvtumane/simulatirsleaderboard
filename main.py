import logging
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ConversationHandler
from config import BOT_TOKEN, ADMIN_ID
from data.db_session import global_init, create_session
from admin import admin_menu, button_click, handle_admin_message
from telegram import ReplyKeyboardRemove
from student import register_student_handlers
from mentors import register_mentor_handlers, MENTOR_NAME, MENTOR_SURNAME, MENTOR_GROUP, MENTOR_CONFIRMATION
from data.users import Mentor
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
        mentor = session.query(Mentor).filter(Mentor.telegram_id == telegram_id).first()
        if mentor:
            await admin_menu(update, context)
        else:
            await update.message.reply_text(
                'Давайте зарегистрируем вас как наставника.\n'
                'Введите ваше имя:',
                reply_markup=ReplyKeyboardRemove()
            )
            return MENTOR_NAME
    else:
        from student import student_start
        await student_start(update, context)

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
    register_admin_handlers(application)
    register_student_handlers(application)
    register_mentor_handlers(application)
    application.add_handler(ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            MENTOR_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND & filters.User(ADMIN_ID), mentors.get_name_ment)],
            MENTOR_SURNAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND & filters.User(ADMIN_ID), mentors.get_surname_ment)],
            MENTOR_GROUP: [
                MessageHandler(filters.TEXT & ~filters.COMMAND & filters.User(ADMIN_ID), mentors.get_group_ment)],
            MENTOR_CONFIRMATION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND & filters.User(ADMIN_ID), mentors.confirm_data_ment)],
        },
        fallbacks=[CommandHandler("cancel", mentors.cancel)],
    ))
    application.run_polling()


if __name__ == '__main__':
    main()