from config import ADMIN_ID
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler, ContextTypes
from data.db_session import create_session
from data.users import Student, FlightResult
from datetime import datetime
import logging
from telegram import ReplyKeyboardRemove, ReplyKeyboardMarkup, KeyboardButton
from io import BytesIO

NAME, SURNAME, GROUP, BIRTH_DATE, CONFIRM, FLIGHT_SIMULATOR, FLIGHT_MODE, FLIGHT_MAP, FLIGHT_TIME, FLIGHT_PHOTO = range(10)

async def student_start(update, context):
    telegram_id = update.effective_user.id
    session = create_session()
    existing_student = session.query(Student).filter(Student.telegram_id == telegram_id).first()
    session.close()
    if existing_student:
        keyboard = [
            [KeyboardButton('Добавить результат полёта')],
            [KeyboardButton('Рейтинг')]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text(
            f'Вы уже зарегистрированы!\n'
            f'Ваши данные:\n'
            f'Имя: {existing_student.name}\n'
            f'Фамилия: {existing_student.surname}\n'
            f'Группа: {existing_student.group}\n'
            f"Дата рождения: {existing_student.birth_date.strftime('%d.%m.%Y') if existing_student.birth_date else 'Не указана'}\n\n"
            'Выберите действие:',
            reply_markup=reply_markup
        )
        return ConversationHandler.END

    await update.message.reply_text(
        'Привет! Тебя нет в моей базе, давай регистрироваться.\n'
        'Как тебя зовут?',
        reply_markup=ReplyKeyboardRemove(),
    )
    return NAME


async def handle_student_choice(update, context):
    text = update.message.text
    if text == "Добавить результат полёта":
        return await add_flight_result(update, context)
    elif text == "Просмотреть мои результаты":
        await view_my_results(update, context)
        return ConversationHandler.END
    else:
        await update.message.reply_text("Выберите дейтвие")
        return ConversationHandler.END


async def register_name(update, context):
    name = update.message.text.strip()
    if not name.isalpha():
        await update.message.reply_text('Имя должно содержать только буквы.')
        return NAME
    context.user_data["name"] = name
    await update.message.reply_text('Супер! Теперь введите свою фамилию:')
    return SURNAME


async def register_surname(update, context):
    surname = update.message.text.strip()
    if not surname.isalpha():
        await update.message.reply_text('Фамилия должна содержать только буквы.')
        return SURNAME
    context.user_data["surname"] = surname
    await update.message.reply_text('Введите свою группу:')
    return GROUP


async def register_group(update, context):
    group = update.message.text.strip()
    if not group:
        await update.message.reply_text('Пожалуйста, введите свою группу:')
        return GROUP
    context.user_data["group"] = group
    await update.message.reply_text(
        'Введите свою дату рождения в формате ДД.ММ.ГГГГ (например, 01.01.2000):'
    )
    return BIRTH_DATE


async def register_birth_date(update, context):
    try:
        birth_date = datetime.strptime(update.message.text, "%d.%m.%Y").date()
        if birth_date > datetime.now().date():
            await update.message.reply_text(
                'Дата рождения не может быть в будущем. Пожалуйста, введите корректную дату:'
            )
            return BIRTH_DATE
        context.user_data["birth_date"] = birth_date
    except ValueError:
        await update.message.reply_text(
            'Неверный формат даты. Пожалуйста, введите дату в формате ДД.ММ.ГГГГ:'
        )
        return BIRTH_DATE

    await update.message.reply_text(
        "Проверьте ваши данные:\n"
        f"Имя: {context.user_data['name']}\n"
        f"Фамилия: {context.user_data['surname']}\n"
        f"Группа: {context.user_data['group']}\n"
        f"Дата рождения: {context.user_data['birth_date'].strftime('%d.%m.%Y')}\n\n"
        "Всё верно? (да/нет)",
    )
    return CONFIRM


async def confirm_registration(update, context):
    answer = update.message.text.lower()
    if answer not in ['да', 'нет']:
        await update.message.reply_text("Пожалуйста, ответьте 'да' или 'нет':")
        return CONFIRM

    if answer == 'нет':
        await update.message.reply_text('Регистрация отменена.', reply_markup=ReplyKeyboardRemove())
        context.user_data.clear()
        return ConversationHandler.END

    session = create_session()
    try:
        student = Student(
            name=context.user_data["name"],
            surname=context.user_data["surname"],
            group=context.user_data["group"],
            birth_date=context.user_data["birth_date"],
            telegram_id=update.effective_user.id,
        )
        session.add(student)
        session.commit()

        keyboard = [
            [KeyboardButton("Добавить результат полёта")],
            [KeyboardButton("Просмотреть мои результаты")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

        await update.message.reply_text(
           ' "Регистрация успешно завершена! Выберите действие:"',
            reply_markup=reply_markup
        )
    except Exception as e:
        session.rollback()
        logging.error(f"Ошибка при регистрации: {str(e)}")
        await update.message.reply_text(
            'Ошибка при регистрации. Пожалуйста, попробуйте позже.'
        )
    session.close()
    context.user_data.clear()

    return ConversationHandler.END


async def add_flight_result(update, context):
    keyboard = [
        [KeyboardButton("FPV Freerider")],
        [KeyboardButton("DCL The Game")],
        [KeyboardButton("Liftoff")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text(
        'Выберите симулятор:',
        reply_markup=reply_markup
    )
    return FLIGHT_SIMULATOR


async def process_simulator(update, context):
    context.user_data['simulator'] = update.message.text

    keyboard = [
        [KeyboardButton("Self-Leveling")],
        [KeyboardButton("Acro")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text(
        'Выберите режим полета:',
        reply_markup=reply_markup
    )
    return FLIGHT_MODE


async def process_flight_mode(update, context):
    context.user_data['flight_mode'] = update.message.text

    keyboard = [
        [KeyboardButton("map1")],
        [KeyboardButton("map2")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text(
        "Выберите карту:",
        reply_markup=reply_markup
    )
    return FLIGHT_MAP


async def process_map(update, context):
    context.user_data['map_name'] = update.message.text
    await update.message.reply_text(
        'Введите время прохождения в секундах (например: 12.523):',
        reply_markup=ReplyKeyboardRemove()
    )
    return FLIGHT_TIME


async def process_time(update, context):
    try:
        time = float(update.message.text.replace(',', '.'))
        if time <= 0:
            raise ValueError('Время должно быть положительным')
        context.user_data['time'] = time
        await update.message.reply_text(
            'Отправьте фото результата или нажмите /skip'
        )
        return FLIGHT_PHOTO
    except ValueError as e:
        await update.message.reply_text(
            f'Некорректное время. Пожалуйста, введите число (например: 10.53)\nОшибка: {e}'
        )
        return FLIGHT_TIME


async def process_photo(update, context):
    if update.message.photo:
        photo_file = await update.message.photo[-1].get_file()
        photo_data = BytesIO()
        await photo_file.download_to_memory(out=photo_data)
        context.user_data['photo_data'] = photo_data.getvalue()
    return await save_flight_result(update, context)


async def skip_photo(update, context):
    context.user_data['photo_data'] = None
    return await save_flight_result(update, context)


async def save_flight_result(update, context):
    session = create_session()
    try:
        student = session.query(Student).filter(
            Student.telegram_id == update.effective_user.id
        ).first()

        if not student:
            await update.message.reply_text('Начните со /start')
            return ConversationHandler.END

        flight_result = FlightResult(
            student_id=student.id,
            simulator=context.user_data['simulator'],
            flight_mode=context.user_data['flight_mode'],
            map_name=context.user_data['map_name'],
            time=context.user_data['time'],
            photo_data=context.user_data.get('photo_data'),
            date_added=datetime.now()
        )

        session.add(flight_result)
        session.commit()

        keyboard = [
            [KeyboardButton('Добавить результат полёта')],
            [KeyboardButton('Просмотреть результаты')]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

        await update.message.reply_text(
            'Результат успешно сохранен!',
            reply_markup=reply_markup
        )
    except Exception as e:
        session.rollback()
        logging.error(f'Ошибка сохранения результата: {str(e)}')
        await update.message.reply_text(
            f'Ошибка при сохранении: {str(e)}\nПопробуйте позже.'
        )

    session.close()
    context.user_data.clear()

    return ConversationHandler.END


async def view_my_results(update, context):
    session = create_session()
    try:
        student = session.query(Student).filter(
            Student.telegram_id == update.effective_user.id
        ).first()

        if not student:
            await update.message.reply_text('Сначала зарегистрируйтесь!')
            return

        results = session.query(FlightResult).filter(
            FlightResult.student_id == student.id
        ).order_by(FlightResult.date_added.desc()).all()

        if not results:
            await update.message.reply_text('У вас пока нет сохраненных результатов.')
            return

        response = ['Ваши результаты:']
        for idx, result in enumerate(results, 1):
            response.append(
                f'{idx}. {result.simulator} - {result.map_name}\n'
                f'Режим: {result.flight_mode}\n'
                f'Время: {result.time} сек\n'
                f"Дата: {result.date_added.strftime('%d.%m.%Y')}\n"
                f"{'Есть фото' if result.photo_data else ''}"
            )

        await update.message.reply_text("\n\n".join(response))
    except Exception as e:
        logging.error(f'Ошибка при просмотре результатов: {str(e)}')
        await update.message.reply_text(
            'Произошла ошибка при получении результатов. Попробуйте позже.'
        )
    session.close()


async def cancel(update, context):
    await update.message.reply_text(
        'Действие отменено.', reply_markup=ReplyKeyboardRemove()
    )
    context.user_data.clear()
    return ConversationHandler.END


def register_student_handlers(application: Application):
    registration_handler = ConversationHandler(
        entry_points=[CommandHandler('start', student_start)],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, register_name)],
            SURNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, register_surname)],
            GROUP: [MessageHandler(filters.TEXT & ~filters.COMMAND, register_group)],
            BIRTH_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, register_birth_date)],
            CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_registration)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    flight_result_handler = ConversationHandler(
        entry_points=[MessageHandler(
            filters.Regex(r'^Добавить результат полёта$') & ~filters.COMMAND,
            add_flight_result
        )],
        states={
            FLIGHT_SIMULATOR: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_simulator)],
            FLIGHT_MODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_flight_mode)],
            FLIGHT_MAP: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_map)],
            FLIGHT_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_time)],
            FLIGHT_PHOTO: [
                MessageHandler(filters.PHOTO & ~filters.COMMAND, process_photo),
                CommandHandler("skip", skip_photo)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    view_results_handler = MessageHandler(
        filters.Regex(r'^Просмотреть мои результаты$') & ~filters.COMMAND,
        view_my_results
    )
    application.add_handler(registration_handler)
    application.add_handler(flight_result_handler)
    application.add_handler(view_results_handler)
