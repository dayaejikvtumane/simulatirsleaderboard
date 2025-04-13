import logging
from telegram.ext import Application, MessageHandler, filters
from config import BOT_TOKEN
from data import db_session

db_session.global_init("db/air_quant_15.sqlite")

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.DEBUG
)

logger = logging.getLogger(__name__)


async def welcome(update, context):
    await update.message.reply_text('Привет! Меня зовут Эир, я запомню твои результаты и покажу твой рейтинг!\n'
                                    'Прежде чем начать, как тебя зовут?')


def main():
    application = Application.builder().token(BOT_TOKEN).build()
    text_handler = MessageHandler(filters.TEXT, welcome)
    application.add_handler(text_handler)
    application.run_polling()


if __name__ == '__main__':
    main()
