from telegram import InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from data.db_session import create_session
from data.users import FlightResult
import csv
import io


async def admin_menu(update, context):
    keyboard = [
        [InlineKeyboardButton("Добавить админа", callback_data='add_admin')],
        [InlineKeyboardButton("Изменить данные", callback_data='change_data')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "Админ-панель:",
        reply_markup=reply_markup
    )


async def button_click(update, context):
    query = update.callback_query
    await query.answer()

    if query.data == 'add_admin':
        await add_admin_handler(update, context)
    elif query.data == 'change_data':
        await change_data_handler(update, context)


async def add_admin_handler(update, context):
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Введите Telegram ID нового администратора:"
    )
    context.user_data['awaiting_admin_id'] = True


async def change_data_handler(update, context):
    session = create_session()
    flights = session.query(FlightResult).all()

    csv_buffer = io.StringIO()
    writer = csv.writer(csv_buffer, delimiter=';', quotechar='"', quoting=csv.QUOTE_MINIMAL)
    writer.writerow(["ID", "student_id", "simulator", "map_name", "flight_mode", "time", "photo_path", "date_added"])

    for flight in flights:
        writer.writerow([
            flight.id,
            flight.student_id,
            flight.simulator,
            flight.map_name,
            flight.flight_mode,
            flight.time,
            flight.photo_path,
            flight.date_added
        ])

    csv_buffer.seek(0)
    csv_bytes = io.BytesIO(csv_buffer.getvalue().encode('utf-8'))

    await context.bot.send_document(
        chat_id=update.effective_chat.id,
        document=InputFile(csv_bytes, filename='Flight_Results.csv'),
        caption="пришлите измененный CSV файл"
    )


async def handle_admin_message(update, context):
    if not context.user_data.get('awaiting_admin_id'):
        return
    text = update.message.text
    try:
        new_admin_id = int(text)
        await update.message.reply_text(f"Добавлен новый администратор с ID: {new_admin_id}")
        context.user_data.pop('awaiting_admin_id', None)
    except ValueError:
        await update.message.reply_text("Неверный формат ID. Введите числовой Telegram ID.")
