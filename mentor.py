import csv
import os
import tempfile
from datetime import datetime
from io import BytesIO
from telegram.error import BadRequest
from telegram import ReplyKeyboardRemove, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import MessageHandler, filters, ConversationHandler, CommandHandler, Application

from asynchronous import async_handler
from config import ADMIN_ID
from data.db_session import create_session
from data.users import Mentor, Student, FlightResult

# Состояния
MENTOR_NAME, MENTOR_SURNAME, MENTOR_GROUP = range(13, 16)
CHECK_GROUP, CHECK_STUDENT, EDIT_OPTIONS, UPLOAD_CSV = range(16, 20)
ADD_MENTOR = 20
SHOW_GROUP_RATING = 19
SELECT_ADD_METHOD = 21
INPUT_MENTORID = 22
SELECT_STUDENT = 23
CONFIRM_ADD = 24
DELETE_MENTOR = 25
# админ меню
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

    # Всегда проверяем is_mentor, а не полагаемся только на переданного ментора
    if is_mentor(update.effective_user.id, ADMIN_ID):
        keyboard.append([KeyboardButton('Добавить наставника')])
        if update.effective_user.id == ADMIN_ID:
            keyboard.append([KeyboardButton('Удалить наставника')])

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
async def delete_mentor_start(update, context):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text('Эта команда доступна только главному администратору.')
        return await show_mentor_menu(update, context, show_welcome=False)

    session = create_session()
    try:
        mentors = session.query(Mentor).all()
        if not mentors:
            await update.message.reply_text('Нет зарегистрированных наставников.')
            return await show_mentor_menu(update, context, show_welcome=False)

        keyboard = []
        for mentor in mentors:
            if mentor.telegram_id != ADMIN_ID:
                btn_text = f"{mentor.surname} {mentor.name} (ID: {mentor.telegram_id})"
                keyboard.append([KeyboardButton(btn_text)])

        if not keyboard:
            await update.message.reply_text('Нет других наставников для удаления.')
            return await show_mentor_menu(update, context, show_welcome=False)

        keyboard.append([KeyboardButton('Назад')])
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

        await update.message.reply_text(
            'Выберите наставника для удаления:',
            reply_markup=reply_markup
        )
        return DELETE_MENTOR
    finally:
        session.close()


