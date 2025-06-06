from aiogram import F, Router, flags
from aiogram.enums import ChatAction
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter, or_f
from aiogram.exceptions import TelegramBadRequest

from utils import *
from filters import ComplaintWithFile
from data.med_exam.questioniers import *
from states import Address, EditComplaint

import re
from redis.asyncio import Redis

router_cal = Router()

questions_dict = {}  # Словарь значений для заданной анкеты
questions_list = []  # Список ключей для заданной анкеты
digit_answer = []  # Список ключей вопросов, требующих ответ числом или текстом в исключительных случаях
conditional_answer = []  # Список вопросов, необходимость ответов на которые зависит от ответа на предыдущий вопрос
answers_dict = {}  # Словарь ответов для вставки в файл


"""******************************************* ВАЛИДАЦИЯ ДАННЫХ Ч1 ********************************************"""


@router_cal.callback_query(F.data == "edit_file", StateFilter(Complaint.final), ComplaintWithFile())
async def can_not_edit_file(callback: types.CallbackQuery, redis: Redis):
    await callback.answer()
    del_mes_1 = await callback.message.answer(
        text="📎 *Вы не можете прикрепить файл, пока текст обращения превышает 590 символов.*\n\nЧтобы добавить "
             "документ, сократите текст до *590 символов или меньше*, "
             "после чего Вам станет доступна функция '*Файл*' в разделе '*Изменить данные*'.")
    await redis.lpush(f"del_tech_{str(callback.from_user.id)}", *[del_mes_1.message_id])


"""*********************************** ИНФОРМАЦИЯ О КЛИНИКАХ И ПРИКРЕПЛЕНИИ ***********************************"""


@router_cal.callback_query(F.data == 'clinic', StateFilter(None))
async def know_clinic(callback: types.CallbackQuery, state: FSMContext, redis: Redis):
    await callback.answer()
    del_mes_1 = await callback.message.answer(
          text="🏠 Введите адрес проживания, чтобы узнать клинику, к которой Вы прикреплены: \n\n"
               "ℹ️ Пример адреса: `Салавата Юлаева 23А` \n\n"
               "🛣 Если вы живёте в *Сосновском районе*, вводите адрес в формате: *«посёлок, микрорайон, улица»* "
               "(без номера дома)\nЕсли вы из посёлков *«Шершни», «Тарасовка» или «Карпов Пруд»*, вводите в формате: "
               "*«посёлок, улица»* (без номера дома)\n\n❗️*Важно: бот чувствителен к формату!* Не ставьте запятую "
               "между улицей и номером дома, а литеру здания пишите сразу после номера, без пробела.",
          reply_markup=cancel_kb("search", "Адрес дома"))
    await redis.lpush(f"del_mes_{str(callback.from_user.id)}", *[del_mes_1.message_id])
    await state.set_state(Address.address)


@router_cal.callback_query(F.data == "yes", flags={"throttle": "check"})
async def yes_address(callback: types.CallbackQuery, state: FSMContext, redis: Redis):
    await delete_redis_mes(callback, redis, f"del_tech_{str(callback.from_user.id)}")
    await callback.message.delete()
    await callback.message.answer(text=f"😔 К сожалению, мы не нашли Ваш адрес "
                                       f"(`{re.search(r'\((.*?)\)', callback.message.text).group(1)}`) "
                                       f"в нашей территории обслуживания. \n\n"
                                       "🏥 Вы можете подойти в любой филиал Полимедики для уточнения условий "
                                       "прикрепления к нашей поликлиники. Возьмите, пожалуйста, с собой *паспорт, "
                                       "полис ОМС, СНИЛС*. Адреса клиник можно посмотреть на [сайте]"
                                       "(https://mnogomed.ru/chelyabinsk/contacts?ysclid=m60ip80gzi494077339#130a) "
                                       "или на фотографии с графиком работы клиник выше.\n\n"
                                       "📞 Для уточнения информации звоните по номеру +73512409977",
                                  disable_web_page_preview=True,
                                  reply_markup=menu_kb())
    await delete_redis_mes(callback, redis, f"del_mes_{str(callback.from_user.id)}")
    await state.set_state(None)


