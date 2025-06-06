from aiogram import F, Router, flags
from aiogram.enums import ChatAction
from aiogram.filters import StateFilter, or_f
from aiogram.types import InputMediaPhoto, ReplyParameters

from utils import *
from filters import *
from database import WrongAddresses
from states import Address, EditComplaint

import os
from pathlib import Path
from datetime import datetime
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession


router_m = Router()


"""******************************************* ВАЛИДАЦИЯ ДАННЫХ Ч1 ********************************************"""


@router_m.message(F.text.contains('❌ Отменить'), or_f(StateFilter(Address), StateFilter(Complaint),
                                                      StateFilter(EditComplaint), StateFilter(MedExam),
                                                      StateFilter(Certificates)), flags={"throttle": "check"})
async def know_clinic(message: types.Message, state: FSMContext, redis: Redis):
    from .callback import answers_dict, questions_dict, questions_list, digit_answer, conditional_answer
    thing = message.text[11:].capitalize()
    text = {"Поиск": "ён", "Создание обращения": "ено", "Изменение": "ено",
            "Анкетирование": "ено", "Заполнение справки": "ено"}
    await message.delete()
    await delete_redis_mes(message, redis, f"del_mes_{str(message.from_user.id)}")
    if thing == "Изменение":
        last_word = await last_word_in_state(state)
        param = {"topic": "темы", "name": "ФИО", "birth": "даты рождения", "number": "номера телефона",
                 "complaint": "текста обращения", "file": "файла"}
        del_mes_1 = await message.answer(text="🛑 " + thing + " " + param[last_word] + " отмен" + text[thing])
        await edited_complaint(message, state, 0, redis)
        await redis.lpush(f"del_tech_{str(message.from_user.id)}", *[del_mes_1.message_id])
        return
    else:
        if thing == "Анкетирование":
            data = await state.get_data()
            if "one_completed_questionnaire" in data:
                os.remove(Path("data") / f"{data['one_completed_questionnaire']}.pdf")
        await message.answer(text="🛑 " + thing + " отмен" + text[thing], reply_markup=menu_kb())
        await state.clear()
    for struct in [answers_dict, questions_dict, questions_list, digit_answer, conditional_answer]:
        struct.clear()
    await delete_redis_mes(message, redis, f"del_tech_{str(message.from_user.id)}")


@router_m.message(lambda message: not message.document,
                  or_f(StateFilter(Complaint.file), StateFilter(EditComplaint.edit_file)), flags={"throttle": "check"})
async def make_complaint_not_file(message: types.Message, redis: Redis, album: list = None):
    if not album:
        await redis.lpush(f"del_mes_{str(message.from_user.id)}", *[message.message_id])
    del_mes_1 = await message.answer(text="📄 *Ожидается получение документа.*\nПовторите попытку или выберите "
                                          "'*Без документа*' в сообщении выше для продолжения:",
                                     reply_markup=cancel_kb("create", "👈 Прикрепите документ"))
    await redis.lpush(f"del_tech_{str(message.from_user.id)}", *[del_mes_1.message_id])


@router_m.message(or_f(StateFilter(Address.confirm), StateFilter(Complaint.agreement),
                       StateFilter(Complaint.topic), StateFilter(EditComplaint.edit_topic),
                       StateFilter(MedExam.agreement), StateFilter(MedExam.gender), StateFilter(MedExam.questions),
                       StateFilter(MedExam.pregnant), StateFilter(Certificates.contact_test),
                       StateFilter(Certificates.c70_gender), StateFilter(Certificates.c70_disable),
                       StateFilter(Certificates.c70_dis_group), StateFilter(Certificates.c70_accompany),
                       StateFilter(Certificates.agreement)),
                  flags={"throttle": "check"})
async def not_clicked_button(message: types.Message, state: FSMContext, redis: Redis, album: dict = None):
    last_word = await last_word_in_state(state)
    message_text = "Вы не дали ответ на вопрос выше"
    param_to_text_keyboard = {
        "confirm": "Пожалуйста, выберите согласие или несогласие выше.",
        "agreement": "Пожалуйста, подтвердите согласие или отказ выше.",
        "topic": "Пожалуйста, выберите тему из списка выше.",
        "gender": "Пожалуйста, укажите Ваш пол выше.",
        "c70_gender": "Пожалуйста, укажите Ваш пол выше.",
        "questions": "Вы не закончили заполнение анкеты.",
    }
    message_text = param_to_text_keyboard.get(last_word, message_text)
    if not album:
        await message.delete()
    del_mes_1 = await message.answer(text=message_text + " 👆\nСделайте это для продолжения.")
    await redis.lpush(f"del_tech_{str(message.from_user.id)}", *[del_mes_1.message_id])