@async_handler
async def confirm_delete_mentor(update, context):
    if update.message.text == 'Назад':
        return await show_mentor_menu(update, context, show_welcome=False)

    try:
        telegram_id = int(update.message.text.split('(ID: ')[1].rstrip(')'))
    except (IndexError, ValueError):
        await update.message.reply_text('Ошибка')
        return DELETE_MENTOR

    context.user_data['mentor_to_delete_id'] = telegram_id

    keyboard = [
        [KeyboardButton('Да')],
        [KeyboardButton('Нет')]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text(
        f'Вы уверены, что хотите удалить наставника с (ID: {telegram_id})',
        reply_markup=reply_markup
    )
    return CONFIRM_ADD


@async_handler
async def execute_delete_mentor(update, context):
    if update.message.text == 'Нет':
        return await show_mentor_menu(update, context, show_welcome=False)
    mentor_id = context.user_data.get('mentor_to_delete_id')
    if not mentor_id:
        await update.message.reply_text('Ошибка: ID не найден.')
        return await show_mentor_menu(update, context, show_welcome=False)
    session = create_session()
    try:
        mentor = session.query(Mentor).filter(Mentor.telegram_id == mentor_id).first()
        if mentor:
            mentor_name = f"{mentor.name} {mentor.surname}"
            session.delete(mentor)
            session.commit()
            try:
                await context.bot.send_message(
                    chat_id=mentor_id,
                    text=f"Вы были удалены из списка наставников.\n"
                         f"Для повторной регистрации используйте команду /start",
                    reply_markup=ReplyKeyboardRemove()
                )
            except BadRequest as e:
                print(f"Не удалось отправить сообщение удаленному наставнику {mentor_id}: {e}")

        with open("admin.txt", "r+") as f:
            lines = f.readlines()
            f.seek(0)
            for line in lines:
                if line.strip() != str(mentor_id):
                    f.write(line)
            f.truncate()

        keyboard = [
            [KeyboardButton('Проверить результаты учеников')],
            [KeyboardButton('Рейтинг')],
            [KeyboardButton('Мои группы')],
            [KeyboardButton('Добавить наставника')],
        ]
        if update.effective_user.id == ADMIN_ID:
            keyboard.append([KeyboardButton('Удалить наставника')])

        await update.message.reply_text(
            f'Наставник с ID {mentor_id} успешно удален!',
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )
    except Exception as e:
        session.rollback()
        await update.message.reply_text(f'Ошибка при удалении: {str(e)}')
    finally:
        session.close()

    return ConversationHandler.END


# рег имя админа
@async_handler
async def register_mentor_name(update, context):
    name = update.message.text.strip()
    if not name.replace(' ', '').isalpha():
        await update.message.reply_text('Имя должно содержать только буквы.')
        return MENTOR_NAME
    context.user_data["mentor_name"] = name
    await update.message.reply_text('Введите вашу фамилию:')
    return MENTOR_SURNAME


# рег фамилии админа
@async_handler
async def register_mentor_surname(update, context):
    surname = update.message.text.strip()
    if not surname.replace(' ', '').isalpha():
        await update.message.reply_text('Фамилия должна содержать только буквы.')
        return MENTOR_SURNAME
    context.user_data["mentor_surname"] = surname
    await update.message.reply_text('Введите группы, которые вы ведёте (через запятую):')
    return MENTOR_GROUP


# рег групп админа
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


# проверить право на просмотр и изменение результатов
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


# проверка результатов
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


# редактирование результатов полета
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

        has_photos = False
        Sp_res = [
            f"Результаты студента {student.surname} {student.name} (группа {student.group}):",
            ""
        ]

        for i in results:
            if i.photo_data:  # если есть фотка, то отправляем фото с подписью рещультатов
                await update.message.reply_photo(
                    photo=BytesIO(i.photo_data),
                    caption=f"{i.simulator}, {i.map_name}, {i.flight_mode} - {i.time:.3f} сек "
                            f"({i.date_added.strftime('%d.%m.%Y')})"
                )
                has_photos = True
            else:
                Sp_res.append(
                    f"{i.simulator}, {i.map_name}, {i.flight_mode} - {i.time:.3f} сек "
                    f"({i.date_added.strftime('%d.%m.%Y')})"
                )

        if not has_photos or len(Sp_res) > 2:  # тут отпраыляем только то что без фоток
            await update.message.reply_text("\n".join(Sp_res))

        context.user_data['selected_student_id'] = student.id

        keyboard = [
            [KeyboardButton('В меню'), KeyboardButton('Редактировать')]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

        await update.message.reply_text(
            "Выберите действие:",
            reply_markup=reply_markup
        )
        return EDIT_OPTIONS
    except Exception as e:
        await update.message.reply_text(f'Произошла ошибка: {str(e)}')
        return await show_mentor_menu(update, context, show_welcome=False)
    finally:
        session.close()


@async_handler
async def handle_edit_choice(update, context):
    choice = update.message.text
    if choice == 'В меню':
        return await show_mentor_menu(update, context, show_welcome=False)
    elif choice == 'Редактировать':
        session = create_session()
        try:
            student_id = context.user_data.get('selected_student_id')
            if not student_id:
                await update.message.reply_text('Ошибка: студент не выбран.')
                return ConversationHandler.END

            results = session.query(FlightResult).filter(
                FlightResult.student_id == student_id
            ).all()

            with tempfile.NamedTemporaryFile(mode='w+', suffix='.csv', delete=False, encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['ID', 'Simulator', 'Map', 'Mode', 'Time', 'Date (YYYY-MM-DD)'])
                # создание CSV
                for i in results:
                    writer.writerow([
                        i.id,
                        i.simulator,
                        i.map_name,
                        i.flight_mode,
                        i.time,
                        i.date_added.strftime('%Y-%m-%d')
                    ])
                temp_file_path = f.name

            with open(temp_file_path, 'rb') as f:
                await update.message.reply_document(
                    document=f,
                    filename='results.csv',
                    caption='Отредактируйте CSV файл и загрузите его обратно. '
                            'Для новых записей оставьте ID пустым.'
                )
            os.remove(temp_file_path)

            return UPLOAD_CSV
        except Exception as e:
            await update.message.reply_text(f'Ошибка при создании файла: {str(e)}')
            return await show_mentor_menu(update, context, show_welcome=False)
        finally:
            session.close()
    else:
        await update.message.reply_text('Неизвестная команда')
        return EDIT_OPTIONS


@async_handler
async def handle_csv_upload(update, context):
    file = await update.message.document.get_file()
    csv_file = await file.download_to_drive()

    session = create_session()
    try:
        student_id = context.user_data.get('selected_student_id')
        if not student_id:
            await update.message.reply_text('Ошибка: студент не выбран')
            return await show_mentor_menu(update, context, show_welcome=False)
        # запись полученного в бд
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            errors = []
            updates = 0
            creates = 0

            for i in reader:  # проходимся по строчкам CSV
                try:
                    if i['ID']:  # Если есть айди - не новая строчка, а просто меняется старая
                        result = session.query(FlightResult).filter(  #
                            FlightResult.id == int(i['ID']),
                            FlightResult.student_id == student_id
                        ).first()
                        if not result:
                            errors.append(f"Запись с ID {i['ID']} не найдена")
                            continue

                        # Запись
                        result.simulator = i['Simulator']
                        result.map_name = i['Map']
                        result.flight_mode = i['Mode']
                        result.time = float(i['Time'])
                        result.date_added = datetime.strptime(i['Date (YYYY-MM-DD)'], '%Y-%m-%d').date()
                        updates += 1
                    else:  # Если новая запись
                        new_result = FlightResult(
                            student_id=student_id,
                            simulator=i['Simulator'],
                            map_name=i['Map'],
                            flight_mode=i['Mode'],
                            time=float(i['Time']),
                            date_added=datetime.strptime(i['Date (YYYY-MM-DD)'], '%Y-%m-%d').date()
                        )
                        session.add(new_result)
                        creates += 1

                except Exception as e:
                    errors.append(f"Ошибка в строке {reader.line_num}: {str(e)}")

            session.commit()

            message = f"Обновлено записей: {updates}\nДобавлено новых записей: {creates}"
            if errors:
                message += "\nОшибки:\n" + "\n".join(errors)

            await update.message.reply_text(message)

    except Exception as e:
        session.rollback()
        await update.message.reply_text(f'Ошибка обработки файла: {str(e)}')
    finally:
        session.close()
        os.remove(csv_file)

    return await show_mentor_menu(update, context, show_welcome=False)


@async_handler
async def cancel_mentor_registration(update, context):
    await update.message.reply_text(
        'Операция отменена.',
        reply_markup=ReplyKeyboardRemove()
    )
    context.user_data.clear()
    return ConversationHandler.END


# проверка txt
def is_mentor(telegram_id, admin_id):
    try:
        with open("admin.txt", "r") as f:
            admin_ids = [line.strip() for line in f.readlines() if line.strip()]
            return str(telegram_id) in admin_ids or telegram_id == admin_id
    except FileNotFoundError:
        return telegram_id == admin_id




# просмотр рейтинга и право на него
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
            reply_markup=reply_markup)
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
            keyboard = [
                [KeyboardButton('Проверить результаты учеников')],
                [KeyboardButton('Рейтинг')],
                [KeyboardButton('Мои группы')]
            ]
            if is_mentor(update.effective_user.id, ADMIN_ID):
                keyboard.append([KeyboardButton('Добавить наставника')])
                if update.effective_user.id == ADMIN_ID:
                    keyboard.append([KeyboardButton('Удалить наставника')])

            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            await update.message.reply_text('Выберите действие:', reply_markup=reply_markup)
            return ConversationHandler.END
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
        mentor = session.query(Mentor).filter(Mentor.telegram_id == update.effective_user.id).first()
        return await show_mentor_menu(update, context, mentor=mentor, show_welcome=False)
    finally:
        session.close()


# добавление нового наставника
@async_handler
async def add_mentor_start(update, context):
    if not is_mentor(update.effective_user.id, ADMIN_ID):
        await update.message.reply_text('Эта команда доступна только администраторам.')
        return await show_mentor_menu(update, context, show_welcome=False)

    keyboard = [
        [KeyboardButton('Добавить по ID')],
        [KeyboardButton('Выбрать из студентов')],
        [KeyboardButton('Назад')]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text(
        'Выберите способ добавления наставника:',
        reply_markup=reply_markup
    )
    return SELECT_ADD_METHOD


@async_handler
async def select_add_method(update, context):
    choice = update.message.text
    if choice == 'Назад':
        return await show_mentor_menu(update, context, show_welcome=False)
    elif choice == 'Добавить по ID':
        keyboard = [
            [KeyboardButton('Назад')]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

        await update.message.reply_text(
            'Введите Telegram ID нового наставника (можно узнать через @getmyid_bot) или нажмите "Назад":',
            reply_markup=reply_markup
        )
        return INPUT_MENTORID
    elif choice == 'Выбрать из студентов':
        session = create_session()
        try:
            students = session.query(Student).all()
            if not students:
                await update.message.reply_text('Нет зарегистрированных студентов.')
                return await show_mentor_menu(update, context, show_welcome=False)

            # Группируем студентов по 2 в строку для компактности
            keyboard = []
            temp_row = []
            for student in students:
                btn = KeyboardButton(f"{student.surname} {student.name} (ID: {student.telegram_id})")
                temp_row.append(btn)
                if len(temp_row) >= 2:
                    keyboard.append(temp_row)
                    temp_row = []
            if temp_row:
                keyboard.append(temp_row)

            keyboard.append([KeyboardButton('Назад')])
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

            await update.message.reply_text(
                'Выберите студента для назначения наставником:',
                reply_markup=reply_markup
            )
            return SELECT_STUDENT
        finally:
            session.close()
    else:
        await update.message.reply_text('Неизвестная команда')
        return SELECT_ADD_METHOD


@async_handler
async def input_mentor_id(update, context):
    user_input = update.message.text.strip()
    # Обработка кнопки "Назад"
    if user_input.lower() == 'назад':
        return await add_mentor_start(update, context)
    try:
        mentor_id = int(user_input)
        if mentor_id <= 0:
            raise ValueError("ID должен быть положительным числом")
        context.user_data['new_mentor_id'] = mentor_id
        keyboard = [
            [KeyboardButton('Подтвердить')],
            [KeyboardButton('Назад')]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

        await update.message.reply_text(
            f'Вы хотите добавить наставника с ID: {mentor_id}?',
            reply_markup=reply_markup
        )
        return CONFIRM_ADD
    except ValueError:
        keyboard = [
            [KeyboardButton('Назад')]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

        await update.message.reply_text(
            'Некорректный ID. Пожалуйста, введите числовой ID или нажмите "Назад".',
            reply_markup=reply_markup
        )
        return INPUT_MENTORID

@async_handler
async def select_student(update, context):
    if update.message.text == 'Назад':
        return await add_mentor_start(update, context)

    try:

        telegram_id = int(update.message.text.split('(ID: ')[1].rstrip(')'))
    except (IndexError, ValueError):
        await update.message.reply_text('Ошибка')
        return SELECT_STUDENT

    context.user_data['new_mentor_id'] = telegram_id

    keyboard = [
        [KeyboardButton('Подтвердить')],
        [KeyboardButton('Назад')]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text(
        f'Вы хотите назначить этого студента наставником? (ID: {telegram_id})',
        reply_markup=reply_markup
    )
    return CONFIRM_ADD


@async_handler
async def confirm_add_mentor(update, context):
    if update.message.text == 'Назад':
        return await add_mentor_start(update, context)

    new_mentor_id = context.user_data.get('new_mentor_id')
    if not new_mentor_id:
        await update.message.reply_text('Ошибка: ID наставника не найден.')
        return await show_mentor_menu(update, context, show_welcome=False)

    session = create_session()
    try:
        student = session.query(Student).filter(Student.telegram_id == new_mentor_id).first()
        if student:
            session.query(FlightResult).filter(FlightResult.student_id == student.id).delete()
            session.delete(student)
            session.commit()

        existing_mentor = session.query(Mentor).filter(Mentor.telegram_id == new_mentor_id).first()
        if existing_mentor:
            await update.message.reply_text('Этот пользователь уже является наставником.')
            return await show_mentor_menu(update, context, show_welcome=False)
        with open("admin.txt", "a+") as f:
            f.seek(0)
            existing_ids = [line.strip() for line in f.readlines() if line.strip()]
            if str(new_mentor_id) in existing_ids:
                await update.message.reply_text('Этот пользователь уже есть в списке наставников.')
                return await show_mentor_menu(update, context, show_welcome=False)

            f.write(f"\n{new_mentor_id}")

        try:
            await context.bot.send_message(
                chat_id=new_mentor_id,
                text="Вас назначили наставником. Пожалуйста, перезапустите бота командой /start для завершения регистрации."
            )
        except BadRequest as e:
            print(f"Не удалось отправить сообщение новому наставнику: {e}")

        await update.message.reply_text(
            f'Пользователь с ID {new_mentor_id} успешно добавлен как наставник!',
            reply_markup=ReplyKeyboardMarkup(
                [[KeyboardButton('Проверить результаты учеников')],
                 [KeyboardButton('Рейтинг')],
                 [KeyboardButton('Мои группы')],
                 [KeyboardButton('Добавить наставника')]],
                resize_keyboard=True
            )
        )
    except Exception as e:
        session.rollback()
        await update.message.reply_text(f'Ошибка при добавлении наставника: {str(e)}')
    finally:
        session.close()

    return ConversationHandler.END


def register_mentor_handlers(application: Application, admin_id):
    check_results_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(r'^Проверить результаты учеников$') & ~filters.COMMAND,
                                     check_student_results)],
        states={
            CHECK_GROUP: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_check_group)],
            CHECK_STUDENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_check_student)],
            EDIT_OPTIONS: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_edit_choice)],
            UPLOAD_CSV: [MessageHandler(filters.Document.FileExtension("csv"), handle_csv_upload)]
        },
        fallbacks=[CommandHandler('cancel', cancel_mentor_registration)],
    )

    add_mentor_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(r'^Добавить наставника$') & ~filters.COMMAND,
                                     add_mentor_start)],
        states={
            SELECT_ADD_METHOD: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_add_method)],
            INPUT_MENTORID: [MessageHandler(filters.TEXT & ~filters.COMMAND, input_mentor_id)],
            SELECT_STUDENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_student)],
            CONFIRM_ADD: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_add_mentor)],
        },
        fallbacks=[CommandHandler('cancel', cancel_mentor_registration)],
    )

    group_rating_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(r'^Мои группы$') & ~filters.COMMAND,
                                     show_mentor_groups)],
        states={
            SHOW_GROUP_RATING: [MessageHandler(filters.TEXT & ~filters.COMMAND, show_group_rating)],
        },
        fallbacks=[CommandHandler('cancel', cancel_mentor_registration)],
    )
    delete_mentor_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(r'^Удалить наставника$') & ~filters.COMMAND,
                                     delete_mentor_start)],
        states={
            DELETE_MENTOR: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_delete_mentor)],
            CONFIRM_ADD: [MessageHandler(filters.TEXT & ~filters.COMMAND, execute_delete_mentor)],
        },
        fallbacks=[CommandHandler('cancel', cancel_mentor_registration)],
    )

    application.add_handler(delete_mentor_handler)
    application.add_handler(check_results_handler)
    application.add_handler(add_mentor_handler)
    application.add_handler(group_rating_handler)
