import csv
from io import BytesIO, StringIO

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram import Update, InputFile
from telegram.ext import ContextTypes

from data.db_session import create_session
from data.users import FlightResult
from data.users import Student


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


async def change_data_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    session = create_session()
    telegram_id = update.effective_user.id
    existing_student = session.query(Student).filter(Student.telegram_id == telegram_id).first()
    if existing_student:
        flights = session.query(FlightResult).all()

        # Создаем CSV с текущими данными
        csv_buffer = StringIO()
        writer = csv.writer(csv_buffer, delimiter=';', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        writer.writerow(
            ["ID", "student_id", "simulator", "map_name", "flight_mode", "time", "photo_path", "date_added"])

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
        csv_bytes = BytesIO(csv_buffer.getvalue().encode('utf-8'))

        # Сохраняем состояние, что мы ожидаем файл для обновления
        context.user_data['awaiting_csv'] = True

        await context.bot.send_document(
            chat_id=update.effective_chat.id,
            document=InputFile(csv_bytes, filename='Flight_Results.csv'),
            caption="Пришлите измененный CSV файл для обновления данных"
        )
    else:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text='Сначала зарегестрируйся'
        )


async def handle_csv_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get('awaiting_csv'):
        return

    # Получаем файл
    file = await update.message.document.get_file()
    file_bytes = BytesIO(await file.download_as_bytearray())

    try:
        # Читаем CSV
        csv_text = file_bytes.getvalue().decode('utf-8')
        csv_reader = csv.reader(StringIO(csv_text), delimiter=';', quotechar='"')

        # Пропускаем заголовок
        next(csv_reader)

        session = create_session()
        updated_count = 0

        for row in csv_reader:

            flight_id = int(row[0])
            flight = session.query(FlightResult).filter(FlightResult.id == flight_id).first()

            if flight:
                # Обновляем поля (пропускаем ID и date_added, так как они обычно не изменяются)
                flight.student_id = row[1]
                flight.simulator = row[2]
                flight.map_name = row[3]
                flight.flight_mode = row[4]
                flight.time = row[5]
                flight.photo_path = row[6]

                updated_count += 1

        session.commit()
        await update.message.reply_text(f"Данные успешно обновлены. Обновлено записей: {updated_count}")

    except Exception as e:
        session.rollback()
        await update.message.reply_text(f"Ошибка при обновлении данных: {str(e)}")
    finally:
        session.close()
        context.user_data.pop('awaiting_csv', None)


# В вашем основном коде нужно добавить хендлер для обработки документов:
# application.add_handler(MessageHandler(filters.Document.FileExtension("csv"), handle_csv_update))

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
