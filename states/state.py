from aiogram.fsm.state import StatesGroup, State


class Address(StatesGroup):
    address = State()
    confirm = State()


class Complaint(StatesGroup):
    agreement = State()
    topic = State()
    name = State()
    birth = State()
    number = State()
    complaint = State()
    file = State()
    final = State()


class EditComplaint(StatesGroup):
    edit_topic = State()
    edit_name = State()
    edit_birth = State()
    edit_number = State()
    edit_complaint = State()
    edit_file = State()


class MedExam(StatesGroup):
    agreement = State()
    birth = State()
    number = State()
    name = State()
    gender = State()
    pregnant = State()
    questions = State()
    write_answer = State()
    digit_answer = State()


class Certificates(StatesGroup):
    choice = State()
    agreement = State()

    exam_name = State()
    exam_birth = State()
    exam_address = State()

    contact_name = State()
    contact_birth_year = State()
    contact_test = State()
    contact_address = State()

    c70_name = State()
    c70_gender = State()
    c70_birth = State()
    c70_pass_address = State()
    c70_polis = State()
    c70_disable = State()
    c70_dis_group = State()
    c70_accompany = State()
    c70_mse = State()
    c70_snils = State()
    c70_preferred_place = State()
    c70_address = State()
