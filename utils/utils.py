from aiogram import types
from aiogram.types import ReplyKeyboardRemove, InputMediaDocument
from aiogram.utils.chat_action import ChatActionSender

from data.addresses import address_dict
from states import Complaint, MedExam, Certificates
from data.med_exam.questioniers import *

import os
from datetime import datetime
from pathlib import Path
from redis.asyncio import Redis


# Функция для поиска клиники, участка и врача по адресу из словаря address_dict
def find_clinic_by_address(user_address, goal_of_usage: str = None):
    for street, data in address_dict.items():
        for section, section_data in data["Участки"].items():
            # Ищем введенный адрес среди адресов для данного участка
            if user_address.lower() in section_data["Адреса"]:
                coordinates = data.get("Координаты", None)
                # Если нашли, возвращаем информацию
                if section == 23:
                    section = "Взрослый 23"
                if goal_of_usage == "certificate":
                    street_to_group_key = {
                        "Кашириных": "gid_Kashirinykh", "Татищева": "gid_Tatishcheva",
                        "Полянка": "gid_Polyanka", "Королева": "gid_Korolova",
                        "Заводская": "gid_Zavodskaya", "Победы": "gid_Pobedy",
                        "Привилегия": "gid_Privilegiya",
                    }
                    group_key = None
                    for keyword, key in street_to_group_key.items():
                        if keyword.lower() in street.lower():
                            group_key = key
                            break
                    return (f"🫴 Забрать готовую справку Вы можете в клинике по адресу прикрепления: *{street}*",
                            group_key, coordinates)
                return (f"🏠 Ваш адрес: *{user_address}*;\n"
                        f"🏥 Вы прикреплены к клинике по адресу: *{street}*;\n"
                        f"#⃣ Терапевтический участок: *{section}*;\n"
                        f"👤 Терапевт: *{section_data['ФИО врача']}*", None, coordinates)

    return f"Вы уверены, что ввели адрес (*{user_address}*) правильно и в нужном формате?", None, None


# Функция определения текста внутри обращения
def complaint_text(data, version, edited, new: str = None):
    edition = "обновлённое " if edited else ""
    if not new:
        new = "Ваше"
    age = calc_age(str(data["birth"]))
    complaint = (f"{new} {edition}обращение:\n\nℹ️ Тема жалобы: *{str(data["topic"])}*\n\n👤 ФИО: *{str(data["name"])}*"
                 f"\n📅 Дата рождения: *{str(data["birth"])}* ({age} {get_age_suffix(age)})\n📱 Номер телефона: "
                 f"*{str(data["number"])}*\n\n📄 Текст обращения: *{str(data["complaint"])}*")
    additions = {
        2: ("\n\n\n‼️ *Если обращение заполнено верно, то не забудьте его отправить, нажав на кнопку ниже!*"
            "\nВ ином случае исправьте данные и отправьте обращение. "
            "\n\nВы также можете отменить отправку, нажав на кнопку отмены внизу."),
        3: "\n\n\n*Выберите, какие данные Вы хотите изменить?*",
        4: "\n\n*Обращение отправлено успешно!*",
        5: "\n\n*Отправка обращения отменена!*",
    }
    return complaint + additions.get(version, "")


# Функция определения возраста
def calc_age(birth: str):
    birth_date = datetime.strptime(birth, "%d.%m.%Y")
    today = datetime.today()
    age = today.year - birth_date.year
    # Если день рождения в этом году уже прошел, то возраст не нужно уменьшать
    if today.month < birth_date.month or (today.month == birth_date.month and today.day < birth_date.day):
        age -= 1
    return age


# Функция определения суффиксального слова для возраста
def get_age_suffix(age: int):
    last_digit = age % 10
    last_two_digits = age % 100
    if last_two_digits in [11, 12, 13, 14]:
        return "лет"
    elif last_digit == 1:
        return "год"
    elif last_digit in [2, 3, 4]:
        return "года"
    else:
        return "лет"