@router_m.message(StateFilter(Complaint.final), flags={"throttle": "check"})
async def make_complaint_not_file(message: types.Message, redis: Redis, album: dict = None):
    if not album:
        await message.delete()
    del_mes_1 = await message.answer(text="📨 Отправьте обращение или нажмите кнопку *'Отменить отправку'* выше, "
                                          "чтобы продолжить.")
    await redis.lpush(f"del_tech_{str(message.from_user.id)}", *[del_mes_1.message_id])


@router_m.message(F.text, or_f(StateFilter(Complaint), StateFilter(EditComplaint), StateFilter(MedExam),
                               StateFilter(Certificates)),
                  ValidMessageText(),
                  flags={"throttle": "check"})
async def valid_text(message: types.Message, state: FSMContext, err_text_filter, redis: Redis):
    last_word = await last_word_in_state(state)
    if "_" in last_word:
        last_word = last_word.split("_")[-1]
    hint_dict = {
        "name": "Фамилия Имя Отчество",
        "birth": "дд.мм.гггг",
        "number": "+7xxxxxxxxxx",
        "address": "Адрес по паспорту",
        "year": "гггг",
        "polis": "Номер полиса ОМС",
        "mse": "Серия Номер Дата",
        "snils": "123-456-789 00",
        "complaint": None,
    }
    hint = hint_dict.get(last_word, None)
    keyb = await identification_cancel_kb(state, hint)
    del_mes_1 = await message.answer(text=err_text_filter, reply_markup=keyb)
    await redis.lpush(f"del_tech_{str(message.from_user.id)}", *[del_mes_1.message_id, message.message_id])


@router_m.message(StateFilter(MedExam.birth), F.text, ~MedExamYearValid())
async def med_exam_year(message: types.Message, state: FSMContext, redis: Redis):
    await message.answer(text="❌ *К сожалению, Вы не входите в перечень граждан, которые могут пройти диспансеризацию"
                              " в этом году.*\n\n✅ Однако Вы всё равно можете пройти *профилактический медицинский "
                              "осмотр* - он проводится ежегодно и включает базовую проверку состояния здоровья.\n\n"
                              "📌 Для получения информации и записи обратитесь в свою клинику по месту прикрепления.",
                         reply_markup=menu_kb())
    await delete_redis_mes(message, redis, f"del_mes_{str(message.from_user.id)}")
    await delete_redis_mes(message, redis, f"del_tech_{str(message.from_user.id)}")
    await state.clear()


@router_m.message(StateFilter(Certificates.contact_birth_year), F.text, ~ContactCertificateYearValid())
async def contact_year_is_under_18(message: types.Message, state: FSMContext, redis: Redis):
    await message.delete()
    await message.answer(text="ℹ️ *Справку о неконтакте онлайн можно оформить только для пациентов старше 18 лет.*"
                              "\n\n📌 Если Вам всё же нужна такая справка, пожалуйста, обратитесь в клинику по месту "
                              "прикрепления - сотрудники помогут оформить её лично.", reply_markup=menu_kb())
    await delete_redis_mes(message, redis, f"del_mes_{str(message.from_user.id)}")
    await delete_redis_mes(message, redis, f"del_tech_{str(message.from_user.id)}")
    await state.clear()


@router_m.message(StateFilter(Complaint.complaint), ComplaintWithFile(), flags={"throttle": "check"})
async def can_not_add_file(message: types.Message, state: FSMContext, redis: Redis):
    await state.update_data(complaint=message.text)
    del_mes_1 = await message.answer(
        text=f"📝 *Ваше обращение содержит {len(message.text)} символов - это превышает лимит для прикрепления "
             f"документа.*\n\nЧтобы добавить файл, сократите текст обращения до *590 символов или меньше*.\n"
             f"После этого возможность прикрепить документ станет доступной в разделе *«Изменить данные»*.")
    await redis.lpush(f"del_tech_{str(message.from_user.id)}", *[del_mes_1.message_id])
    await redis.lpush(f"del_mes_{str(message.from_user.id)}", *[message.message_id])
    data = await state.get_data()
    await message.answer(text=complaint_text(data, 2, 0),
                         reply_markup=change_complaint_ikb())
    await state.set_state(Complaint.final)
    await delete_redis_mes(message, redis, f"del_mes_{str(message.from_user.id)}")