@router_cal.callback_query(F.data == "no", flags={"throttle": "check"})
async def no_address(callback: types.CallbackQuery, state: FSMContext, redis: Redis):
    await delete_redis_mes(callback, redis, f"del_tech_{str(callback.from_user.id)}")
    await callback.message.delete()
    del_mes_1 = await callback.message.answer(text="🔄 Повторите попытку ввода адреса:")
    await redis.lpush(f"del_mes_{str(callback.from_user.id)}", *[del_mes_1.message_id])
    await state.set_state(Address.address)


"""************************************* ОФОРМЛЕНИЕ ЖАЛОБ И ПРЕДЛОЖЕНИЙ **************************************"""


@router_cal.callback_query(F.data == "agree", StateFilter(Complaint.agreement), flags={"throttle": "check"})
async def agree_processing_data(callback: types.CallbackQuery, state: FSMContext, redis: Redis):
    await delete_redis_mes(callback, redis, f"del_tech_{str(callback.from_user.id)}")
    await agree_data(callback, "Выберите тему жалобы:", complaint_topics_ikb(), state, Complaint.topic, redis)


@router_cal.callback_query(F.data == "disagree", or_f(StateFilter(Complaint.agreement),
                                                      StateFilter(MedExam.agreement),
                                                      StateFilter(Certificates.agreement)),
                           flags={"throttle": "check"})
async def disagree_processing_data(callback: types.CallbackQuery, state: FSMContext, redis: Redis):
    await delete_redis_mes(callback, redis, f"del_tech_{str(callback.from_user.id)}")
    await callback.message.delete()
    await callback.message.answer(text="⚖️ *Вы отказались от согласия на обработку персональных данных.*\n🛎️ В таком "
                                       "случае мы не можем оказать Вам услугу согласно действующему законодательству.",
                                  reply_markup=menu_kb())
    await state.set_state(None)
    await delete_redis_mes(callback, redis, f"del_mes_{str(callback.from_user.id)}")


@router_cal.callback_query(F.data.contains("topic"), StateFilter(Complaint.topic), flags={"throttle": "check"})
async def make_complaint_topic(callback: types.CallbackQuery, state: FSMContext, redis: Redis):
    await delete_redis_mes(callback, redis, f"del_tech_{str(callback.from_user.id)}")
    await callback.answer()
    await state.update_data(topic=callback.message.reply_markup.inline_keyboard[int(callback.data[-1]) - 1][0].text)
    del_mes_1 = await callback.message.edit_text(
        text=f"Тема жалобы: *{callback.message.reply_markup.inline_keyboard
                              [int(callback.data[-1]) - 1][0].text}*\n\n"
             f"❗️ *Все данные можно будет изменить после заполнения обращения*",)
    del_mes_2 = await callback.message.answer(text="Укажите Ваши Фамилию Имя Отчество (при наличии):",
                                              reply_markup=cancel_kb("create", "Фамилия Имя Отчество"))
    await redis.lpush(f"del_mes_{str(callback.from_user.id)}", *[del_mes_1.message_id, del_mes_2.message_id])
    await state.set_state(Complaint.name)


@router_cal.callback_query(F.data == "no_doc", or_f(StateFilter(Complaint.file), StateFilter(EditComplaint.edit_file)))
async def make_complaint_without_file(callback: types.CallbackQuery, state: FSMContext, redis: Redis):
    await delete_redis_mes(callback, redis, f"del_tech_{str(callback.from_user.id)}")
    await callback.answer()
    remove_kb_text = {"file": "✅ Создание обращения завершено!", "edit_file": "Данные успешно изменены!"}
    cur_state = await state.get_state()
    del_mes_1 = await callback.message.answer(text=remove_kb_text[cur_state.split(":")[-1]],
                                              reply_markup=ReplyKeyboardRemove())
    await redis.lpush(f"del_tech_{str(callback.from_user.id)}", *[del_mes_1.message_id])
    data = await state.get_data()
    if "file" in data:
        del data["file"]
    await state.set_data(data)
    await callback.message.answer(text=complaint_text(data, 2, 0),
                                  reply_markup=change_complaint_ikb())
    await state.set_state(Complaint.final)
    await delete_redis_mes(callback, redis, f"del_mes_{str(callback.from_user.id)}")


