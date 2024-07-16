from aiogram import Router, types
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import User
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
import logging

# Инициализация логгера
logger = logging.getLogger(__name__)


restore_router = Router()

@restore_router.message(lambda message: message.text == "Восстановить сотрудника")
async def show_deleted_guests(message: Message):
    session: Session = SessionLocal()
    try:
        deleted_guests = session.query(User).filter(User.role == "guest", User.deleted_flag == 1).all()
        if not deleted_guests:
            await message.answer("Нет удаленных пользователей.")
            return
        
        inline_kb = InlineKeyboardMarkup(inline_keyboard=[])
        for guest in deleted_guests:
            button = InlineKeyboardButton(text=f"{guest.first_name}", callback_data=f"restore_guest_{guest.id}")
            inline_kb.inline_keyboard.append([button])
        
        await message.answer("Список удаленных пользователей:", reply_markup=inline_kb)
    except IntegrityError as e: 
        logger.error(f"IntegrityError: {str(e)}") 
        await message.answer("Произошла ошибка целостности данных. Попробуйте позже.") 
    except SQLAlchemyError as e: 
        logger.error(f"SQLAlchemyError: {str(e)}") 
        await message.answer("Произошла ошибка базы данных. Попробуйте позже.") 
    except Exception as e: 
        logger.error(f"Unexpected error: {str(e)}") 
        await message.answer(f"Произошла ошибка: {str(e)}") 
    finally: 
        session.close()

@restore_router.callback_query(lambda c: c.data.startswith("restore_guest_"))
async def restore_guest(callback: CallbackQuery):
    user_id = int(callback.data.split("_")[2])
    
    session: Session = SessionLocal()
    try:
        user = session.query(User).filter(User.id == user_id, User.role == "guest", User.deleted_flag == 1).first()
        if user:
            user.deleted_flag = 0
            session.commit()
            await callback.message.answer(f"Пользователь {user.first_name} был восстановлен.")

            await callback.bot.send_message(user.telegram_id, "Вы были восстановлены.")
        else:
            await callback.message.answer("Пользователь не найден или уже восстановлен.")
    except IntegrityError as e: 
        logger.error(f"IntegrityError: {str(e)}") 
        await callback.message.answer("Произошла ошибка целостности данных. Попробуйте позже.") 
    except SQLAlchemyError as e: 
        logger.error(f"SQLAlchemyError: {str(e)}") 
        await callback.message.answer("Произошла ошибка базы данных. Попробуйте позже.") 
    except Exception as e: 
        logger.error(f"Unexpected error: {str(e)}") 
        await callback.message.answer(f"Произошла ошибка: {str(e)}") 
    finally: 
        session.close()