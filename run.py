import logging
import os
import asyncio
from datetime import datetime
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher
from aiogram.types import CallbackQuery
from handlers.router.users import user_router
from handlers.router.meeting import meeting_router
from handlers.router.reminders import reminder_router
from handlers.router.note import note_router
from handlers.router.feedback import guest_router, admin_router
from handlers.people.participants import participants_router
from handlers.people.invitation import invitation_router
from handlers.people.restore import restore_router
from handlers.router.unknow import unknow_router

import app.keyboards as kb
from app.database import SessionLocal
from app.models import Reminder, User, Meeting

# Создание папки для логов, если она не существует
log_directory = 'logs'
if not os.path.exists(log_directory):
    os.makedirs(log_directory)

# Настройка обработчиков логов
info_log_file_path = os.path.join(log_directory, 'info.log')
error_log_file_path = os.path.join(log_directory, 'error.log')

# Обработчик для информационных сообщений
info_handler = logging.FileHandler(info_log_file_path)
info_handler.setLevel(logging.INFO)
info_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
info_handler.setFormatter(info_formatter)

# Обработчик для ошибок и критических сообщений
error_handler = logging.FileHandler(error_log_file_path)
error_handler.setLevel(logging.ERROR)
error_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
error_handler.setFormatter(error_formatter)

# Основной обработчик для вывода в консоль
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
console_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(console_formatter)

# Настройка логгера
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
logger.addHandler(info_handler)
logger.addHandler(error_handler)
logger.addHandler(console_handler)

# Загрузка переменных окружения из файла .env
load_dotenv()

# Получение токена из переменных окружения
TOKEN = os.getenv('TOKEN')
if TOKEN is None:
    raise ValueError("TOKEN не найден в переменных окружения")

async def send_reminders(bot: Bot):
    while True:
        now = datetime.now()
        session = SessionLocal()
        try:
            reminders = session.query(Reminder).filter(Reminder.reminder_time <= now).all()
            for reminder in reminders:
                user_id = reminder.user_id
                meeting_id = reminder.meeting_id
                user = session.query(User).filter(User.id == user_id).first()
                meeting = session.query(Meeting).filter(Meeting.id == meeting_id).first()

                if user and meeting:
                    await bot.send_message(user.telegram_id, f"Напоминание:\nСовещание '{meeting.title}' начнется через несколько минут.")
                    session.delete(reminder)
                    session.commit()
        except Exception as e:
            logger.error(f"Ошибка при отправке напоминаний: {str(e)}")
        finally:
            session.close()
        await asyncio.sleep(60)

async def check_user_roles(bot: Bot):
    while True:
        session = SessionLocal()
        try:
            users = session.query(User).filter(User.role_changed == 1).all()  # Фильтруем только тех, у кого role_changed == 1
            for user in users:
                telegram_id = user.telegram_id
                role = user.role
                if role == 'admin':
                    await bot.send_message(telegram_id, "Ваша роль обновлена на начальника", reply_markup=kb.admin_keyboard())
                else:
                    await bot.send_message(telegram_id, "Ваша роль обновлена на сотрудника", reply_markup=kb.guest_keyboard())
                
                # Сбрасываем флаг изменения роли
                user.role_changed = 0
                session.commit()
        except Exception as e:
            logger.error(f"Ошибка при проверке ролей пользователей: {str(e)}")
        finally:
            session.close()
        await asyncio.sleep(15)

async def main():
    bot = Bot(token=TOKEN)
    dp = Dispatcher()

    # Подключение маршрутизаторов
    dp.include_router(user_router)
    dp.include_router(meeting_router)
    dp.include_router(reminder_router)
    dp.include_router(note_router)
    dp.include_router(participants_router)
    dp.include_router(invitation_router)
    dp.include_router(restore_router)
    dp.include_router(guest_router)
    dp.include_router(admin_router)
    dp.include_router(unknow_router)
    
    # Запуск фоновой задачи для отправки напоминаний
    asyncio.create_task(send_reminders(bot))
    # Запуск фоновой задачи для проверки ролей пользователей
    asyncio.create_task(check_user_roles(bot))
    await dp.start_polling(bot)

if __name__ == '__main__':
    #logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    try:
        asyncio.run(main())
    except Exception as e:
        logger.error(f'Бот не работает: {str(e)}')