@router_cal.callback_query(F.data == "send", StateFilter(Complaint.final), flags={"throttle": "check"})
async def send_complaint(callback: types.CallbackQuery, state: FSMContext, redis: Redis):
    await delete_redis_mes(callback, redis, f"del_tech_{str(callback.from_user.id)}")
    data = await state.get_data()
    if "file" in data:
        await callback.message.edit_caption(caption=complaint_text(data, 4, 0))
        await callback.bot.send_document(chat_id=await redis.get(name="gid_complaints"),
                                         document=str(data["file"]),
                                         caption=complaint_text(data, 1, 0, "Новое"))
    else:
        await callback.message.edit_text(text=complaint_text(data, 4, 0))
        await callback.bot.send_message(chat_id=await redis.get(name="gid_complaints"),
                                        text=complaint_text(data, 1, 0, "Новое"))
    await callback.message.answer(text="🙏 Спасибо, Ваше обращение принято к рассмотрению службой качества! \n\n"
                                       f"⏳ Сотрудник службы качества свяжется с Вами по указанному номеру телефона "
                                       f"({str(data["number"])}) в течение 3 рабочих дней.",
                                  reply_markup=menu_kb())
    await state.clear()
    await delete_redis_mes(callback, redis, f"del_mes_{str(callback.from_user.id)}")
    await delete_redis_mes(callback, redis, f"del_tech_{str(callback.from_user.id)}")


@router_cal.callback_query(F.data == "cancel_send", StateFilter(Complaint.final), flags={"throttle": "check"})
async def cancel_send_complaint(callback: types.CallbackQuery, state: FSMContext, redis: Redis):
    await delete_redis_mes(callback, redis, f"del_tech_{str(callback.from_user.id)}")
    data = await state.get_data()
    if "file" in data:
        await callback.message.edit_caption(caption=complaint_text(data, 5, 0))
    else:
        await callback.message.edit_text(text=complaint_text(data, 5, 0))
    await callback.message.answer(text="🛑 Вы успешно отменили отправку обращения!",
                                  reply_markup=menu_kb())
    await state.clear()
    await delete_redis_mes(callback, redis, f"del_mes_{str(callback.from_user.id)}")
    await delete_redis_mes(callback, redis, f"del_tech_{str(callback.from_user.id)}")


"""******************************************** ИЗМЕНЕНИЕ ДАННЫХ *********************************************"""


@router_cal.callback_query(F.data == "change", StateFilter(Complaint.final), flags={"throttle": "check"})
async def change_complaint(callback: types.CallbackQuery, state: FSMContext, redis: Redis):
    await delete_redis_mes(callback, redis, f"del_tech_{str(callback.from_user.id)}")
    await callback.answer()
    data = await state.get_data()
    if callback.message.document:
        await callback.message.edit_caption(caption=complaint_text(data, 3, 0))
    else:
        await callback.message.edit_text(text=complaint_text(data, 3, 0))
    await callback.message.edit_reply_markup(reply_markup=edit_complaint_ikb())


@router_cal.callback_query(F.data.contains("edit"), StateFilter(Complaint.final))
async def changing_complaint(callback: types.CallbackQuery, state: FSMContext, redis: Redis):
    await delete_redis_mes(callback, redis, f"del_tech_{str(callback.from_user.id)}")
    p = str(callback.data[5:])
    data = await state.get_data()
    chat_id = callback.from_user.id
    old_data = ""
    if p != "file" and p != "back":
        old_data = f"\n\n*Ваши текущие данные*: `{str(data[p])}` (нажмите, чтобы скопировать для более удобной правки)"
    param_to_text_keyboard = {
        "topic": ("Выберите новую тему жалобы:", complaint_topics_ikb(), ""),
        "name": ("Введите исправленные Фамилию Имя Отчество (при наличии):",
                 cancel_kb("edit", "Фамилия Имя Отчество"), old_data),
        "birth": ("Введите исправленную дату рождения в формате 'дд.мм.гггг':", cancel_kb("edit", "дд.мм.гггг"),
                  old_data),
        "number": ("Введите новый номер телефона для дальнейшей связи, начиная с +7 без пробелов:",
                   cancel_kb("edit", "+7xxxxxxxxxx"), old_data),
        "complaint": ("Введите исправленную жалобу или предложение:", cancel_kb("edit"), old_data),
        "file": (
            "Отправьте новый документ.\n\n⚠️ *Будьте внимательны, Вы можете прикрепить только 1 документ! Если вы "
            "отправить больше, то к обращение прикрепится первый полученный документ.*\n\n"
            "Если хотите удалить текущий документ, то нажмите на кнопку 'Без документа'",
            document_no_ikb(), ""),
    }
    if p == "back":
        if "file" in data:
            await callback.message.edit_caption(caption=complaint_text(data, 2, 0))
        else:
            await callback.message.edit_text(text=complaint_text(data, 2, 0))
        await callback.message.edit_reply_markup(reply_markup=change_complaint_ikb())
    if p in param_to_text_keyboard:
        text, keyb, old_data = param_to_text_keyboard[p]
        await callback.message.delete()
        del_mes_1 = await callback.bot.send_message(chat_id=chat_id, text=text + old_data, reply_markup=keyb)
        await state.set_state(getattr(EditComplaint, callback.data))
        await redis.lpush(f"del_mes_{str(callback.from_user.id)}", *[del_mes_1.message_id])


