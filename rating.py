from telegram import ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import MessageHandler, filters, ConversationHandler, CommandHandler
from data.db_session import create_session
from data.users import FlightResult, Student
from datetime import datetime
from asynchronous import async_handler

RATING_SIMULATOR, RATING_MODE, RATING_MAP = range(10, 13)

@async_handler
async def start_rating(update, context):
    keyboard = [
        [KeyboardButton("FPV Freerider")],
        [KeyboardButton("DCL The Game")],
        [KeyboardButton("Liftoff")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text('Рейтинг\nВыберите симулятор:', reply_markup=reply_markup)
    return RATING_SIMULATOR

@async_handler
async def rating_simulator(update, context):
    context.user_data['rating_simulator'] = update.message.text
    keyboard = [
        [KeyboardButton("Self-Leveling")],
        [KeyboardButton("Acro")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text('Выберите режим полёта:', reply_markup=reply_markup)
    return RATING_MODE

@async_handler
async def rating_mode(update, context):
    context.user_data['rating_mode'] = update.message.text
    keyboard = [
        [KeyboardButton("map1")],
        [KeyboardButton("map2")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text('Выберите название трассы:', reply_markup=reply_markup)
    return RATING_MAP

@async_handler
async def rating_map(update, context):
    context.user_data['rating_map'] = update.message.text
    session = create_session()
    try:
        current_student = session.query(Student).filter(
            Student.telegram_id == update.effective_user.id
        ).first()

        results = session.query(FlightResult, Student).join(Student).filter(
            FlightResult.simulator == context.user_data['rating_simulator'],
            FlightResult.flight_mode == context.user_data['rating_mode'],
            FlightResult.map_name == context.user_data['rating_map']
        ).order_by(FlightResult.time.asc()).limit(10).all()

        user_best_result = session.query(FlightResult).filter(
            FlightResult.simulator == context.user_data['rating_simulator'],
            FlightResult.flight_mode == context.user_data['rating_mode'],
            FlightResult.map_name == context.user_data['rating_map'],
            FlightResult.student_id == current_student.id if current_student else False
        ).order_by(FlightResult.time.asc()).first() if current_student else None

        if not results and not user_best_result:
            await update.message.reply_text('Нет результатов для выбранных параметров.')
            return ConversationHandler.END

        current_date = datetime.now().strftime('%H:%M %d.%m.%Y г.')
        response = [
            f"Leaderboard Аэроквантум-15 от {current_date}",
            f"{context.user_data['rating_simulator']}, {context.user_data['rating_mode']}, {context.user_data['rating_map']}",
            ""
        ]

        for idx, (result, student) in enumerate(results, 1):
            response.append(f"{idx}. {result.time:.3f} - {student.surname} {student.name}, гр. {student.group}")

        for idx in range(len(results) + 1, 11):
            response.append(f"{idx}. (место не занято)")

        if current_student and user_best_result:
            in_top = any(result.student_id == current_student.id for result, _ in results)
            if not in_top:
                user_position = session.query(FlightResult).filter(
                    FlightResult.simulator == context.user_data['rating_simulator'],
                    FlightResult.flight_mode == context.user_data['rating_mode'],
                    FlightResult.map_name == context.user_data['rating_map'],
                    FlightResult.time < user_best_result.time
                ).count() + 1

                response.append("")
                response.append(
                    f"Ваш лучший результат: {user_position}. {user_best_result.time:.3f} - {current_student.surname} {current_student.name}, гр. {current_student.group}")

        await update.message.reply_text("\n".join(response))
    except Exception as e:
        await update.message.reply_text('Произошла ошибка при получении рейтинга. Попробуйте позже.')
    finally:
        session.close()

    return ConversationHandler.END

@async_handler
async def cancel_rating(update, context):
    await update.message.reply_text('Просмотр рейтинга отменен.')
    context.user_data.clear()
    return ConversationHandler.END


def register_rating_handlers(application):
    rating_handler = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex(r'^Рейтинг$') & ~filters.COMMAND, start_rating)
        ],
        states={
            RATING_SIMULATOR: [MessageHandler(filters.TEXT & ~filters.COMMAND, rating_simulator)],
            RATING_MODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, rating_mode)],
            RATING_MAP: [MessageHandler(filters.TEXT & ~filters.COMMAND, rating_map)],
        },
        fallbacks=[CommandHandler("cancel", cancel_rating)],
    )
    application.add_handler(rating_handler)
