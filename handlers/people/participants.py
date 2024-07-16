from aiogram import Router, types
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy.orm import Session
from app.database import SessionLocal
import app.keyboards as kb
from app.models import User, Meeting, MeetingInvitation
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
import logging

# Инициализация логгера
logger = logging.getLogger(__name__)


participants_router = Router()

@participants_router.callback_query(lambda c: c.data == "employee_management")
async def handle_employee_management(callback: CallbackQuery):
    await callback.message.answer("Выберите действие:", reply_markup=kb.employee_management_keyboard())


@participants_router.message(lambda message: message.text == "Удалить сотрудника")
async def show_guests(message: Message):
    session: Session = SessionLocal()
    try:
        guests = session.query(User).filter(User.role == "guest", User.deleted_flag == 0).all()
        if not guests:
            await message.answer("Нет сотрудников.")
            return
        
        inline_kb = InlineKeyboardMarkup(inline_keyboard=[])
        for guest in guests:
            button = InlineKeyboardButton(text=f"{guest.first_name}", callback_data=f"delete_guest_{guest.id}")
            inline_kb.inline_keyboard.append([button])
        
        await message.answer("Список сотрудников:", reply_markup=inline_kb)
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

@participants_router.callback_query(lambda c: c.data.startswith("delete_guest"))
async def delete_guest(callback: CallbackQuery):
    user_id = int(callback.data.split("_")[2]) #из данных, которые передаются вместе с нажатием кнопки, извлекается id. 
                                               #Данные делятся по _ и берется третий элемент, который приобразуется в int
    
    session: Session = SessionLocal()
    try:
        user = session.query(User).filter(User.id == user_id, User.role == "guest").first() #first возвращает первый найденный результат
        if user:
            user.deleted_flag = 1
            session.commit()
            await callback.message.answer(f"Пользователь {user.first_name} был помечен как удаленный.")
            
            # Отправка уведомления пользователю и закрытие возможности использовать клавиатуру
            await callback.bot.send_message(user.telegram_id, "Вы были заблокированы.", reply_markup=types.ReplyKeyboardRemove())
        else:
            await callback.message.answer("Пользователь не найден или уже помечен как удаленный.")
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

@participants_router.message(lambda message: message.text == "Посмотреть список сотрудников по совещаниям")
async def view_invited_users(message: Message):
    session: Session = SessionLocal()
    try:
        meetings = session.query(Meeting).all()
        if meetings:
            inline_kb = InlineKeyboardMarkup(inline_keyboard=[])
            for meeting in meetings:
                button = InlineKeyboardButton(text=meeting.title, callback_data=f"view_invited_users_{meeting.id}")
                inline_kb.inline_keyboard.append([button])
            await message.answer("Выберите совещание для просмотра приглашенных сотрудников:", reply_markup=inline_kb)
        else:
            await message.answer("Нет доступных совещаний.")
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


@participants_router.callback_query(lambda c: c.data.startswith("view_invited_users_"))
async def handle_view_invited_users(callback: CallbackQuery):  
    meeting_id_str = callback.data.split("_")[3]
    if not meeting_id_str.isdigit(): #проверка на содержание в строке цифр
        await callback.message.answer("Некорректный идентификатор совещания.")
        return

    meeting_id = int(meeting_id_str)

    session: Session = SessionLocal()
    try:
        invitations = session.query(MeetingInvitation).filter(
            MeetingInvitation.meeting_id == meeting_id,
            MeetingInvitation.accepted == "accepted"  # Фильтр по принятым приглашениям
        ).all()

        if invitations:
            response = "Приглашенные сотрудники на совещание:\n"
            for invitation in invitations:
                user = session.query(User).filter(User.id == invitation.user_id).first()
                if user and user.deleted_flag == 0:
                    response += f"- {user.first_name} (@{user.username})\n"
                else:
                    # Удаляем запись приглашения, если пользователь удален
                    session.delete(invitation)
                    session.commit()
        else:
            response = "На данное совещание никто не принял приглашение."

        await callback.message.answer(response)
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