@router_cal.callback_query(F.data.contains('topic'), StateFilter(EditComplaint.edit_topic), flags={"throttle": "check"})
async def edit_complaint_topic(callback: types.CallbackQuery, state: FSMContext, redis: Redis):
    await delete_redis_mes(callback, redis, f"del_tech_{str(callback.from_user.id)}")
    await callback.message.delete()
    await edited_complaint(callback, state, 1, redis, "topic",
                           callback.message.reply_markup.inline_keyboard[int(callback.data[-1]) - 1][0].text)
    await delete_redis_mes(callback, redis, f"del_mes_{str(callback.from_user.id)}")


"""****************************************** ПРОЙТИ ДИСПАНСЕРИЗАЦИЮ *******************************************"""


@router_cal.callback_query(F.data == "med_exam", StateFilter(None))
@flags.chat_action(action=ChatAction.UPLOAD_DOCUMENT)
async def med_exam_agreement(callback: types.CallbackQuery, state: FSMContext, redis: Redis):
    await callback.answer()
    await call_agreement(callback, redis)
    await state.set_state(MedExam.agreement)


@router_cal.callback_query(F.data == "agree", StateFilter(MedExam.agreement), flags={"throttle": "check"})
async def agree_processing_data(callback: types.CallbackQuery, state: FSMContext, redis: Redis):
    await delete_redis_mes(callback, redis, f"del_tech_{str(callback.from_user.id)}")
    await agree_data(callback, "Введите Вашу дату рождения в формате 'дд.мм.гггг':",
                     cancel_kb("med_exam", "дд.мм.гггг"), state, MedExam.birth, redis)


@router_cal.callback_query(F.data == "man", StateFilter(MedExam.gender), flags={"throttle": "check"})
@flags.chat_action(action=ChatAction.UPLOAD_DOCUMENT)
async def med_exam_questions(callback: types.CallbackQuery, state: FSMContext, redis: Redis):
    await delete_redis_mes(callback, redis, f"del_tech_{str(callback.from_user.id)}")
    data, age = await prep_questionnaire(callback, state, "Мужской", redis)
    if age <= 30:
        await start_questionnaire(callback, state, data, "m30", "AnketaDo65", "", anketa_do_65,
                                  anketa_do_65_digit_answer, anketa_do_65_conditional_answer, redis)
    elif 30 < age <= 65:
        await start_questionnaire(callback, state, data, "<65", "AnketaDo65", "", anketa_do_65,
                                  anketa_do_65_digit_answer, anketa_do_65_conditional_answer, redis)
    elif age > 65:
        await start_questionnaire(callback, state, data, ">65", "AnketaPosle65", "", anketa_po_65,
                                  anketa_po_65_digit_answer, anketa_po_65_conditional_answer, redis)


@router_cal.callback_query(F.data == "woman", StateFilter(MedExam.gender), flags={"throttle": "check"})
@flags.chat_action(action=ChatAction.UPLOAD_DOCUMENT)
async def med_exam_questions(callback: types.CallbackQuery, state: FSMContext, redis: Redis):
    await delete_redis_mes(callback, redis, f"del_tech_{str(callback.from_user.id)}")
    data, age = await prep_questionnaire(callback, state, "Женский", redis)
    if age <= 49:
        del_mes_1 = await callback.message.answer(text="Беременны ли Вы в данный момент?", reply_markup=questions_ikb())
        await redis.lpush(f"del_mes_{str(callback.from_user.id)}", *[del_mes_1.message_id])
        await state.set_state(MedExam.pregnant)
    elif 49 < age <= 65:
        await start_questionnaire(callback, state, data, "<65", "AnketaDo65", "", anketa_do_65,
                                  anketa_do_65_digit_answer, anketa_do_65_conditional_answer, redis)
    elif age > 65:
        await start_questionnaire(callback, state, data, ">65", "AnketaPosle65", "", anketa_po_65,
                                  anketa_po_65_digit_answer, anketa_po_65_conditional_answer, redis)


