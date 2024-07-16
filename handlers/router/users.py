from aiogram import Router
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart
from app.models import User
from app.database import SessionLocal
import app.keyboards as kb
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
import logging

# Инициализация логгера
logger = logging.getLogger(__name__)

user_router = Router()

@user_router.message(CommandStart())
async def cmd_start(message: Message):
    first_name = message.from_user.first_name
    await message.answer(f"Здравствуйте, {first_name}👋\nРад вас видеть! Я - чат-помощник для планирования совещаний. Давайте начнем!", reply_markup=kb.start_keyboard())

@user_router.callback_query(lambda c: c.data == "start_bot")
async def handle_start_bot(callback: CallbackQuery):
    telegram_id = callback.from_user.id
    username = callback.from_user.username or ''
    first_name = callback.from_user.first_name or ''  

    session = SessionLocal()
    try:
        user = session.query(User).filter(User.telegram_id == telegram_id).first() 
        if user:
            if user.deleted_flag == 1:
                await callback.message.answer("У вас нет доступа.")
            else:
                await callback.message.answer(f"Информация о вас:\nИмя: {first_name}\nUsername: {username}\nTelegram ID: {telegram_id}")
                if user.role == 'admin':
                    await callback.message.answer("Выберите действие:", reply_markup=kb.admin_keyboard())
                else:
                    await callback.message.answer("Выберите действие:", reply_markup=kb.guest_keyboard())
        else:
            new_user = User(
                telegram_id=telegram_id,
                username=username,
                first_name=first_name, 
                role=None,
                deleted_flag=0
            )
            session.add(new_user)
            session.commit()

            await callback.message.answer(f"Информация о вас:\nИмя: {first_name}\nUsername: {username}\nTelegram ID: {telegram_id}\n")
            await callback.message.answer("Уточняю. Вы являетесь начальником или его заместителем?", reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(text="Да", callback_data="role_admin"),
                        InlineKeyboardButton(text="Нет", callback_data="role_guest")
                    ]
                ]
            ))
    except IntegrityError as e:
        logger.error(f"IntegrityError: {str(e)}")
        await callback.message.answer("Произошла ошибка целостности данных. Попробуйте позже.")
    except SQLAlchemyError as e:
        logger.error(f"SQLAlchemyError: {str(e)}")
        await callback.message.answer("Произошла ошибка базы данных. Попробуйте позже.")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        await callback.message.answer("Произошла неизвестная ошибка. Попробуйте позже.")
    finally:
        session.close()

@user_router.callback_query(lambda c: c.data in ["role_admin", "role_guest"])
async def handle_role(callback: CallbackQuery):
    telegram_id = callback.from_user.id
    role = 'admin' if callback.data == 'role_admin' else 'guest'

    session = SessionLocal()
    try:
        user = session.query(User).filter(User.telegram_id == telegram_id).first()
        if user:
            if user.role is None:  # Проверяем, не установлен ли уже ответ на вопрос о роли
                user.role = role
                session.commit()
                if role == 'admin':
                    await callback.message.answer(f"Ваша роль обновлена на начальника")
                    await callback.message.answer("Выберите действие:", reply_markup=kb.admin_keyboard())
                else:
                    await callback.message.answer(f"Ваша роль обновлена на сотрудника")
                    await callback.message.answer("Выберите действие:", reply_markup=kb.guest_keyboard())
                
                # Скрываем клавиатуру после ответа
               # await callback.message.edit_reply_markup(reply_markup=None)
            else:
                await callback.message.answer("Вы уже ответили на вопрос о роли.")
    except IntegrityError as e:
        logger.error(f"IntegrityError: {str(e)}")
        await callback.message.answer("Произошла ошибка целостности данных. Попробуйте позже.")
    except SQLAlchemyError as e:
        logger.error(f"SQLAlchemyError: {str(e)}")
        await callback.message.answer("Произошла ошибка базы данных. Попробуйте позже.")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        await callback.message.answer("Произошла неизвестная ошибка. Попробуйте позже.")
    finally:
        session.close()