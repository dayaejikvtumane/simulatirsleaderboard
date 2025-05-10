import logging
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from config import BOT_TOKEN, ADMIN_ID
from data.db_session import global_init
from admin import admin_menu, button_click, handle_admin_message, handle_csv_update
from student import register_student_handlers

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
    print(update.effective_user.id)
    if update.effective_user.id == ADMIN_ID:
        from admin import admin_menu

        await admin_menu(update, context)
    else:
        from student import student_start
        await student_start(update, context)


def register_admin_handlers(application):
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.User(ADMIN_ID),
        handle_admin_message
    ))
    application.add_handler(CallbackQueryHandler(button_click))
    application.add_handler(CommandHandler("admin", admin_menu))


def main():
    application = Application.builder().token(BOT_TOKEN).build()
    register_admin_handlers(application)
    register_student_handlers(application)
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.Document.FileExtension("csv"), handle_csv_update))
    application.run_polling()


if __name__ == '__main__':
    main()