# Функция определения суффиксального слова для дня
def get_day_suffix(days: int):
    last_digit = days % 10
    last_two_digits = days % 100
    if last_two_digits in [11, 12, 13, 14]:
        return "дней"
    elif last_digit == 1:
        return "день"
    elif last_digit in [2, 3, 4]:
        return "дня"
    else:
        return "дней"


# Функция отправляющая текст созданного/отредактированного обращения
async def edited_complaint(message, state, edited, redis, key: str = None, value=None):
    if key:
        await state.update_data({key: value})
        del_mes_1 = await message.bot.send_message(chat_id=message.from_user.id,
                                                   text="✅ *Данные успешно изменены!*",
                                                   reply_markup=ReplyKeyboardRemove())
        await redis.lpush(f"del_tech_{str(message.from_user.id)}", *[del_mes_1.message_id])
    data = await state.get_data()
    if "file" in data:
        await message.bot.send_document(chat_id=message.from_user.id,
                                        document=str(data["file"]),
                                        caption=complaint_text(data, 2, edited),
                                        parse_mode="markdown",
                                        reply_markup=change_complaint_ikb())
    else:
        await message.bot.send_message(chat_id=message.from_user.id,
                                       text=complaint_text(data, 2, edited),
                                       parse_mode="markdown",
                                       reply_markup=change_complaint_ikb())
    await state.set_state(Complaint.final)


# Метод удаления сообщений из списка Redis
async def delete_redis_mes(message, redis, redis_key):
    if await redis.exists(redis_key):
        try:
            message_ids = [int(i) for i in await redis.lrange(redis_key, 0, -1)]
            await message.bot.delete_messages(chat_id=message.from_user.id, message_ids=message_ids)
        except Exception as e:
            print(e)
        finally:
            await redis.delete(redis_key)


# Функция определения состояния (последнего его слова) в сообщениях
async def last_word_in_state(state):
    str_state = await state.get_state()
    last_word = str_state.split(':')[-1]
    if str_state.startswith("Edit"):
        last_word = last_word.split("_")[-1]
    return last_word


# Метод, отправляющее согласие на обработку данных
async def call_agreement(message, redis):
    del_mes_1 = await message.bot.send_document(chat_id=message.from_user.id,
                                                document=types.FSInputFile(Path("data/Согласие_на_обработку.pdf")),
                                                caption="❗️ Пожалуйста, перед продолжением ознакомьтесь "
                                                        "ознакомьтесь с Согласием на обработку Персональных данных:",
                                                reply_markup=agreement_ikb())
    await redis.lpush(f"del_mes_{str(message.from_user.id)}", *[del_mes_1.message_id])


# Функция, срабатывающая после принятия согласия на обработку данных
async def agree_data(callback, text, reply_markup, state, set_state, redis):
    await callback.answer()
    await callback.message.edit_caption(caption="*Вы ознакомились и приняли Согласие на "
                                                "обработку Персональных данных.*")
    del_mes_1 = await callback.message.answer(text=text,
                                              reply_markup=reply_markup)
    await redis.lpush(f"del_mes_{str(callback.from_user.id)}", *[del_mes_1.message_id])
    await state.set_state(set_state)


# Функция определения нужной клавиатуры отмены
async def identification_cancel_kb(state, hint=None):
    str_state = await state.get_state()
    keyb = cancel_kb("create", hint)
    if str_state.startswith("Edit"):
        keyb = cancel_kb("edit", hint)
    if str_state.startswith("Med"):
        keyb = None
    if str_state.startswith("Certificates"):
        keyb = cancel_kb("certification", hint)
    return keyb


# Функция, прикрепляющая только первый отправленный документ, если была отправлена пачка
async def pinned_first_doc(message, album, redis):
    first = album[0]
    del_mes_1 = await message.answer(text="К обращению добавлен первый из присланных документов!")
    await redis.lpush(f"del_tech_{str(message.from_user.id)}", *[del_mes_1.message_id])
    return first


# Функция, получающая текст с нажатой inline кнопки
async def get_button_text_from_keyboard(callback: types.CallbackQuery, keyboa: InlineKeyboardMarkup):
    for row in keyboa.inline_keyboard:  # inline_keyboard - это список строк (рядов) кнопок
        for button in row:
            if callback.data == button.callback_data:
                return button.text
    return None


