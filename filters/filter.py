from aiogram import types
from aiogram.filters import Filter
from aiogram.fsm.context import FSMContext

from utils import last_word_in_state, calc_age

import re
from datetime import datetime


# Список годов, подлежащих диспансеризации, который обновляется автоматически от текущего года
base_years = [1983, 1986, 1989, 1992, 1995, 1998, 2001, 2004, 2007]
med_exam_year_list = [str(year + datetime.now().year - 2025) for year in base_years]


# Проверяет тип чата, чтобы не реагировать на сообщения в группе
class ChatTypeFilter(Filter):
    def __init__(self, chat_types: list[str]):
        self.chat_types = chat_types

    async def __call__(self, message: types.Message):
        return message.chat.type in self.chat_types


class ValidMessageText(Filter):
    key = "Is_Particular_Text_Valid"

    async def __call__(self, message: types.Message, state: FSMContext):
        last_word = await last_word_in_state(state)
        if "_" in last_word and last_word != "c70_pass_address":
            last_word = last_word.split("_")[-1]
        # Проверяет валидность ФИО на соответствие шаблону и на размер сообщения
        if last_word == "name":
            pattern = re.compile(
                r"^[А-ЯЁ][а-яё]+(-[А-ЯЁ][а-яё]+)? [А-ЯЁ][а-яё]+(-[А-ЯЁ][а-яё]+)?( [А-ЯЁ][а-яё]+(-[А-ЯЁ][а-яё]+)?)?$",
                re.IGNORECASE
            )
            if not pattern.fullmatch(message.text):
                return {
                    "err_text_filter": "❗ *Введённое ФИО не соответствует формату*.\n\nПожалуйста, введите ФИО "
                                       "*кириллицей*, *без лишних пробелов*, в формате: 'Фамилия Имя Отчество'"}
            if len(message.text) > 43:
                return {"err_text_filter": "😬 Упс, мы не ожидали, что у Вас настолько длинное ФИО!\n\n"
                                           "*К сожалению, по техническим причинам бот не может принять ФИО, если в нём "
                                           "более 43 символов.*\nПовторите ввод, сократив вводимый текст (это не будет "
                                           "являться проблемой):"}
        # Проверяет валидность даты на соответствие шаблону, на существующую дату и на количество лет
        if last_word == "birth":
            pattern = re.compile(r"^\d{2}\.\d{2}\.\d{4}$")
            if not pattern.fullmatch(message.text):
                return {
                    "err_text_filter": "❗ *Ваша дата не соответствует формату*.\n\nВведите дату в формате *дд.мм.гггг*"
                                       " без лишних символов.\nПример сообщения: '21.01.2004'"}
            try:
                datetime.strptime(message.text, "%d.%m.%Y")
                day, month, year = map(int, message.text.split("."))
                current_year = datetime.now().year
                if year < current_year - 100 or year > current_year - 12:
                    return {"err_text_filter": "❗ *Дата не подходит* - проверьте, что возраст от 12 до 100 лет.\n"
                                               "Введите дату в формате *дд.мм.гггг* без лишних символов.\n"
                                               "Пример сообщения: '21.01.2004'"}
                return False
            except ValueError:
                return {"err_text_filter": "❗ *Такой даты не существует.*\n\nВведите существующую дату в формате "
                                           "*дд.мм.гггг* без лишних символов.\nПример сообщения: "
                                           "'21.01.2004'"}
        # Проверяет валидность номера телефона, но только по шаблону
        if last_word == "number":
            pattern = re.compile(r"^\+7\d{10}$")
            if not pattern.fullmatch(message.text):
                return {"err_text_filter": "❗ *Ваш номер не соответствует формату*.\n\nВведите номер телефона в "
                                           "формате *+7xxxxxxxxxx* без лишних символов.\nПример сообщения: "
                                           "'+73512409977'"}
            if message.text == "+73512409977":
                return {
                    "err_text_filter": "👋 *Привет от разработчика за находчивость, а так - нет, номер телефона "
                                       "клиники не подойдёт*\n\nВведите номер телефона в формате *+7xxxxxxxxxx* без "
                                       "лишних символов.\nПример сообщения: '+73512409977'"}
        if last_word == "complaint":
            # При редактировании текста обращения с прикреплённым файлом
            # проверяет, чтобы новый текст был не более 590 символов
            data = await state.get_data()
            if "file" in data:
                if len(message.text) > 590:
                    return {"err_text_filter": "📎 *К обращению прикреплён документ, поэтому текст обращения не должен"
                                               " превышать 590 символов.*\n\nКоличество символов в новом тексте: "
                                               f"{len(message.text)}\n\nПовторите попытку ввода или отмените изменение,"
                                               f" открепив документ в разделе *«Изменить данные» → «Файл»*, а затем "
                                               f"повторите изменение текста обращения."}
            # Проверяет больше ли текст обращения, чем 3600 символов
            if len(message.text) > 3600:
                return {"err_text_filter": "⚠️ *Максимальный размер обращения - 3600 символов.*\n\n"
                                           f"Количество символов в вашем сообщении: {len(message.text)}.\n\n"
                                           f"Пожалуйста, повторите ввод, сократив текст:"}
        # Проверяет валидность года на соответствие шаблону, на существующую дату и на количество лет
        if last_word == "year":
            pattern = re.compile(r"^\d{4}$")
            if not pattern.fullmatch(message.text):
                return {
                    "err_text_filter": "❗ *Год рождения не соответствует формату.*\n\nВведите *только 4 цифры года,"
                                       " без точек и других символов*.\nПример сообщения: '2004'"
                }
            try:
                year = int(message.text)
                current_year = datetime.now().year
                if year < current_year - 100:
                    return {
                        "err_text_filter": "❗ *Некорректный год рождения.*\n\nПожалуйста, укажите корректный год "
                                           "рождения - *не старше 100 лет от текущего*.\nПример сообщения: '1960'"
                    }
                return False
            except ValueError:
                return {
                    "err_text_filter": "*Ошибка при обработке года.*\n\nПожалуйста, укажите только число - "
                                       "пример: '2004'"
                }
        # Проверяет валидность адреса регистрации по паспорту
        if last_word == "c70_pass_address":
            pattern = re.compile(
                r'^(?:[А-Яа-яёЁ\s\-]+\s(обл\.|край|респ\.))?,?\s*'  # Регион (необязательный)
                r'(г\.|пгт\.|с\.)\s?[А-Яа-яёЁ\s\-]+,?\s*'  # Населённый пункт
                r'(ул\.|пр-т|пер\.|наб\.|б-р|ш\.)\s?[А-Яа-яёЁ\s\-]+,?\s*'  # Улица
                r'д\.\s?\d+[А-Яа-я]?,?\s*'  # Дом
                r'(кв\.\s?\d+)?$'  # Квартира (необязательна)
            )
            if not pattern.fullmatch(message.text.strip()):
                return {
                    "err_text_filter":
                        "❗️ *Адрес регистрации не соответствует формату.*\n\n"
                        "Пожалуйста, введите адрес точно так, как он указан в паспорте. \nПример сообщения: "
                        "'Свердловская обл., г. Екатеринбург, ул. Ленина, д. 10, кв. 5'\n\n"
                        "❗️ Учитывайте сокращения ('г.', 'ул.', 'д.', 'кв.'), запятые и пробелы!"
                }
        # Проверяет номер полиса ОМС на удовлетворение формату
        if last_word == "polis":
            pattern = re.compile(r"^\d{16}$")
            if not pattern.fullmatch(message.text.strip()):
                return {
                    "err_text_filter": "❗️ *Неверный формат номера полиса.*\n\nВведите *16 цифр подряд - без пробелов и"
                                       " других символов*.\nПример сообщения: '1234567890123456'"
                }
        # Проверяет данные о справке МСЭ на формат и существование даты выдачи
        if last_word == "mse":
            pattern = re.compile(r"(?i)^мсэ-\d{4}\s+\d+\s+\d{2}\.\d{2}\.\d{4}$")
            if not pattern.fullmatch(message.text.strip()):
                return {
                    "err_text_filter": "❗️ *Неверный формат справки МСЭ.*\n\n"
                                       "Проверьте, что вы указали:\n"
                                       "• серию (МСЭ-2006)\n"
                                       "• номер (0005220136)\n"
                                       "• дату выдачи (22.05.2007)\n\n"
                                       "Пример сообщения: '*МСЭ-2006 0005220136 22.05.2007*'"
                }
            # Проверка даты (последняя часть строки)
            try:
                date_str = message.text.strip().split()[-1]
                datetime.strptime(date_str, "%d.%m.%Y")
                return False  # всё ок
            except ValueError:
                return {
                    "err_text_filter": "❗ *Такой даты не существует.*\n\nПожалуйста, укажите дату выдачи справки"
                                       " в формате *дд.мм.гггг*."
                }
        if last_word == "snils":
            pattern = re.compile(r"^\d{3}-\d{3}-\d{3}\s+\d{2}$")
            if not pattern.fullmatch(message.text.strip()):
                return {
                    "err_text_filter": "❗ *Неверный формат номера СНИЛС.*\n\nВведите номер в формате '123-456-789 00':"
                }
        return False


