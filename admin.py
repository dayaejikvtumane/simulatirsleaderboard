from telegram import InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from data.db_session import create_session
from data.users import FlightResult
import csv
import io



async def admin_menu(update, context):
    keyboard = [
        [InlineKeyboardButton("Добавить админа", callback_data='add_admin')],
        [InlineKeyboardButton("Проверить данные", callback_data='check_data')],
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
    elif query.data == 'check_data':
        await check_data_handler(update, context)

async def add_admin_handler(update, context):
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Введите Telegram ID нового администратора:"
    )
    context.user_data['awaiting_admin_id'] = True


async def check_data_handler(update, context):
    session = create_session()
    sp_flight_results = []

    for i in session.query(FlightResult).all():
        sp_flight_results.append(str(i))

    csv_buffer = io.StringIO()
    writer = csv.writer(csv_buffer, delimiter=';', quotechar='"', quoting=csv.QUOTE_MINIMAL)

    for i in sp_flight_results:
        data = i.split()
        print(data)
        writer.writerow([data[0], data[1], data[2], data[3], data[4], data[5]])

    csv_buffer.seek(0)
    csv_bytes = io.BytesIO(csv_buffer.getvalue().encode('utf-8'))
    csv_bytes.seek(0)

    await context.bot.send_document(
        chat_id=update.effective_chat.id,
        document=InputFile(csv_bytes, filename='Flight_Results.csv'),
        caption="Flight_Results"
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