# Функция, подготавливающая к заполнению анкет
async def prep_questionnaire(callback, state, gender: str, redis):
    from .docx_pdf import convert_docx_to_pdf
    await callback.answer()
    await state.update_data(gender=gender)
    data = await state.get_data()
    await state.set_state(MedExam.questions)
    age = calc_age(str(data["birth"]))
    await state.update_data(age=age, current_date=datetime.now().strftime("%d.%m.%Y"), q_num=0, frequency_test=0,
                            pregnant=0)
    notification = await callback.message.answer(text="Загрузка...")
    del_mes_1 = await callback.bot.send_document(
        chat_id=callback.from_user.id,
        document=types.FSInputFile(convert_docx_to_pdf(
            "med_exam/AgreementMedExam", data,
            f"med_exam/completed_q/Согласие_{"_".join(data['name'].split()[:2])}")),
        caption="👆 *Вы также можете ознакомиться с согласием на проведение диспансеризации* 👆")
    await callback.bot.delete_message(chat_id=callback.from_user.id, message_id=notification.message_id)
    await redis.lpush(f"del_mes_{str(callback.from_user.id)}", *[del_mes_1.message_id])
    # Аналог os.remove()
    Path(f"data/med_exam/completed_q/Согласие_{'_'.join(data['name'].split()[:2])}.pdf").unlink()
    return data, age


# Функция назначения и начала анкетирования
async def start_questionnaire(callback, state, data, msg_text: str, questionnaire: str, prefix: str, questions: dict,
                              digit_answers: list, conditional_answers: list, redis: Redis):
    from handlers import questions_dict, questions_list, digit_answer, conditional_answer
    common_note = ("\n\n📤 *Анкеты будут сформированы автоматически на основе ваших ответов и отправлены в клинику.*\n"
                   "🔄 Если допустили ошибку или заметили, что бот неверно записал ответ, Вы всегда можете "
                   "отменить заполнение и начать заново."
                   "\n\n⏱️ Примерное время заполнения: *{time} минут*\n"
                   "📌 Вы в любой момент можете продолжить с того места, где остановились, если не отмените заполнение."
                   "\n\n⚠️ Пожалуйста, не спешите! Если после нажатия кнопки ничего не происходит, подождите "
                   "пару секунд и повторите попытку.\n\n"
                   "📝 *Желаем вам успешного и комфортного заполнения!*")
    param_to_text_keyboard = {
        "m30": "✅ *Отлично!* Вам предстоит заполнить две анкеты:\n"
               "• '*Анкета для граждан в возрасте до 65 лет*';\n"
               "• '*Анамнестическая анкета для оценки риска нарушений репродуктивного "
               "здоровья для мужчин 18 - 49 лет*'."
               + common_note.format(time=10),
        "w49": "✅ *Отлично!* Вам предстоит заполнить две анкеты:\n"
               "• '*Анкета для граждан в возрасте до 65 лет*';\n"
               "• '*Анамнестическая анкета для женщин 18-49 лет*'."
               + common_note.format(time=15),
        "<65": "✅ *Отлично!* Вам предстоит заполнить одну анкету:\n"
               "• '*Анкета для граждан в возрасте до 65 лет*'."
               + common_note.format(time=10),
        ">65": "✅ *Отлично!* Вам предстоит заполнить одну анкету:\n"
               "• '*Анкета для граждан в возрасте 65 лет и старше*'."
               + common_note.format(time=10),
        "seq": "✅ *Данные успешно сохранены!*\n\nТеперь перейдём к заполнению *второй анкеты*."
    }
    msg_text = param_to_text_keyboard[msg_text]
    del_mes_1 = await callback.message.answer(text=msg_text, reply_markup=cancel_kb("med_exam"))
    await redis.lpush(f"del_mes_{str(callback.from_user.id)}", *[del_mes_1.message_id])
    await state.update_data(template_path="med_exam/" + questionnaire)
    await state.update_data(output_doc_path=f"med_exam/completed_q/Анкета_{prefix}"
                                            f"{"_".join(data['name'].split()[:2])}_"
                                            f"{datetime.now().strftime("%H%M%S")}")
    questions_dict.update(questions)
    if questionnaire == "AnketaDo65" or questionnaire == "AnketaPosle65":
        questions_dict.update(covid_questi)
    questions_list.extend(questions_dict.keys())
    digit_answer.extend(digit_answers)
    conditional_answer.extend(conditional_answers)
    if prefix != "для_женщин_":
        del_mes_2 = await callback.bot.send_message(chat_id=callback.from_user.id,
                                                    text=questions_dict["1_1"][0],
                                                    reply_markup=questions_ikb())
        await redis.lpush(f"del_tech_{str(callback.from_user.id)}", *[del_mes_2.message_id])
        await state.update_data(msg_text=questions_dict["1_1"][0])


