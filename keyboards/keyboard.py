from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def menu_kb():
    kb = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text='🏥 Информация о клиниках и прикреплении')],
        [KeyboardButton(text="🩺 Пройти диспансеризацию")],
        [KeyboardButton(text="📄 Заказать справку онлайн")],
        [KeyboardButton(text='📝 Оформление жалоб и предложений')],
    ], resize_keyboard=True, input_field_placeholder="Главное меню")
    return kb


def cancel_kb(what: str, hint: str = None):
    thing = {"search": "поиск", "create": "создание обращения", "edit": "изменение", "med_exam": "анкетирование",
             "certification": "заполнение справки"}
    kb = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="❌ Отменить " + thing[what])],
    ], resize_keyboard=True, input_field_placeholder=hint)
    return kb


def certificates_kb():
    kb = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text='Справка о неконтакте')],
        [KeyboardButton(text="Справка о прохождении диспансеризации")],
        [KeyboardButton(text="Справка для получения путевки на санаторно-курортное лечение")],
        [KeyboardButton(text='⬅ Выйти в главное меню')],
    ], resize_keyboard=True, input_field_placeholder="Справки")
    return kb