@router_cal.callback_query(StateFilter(MedExam.pregnant), flags={"throttle": "check"})
async def woman_is_pregnant(callback: types.CallbackQuery, state: FSMContext, redis: Redis):
    await delete_redis_mes(callback, redis, f"del_tech_{str(callback.from_user.id)}")
    await callback.bot.delete_message(chat_id=callback.from_user.id, message_id=callback.message.message_id)
    data = await state.get_data()
    await state.set_state(MedExam.questions)
    if callback.data == "q_yes":
        await start_questionnaire(callback, state, data, "<65", "AnketaDo65", "", anketa_do_65,
                                  anketa_do_65_digit_answer, anketa_do_65_conditional_answer, redis)
        await state.update_data(pregnant=1)
    else:
        await start_questionnaire(callback, state, data, "w49", "AnketaDo65", "", anketa_do_65,
                                  anketa_do_65_digit_answer, anketa_do_65_conditional_answer, redis)


@router_cal.callback_query(F.data == "q_yes", StateFilter(MedExam.questions), flags={"throttle": "check"})
async def question_yes(callback: types.CallbackQuery, state: FSMContext, redis: Redis):
    data, msg_text, key, key_word = await write_answer_to_dict(callback, state, "y")
    if data["q_num"] + 1 == len(questions_list):
        if await finish_questionnaire(callback, state, data, key, key_word, redis, msg_text):
            return
    key_1 = questions_list[data["q_num"] + 1]
    if key_1 in digit_answer:
        await digit_question(callback, state, data, msg_text, key_word, key_1, redis)
        if key_1 == "1_9_a" or key_1 == "1_3_a":
            await state.set_state(MedExam.write_answer)
        return
    try:
        await edit_questionnaire(callback, state, data, key_word, key_1, msg_text)
    except TelegramBadRequest as e:
        await message_is_too_long(callback, state, data, answers_dict, key_word, questions_dict, key_1, e, redis)


@router_cal.callback_query(F.data == "q_no", StateFilter(MedExam.questions), flags={"throttle": "check"})
async def question_no(callback: types.CallbackQuery, state: FSMContext, redis: Redis):
    data, msg_text, key, key_word = await write_answer_to_dict(callback, state, "n")
    if await finish_questionnaire(callback, state, data, key, key_word, redis, msg_text):
        return
    key_1 = questions_list[data["q_num"]+1]
    try:
        if key_1 == "10_a":
            await skip_questions_women_med_exam(callback, state, data, key_word, redis)
            return
        if key_1 in conditional_answer:
            await state.update_data(q_num=data["q_num"] + 1)
            data = await state.get_data()
            data, key_1 = await skip_multiple_cond_q(state, data, questions_list)
            await edit_questionnaire(callback, state, data, key_word, key_1, msg_text)
            return
        if key_1 in digit_answer:
            await digit_question(callback, state, data, msg_text, key_word, key_1, redis)
            return
        await edit_questionnaire(callback, state, data, key_word, key_1, msg_text)
    except TelegramBadRequest as e:
        await message_is_too_long(callback, state, data, answers_dict, key_word, questions_dict, key_1, e, redis)


@router_cal.callback_query(F.data.startswith("frequency"), StateFilter(MedExam.questions), flags={"throttle": "check"})
async def question_frequency(callback: types.CallbackQuery, state: FSMContext, redis: Redis):
    score = callback.data.split("_")[-1]
    data, msg_text, key, key_word = await write_answer_to_dict(callback, state, "f",
                                                               score, callback.data.split("_")[-2])
    key_1 = questions_list[data["q_num"]+1]
    await state.update_data(frequency_test=data["frequency_test"] + int(score))
    try:
        await edit_questionnaire(callback, state, data, key_word, key_1, msg_text)
    except TelegramBadRequest as e:
        await message_is_too_long(callback, state, data, answers_dict, key_word, questions_dict, key_1, e, redis)