# Функция, проверяющая окончание анкеты и начинающая вторую или отправляет готовые
async def finish_questionnaire(callback, state, data, key, key_word, redis, msg_text=None):
    from handlers import questions_dict, questions_list, digit_answer, conditional_answer, answers_dict
    from .docx_pdf import convert_docx_to_pdf
    user_text = ("\n\n📨 *Ваша заявка передана в Полимедику.*\n📞 В течение 3 рабочих дней с Вами свяжется оператор "
                 f"для уточнения даты прохождения диспансеризации по номеру, указанному ранее: *{data["number"]}*"
                 f"\n\n🖨️ Вы можете:\n• распечатать файл(ы) самостоятельно,\n• или попросить распечатку в клинике.")
    group_text = (f"👆 Новая заявка на диспансеризацию! 👆\n\nДата заполнения: *{data["current_date"]}\n*ФИО "
                  f"пациента: *{data["name"]}*\nНомер телефона: *{data["number"]}*")
    if key == "c_1" or data["q_num"] + 1 == len(questions_list):
        if msg_text is not None:
            await callback.message.edit_text(text=msg_text + f" (*{answers_dict[key_word]}*)",
                                             reply_markup=None)
        answers_dict.update(data)
        notification = await callback.bot.send_message(chat_id=callback.from_user.id,
                                                       text="Заполняю документ...",
                                                       reply_markup=ReplyKeyboardRemove())
        pdf_path = convert_docx_to_pdf(str(data["template_path"]), answers_dict, str(data["output_doc_path"]))
        one_completed_questionnaire = str(data["output_doc_path"])
        await callback.bot.delete_message(chat_id=callback.from_user.id,
                                          message_id=notification.message_id)
        for struct in [answers_dict, questions_dict, questions_list, digit_answer, conditional_answer]:
            struct.clear()
        if ((data["gender"] == "Женский" and data["age"] > 49) or (data["gender"] == "Мужской" and data["age"] > 30)
                or (data["gender"] == "Женский" and data["age"] <= 49 and data["pregnant"])):
            async with ChatActionSender.upload_document(
                    bot=callback.bot,
                    chat_id=callback.chat.id if isinstance(callback, types.Message) else callback.message.chat.id):
                await callback.bot.send_document(chat_id=callback.from_user.id,
                                                 document=types.FSInputFile(pdf_path),
                                                 caption="✅ Вы успешно заполнили анкету!" + user_text,
                                                 message_effect_id="5046509860389126442",
                                                 reply_markup=menu_kb())
                await callback.bot.send_document(chat_id=await redis.get(name="gid_med_exam"),
                                                 document=types.FSInputFile(pdf_path),
                                                 caption=group_text)
                await state.clear()
                os.remove(pdf_path)
            await delete_redis_mes(callback, redis, f"del_mes_{str(callback.from_user.id)}")
            await delete_redis_mes(callback, redis, f"del_tech_{str(callback.from_user.id)}")
            return True
        if data["gender"] == "Женский" and data["age"] <= 49:
            if await sent_questionnaire(callback, state, data, await redis.get(name="gid_med_exam"),
                                        "✅ Вы успешно заполнили анкеты!" + user_text,
                                        group_text, prefix="для_женщин_", redis=redis):
                return True
            await start_questionnaire(callback, state, data, "seq", "AnketaWoman", "для_женщин_",
                                      anketa_woman, anketa_woman_digit_answer, anketa_woman_conditional_answer, redis)
            del_mes_1 = await callback.bot.send_message(chat_id=callback.from_user.id,
                                                        text=questions_dict["1"][1],
                                                        reply_markup=questions_dict["1"][2])
            await redis.lpush(f"del_tech_{str(callback.from_user.id)}", *[del_mes_1.message_id])
            await state.update_data(msg_text="")
            await state.set_state(MedExam.digit_answer)
            await state.update_data(q_num=0)
            await state.update_data(one_completed_questionnaire=one_completed_questionnaire)
        if data["gender"] == "Мужской" and data["age"] <= 30:
            if await sent_questionnaire(callback, state, data, await redis.get(name="gid_med_exam"),
                                        "✅ Вы успешно заполнили анкеты!" + user_text,
                                        group_text, prefix="для_мужчин_", redis=redis):
                return True
            await start_questionnaire(callback, state, data, "seq", "AnketaMan", "для_мужчин_",
                                      anketa_rep_m, anketa_rep_m_digit_answer, [], redis)
            await state.update_data(q_num=0)
            await state.update_data(one_completed_questionnaire=one_completed_questionnaire)
        return True
    return False