class ComplaintWithFile(Filter):
    key = "Is_Less_Than_600"

    async def __call__(self, message: types.Message, state: FSMContext):
        data = await state.get_data()
        # Проверяет, можно ли добавить файл к уже созданному обращению
        if "complaint" in data:
            complaint_text = data.get("complaint", "")
            if len(complaint_text) > 590:
                return True
            return False
        # Проверяет при создании обращения, может ли пользователь добавить файл или выдавать уже готовое обращение
        if message.text:
            if len(message.text) > 590:
                return True
        return False


# Проверяет, может ли человек с данным годом рождения пройти диспансеризацию
class MedExamYearValid(Filter):
    key = "Is_Year_In_List"

    async def __call__(self, message: types.Message):
        age = calc_age(message.text)
        if age < 40:
            if message.text[6:] not in med_exam_year_list or age < 18:
                return False
        return True


# Проверяет, является ли пользователь совершеннолетним для заказа справки
class ContactCertificateYearValid(Filter):
    key = "Is_Year_Valid"

    async def __call__(self, message: types.Message):
        year = int(message.text)
        current_year = datetime.now().year
        if year > current_year - 18:
            return False
        return True


# Проверяет, является ли сообщение числом
class DigitMessage(Filter):
    key = "Is_Message_Digit"

    async def __call__(self, message: types.Message):
        if message.text is None:
            return True
        if not message.text.isdigit():
            return False
        return True