@router_cal.callback_query(F.data.startswith("level"), StateFilter(MedExam.questions), flags={"throttle": "check"})
async def question_level(callback: types.CallbackQuery, state: FSMContext, redis: Redis):
    score = callback.data.split("_")[-1]
    data, msg_text, key, key_word = await write_answer_to_dict(callback, state, "l", score)
    key_1 = questions_list[data["q_num"]+1]
    msg_text += "\n" + questions_dict[key][0] + f" (*{answers_dict[key_word]}*)\n{questions_dict[key_1][0]}"
    del_mes_1 = await callback.message.answer(text=msg_text, reply_markup=questions_dict[key_1][1])
    await state.update_data(msg_text=msg_text)
    await delete_redis_mes(callback, redis, f"del_tech_{str(callback.from_user.id)}")
    await redis.lpush(f"del_tech_{str(callback.from_user.id)}", *[del_mes_1.message_id])
    await state.update_data(q_num=data["q_num"] + 1)


@router_cal.callback_query(F.data.startswith("rating"), StateFilter(MedExam.questions), flags={"throttle": "check"})
async def question_rating(callback: types.CallbackQuery, state: FSMContext, redis: Redis):
    score = callback.data.split("_")[-1]
    data, msg_text, key, key_word = await write_answer_to_dict(callback, state, "r", score)
    if await finish_questionnaire(callback, state, data, key, key_word, redis, msg_text):
        return
    key_1 = questions_list[data["q_num"]+1]
    try:
        await edit_questionnaire(callback, state, data, key_word, key_1, msg_text)
    except TelegramBadRequest as e:
        await message_is_too_long(callback, state, data, answers_dict, key_word, questions_dict, key_1, e, redis)


@router_cal.callback_query(F.data == "no_button_q", StateFilter(MedExam.digit_answer), flags={"throttle": "check"})
async def question_no_sex(callback: types.CallbackQuery, state: FSMContext, redis: Redis):
    await callback.bot.delete_message(chat_id=callback.from_user.id, message_id=callback.message.message_id)
    data, msg_text, key, key_word = await write_answer_to_dict(callback, state, "b")
    data, key_1 = await skip_multiple_cond_q(state, data, questions_list)
    await transition_to_state_questions(callback, state, data, key_word, key_1, key, redis)


"""********************************************** ЗАКАЗ СПРАВОК ***********************************************"""


@router_cal.callback_query(F.data == "cert_start", StateFilter(Certificates.choice))
async def certificates_start(callback: types.CallbackQuery, state: FSMContext, redis: Redis):
    await callback.answer()
    await call_agreement(callback, redis)
    await state.set_state(Certificates.agreement)
    first = callback.message.text.find('"')
    certificate_type = callback.message.text[first + 1:callback.message.text.find('"', first + 1)]
    param_to_text_keyboard = {
        "Справка о неконтакте": "contact_name",
        "Справка о прохождении диспансеризации": "exam_name",
        "Справка для получения путевки на санаторно-курортное лечение": "c70_name",
    }
    await state.update_data(cert_type=certificate_type)
    await redis.set(f"type_cert_{str(callback.from_user.id)}", param_to_text_keyboard[certificate_type])


@router_cal.callback_query(F.data == "agree", StateFilter(Certificates.agreement))
async def certificates_agree(callback: types.CallbackQuery, state: FSMContext, redis: Redis):
    cert_type = await redis.get(f"type_cert_{str(callback.from_user.id)}")
    await agree_data(callback, "Укажите Ваши Фамилию Имя Отчество (при наличии):",
                     cancel_kb("certification", "Фамилия Имя Отчество"), state,
                     getattr(Certificates, cert_type.decode()), redis)
    await redis.delete(cert_type)


@router_cal.callback_query(F.data == "q_yes", StateFilter(Certificates.contact_test), flags={"throttle": "check"})
async def contact_test_yes(callback: types.CallbackQuery, state: FSMContext, redis: Redis):
    await callback.message.edit_text(text=f"{callback.message.text} "
                                          f"({await get_button_text_from_keyboard(callback, questions_ikb())}",
                                     reply_markup=None)
    await callback.message.answer(text="❌ *К сожалению, мы не можем выдать Вам справку в таком случае*.\n\nДля "
                                       "получения справки необходимо записаться на приём к терапевту в Вашей клинике.",
                                  reply_markup=menu_kb())
    await callback.message.answer(text="✍️ Для записи к врачу скачайте приложение 2dr по одной из ссылок ниже "
                                       "или воспользуйтесь [сайтом](https://74.2dr.ru/)",
                                  reply_markup=app_links_ikb(),
                                  disable_web_page_preview=True)
    await delete_redis_mes(callback, redis, f"del_mes_{str(callback.from_user.id)}")
    await delete_redis_mes(callback, redis, f"del_tech_{str(callback.from_user.id)}")
    await state.clear()


