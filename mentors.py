
from telegram import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import ConversationHandler, MessageHandler, filters, CommandHandler
from data.db_session import create_session
from data.users import Mentor, Student, FlightResult
from datetime import datetime
from config import ADMIN_ID
import logging

MENTOR_NAME, MENTOR_SURNAME, MENTOR_GROUP, MENTOR_CONFIRMATION = range(12, 16)


async def mentor_start(update, context):
    await update.message.reply_text('Введите ваше имя:', reply_markup=ReplyKeyboardRemove())
    return MENTOR_NAME


async def get_name_ment(update, context):
    name = update.message.text.strip()
    if not name.isalpha():
        await update.message.reply_text('Имя должно содержать только буквы.')
        return MENTOR_NAME

    context.user_data["name"] = name
    await update.message.reply_text('Введите вашу фамилию:')
    return MENTOR_SURNAME


async def get_surname_ment(update, context):
    surname = update.message.text.strip()
    if not surname.isalpha():
        await update.message.reply_text('Фамилия должна содержать только буквы.')
        return MENTOR_SURNAME

    context.user_data["surname"] = surname
    await update.message.reply_text('Введите вашу группу (или группы через запятую):')
    return MENTOR_GROUP


async def get_group_ment(update, context):
    group = update.message.text.strip()
    if not group:
        await update.message.reply_text('Пожалуйста, введите группу:')
        return MENTOR_GROUP

    context.user_data["group"] = group
    await update.message.reply_text(
        "Проверьте ваши данные:\n"
        f"Имя: {context.user_data['name']}\n"
        f"Фамилия: {context.user_data['surname']}\n"
        f"Группа: {context.user_data['group']}\n\n"
        "Всё верно? (да/нет)",
    )
    return MENTOR_CONFIRMATION


async def confirm_data_ment(update, context):
    answer = update.message.text.lower()
    if answer not in ['да', 'нет']:
        await update.message.reply_text("Пожалуйста, ответьте 'да' или 'нет':")
        return MENTOR_CONFIRMATION

    if answer == 'нет':
        await update.message.reply_text(
            'Регистрация отменена.',
            reply_markup=ReplyKeyboardRemove()
        )
        context.user_data.clear()
        return ConversationHandler.END
    session = create_session()
    telegram_id = update.effective_user.id

    try:
        mentor = Mentor(
            name=context.user_data["name"],
            surname=context.user_data["surname"],
            group=context.user_data["group"],
            telegram_id=telegram_id,
        )
        session.add(mentor)
        session.commit()

        await update.message.reply_text(
            "Спасибо! Вы успешно зарегистрированы как наставник!",
            reply_markup=ReplyKeyboardRemove()
        )
        from admin import admin_menu
        await admin_menu(update, context)
    except Exception as e:
        session.rollback()
        await update.message.reply_text(
            "Произошла ошибка при сохранении данных. Пожалуйста, попробуйте позже."
        )
        logging.error(f"{e}")
    finally:
        session.close()
        context.user_data.clear()

    return ConversationHandler.END


async def mentor_menu(update, context):
    keyboard = [
        [KeyboardButton("Просмотреть мои группы")],
        [KeyboardButton("Просмотреть результаты студентов")],
        [KeyboardButton("Рейтинг")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text(
        "Меню наставника:",
        reply_markup=reply_markup
    )


async def show_rating(update, context):
    try:
        session = create_session()
        top_students = session.query(
            Student,
            FlightResult
        ).join(FlightResult).order_by(
            FlightResult.time.asc()
        ).limit(10).all()

        if not top_students:
            await update.message.reply_text("Пока нет данных для рейтинга.")
            return
        response = "Топ-10 студентов по времени полета:\n\n"
        for i, (student, result) in enumerate(top_students, 1):
            response += (
                f"{i}. {student.name} {student.surname} ({student.group})\n"
                f"Время: {result.time} сек\n"
                f"Симулятор: {result.simulator}\n"
                f"Карта: {result.map_name}\n\n"
            )

        await update.message.reply_text(response)

    except Exception as e:
        logging.error(f"Error in show_rating: {e}")
        await update.message.reply_text("Произошла ошибка при формировании рейтинга.")
    finally:
        session.close()


async def cancel(update, context):
    await update.message.reply_text(
        "Регистрация отменена.", reply_markup=ReplyKeyboardRemove()
    )
    context.user_data.clear()
    return ConversationHandler.END


def register_mentor_handlers(application):
    registration_conv = ConversationHandler(
        entry_points=[CommandHandler("start", mentor_start, filters.User(ADMIN_ID))],
        states={
            MENTOR_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name_ment)],
            MENTOR_SURNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_surname_ment)],
            MENTOR_GROUP: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_group_ment)],
            MENTOR_CONFIRMATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_data_ment)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    application.add_handler(registration_conv)
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.User(ADMIN_ID) & filters.Regex(r'^Меню наставника$'),
        mentor_menu
    ))
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.User(ADMIN_ID) & filters.Regex(r'^Рейтинг$'),
        show_rating
    ))