# Функция, отправляющая анкеты пользователю и в группу
async def sent_questionnaire(callback, state, data, group_id, user_text, group_text, prefix, redis):
    required_files = []
    for filename in Path("data/med_exam/completed_q").iterdir():
        if (filename.name.startswith(f"Анкета_{prefix}{'_'.join(data['name'].split()[:2])}") or
                filename.name.startswith(f"Анкета_{'_'.join(data['name'].split()[:2])}")):
            required_files.append(filename)
        if len(required_files) == 2:
            async with ChatActionSender.upload_document(
                    bot=callback.bot,
                    chat_id=callback.chat.id if isinstance(callback, types.Message) else callback.message.chat.id):
                await callback.bot.send_media_group(chat_id=callback.from_user.id,
                                                    media=[
                                                        InputMediaDocument(media=types.FSInputFile(required_files[0])),
                                                        InputMediaDocument(media=types.FSInputFile(required_files[1]))])
                await callback.bot.send_message(chat_id=callback.from_user.id,
                                                text=user_text,
                                                reply_markup=menu_kb(),
                                                message_effect_id="5046509860389126442")
            await callback.bot.send_media_group(chat_id=group_id,
                                                media=[InputMediaDocument(media=types.FSInputFile(required_files[0])),
                                                       InputMediaDocument(media=types.FSInputFile(required_files[1]))])
            await callback.bot.send_message(chat_id=group_id,
                                            text=group_text)
            await state.clear()
            for file in required_files:
                os.remove(file)
            required_files.clear()
            await delete_redis_mes(callback, redis, f"del_tech_{str(callback.from_user.id)}")
            await delete_redis_mes(callback, redis, f"del_mes_{str(callback.from_user.id)}")
            return True
    return False


# Функция, присылающая вопрос, который предусматривает ответ в виде числа
async def digit_question(callback, state, data, msg_text, key_word, key_1, redis):
    from handlers import answers_dict, questions_dict
    await callback.message.edit_text(text=msg_text + f" (*{answers_dict[key_word]}*)", reply_markup=None)
    await state.update_data(msg_text=msg_text + f" (*{answers_dict[key_word]}*)")
    del_mes_1 = await callback.bot.send_message(chat_id=callback.from_user.id,
                                                text=questions_dict[key_1][1],
                                                reply_markup=questions_dict[key_1][2])
    await redis.lpush(f"del_tech_{str(callback.from_user.id)}", *[del_mes_1.message_id])
    await state.update_data(q_num=data["q_num"] + 1)
    await state.set_state(MedExam.digit_answer)