@router_cal.callback_query(F.data == "q_no", StateFilter(Certificates.contact_test), flags={"throttle": "check"})
async def contact_test_no(callback: types.CallbackQuery, state: FSMContext, redis: Redis):
    await callback.message.edit_text(text=f"{callback.message.text} "
                                          f"({await get_button_text_from_keyboard(callback, questions_ikb())})",
                                     reply_markup=None)
    questions = {
        "Выезжали ли Вы за пределы РФ": "Был ли у Вас контакт с лицами, выезжавшими за пределы РФ, в г. Москва, в г. "
                                        "Санкт-Петербург в течение последних 14 дней?",
        "Был ли у Вас контакт с лицами": "Находитесь ли вы на карантине в данный момент?",
    }
    for key, question in questions.items():
        if callback.message.text.startswith(key):
            del_mes_1 = await callback.message.answer(text=question, reply_markup=questions_ikb())
            await redis.lpush(f"del_mes_{str(callback.from_user.id)}", *[del_mes_1.message_id])
            return
    del_mes_2 = await callback.message.answer(
        text="🏠 Введите адрес проживания, чтобы узнать клинику, к которой Вы прикреплены: \n\n"
             "ℹ️ Пример адреса: `Салавата Юлаева 23А` \n\n"
             "🛣 Если вы живёте в *Сосновском районе*, вводите адрес в формате: *«посёлок, микрорайон, улица»* "
             "(без номера дома)\nЕсли вы из посёлков *«Шершни», «Тарасовка» или «Карпов Пруд»*, вводите в формате: "
             "*«посёлок, улица»* (без номера дома)\n\n❗️*Важно: бот чувствителен к формату!* Не ставьте запятую "
             "между улицей и номером дома, а литеру здания пишите сразу после номера, без пробела.",
        reply_markup=cancel_kb("certification", "Адрес дома"))
    await redis.lpush(f"del_mes_{str(callback.from_user.id)}", *[del_mes_2.message_id])
    await delete_redis_mes(callback, redis, f"del_tech_{str(callback.from_user.id)}")
    await state.set_state(Certificates.contact_address)


@router_cal.callback_query(StateFilter(Certificates.c70_gender), flags={"throttle": "check"})
async def c70_gender(callback: types.CallbackQuery, state: FSMContext, redis: Redis):
    await state.update_data(**({"mg": "\u2713"} if callback.data == "man" else {"wg": "\u2713"}))
    del_mes_1 = await callback.message.answer(text="Введите Вашу дату рождения в формате 'дд.мм.гггг':",
                                              reply_markup=cancel_kb("certification", "дд.мм.гггг"))
    await callback.message.edit_text(text="Ваш пол: " + await get_button_text_from_keyboard(callback, gender_ikb()),
                                     reply_markup=None)
    await redis.lpush(f"del_mes_{str(callback.from_user.id)}", *[del_mes_1.message_id])
    await delete_redis_mes(callback, redis, f"del_tech_{str(callback.from_user.id)}")
    await state.set_state(Certificates.c70_birth)


@router_cal.callback_query(StateFilter(Certificates.c70_disable), flags={"throttle": "check"})
async def c70_disable_yes(callback: types.CallbackQuery, state: FSMContext, redis: Redis):
    await callback.message.edit_text(text=f"{callback.message.text} "
                                          f"({await get_button_text_from_keyboard(callback, questions_ikb())})",
                                     reply_markup=None)
    if callback.data == "q_yes":
        del_mes_1 = await callback.message.answer(text="К какой группе инвалидности Вы относитесь?",
                                                  reply_markup=disable_group_ikb())
        await redis.lpush(f"del_mes_{str(callback.from_user.id)}", *[del_mes_1.message_id])
        await state.set_state(Certificates.c70_dis_group)
    else:
        await mse_text_message(callback, state, redis)
    await delete_redis_mes(callback, redis, f"del_tech_{str(callback.from_user.id)}")


