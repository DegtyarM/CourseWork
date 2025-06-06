from aiogram import types, Router
from aiogram.filters import StateFilter, Command
from aiogram.fsm.context import FSMContext

from keyboards import *

import os
from pathlib import Path
from redis.asyncio import Redis


router_com = Router()


@router_com.message(Command("start"), StateFilter(None))
async def start_command(message: types.Message):
    await message.answer(text="👋 *Привет! Я - бот-помощник пациента Полимедики*. \n\n🤖 Я работаю *24 часа без "
                              "выходных* и могу помочь с: \n"
                              "✔ *Записью к участковому терапевту* - подскажу Вашу клинику прикрепления и "
                              "как записаться на приём;\n"
                              "✔ *Диспансеризацией* - помогу оставить заявку и заполнить документы заранее;\n"
                              "✔ *Справками онлайн* - заполните данные, и заберите готовую справку "
                              "в клиники прикрепления;\n"
                              "✔ *Обратной связью* - приму обращение по качеству обслуживания\n\n"
                              "👇 *Выберите интересующий раздел из меню*",
                         reply_markup=menu_kb())
    await message.delete()


@router_com.message(Command("reboot"), StateFilter("*"))
async def reboot_command(message: types.Message, state: FSMContext, redis: Redis):
    from .callback import answers_dict, questions_dict, questions_list, digit_answer, conditional_answer
    await redis.delete(f"del_mes_{str(message.from_user.id)}")
    await redis.delete(f"del_tech_{str(message.from_user.id)}")
    data = await state.get_data()
    if "one_completed_questionnaire" in data:
        os.remove(Path("data") / f"{data['one_completed_questionnaire']}.pdf")
    await state.clear()
    await message.answer(text="🔄 *Бот перезапущен - теперь всё работает корректно!\n\n"
                              "👇 Выбери нужный раздел в меню и продолжай*",
                         reply_markup=menu_kb())
    for struct in [answers_dict, questions_dict, questions_list, digit_answer, conditional_answer]:
        struct.clear()
    await message.delete()


@router_com.message(Command("author"), StateFilter(None))
async def author_command(message: types.Message):
    await message.answer(text="🤯 Ого, ты оказался достаточно находчивым, чтобы найти эту команду! Тебе явно понравился"
                              " бот, что меня не может не радовать! Раз ты тут, то расскажу о себе:"
                              "\n\nДанный бот был создан студентом ЮУрГУ - *Дегтярь Матвеем* 🎓\n\n"
                              "📚 Факультет: Высшая школа электроники и компьютерных наук\n"
                              "💻 Направление: Фундаментальная информатика и информационные технологии\n"
                              "📆 Год обучения: 3 курс (2025 год)\n\n"
                              "📬 [Связаться с автором](tg://user?id=1245744572)\n\n"
                              "✨ Спасибо, что пользуешься ботом!")