@router_m.message(StateFilter(MedExam.digit_answer), ~DigitMessage(), flags={"throttle": "check"})
async def message_is_not_digit(message: types.Message, redis: Redis):
    del_mes_1 = await message.answer(text="🔢 *Пожалуйста, введите только число без лишних символов*.\n"
                                          "Повторите попытку ввода:",
                                     reply_markup=cancel_kb("med_exam"))
    await redis.lpush(f"del_tech_{str(message.from_user.id)}", *[message.message_id, del_mes_1.message_id])


"""*********************************** ИНФОРМАЦИЯ О КЛИНИКАХ И ПРИКРЕПЛЕНИИ ***********************************"""


@router_m.message(F.text == '🏥 Информация о клиниках и прикреплении', StateFilter(None), flags={"throttle": "check"})
@flags.chat_action(action=ChatAction.UPLOAD_PHOTO)
async def schedule(message: types.Message, redis: Redis):
    redis_key = f"schedule_msg_{str(message.from_user.id)}"
    del_mes_1 = await message.bot.send_photo(chat_id=message.from_user.id,
                                             caption='*Адреса Полимедики в Челябинске* 👆',
                                             photo=types.FSInputFile(Path("data/clinic_schedule.jpg")),
                                             reply_markup=clinic_ikb())
    await delete_redis_mes(message, redis, redis_key)
    await redis.lpush(redis_key, *[del_mes_1.message_id, message.message_id])


@router_m.message(F.text, StateFilter(Address.address), flags={"throttle": "check", "database": "commit"})
@flags.chat_action(action=ChatAction.FIND_LOCATION)
async def check_address(message: types.Message, state: FSMContext, session: AsyncSession, redis: Redis):
    result, useless_thing_here, coordinates = find_clinic_by_address(message.text)
    await redis.lpush(f"del_mes_{str(message.from_user.id)}", *[message.message_id])
    if "Вы уверены" in result:
        await session.merge(WrongAddresses(user_id=message.from_user.id, address=message.text[:100], place="Поиск"))
        del_mes_1 = await message.answer(text=result, reply_markup=confirm_ikb())
        await redis.lpush(f"del_mes_{str(message.from_user.id)}", *[del_mes_1.message_id])
        await state.set_state(Address.confirm)
    else:
        await message.bot.send_venue(chat_id=message.from_user.id, latitude=coordinates[0], longitude=coordinates[1],
                                     title="Геолокация клиники прикрепления", address="")
        await message.answer(text=result,
                             reply_markup=menu_kb())
        await message.answer(text="✍️ Для записи к врачу скачайте приложение 2dr по одной из ссылок ниже "
                                  "или воспользуйтесь [сайтом](https://74.2dr.ru/)",
                             reply_markup=app_links_ikb(),
                             disable_web_page_preview=True)
        await delete_redis_mes(message, redis, f"del_mes_{str(message.from_user.id)}")
        await state.set_state(None)


"""************************************* ОФОРМЛЕНИЕ ЖАЛОБ И ПРЕДЛОЖЕНИЙ **************************************"""


@router_m.message(F.text == '📝 Оформление жалоб и предложений', StateFilter(None), flags={"throttle": "check"})
@flags.chat_action(action=ChatAction.UPLOAD_DOCUMENT)
async def make_complaint(message: types.Message, state: FSMContext, redis: Redis):
    await call_agreement(message, redis)
    await state.set_state(Complaint.agreement)


@router_m.message(F.text, StateFilter(Complaint), flags={"throttle": "check"})
async def make_complaint_contains_text(message: types.Message, state: FSMContext, redis: Redis):
    await delete_redis_mes(message, redis, f"del_tech_{str(message.from_user.id)}")
    last_word = await last_word_in_state(state)
    param_to_text_keyboard = {
        "name": ("Введите Вашу дату рождения в формате 'дд.мм.гггг':", cancel_kb("create", "дд.мм.гггг"), "birth"),
        "birth": ("Введите Ваш номер телефона для дальнейшей связи, начиная с +7 без пробелов:",
                  cancel_kb("create", "+7xxxxxxxxxx"), "number"),
        "number": ("Введите Вашу жалобу или предложение.\n\n⚠️ *Учтите:* если текст превышает *590 символов*, Вы не "
                   "сможете прикрепить документ.\n⚠️ При объёме более *4090 символов* сообщение будет автоматически"
                   " сокращено средствами Telegram.",
                   cancel_kb("create"), "complaint"),
        "complaint": ("Отправьте дополнительно документ, если необходимо.\n\n⚠️ *Можно прикрепить только 1 файл!* Если"
                      " отправите несколько - будет учтён только первый.\n\nЕсли документа нет, нажмите на кнопку"
                      " 'Без документа'", document_no_ikb(), "file"),
    }
    if last_word in param_to_text_keyboard:
        text, keyb, new_state = param_to_text_keyboard[last_word]
        await state.update_data({last_word: message.text})
        del_mes_1 = await message.answer(text=text, reply_markup=keyb)
        await redis.lpush(f"del_mes_{str(message.from_user.id)}", *[del_mes_1.message_id, message.message_id])
        await state.set_state(getattr(Complaint, new_state))


