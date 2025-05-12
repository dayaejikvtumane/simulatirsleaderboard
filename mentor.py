from telegram import ReplyKeyboardRemove, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import MessageHandler, filters, ConversationHandler, CommandHandler, Application
from data.db_session import create_session
from data.users import Mentor, Student, FlightResult
from config import ADMIN_ID
from asynchronous import async_handler

MENTOR_NAME, MENTOR_SURNAME, MENTOR_GROUP = range(13, 16)
CHECK_GROUP, CHECK_STUDENT = range(16, 18)

ADD_MENTOR = 18

@async_handler
async def add_mentor_start(update, context):
    if not is_mentor(update.effective_user.id, ADMIN_ID):
        await update.message.reply_text('Эта команда доступна только администраторам.')
        return ConversationHandler.END

    await update.message.reply_text(
        'Введите Telegram ID нового наставника:',
        reply_markup=ReplyKeyboardRemove()
    )
    return ADD_MENTOR

@async_handler
async def add_mentor_id(update, context):
    try:
        new_mentor_id = int(update.message.text.strip())
        if new_mentor_id <= 0:
            raise ValueError("ID должен быть положительным числом")
        with open("admin.txt", "a+") as f:
            f.seek(0)
            existing_ids = [line.strip() for line in f.readlines() if line.strip()]

            if str(new_mentor_id) in existing_ids:
                await update.message.reply_text('Этот наставник уже есть в списке.')
                return await show_mentor_menu(update, context, show_welcome=False)

            f.write(f"\n{new_mentor_id}")

        keyboard = [
            [KeyboardButton('Проверить результаты учеников')],
            [KeyboardButton('Рейтинг')],
            [KeyboardButton('Мои группы')],
            [KeyboardButton('Добавить наставника')]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

        await update.message.reply_text(
            f"Наставник с ID {new_mentor_id} успешно добавлен!",
            reply_markup=reply_markup
        )

    except ValueError as e:
        await update.message.reply_text(f"Некорректный ID: {e}\nПопробуйте еще раз.")
        return ADD_MENTOR

    return ConversationHandler.END


def is_mentor(telegram_id, admin_id):
    try:
        with open("admin.txt", "r") as f:
            admin_ids = [line.strip() for line in f.readlines() if line.strip()]
            return str(telegram_id) in admin_ids or telegram_id == admin_id
    except FileNotFoundError:
        return telegram_id == admin_id

@async_handler
async def register_mentor_name(update, context):
    name = update.message.text.strip()
    if not name.replace(' ', '').isalpha():
        await update.message.reply_text('Имя должно содержать только буквы и пробелы.')
        return MENTOR_NAME

    context.user_data["mentor_name"] = name
    await update.message.reply_text('Введите вашу фамилию:')
    return MENTOR_SURNAME

@async_handler
async def register_mentor_surname(update, context):
    surname = update.message.text.strip()
    if not surname.replace(' ', '').isalpha():
        await update.message.reply_text('Фамилия должна содержать только буквы и пробелы.')
        return MENTOR_SURNAME

    context.user_data["mentor_surname"] = surname
    await update.message.reply_text('Введите группы, которые вы ведёте (через запятую):')
    return MENTOR_GROUP

@async_handler
async def register_mentor_group(update, context):
    groups = update.message.text.strip()
    if not groups:
        await update.message.reply_text('Пожалуйста, введите хотя бы одну группу.')
        return MENTOR_GROUP

    groups_list = [g.strip() for g in groups.split(',') if g.strip()]
    if not groups_list:
        await update.message.reply_text('Неверный формат групп. Пожалуйста, введите группы через запятую.')
        return MENTOR_GROUP

    context.user_data["mentor_groups"] = ", ".join(groups_list)

    try:
        session = create_session()
        mentor = Mentor(
            name=context.user_data["mentor_name"],
            surname=context.user_data["mentor_surname"],
            group=context.user_data["mentor_groups"],
            telegram_id=update.effective_user.id
        )

        session.add(mentor)
        session.commit()

        await update.message.reply_text(
            f'Регистрация наставника завершена!\n'
            f'Имя: {mentor.name}\n'
            f'Фамилия: {mentor.surname}\n'
            f'Группы: {mentor.group}',
            reply_markup=ReplyKeyboardRemove()
        )

        return await show_mentor_menu(update, context, mentor)

    except Exception as e:
        session.rollback()
        await update.message.reply_text('Произошла ошибка при регистрации. Попробуйте позже.')
        return ConversationHandler.END
    finally:
        session.close()

@async_handler
async def show_mentor_menu(update, context, mentor=None, show_welcome=True):
    if not mentor:
        session = create_session()
        mentor = session.query(Mentor).filter(Mentor.telegram_id == update.effective_user.id).first()
        session.close()
        if not mentor:
            await update.message.reply_text('Вы не зарегистрированы как наставник.')
            return ConversationHandler.END

    keyboard = [
        [KeyboardButton('Проверить результаты учеников')],
        [KeyboardButton('Рейтинг')],
        [KeyboardButton('Мои группы')]
    ]

    # Добавляем кнопку для администраторов
    if is_mentor(update.effective_user.id, ADMIN_ID):
        keyboard.append([KeyboardButton('Добавить наставника')])

    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    if show_welcome:
        await update.message.reply_text(
            f'Добро пожаловать, {mentor.name} {mentor.surname}!\n'
            'Выберите действие:',
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            'Выберите действие:',
            reply_markup=reply_markup
        )
    return ConversationHandler.END

@async_handler
async def cancel_mentor_registration(update, context):
    await update.message.reply_text(
        'Регистрация наставника отменена.',
        reply_markup=ReplyKeyboardRemove()
    )
    context.user_data.clear()
    return ConversationHandler.END

@async_handler
async def check_student_results(update, context):
    session = create_session()
    try:
        mentor = session.query(Mentor).filter(Mentor.telegram_id == update.effective_user.id).first()
        if not mentor:
            await update.message.reply_text('Вы не зарегистрированы как наставник.')
            return ConversationHandler.END

        groups = [g.strip() for g in mentor.group.split(',')]

        keyboard = [[KeyboardButton(group)] for group in groups]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

        await update.message.reply_text(
            'Выберите группу для просмотра результатов:',
            reply_markup=reply_markup
        )
        return CHECK_GROUP
    finally:
        session.close()

@async_handler
async def process_check_group(update, context):
    context.user_data['check_group'] = update.message.text
    session = create_session()
    try:
        students = session.query(Student).filter(Student.group == context.user_data['check_group']).all()

        if not students:
            await update.message.reply_text('В этой группе нет студентов.')
            return await show_mentor_menu(update, context, show_welcome=False)

        keyboard = [[KeyboardButton(f"{student.surname} {student.name}")] for student in students]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

        await update.message.reply_text(
            'Выберите студента:',
            reply_markup=reply_markup
        )
        return CHECK_STUDENT
    finally:
        session.close()

@async_handler
async def process_check_student(update, context):
    student_name = update.message.text
    session = create_session()
    try:
        parts = student_name.split()
        if len(parts) < 2:
            await update.message.reply_text('Неверный формат. Попробуйте еще раз.')
            return CHECK_STUDENT

        surname, name = parts[0], ' '.join(parts[1:])
        student = session.query(Student).filter(
            Student.surname == surname,
            Student.name == name,
            Student.group == context.user_data['check_group']
        ).first()

        if not student:
            await update.message.reply_text('Студент не найден.')
            return await show_mentor_menu(update, context, show_welcome=False)

        results = session.query(FlightResult).filter(
            FlightResult.student_id == student.id
        ).order_by(FlightResult.date_added.desc()).all()

        if not results:
            await update.message.reply_text('У этого студента пока нет результатов.')
            return await show_mentor_menu(update, context, show_welcome=False)

        response = [
            f"Результаты студента {student.surname} {student.name} (группа {student.group}):",
            ""
        ]

        for result in results:
            response.append(
                f"{result.simulator}, {result.map_name}, {result.flight_mode} - {result.time:.3f} сек "
                f"({result.date_added.strftime('%d.%m.%Y')})"
            )

        await update.message.reply_text("\n".join(response))
        return await show_mentor_menu(update, context, show_welcome=False)
    finally:
        session.close()


SHOW_GROUP_RATING = 19


@async_handler
async def show_mentor_groups(update, context):
    session = create_session()
    try:
        mentor = session.query(Mentor).filter(Mentor.telegram_id == update.effective_user.id).first()
        if not mentor:
            await update.message.reply_text('Вы не зарегистрированы как наставник.')
            return ConversationHandler.END

        groups = [g.strip() for g in mentor.group.split(',') if g.strip()]

        if not groups:
            await update.message.reply_text('У вас нет назначенных групп.')
            return await show_mentor_menu(update, context, show_welcome=False)

        keyboard = [[KeyboardButton(group)] for group in groups]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

        await update.message.reply_text(
            'Выберите группу для просмотра рейтинга:',
            reply_markup=reply_markup
        )
        return SHOW_GROUP_RATING
    finally:
        session.close()


@async_handler
async def show_group_rating(update, context):
    selected_group = update.message.text
    session = create_session()
    try:
        students = session.query(Student).filter(Student.group == selected_group).all()
        if not students:
            await update.message.reply_text(f'В группе {selected_group} нет студентов.')
            return await show_mentor_menu(update, context, show_welcome=False)
        results = session.query(FlightResult, Student).join(Student).filter(
            Student.group == selected_group
        ).order_by(
            FlightResult.simulator,
            FlightResult.map_name,
            FlightResult.flight_mode,
            FlightResult.time.asc()
        ).all()

        if not results:
            await update.message.reply_text(f'В группе {selected_group} пока нет результатов.')
            return await show_mentor_menu(update, context, show_welcome=False)
        rating_data = {}
        for result, student in results:
            key = (result.simulator, result.map_name, result.flight_mode)
            if key not in rating_data:
                rating_data[key] = []
            rating_data[key].append((result.time, student))
        response = [f"Рейтинг группы {selected_group}:"]

        for (simulator, map_name, flight_mode), results in rating_data.items():
            response.append(f"\n{simulator}, {map_name}, {flight_mode}:")
            for idx, (time, student) in enumerate(results, 1):
                response.append(f"{idx}. {time:.3f} сек - {student.surname} {student.name}")

        message = "\n".join(response)
        max_length = 4000
        if len(message) > max_length:
            parts = [message[i:i + max_length] for i in range(0, len(message), max_length)]
            for part in parts:
                await update.message.reply_text(part)
        else:
            await update.message.reply_text(message)

        return await show_mentor_menu(update, context, show_welcome=False)
    finally:
        session.close()

def register_mentor_handlers(application: Application, admin_id):
    # Обработчик проверки результатов студентов
    check_results_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(r'^Проверить результаты учеников$') & ~filters.COMMAND,
                                     check_student_results)],
        states={
            CHECK_GROUP: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_check_group)],
            CHECK_STUDENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_check_student)],
        },
        fallbacks=[CommandHandler('cancel', cancel_mentor_registration)],
    )

    # Обработчик просмотра рейтинга групп
    group_rating_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(r'^Мои группы$') & ~filters.COMMAND,
                                     show_mentor_groups)],
        states={
            SHOW_GROUP_RATING: [MessageHandler(filters.TEXT & ~filters.COMMAND, show_group_rating)],
        },
        fallbacks=[CommandHandler('cancel', cancel_mentor_registration)],
    )

    # Обработчик добавления наставников
    add_mentor_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(r'^Добавить наставника$') & ~filters.COMMAND,
                                     add_mentor_start)],
        states={
            ADD_MENTOR: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_mentor_id)],
        },
        fallbacks=[CommandHandler('cancel', cancel_mentor_registration)],
    )

    application.add_handler(check_results_handler)
    application.add_handler(group_rating_handler)
    application.add_handler(add_mentor_handler)