# Функция, дополняющая анкеты следующим сообщением
async def edit_questionnaire(callback, state, data, key_word, key_1, msg_text=""):
    from handlers import answers_dict, questions_dict
    await callback.message.edit_text(text=msg_text + f" (*{answers_dict[key_word]}*)\n*{questions_dict[key_1][0]}*",
                                     reply_markup=questions_dict[key_1][1])
    await state.update_data(msg_text=msg_text + f" (*{answers_dict[key_word]}*)\n{questions_dict[key_1][0]}")
    await state.update_data(q_num=data["q_num"] + 1)


# Метод для перехода к кнопочным ответам после digit_answer
async def transition_to_state_questions(message, state, data, key_word, key_1, key, redis):
    from handlers import answers_dict, questions_dict
    if isinstance(questions_dict[key_1][1], str):
        await state.update_data(
            msg_text=data["msg_text"] + "\n" + questions_dict[key][0] + f" *{answers_dict[key_word]}*")
        del_mes_1 = await message.bot.send_message(chat_id=message.from_user.id,
                                                   text=data["msg_text"] + "\n" + questions_dict[key][0] +
                                                                           f" *{answers_dict[key_word]}*")
        del_mes_2 = await message.bot.send_message(chat_id=message.from_user.id,
                                                   text=questions_dict[key_1][1],
                                                   reply_markup=questions_dict[key_1][2])
        await delete_redis_mes(message, redis, f"del_tech_{str(message.from_user.id)}")
        await redis.lpush(f"del_tech_{str(message.from_user.id)}", *[del_mes_1.message_id, del_mes_2.message_id])
        await state.update_data(q_num=data["q_num"] + 1)
        return
    else:
        del_mes_1 = await message.bot.send_message(chat_id=message.from_user.id,
                                                   text=data["msg_text"] + "\n" + questions_dict[key][0] +
                                                                           f" *{answers_dict[key_word]}*\n*"
                                                                           f"{questions_dict[key_1][0]}*",
                                                   reply_markup=questions_dict[key_1][1])
        await state.update_data(msg_text=data["msg_text"] + "\n" + questions_dict[key][0] +
                                                            f" *{answers_dict[key_word]}*\n{questions_dict[key_1][0]}")
        await delete_redis_mes(message, redis, f"del_tech_{str(message.from_user.id)}")
        await redis.lpush(f"del_tech_{str(message.from_user.id)}", *[del_mes_1.message_id])
        await state.update_data(q_num=data["q_num"] + 1)
        await state.set_state(MedExam.questions)


# Функция, пропускающая вопросы, ответ на который не требуется
async def skip_multiple_cond_q(state, data, questions_list):
    while "s" in str(questions_list[data["q_num"]+1]):
        await state.update_data(q_num=data["q_num"] + 1)
        data = await state.get_data()
    key_1 = questions_list[data["q_num"]+1]
    return data, key_1


async def write_answer_to_dict(callback, state, param: str, score: str = "", f_data: str = ""):
    from handlers import questions_list, answers_dict, questions_dict
    data = await state.get_data()
    msg_text = data["msg_text"]
    key = questions_list[data["q_num"]]
    param_to_text_keyboard = {
        "y": ("y_", "", "", "", questions_dict[key][1]),
        "n": ("n_", "", "", "", questions_dict[key][1]),
        "f": ("f_" + score + "_", "", "", "\n(" + score + " балл" + f_data, questions_dict[key][1]),
        "l": ("", "_" + score, answers_dict.get("d_c_2", "") + " мес. ", "", level_ikb()),
        "r": ("", "_" + score, "", "", questions_dict[key][1]),
        "b": ("w_", "", "", "", questions_dict.get(key,
              ["", "", None])[2] if len(questions_dict.get(key, ("",))) > 2 else None),
        "w": ("w_", "", "", "", None)
    }
    pref_k_word, post_k_word, pref_ans, post_ans, keyb = param_to_text_keyboard[param]
    key_word = pref_k_word + key + post_k_word
    if param == "w":
        answers_dict[key_word] = callback.text
        return data, msg_text, key, key_word
    answers_dict[key_word] = pref_ans + await get_button_text_from_keyboard(callback, keyb) + post_ans
    return data, msg_text, key, key_word