@router_m.message(F.document, StateFilter(Complaint.file))
async def make_complaint_file(message: types.Message, redis: Redis, state: FSMContext = None, album: list = None):
    await delete_redis_mes(message, redis, f"del_tech_{str(message.from_user.id)}")
    if album:
        first = await pinned_first_doc(message, album, redis)
        await state.update_data(file=first.document.file_id)
    else:
        await state.update_data(file=message.document.file_id)
    data = await state.get_data()
    del_mes_1 = await message.answer(text="✅ Создание обращения завершено!",
                                     reply_markup=ReplyKeyboardRemove())
    await redis.lpush(f"del_tech_{str(message.from_user.id)}", *[del_mes_1.message_id])
    await message.bot.send_document(chat_id=message.from_user.id,
                                    document=str(data["file"]),
                                    caption=complaint_text(data, 2, 0),
                                    reply_markup=change_complaint_ikb())
    await redis.lpush(f"del_mes_{str(message.from_user.id)}", *[message.message_id])
    await delete_redis_mes(message, redis, f"del_mes_{str(message.from_user.id)}")
    await state.set_state(Complaint.final)


"""******************************************** ИЗМЕНЕНИЕ ДАННЫХ *********************************************"""


@router_m.message(F.text, StateFilter(EditComplaint), flags={"throttle": "check"})
async def edit_complaint_contains_text(message: types.Message, state: FSMContext, redis: Redis):
    await delete_redis_mes(message, redis, f"del_tech_{str(message.from_user.id)}")
    last_word = await last_word_in_state(state)
    await edited_complaint(message, state, 1, redis, last_word, message.text)
    await redis.lpush(f"del_mes_{str(message.from_user.id)}", *[message.message_id])
    await delete_redis_mes(message, redis, f"del_mes_{str(message.from_user.id)}")


@router_m.message(F.document, StateFilter(EditComplaint.edit_file), flags={"throttle": "check"})
async def make_complaint_file(message: types.Message, state: FSMContext, redis: Redis, album: list = None):
    await delete_redis_mes(message, redis, f"del_tech_{str(message.from_user.id)}")
    if album:
        first = await pinned_first_doc(message, album, redis)
        await edited_complaint(message, state, 1, redis, "file", first.document.file_id)
    else:
        await edited_complaint(message, state, 1, redis, "file", message.document.file_id)
    await redis.lpush(f"del_mes_{str(message.from_user.id)}", *[message.message_id])
    await delete_redis_mes(message, redis, f"del_mes_{str(message.from_user.id)}")


"""****************************************** ПРОЙТИ ДИСПАНСЕРИЗАЦИЮ *******************************************"""


@router_m.message(F.text == '🩺 Пройти диспансеризацию', StateFilter(None), flags={"throttle": "check"})
@flags.chat_action(action=ChatAction.UPLOAD_PHOTO)
async def start_medical_exam(message: types.Message, redis: Redis):
    redis_key = f"med_exam_msg_{str(message.from_user.id)}"
    med_exam_list = await message.bot.send_media_group(
        chat_id=message.from_user.id,
        media=[InputMediaPhoto(media=types.FSInputFile(Path("data/med_exam/man_med_exam.jpg"))),
               InputMediaPhoto(media=types.FSInputFile(Path("data/med_exam/woman_med_exam.jpg"))),])
    base_year = [1983, 1986, 1989, 1992, 1995, 1998, 2001, 2004, 2007]
    med_exam_years_list = [str(year + datetime.now().year - 2025) for year in base_year]
    years_text = ", ".join(med_exam_years_list)
    med_exam_text = await message.answer(text="‼️ *Работающим гражданам предоставляется оплачиваемое освобождение "
                                              "от работы в количестве 1 рабочего дня для прохождения диспансеризации!*"
                                              f"  (оплачиваемый день отдыха для годов рождения *{years_text}*, а также "
                                              f"*всем старше 40 лет*)"
                                              "\n\n🤖 Наш бот предоставляет возможность уже *сейчас заполнить "
                                              "анкетирование прямо в боте*, чтобы сэкономить Ваше время. \n\n*До начала"
                                              " прохождения диспансеризации остался всего один шаг!* 👇",
                                         reply_markup=med_exam_ikb())
    await delete_redis_mes(message, redis, redis_key)
    await redis.lpush(redis_key, *([msg.message_id for msg in med_exam_list] +
                                   [med_exam_text.message_id, message.message_id]))


