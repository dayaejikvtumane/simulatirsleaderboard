from config import ADMIN_ID
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler, ContextTypes
from data.db_session import create_session
from data.users import Student
from datetime import datetime
import logging
from telegram import ReplyKeyboardRemove

NAME, SURNAME, GROUP, BIRTH_DATE, CONFIRMATION = range(5)


async def student_start(update, context):
    print(f'СТАРТ СТУДЕНТА! ID: {update.effective_user.id}')
    telegram_id = update.effective_user.id
    session = create_session()
    existing_student = session.query(Student).filter(Student.telegram_id == telegram_id).first()
    session.close()
    if existing_student:
        await update.message.reply_text(
            f'Вы уже зарегистрированы в системе!\n'
            f'Ваши данные:\n'
            f'Имя: {existing_student.name}\n'
            f'Фамилия: {existing_student.surname}\n'
            f'Группа: {existing_student.group}\n'
            f"Дата рождения: {existing_student.birth_date.strftime('%d.%m.%Y') if existing_student.birth_date else 'Не указана'}",
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END

    await update.message.reply_text(
        'Привет! Тебя нет в моей базе, давай зарегистрируем тебя в системе.\n'
        'Как тебя зовут? (Введите только имя)',
        reply_markup=ReplyKeyboardRemove(),
    )
    return NAME


async def get_name(update, context):
    print(f'имя: {update.message.text}')
    name = update.message.text.strip()
    if not name.isalpha():
        await update.message.reply_text('Имя должно содержать только буквы.')
        return NAME

    context.user_data["name"] = name
    await update.message.reply_text('Отлично! Теперь введите свою фамилию:')
    return SURNAME


async def get_surname(update, context: ContextTypes.DEFAULT_TYPE):
    surname = update.message.text.strip()
    if not surname:
        await update.message.reply_text('Отлично! Теперь введите свою фамилию:')
        return SURNAME

    context.user_data["surname"] = surname
    await update.message.reply_text('Введите свою группу:')
    return GROUP


async def get_group(update, context):
    group = update.message.text.strip()
    if not group:
        await update.message.reply_text('Введите свою группу:')
        return GROUP

    context.user_data["group"] = group
    await update.message.reply_text(
        'Введите свою дату рождения в формате ДД.ММ.ГГГГ (например, 01.01.2000):'
    )
    return BIRTH_DATE


async def get_birth_date(update, context):
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

    # Show confirmation message
    await update.message.reply_text(
        "Проверьте ваши данные:\n"
        f"Имя: {context.user_data['name']}\n"
        f"Фамилия: {context.user_data['surname']}\n"
        f"Группа: {context.user_data['group']}\n"
        f"Дата рождения: {context.user_data['birth_date'].strftime('%d.%m.%Y')}\n\n"
        "Всё верно? (да/нет)",
    )
    return CONFIRMATION


async def confirm_data(update, context):
    answer = update.message.text.lower()
    if answer not in ['да', 'нет']:
        await update.message.reply_text("Пожалуйста, ответьте 'да' или 'нет':")
        return CONFIRMATION

    if answer == 'нет':
        await update.message.reply_text(
            'Регистрация отменена.',
            reply_markup=ReplyKeyboardRemove()
        )
        context.user_data.clear()
        return ConversationHandler.END

    # Save to database
    session = create_session()
    telegram_id = update.effective_user.id

    try:
        student = Student(
            name=context.user_data["name"],
            surname=context.user_data["surname"],
            group=context.user_data["group"],
            birth_date=context.user_data["birth_date"],
            telegram_id=telegram_id,
        )
        session.add(student)
        session.commit()

        await update.message.reply_text(
            "Спасибо! Вы успешно зарегистрированы!",
            reply_markup=ReplyKeyboardRemove()
        )
    except Exception as e:
        session.rollback()
        await update.message.reply_text(
            "Произошла ошибка при сохранении данных. Пожалуйста, попробуйте позже."
        )
        logging.error(f"Error saving student data: {e}")
    finally:
        session.close()
        context.user_data.clear()

    return ConversationHandler.END


async def cancel(update, context):
    await update.message.reply_text(
        "Регистрация отменена.", reply_markup=ReplyKeyboardRemove()
    )
    context.user_data.clear()
    return ConversationHandler.END


def register_student_handlers(application: Application):
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", student_start)],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.User(ADMIN_ID), get_name)],
            SURNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.User(ADMIN_ID), get_surname)],
            GROUP: [MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.User(ADMIN_ID), get_group)],
            BIRTH_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.User(ADMIN_ID), get_birth_date)],
            CONFIRMATION: [MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.User(ADMIN_ID), confirm_data)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(conv_handler)
