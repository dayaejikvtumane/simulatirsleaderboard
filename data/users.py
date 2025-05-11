import sqlalchemy.orm
from sqlalchemy import Column, String, Date, Integer, ForeignKey, Float
from .db_session import SqlAlchemyBase
import datetime


"""БД состоит из трех таблиц, одна - ученик и информация о нем (ИД, имя, фамилия, группа
Дата рождения, тг). Эта таблиуа связана с таблицей рещультытов полета
вторая таблица - наставник. содержит информацию о наставнике (ИД, имя, фамилия, группа, ТГ)
третья - рещультаты полета(ИД ученика(из таблицы Student) симулятор, карта, режим полета,
время, путь к фото, дата добавлния)"""

class Student(SqlAlchemyBase):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    surname = Column(String, nullable=False)
    group = Column(String, nullable=False)
    birth_date = Column(Date)
    telegram_id = Column(Integer, unique=True)
    results = sqlalchemy.orm.relationship("FlightResult", back_populates="student")


class Mentor(SqlAlchemyBase):
    __tablename__ = "mentors"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    surname = Column(String, nullable=False)
    group = Column(String)
    telegram_id = Column(Integer, unique=True)


from sqlalchemy import Column, String, Date, Integer, ForeignKey, Float, LargeBinary, DateTime

class FlightResult(SqlAlchemyBase):
    __tablename__ = "flight_results"
    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey("students.id"))
    simulator = Column(String, nullable=False)
    map_name = Column(String, nullable=False)
    flight_mode = Column(String, nullable=False)
    time = Column(Float, nullable=False)
    photo_data = Column(LargeBinary)
    date_added = Column(Date, default=datetime.datetime.now)

    student = sqlalchemy.orm.relationship("Student", back_populates="results")