@router_m.message(F.text, or_f(StateFilter(MedExam.name), StateFilter(MedExam.birth),
                               StateFilter(MedExam.number)), flags={"throttle": "check"})
async def med_exam_contains_text(message: types.Message, state: FSMContext, redis: Redis):
    await delete_redis_mes(message, redis, f"del_tech_{str(message.from_user.id)}")
    last_word = await last_word_in_state(state)
    param_to_text_keyboard = {
        "birth": ("Введите Ваш номер телефона для дальнейшей связи, начиная с +7 без пробелов:",
                  cancel_kb("med_exam", "+7xxxxxxxxxx"), "number"),
        "number": ("Укажите Ваши Фамилию Имя Отчество (при наличии):",
                   cancel_kb("med_exam", "Фамилия Имя Отчество"), "name"),
        "name": ("Выберите Ваш пол:", gender_ikb(), "gender"),
    }
    if last_word in param_to_text_keyboard:
        text, keyb, new_state = param_to_text_keyboard[last_word]
        await state.update_data({last_word: message.text})
        del_mes_1 = await message.answer(text=text, reply_markup=keyb)
        await redis.lpush(f"del_mes_{str(message.from_user.id)}", *[del_mes_1.message_id, message.message_id])
        await state.set_state(getattr(MedExam, new_state))


@router_m.message(F.text, or_f(StateFilter(MedExam.digit_answer), StateFilter(MedExam.write_answer)),
                  flags={"throttle": "check"})
async def med_exam_digit_answer(message: types.Message, state: FSMContext, redis: Redis):
    from .callback import answers_dict, questions_list
    await redis.lpush(f"del_tech_{str(message.from_user.id)}", *[message.message_id])
    data, msg_text, key, key_word = await write_answer_to_dict(message, state, "w")
    if data["q_num"] + 1 == len(questions_list):
        await finish_questionnaire(message, state, data, key, key_word, redis)
        return
    if key in ['1', '12', '13', "60", "2"]:  # 2 - муж, остальное - жен
        answers_dict[key_word] = message.text + " " + get_age_suffix(int(message.text))
    if key in ['3_s', '4_s', '10_a']:
        answers_dict[key_word] = message.text + " " + get_day_suffix(int(message.text))
    if key == '11':
        answers_dict[key_word] = message.text + " день"
    key_1 = questions_list[data["q_num"] + 1]
    # Если вопрос о количестве детей и ответ "0", то вопрос о наименьшем возрасте пропускаем
    if message.text == "0" and questions_list[data["q_num"]] == "59":
        await skip_questions_women_med_exam(message, state, data, key_word, redis)
        return
    # Вопрос о том, сколько месяцев прошло с ковида, то сохраняем часть ответа и присылаем следующий вопрос (не все)
    if key == "c_2":
        answers_dict["d_c_2"] = message.text
        del_mes_1 = await message.answer(text="Укажите степень тяжести коронавирусной инфекции "
                                              "(COVID-19) в Вашем случае:",
                                         reply_markup=level_ikb())
        await redis.lpush(f"del_tech_{str(message.from_user.id)}", *[del_mes_1.message_id])
        await state.set_state(MedExam.questions)
        return
    await transition_to_state_questions(message, state, data, key_word, key_1, key, redis)


"""********************************************** ЗАКАЗ СПРАВОК ***********************************************"""


@router_m.message(F.text == "📄 Заказать справку онлайн", StateFilter(None), flags={"throttle": "check"})
async def start_certificate(message: types.Message, state: FSMContext, redis: Redis):
    del_mes_1 = await message.answer(text="📄 *Выберите нужную справку из списка ниже:*", reply_markup=certificates_kb())
    await redis.lpush(f"del_mes_{str(message.from_user.id)}", *[del_mes_1.message_id])
    await state.set_state(Certificates.choice)


