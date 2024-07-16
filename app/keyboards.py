from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton

def start_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Начать работу", callback_data="start_bot")]
    ])

def admin_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Управление совещаниями", callback_data="meeting_management")],
        [InlineKeyboardButton(text="Добавить напоминание", callback_data="create_reminder")],
        [InlineKeyboardButton(text="Добавить заметку", callback_data="create_note")],
        [InlineKeyboardButton(text="Управление сотрудниками", callback_data="employee_management")]
    ])

def next_admin_keyboard():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="Создать совещание")],
        [KeyboardButton(text="Удалить совещание")],
        [KeyboardButton(text="Просмотреть совещания")],
        [KeyboardButton(text="🔙 Назад")]
    ], resize_keyboard=True)

def guest_keyboard():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="Просмотреть совещания")],
        [KeyboardButton(text="Добавить напоминание")],
        [KeyboardButton(text="Добавить заметку")],
        [KeyboardButton(text="Задать вопрос")],
    ])

def employee_management_keyboard():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="Удалить сотрудника")],
        [KeyboardButton(text="Восстановить сотрудника")],
        [KeyboardButton(text="Пригласить сотрудника на совещание")],
        [KeyboardButton(text="Посмотреть список сотрудников по совещаниям")],
        [KeyboardButton(text="Ответить на вопросы")],
        [KeyboardButton(text="🔙 Назад")]
    ], resize_keyboard=True)