@router_cal.callback_query(StateFilter(Certificates.c70_dis_group), flags={"throttle": "check"})
async def c70_disable_group(callback: types.CallbackQuery, state: FSMContext, redis: Redis):
    await callback.message.edit_text(text=f"Ваша группа инвалидности: "
                                          f"{await get_button_text_from_keyboard(callback, disable_group_ikb())}",
                                     reply_markup=None)
    disable_group_id = callback.data[-1]
    await state.update_data(c1="0", c2="0", c3=disable_group_id)
    if disable_group_id == "1":
        del_mes_1 = await callback.message.answer(text="Необходимо ли Вам сопровождение?", reply_markup=questions_ikb())
        await redis.lpush(f"del_mes_{str(callback.from_user.id)}", *[del_mes_1.message_id])
        await state.set_state(Certificates.c70_accompany)
    else:
        await mse_text_message(callback, state, redis)
    await delete_redis_mes(callback, redis, f"del_tech_{str(callback.from_user.id)}")


@router_cal.callback_query(StateFilter(Certificates.c70_accompany), flags={"throttle": "check"})
async def c70_accompany(callback: types.CallbackQuery, state: FSMContext, redis: Redis):
    await callback.message.edit_text(text=f"{callback.message.text} "
                                          f"({await get_button_text_from_keyboard(callback, questions_ikb())})",
                                     reply_markup=None)
    await state.update_data(ac="\u2713" if callback.data == "q_yes" else "\u2013")
    await mse_text_message(callback, state, redis)
    await delete_redis_mes(callback, redis, f"del_tech_{str(callback.from_user.id)}")


"""******************************************* ВАЛИДАЦИЯ ДАННЫХ Ч2 ********************************************"""


@router_cal.callback_query(or_f(F.data == "clinic", F.data == "med_exam", F.data == "cert_start"), ~StateFilter(None))
async def start_func_in_state(callback: types.CallbackQuery):
    func = {"clinic": "узнать адрес прикрепления", "med_exam": "начать анкетирование",
            "cert_start": "перейти к заполнению справки"}
    await callback.answer(text="ℹ️ Завершите текущую функцию, выйдя в главное меню, чтобы " + func[callback.data],
                          show_alert=True)


@router_cal.callback_query(or_f(F.data.contains("topic"), F.data == "no_doc"))
async def topic_not_in_state(callback: types.CallbackQuery):
    await callback.message.edit_reply_markup(reply_markup=None)
    if F.data.contains("topic") or F.data == "no_doc":
        await callback.answer(text="❌ Вы уже отменили процесс создания/изменения обращения либо бот был перезапущен. \n"
                                   "ℹ️ Вы можете начать процесс заново, выбрав соответствующий пункт в главном меню",
                              show_alert=True)


@router_cal.callback_query(or_f(F.data == "send", F.data == "change", F.data == "cancel_send",
                                F.data.contains("edit")), ~StateFilter(Complaint.final))
async def still_not_send_complaint(callback: types.CallbackQuery):
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.answer(text="❌ Вы уже отменили отправку данного обращения либо бот был перезапущен. \n"
                               "ℹ️ Вы можете создать обращение заново, выбрав соответствующий пункт в главном меню",
                          show_alert=True)


@router_cal.callback_query(or_f(F.data == "frequency_ов)_0", F.data == "frequency_)_1", F.data == "frequency_а)_2",
                                F.data == "frequency_а)_3", F.data == "frequency_а)_4", F.data == "level_1",
                                F.data == "level_2", F.data == "level_3", F.data == "rating_1", F.data == "rating_2",
                                F.data == "rating_3", F.data == "no_button_q"))
async def med_exam_not_in_state(callback: types.CallbackQuery):
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.answer(text="❌ Вы уже отменили заполнение анкеты для диспансеризации либо бот был перезапущен. \n"
                               "ℹ️ Вы можете начать процесс заново, выбрав соответствующий пункт в главном меню",
                          show_alert=True)


@router_cal.callback_query(or_f(F.data == "dg_1", F.data == "dg_2", F.data == "dg_3"))
async def certificates_not_in_state(callback: types.CallbackQuery):
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.answer(text="❌ Вы уже отменили заполнение справки либо бот был перезапущен. \n"
                               "ℹ️ Вы можете начать процесс заново, выбрав соответствующий пункт в главном меню",
                          show_alert=True)


@router_cal.callback_query(or_f(F.data == "agree", F.data == "disagree", F.data == "q_yes", F.data == "q_no",
                                F.data == "man", F.data == "woman",))
async def others_not_in_state(callback: types.CallbackQuery):
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.answer(text="❌ Вы уже отменили данную функцию либо бот был перезапущен. \n"
                               "ℹ️ Вы можете начать процесс заново, выбрав соответствующий пункт в главном меню",
                          show_alert=True)