@router_m.message(F.text == "⬅ Выйти в главное меню", StateFilter(Certificates.choice), flags={"throttle": "check"})
async def back_to_menu(message: types.Message, state: FSMContext, redis: Redis):
    await delete_redis_mes(message, redis, f"del_mes_{str(message.from_user.id)}")
    await delete_redis_mes(message, redis, f"del_tech_{str(message.from_user.id)}")
    await message.delete()
    await state.set_state(None)
    await message.answer(text="🏠 *Вы вернулись в главное меню бота.*\nВыберите нужный раздел ниже 👇",
                         reply_markup=menu_kb())


@router_m.message(F.text, StateFilter(Certificates.choice))
async def certificate_choose(message: types.Message, redis: Redis):
    await delete_redis_mes(message, redis, f"del_tech_{str(message.from_user.id)}")
    await message.delete()
    param_to_text_keyboard = {
        "Справка о неконтакте":
            "Справку о эпидокружении (справку об отсутствии контактов с инфекционными больными) также называют "
            "справкой «о неконтакте». Этот документ подтверждает, что человек не находился в непосредственной "
            "близости с людьми, больными инфекционными заболеваниями, на протяжении определенного периода "
            "(обычно 21 дня или 14 дней).\n\n🕒 *Срок действия - 3 дня с момента получения справки в клинике.*",
        "Справка о прохождении диспансеризации":
            "Справка о прохождении диспансеризации - документ, который подтверждает, что пациент прошёл"
            " профилактическое или диспансерное медицинское обследование в медицинской организации."
            "\n📌 Может потребоваться для *работодателя, учёбы или при обращении в другие учреждения*."
            "\n⚠️ Для получения этой справки *необходимо пройти диспансеризацию*.",
        "Справка для получения путевки на санаторно-курортное лечение":
            "Данная справка подтверждает медицинскую необходимость санаторно-курортного лечения.\n"
            "⚠️ Для оформления этой справки *необходимо иметь справку МСЭ* (медико-социальной экспертизы)."
            "\n\n🕒 *Срок действия - 12 месяцев с момента заполнения*",
    }
    certificate_warning = ("\n\n\n📤 После заполнения бот автоматически сформирует *шаблон справки* и отправит его вам. "
                           "Он будет *частично заполнен* на основе ваших ответов и сразу передан в клинику.\n"
                           "📝 *Окончательное оформление и выдача справки происходят только в клинике*, при личном "
                           "визите.\n\n❗️*Пожалуйста, будьте внимательны*: если допустите ошибку, "
                           "отмените заполнение и начните заново.")
    if message.text in param_to_text_keyboard:
        text = param_to_text_keyboard[message.text]
        del_mes_1 = await message.answer(text=f'"*{message.text}*"\n\n' + text + certificate_warning,
                                         reply_markup=certificate_agree_ikb())
        await redis.lpush(f"del_mes_{str(message.from_user.id)}", *[del_mes_1.message_id])
    else:
        del_mes_2 = await message.answer(text="❗️*Похоже, такой справки не существует.*\n\nВоспользуйтесь кнопками "
                                              "ниже 👇 или начните оформление под нужной справкой 👆.",
                                         reply_markup=certificates_kb())
        await redis.lpush(f"del_mes_{str(message.from_user.id)}", *[del_mes_2.message_id])