# Функция, конвертирующая номер месяца в название
def get_month_name(month_str):
    months = {
        '1': 'января', '2': 'февраля', '3': 'марта', '4': 'апреля',
        '5': 'мая', '6': 'июня', '7': 'июля', '8': 'августа',
        '9': 'сентября', '10': 'октября', '11': 'ноября', '12': 'декабря'
    }
    return months.get(month_str, 'Некорректный месяц')


# Метод, отправляющий сообщение с запросом данных по справке МСЭ
async def mse_text_message(callback, state, redis):
    del_mes_1 = await callback.bot.send_photo(
        chat_id=callback.from_user.id,
        caption="📄 Введите *номер, серию и дату выдачи* Вашей справки МСЭ:\n\n🖼 На изображении ниже показано, "
                "где расположены эти данные.\n📌 Пример ввода: *'МСЭ-2006 0005220136 22.05.2007'*",
        reply_markup=cancel_kb("certification", "Серия Номер Дата"),
        photo=types.FSInputFile(Path("data/med_certificate/msa_example.jpg")),
        show_caption_above_media=True)
    await redis.lpush(f"del_mes_{str(callback.from_user.id)}", *[del_mes_1.message_id])
    await state.set_state(Certificates.c70_mse)


# Метод, обрабатывающий слишком длинные сообщения в диспансеризации
async def message_is_too_long(callback, state, data, answers_dict, key_word, questions_dict, key_1, e, redis):
    if 'MESSAGE_TOO_LONG' in str(e):
        await callback.message.edit_reply_markup(None)
        del_mes_1 = await callback.message.answer(text=f"*{answers_dict[key_word]}*\n*{questions_dict[key_1][0]}*",
                                                  reply_markup=questions_dict[key_1][1])
        # При разделении сообщений переносим первое сообщение в отдельный список, чтобы он не удалялся раньше нужного
        message_ids = await redis.lrange(f"del_tech_{callback.from_user.id}", 0, -1)
        if message_ids:
            await redis.lpush(f"del_mes_{callback.from_user.id}", message_ids[-1])
            # Удаляем оставшиеся технические сообщения, кроме самой анкеты
            for msg_id in message_ids[:-1]:
                await callback.bot.delete_message(chat_id=callback.from_user.id, message_id=int(msg_id))
            await redis.delete(f"del_tech_{callback.from_user.id}")
        await redis.lpush(f"del_tech_{str(callback.from_user.id)}", *[del_mes_1.message_id])
        await state.update_data(msg_text=f"*{answers_dict[key_word]}*\n{questions_dict[key_1][0]}")
        await state.update_data(q_num=data["q_num"] + 1)


# Метод, который обрабатывает некоторые моменты при заполнении анкет для диспансеризаций у женщин
async def skip_questions_women_med_exam(callback, state, data, key_word, redis):
    from handlers import questions_dict, answers_dict, questions_list
    await state.update_data(q_num=data["q_num"] + 1)
    data = await state.get_data()
    key_1 = questions_list[data["q_num"] + 1]
    if questions_list[data["q_num"]] == "10_a":
        await callback.message.edit_text(text=data["msg_text"] + f" (*{answers_dict[key_word]}*)", reply_markup=None)
        await state.update_data(msg_text=data["msg_text"] + f" (*{answers_dict[key_word]}*)")
        await state.set_state(MedExam.digit_answer)
    else:
        await state.update_data(msg_text=data["msg_text"] + f" *{answers_dict[key_word]}*\n{questions_dict[key_1][0]}")
    del_mes_2 = await callback.bot.send_message(chat_id=callback.from_user.id,
                                                text=questions_dict[key_1][1],
                                                reply_markup=questions_dict[key_1][2])
    await redis.lpush(f"del_mes_{str(callback.from_user.id)}", *[del_mes_2.message_id])
    await state.update_data(q_num=data["q_num"] + 1)
