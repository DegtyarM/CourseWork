from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def clinic_ikb():
    ikb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Узнать клинику прикрепления", callback_data='clinic')],
    ])
    return ikb


def confirm_ikb():
    ikb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да", callback_data='yes'),
         InlineKeyboardButton(text="❌ Нет", callback_data="no")],
    ])
    return ikb


def app_links_ikb():
    ikb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Для Android",
                              url="https://play.google.com/store/apps/details?id=softrust.application2dr"),
         InlineKeyboardButton(text="Для  IOS", url="https://apps.apple.com/ru/app/2dr-ru/id1492097146")],
    ])
    return ikb


def agreement_ikb():
    ikb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Принять", callback_data='agree'),
         InlineKeyboardButton(text="❌ Отклонить", callback_data="disagree")],
    ])
    return ikb


def complaint_topics_ikb():
    ikb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Качество медицинской помощи", callback_data='topic_1')],
        [InlineKeyboardButton(text="Сроки оказания медицинской помощи", callback_data='topic_2')],
        [InlineKeyboardButton(text="Обеспечение льготными препаратами", callback_data='topic_3')],
        [InlineKeyboardButton(text="Этика и деонтология персонала", callback_data='topic_4')],
        [InlineKeyboardButton(text="Прочее", callback_data='topic_5')],
    ])
    return ikb


def document_no_ikb():
    ikb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Без документа", callback_data="no_doc")],
    ], resize_keyboard=True)
    return ikb


def change_complaint_ikb():
    ikb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Изменить данные", callback_data='change')],
        [InlineKeyboardButton(text="✉️ Отправить обращение", callback_data="send")],
        [InlineKeyboardButton(text="❌ Отменить отправку", callback_data="cancel_send")]
    ])
    return ikb


def edit_complaint_ikb():
    ikb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="ℹ️ Тему жалобы", callback_data='edit_topic')],
        [InlineKeyboardButton(text="👤 ФИО", callback_data='edit_name')],
        [InlineKeyboardButton(text="📅 Дату рождения", callback_data='edit_birth')],
        [InlineKeyboardButton(text="📱 Номер телефона", callback_data='edit_number')],
        [InlineKeyboardButton(text="📄 Текст обращения", callback_data='edit_complaint')],
        [InlineKeyboardButton(text="📎 Файл", callback_data='edit_file')],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data='edit_back')],
    ])
    return ikb


def med_exam_ikb():
    ikb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Хочу пройти диспансеризацию!", callback_data="med_exam")]
    ])
    return ikb


def gender_ikb():
    ikb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚹 М", callback_data="man"),
         InlineKeyboardButton(text="️🚺 Ж", callback_data="woman")]
    ])
    return ikb


def questions_ikb():
    ikb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Да", callback_data="q_yes"),
         InlineKeyboardButton(text="Нет", callback_data="q_no")]
    ])
    return ikb


def time_ikb():
    ikb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="До 30 минут", callback_data="q_yes")],
        [InlineKeyboardButton(text="30 минут и более", callback_data="q_no")]
    ])
    return ikb


def quantity_ikb():
    ikb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="До 5", callback_data="q_yes")],
        [InlineKeyboardButton(text="5 и более", callback_data="q_no")]
    ])
    return ikb


def frequency_ikb():
    ikb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Никогда", callback_data="frequency_ов)_0")],
        [InlineKeyboardButton(text="Раз в месяц и реже", callback_data="frequency_)_1")],
        [InlineKeyboardButton(text="2-4 раза в месяц", callback_data="frequency_а)_2")],
        [InlineKeyboardButton(text="2-3 раза в неделю", callback_data="frequency_а)_3")],
        [InlineKeyboardButton(text="≥ 4 раз в неделю", callback_data="frequency_а)_4")]
    ])
    return ikb


def alco_ikb():
    ikb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1-2 порции", callback_data="frequency_ов)_0")],
        [InlineKeyboardButton(text="3-4 порции", callback_data="frequency_)_1")],
        [InlineKeyboardButton(text="5-6 порций", callback_data="frequency_а)_2")],
        [InlineKeyboardButton(text="7-9 порций", callback_data="frequency_а)_3")],
        [InlineKeyboardButton(text="≥ 10 порций", callback_data="frequency_а)_4")]
    ])
    return ikb


def level_ikb():
    ikb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Легкой", callback_data="level_1")],
        [InlineKeyboardButton(text="Средней и выше", callback_data="level_2")],
        [InlineKeyboardButton(text="Не знаю", callback_data="level_3")]
    ])
    return ikb


def feeling_ikb():
    ikb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Да, ощущаю существенное снижение КЖ и/или РСП", callback_data="rating_1")],
        [InlineKeyboardButton(text="Да, ощущаю значительное снижение КЖ и/или РСП", callback_data="rating_2")],
        [InlineKeyboardButton(text="Нет, не ощущаю", callback_data="rating_3")]
    ])
    return ikb


def rating_ikb():
    ikb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Основной", callback_data="rating_1")],
        [InlineKeyboardButton(text="Второстепенный", callback_data="rating_2")],
        [InlineKeyboardButton(text="Отсутствовал", callback_data="rating_3")]
    ])
    return ikb


def no_sex_ikb(postfix: str = ""):
    ikb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Не начал" + postfix, callback_data="no_button_q")]
    ])
    return ikb


def no_period_ikb():
    ikb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Не начались", callback_data="no_button_q")]
    ])
    return ikb


def no_period_now_ikb():
    ikb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Отсутствует", callback_data="no_button_q")]
    ])
    return ikb


def not_over_ikb():
    ikb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Не закончились", callback_data="no_button_q")]
    ])
    return ikb


def certificate_agree_ikb():
    ikb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Перейти к заполнению", callback_data="cert_start")]
    ])
    return ikb


def disable_group_ikb():
    ikb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1", callback_data="dg_1"),
         InlineKeyboardButton(text="2", callback_data="dg_2"),
         InlineKeyboardButton(text="3", callback_data="dg_3")]
    ])
    return ikb