@router_m.message(F.text, StateFilter(Certificates), flags={"throttle": "check", "database": "commit"})
async def certificates_questioning(message: types.Message, state: FSMContext, redis: Redis, session: AsyncSession):
    await delete_redis_mes(message, redis, f"del_tech_{str(message.from_user.id)}")
    await redis.lpush(f"del_mes_{str(message.from_user.id)}", *[message.message_id])
    last_word = await last_word_in_state(state)
    cert_name, parameter = last_word.split("_")[0], "_".join(last_word.split("_")[1:])
    address_text = (
        "🏠 Введите адрес проживания, чтобы узнать клинику, к которой Вы прикреплены: \n\n"
        "ℹ️ Пример адреса: `Салавата Юлаева 23А` \n\n"
        "🛣 Если вы живёте в *Сосновском районе*, вводите адрес в формате: *«посёлок, микрорайон, улица»* "
        "(без номера дома)\nЕсли вы из посёлков *«Шершни», «Тарасовка» или «Карпов Пруд»*, вводите в формате: "
        "*«посёлок, улица»* (без номера дома)\n\n❗️*Важно: бот чувствителен к формату!* Не ставьте запятую "
        "между улицей и номером дома, а литеру здания пишите сразу после номера, без пробела.")
    param_to_text_keyboard = {
        "exam": {"birth": (address_text, cancel_kb("certification", "Адрес дома"), "address"),
                 "name": ("Введите Вашу дату рождения в формате 'дд.мм.гггг':", cancel_kb("certification",
                                                                                          "дд.мм.гггг"), "birth")},
        "contact": {"name": ("Введите Ваш год рождения в формате гггг:", cancel_kb("certification", "гггг"),
                             "birth_year"),
                    "birth_year": ("Выезжали ли Вы за пределы РФ, в г. Москва, в г. Санкт-Петербург в течение последних"
                                   " 14 денй?", questions_ikb(), "test")},
        "c70": {"name": ("Выберите Ваш пол:", gender_ikb(), "gender"),
                "birth": ("Введите Ваш адрес регистрации *в точности как в паспорте*:",
                          cancel_kb("certification", "Адрес по паспорту"), "pass_address"),
                "pass_address": ("Введите номер Вашего полиса ОМС (16 цифр без пробелов):",
                                 cancel_kb("certification", "Номер полиса ОМС"), "polis"),
                "polis": ("Являетесь ли Вы инвалидом?", questions_ikb(), "disable"),
                "mse": ("Введите номер Вашего СНИЛСа в формате '123-456-789 00':",
                        cancel_kb("certification", "123-456-789 00"), "snils"),
                "snils": ("Укажите один или несколько курортов, на которых предпочтительно лечение для Вас:",
                          cancel_kb("certification", "Предпочтительное место лечения"), "preferred_place"),
                "preferred_place": (address_text, cancel_kb("certification", "Адрес дома"), "address")}
    }
    if cert_name in param_to_text_keyboard and parameter in param_to_text_keyboard[cert_name]:
        text, keyb, new_state = param_to_text_keyboard[cert_name][parameter]
        if last_word in ("c70_polis", "c70_snils", "c70_birth"):
            prefix_mapping = {"c70_birth": "b", "c70_polis": "p", "c70_snils": "s"}
            data_to_save = {f"{prefix_mapping[last_word]}{i + 1}": digit for i, digit in enumerate(message.text)}
            await state.update_data(data_to_save)
        elif last_word == "c70_mse":
            series, number, date = message.text.split()
            date_digits = date.replace(".", "")
            data_to_save = {f"m{i + 1}": digit for i, digit in enumerate(date_digits)}
            await state.update_data(data_to_save, series=series, number=number)
        else:
            await state.update_data({parameter: message.text})
        del_mes_1 = await message.answer(text=text, reply_markup=keyb)
        await redis.lpush(f"del_mes_{str(message.from_user.id)}", *[del_mes_1.message_id])
        await state.set_state(getattr(Certificates, cert_name + "_" + new_state))
    else:
        await state.update_data({parameter: f"г. Челябинск, ул. {message.text}"})
        await state.update_data(day=str(datetime.now().day), month=get_month_name(str(datetime.now().month)),
                                year=str(datetime.now().year % 100))
        result_text, group_key, coordinates = find_clinic_by_address(message.text, "certificate")
        if "Вы уверены" in result_text:
            await session.merge(WrongAddresses(user_id=message.from_user.id, address=message.text[:100],
                                               place="Справка"))
            result_text = "🫴 Забрать готовую справку Вы можете в клинике по адресу прикрепления."
            group_key = "gid_rest"
        data = await state.get_data()
        notification = await message.bot.send_message(chat_id=message.from_user.id,
                                                      text="Заполняю документ...",
                                                      reply_markup=ReplyKeyboardRemove())
        async with ChatActionSender.upload_document(bot=message.bot, chat_id=message.chat.id):
            pdf_path = convert_docx_to_pdf(
                f"med_certificate/Cert{cert_name.capitalize()}", data,
                f"med_certificate/completed_c/Справка_{"_".join(data['name'].split()[:2])}_"
                f"{datetime.now().strftime("%H%M%S")}")
            await message.bot.delete_message(chat_id=message.from_user.id,
                                             message_id=notification.message_id)
            address_message = await message.bot.send_document(
                chat_id=message.from_user.id,
                document=types.FSInputFile(pdf_path),
                caption=f"✅ Вы успешно заполнили справку!\n\n{result_text}",
                message_effect_id="5046509860389126442",
                reply_markup=menu_kb())
        if coordinates is not None:
            async with ChatActionSender.find_location(bot=message.bot, chat_id=message.chat.id):
                await message.bot.send_location(chat_id=message.from_user.id, latitude=coordinates[0],
                                                longitude=coordinates[1],
                                                reply_parameters=ReplyParameters(message_id=address_message.message_id,
                                                quote=":".join(result_text.split(":")[1:]).strip()))
        await message.bot.send_document(chat_id=await redis.get(group_key),
                                        document=types.FSInputFile(pdf_path),
                                        caption=f"*Новая заявка на справку!*\n\n📄 Тип справки: *{data['cert_type']}*"
                                                f"\n\n👤 ФИО: *{data["name"]}*\n🏠 Адрес проживания: "
                                                f"*{data["address"]}*\n\n📆 Дата оформления справки: "
                                                f"*{datetime.today().strftime("%d.%m.%Y")}*")
        await delete_redis_mes(message, redis, f"del_mes_{str(message.from_user.id)}")
        await state.clear()
        os.remove(pdf_path)


