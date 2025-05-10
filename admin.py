from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from data.db_session import create_session
from data.users import Mentor, Student, FlightResult
from config import ADMIN_ID
import logging


async def admin_menu(update, context):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("У вас нет прав доступа к этой команде.")
        return
    keyboard = []
    if update.effective_user.id == ADMIN_ID:
        keyboard.append([InlineKeyboardButton("Добавить админа", callback_data='add_admin')])
    keyboard.append([InlineKeyboardButton("Проверить данные", callback_data='check_data')])
    keyboard.append([InlineKeyboardButton("Рейтинг", callback_data='show_rating')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.callback_query:
        await update.callback_query.message.reply_text(
            "Админ-панель:",
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            "Админ-панель:",
            reply_markup=reply_markup
        )


async def button_click(update, context):
    query = update.callback_query
    await query.answer()
    if query.from_user.id != ADMIN_ID:
        await query.message.reply_text("У вас нет прав для выполнения этой операции.")
        return

    if query.data == 'add_admin':
        await add_admin_handler(update, context)
    elif query.data == 'check_data':
        await check_data_handler(update, context)
    elif query.data == 'show_rating':
        await show_rating(update, context)


async def add_admin_handler(update, context):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("У вас нет прав для выполнения этой операции.")
        return

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Введите Telegram ID нового администратора:"
    )
    context.user_data['awaiting_admin_id'] = True


async def check_data_handler(update, context):
    try:
        session = create_session()
        students_count = session.query(Student).count()
        mentors_count = session.query(Mentor).count()
        results_count = session.query(FlightResult).count()

        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"Статистика системы:\n"
                 f"Студентов: {students_count}\n"
                 f"Наставников: {mentors_count}\n"
                 f"Результатов полетов: {results_count}"
        )
    except Exception as e:
        logging.error(f"{e}")
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Произошла ошибка при получении данных."
        )
    finally:
        session.close()


async def show_rating(update, context):
    try:
        session = create_session()

        # Получаем топ-10 студентов по лучшему времени
        top_students = session.query(
            Student,
            FlightResult
        ).join(FlightResult).order_by(
            FlightResult.time.asc()
        ).limit(10).all()

        if not top_students:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Пока нет данных для рейтинга."
            )
            return

        response = "Топ-10 студентов по времени полета:\n\n"
        for i, (student, result) in enumerate(top_students, 1):
            response += (
                f"{i}. {student.name} {student.surname} ({student.group})\n"
                f"Время: {result.time} сек\n"
                f"Симулятор: {result.simulator}\n"
                f"Карта: {result.map_name}\n\n"
            )

        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=response
        )

    except Exception as e:
        logging.error(f"Error in show_rating: {e}")
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Произошла ошибка при формировании рейтинга."
        )
    finally:
        session.close()


async def handle_admin_message(update, context):
    if update.effective_user.id != ADMIN_ID:
        return

    if not context.user_data.get('awaiting_admin_id'):
        return

    text = update.message.text
    try:
        new_admin_id = int(text)
        await update.message.reply_text(f"Добавлен новый администратор {new_admin_id}")
        context.user_data.pop('awaiting_admin_id', None)
    except ValueError:
        await update.message.reply_text("Неверный формат ID. Введите числовой Telegram ID.")