"""******************************************* ВАЛИДАЦИЯ ДАННЫХ Ч2 ********************************************"""


@router_m.message(~F.text, or_f(StateFilter(Address.address), StateFilter(Certificates.c70_address),
                                StateFilter(Certificates.contact_address), StateFilter(Certificates.exam_address),
                                StateFilter(Certificates.c70_pass_address)))
async def address_not_text(message: types.Message, state: FSMContext, redis: Redis, album: dict = None):
    if not album:
        await message.delete()
    keyb = await identification_cancel_kb(state, "Адрес дома")
    str_state = await state.get_state()
    address_type = "регистрации" if "pass_" in str_state else "проживания"
    del_mes_1 = await message.answer(text=f"⌨️ Пожалуйста, введите адрес {address_type} *текстом!*\nПовторите попытку "
                                          f"ввода:", reply_markup=keyb)
    await redis.lpush(f"del_tech_{str(message.from_user.id)}", *[del_mes_1.message_id])


@router_m.message(~F.text, or_f(StateFilter(Complaint), StateFilter(EditComplaint), StateFilter(MedExam),
                                StateFilter(Certificates)))
async def make_complaint_not_text(message: types.Message, state: FSMContext, redis: Redis, album: dict = None):
    last_word = await last_word_in_state(state)
    str_state = await state.get_state()
    if str_state.startswith("Certificates") and "_" in last_word:
        last_word = last_word.split("_")[-1]
    prompt_template = "⌨️ Пожалуйста, введите {} *текстом*.\nПовторите попытку ввода:"
    param_to_text_keyboard = {
        "name": (prompt_template.format("Фамилию Имя Отчество (при наличии)"), "Фамилия Имя Отчество"),
        "birth": (prompt_template.format("дату рождения"), "дд.мм.гггг"),
        "number": (prompt_template.format("номер телефона"), "+7xxxxxxxxxx"),
        "complaint": ("🔤 Обращение должно быть в *текстовом* формате.\nПовторите попытку ввода:", None),
        "write_answer": (prompt_template.format("наименования новообразований"), None),
        "digit_answer": ("🔢 Пожалуйста, введите число *текстом*, используя только цифры.\n"
                         "Повторите попытку ввода:", None),
        "choice": ("❗️*Похоже, вы отправили документ вместо выбора справки.*\n\nПожалуйста, выберите нужную справку"
                   " на клавиатуре ниже 👇 или нажмите кнопку под её описанием 👆, чтобы начать оформление.", None),
        "year": (prompt_template.format("год рождения"), "гггг"),
        "polis": (prompt_template.format("номер полиса"), "Номер полиса ОМС"),
        "mse": (prompt_template.format("данные о справке МСЭ"), "Серия Номер Дата"),
        "snils": (prompt_template.format("номер Вашего СНИЛСа"), "123-456-789 00"),
        "place": (prompt_template.format("предпочтительное место лечения"), "Предпочтительное место лечения"),
    }
    if last_word in param_to_text_keyboard:
        text, hint, = param_to_text_keyboard[last_word]
        keyb = await identification_cancel_kb(state, hint)
        if last_word == "choice":
            keyb = certificates_kb()
        del_mes_1 = await message.answer(text=text, reply_markup=keyb)
        if not album:
            await redis.lpush(f"del_tech_{str(message.from_user.id)}", *[message.message_id])
        await redis.lpush(f"del_tech_{str(message.from_user.id)}", *[del_mes_1.message_id])


@router_m.message(flags={"throttle": "check"})
async def all_text(message: types.Message):
    await message.answer(text="ℹ️ *Ничего не выбрано*.\nДля продолжения выберите нужный раздел в меню 👇",
                         reply_markup=menu_kb())
