from aiogram import Router, types
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from aiogram.fsm.state import StatesGroup, State
from app.database import SessionLocal
from sqlalchemy.orm import Session
from app.models import User, Meeting, MeetingInvitation
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
import logging

# Инициализация логгера
logger = logging.getLogger(__name__)

invitation_router = Router()

class InviteStates(StatesGroup):
    select_meeting = State()
    select_user = State()

@invitation_router.message(lambda message: message.text == "Пригласить сотрудника на совещание")
async def invite_user_callback(message: Message):
    telegram_id = message.from_user.id
    session: Session = SessionLocal()
    try:
        user = session.query(User).filter(User.telegram_id == telegram_id).first()
        if user and user.is_meeting_creator:
            meetings = session.query(Meeting).filter(Meeting.creator_id == user.id).all()
            if meetings:
                inline_kb = InlineKeyboardMarkup(inline_keyboard=[])
                for meeting in meetings:
                    button = InlineKeyboardButton(text=meeting.title, callback_data=f"select_meeting_{meeting.id}")
                    inline_kb.inline_keyboard.append([button])
                await message.answer("Выберите совещание для приглашения:", reply_markup=inline_kb)
            else:
                await message.answer("Нет доступных совещаний для приглашения.")
        else:
            await message.answer("У вас нет доступа.")
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

@invitation_router.callback_query(lambda c: c.data.startswith("select_meeting_"))
async def select_meeting_for_invitation(callback: CallbackQuery, state: FSMContext):
    meeting_id = int(callback.data.split("_")[2])
    await state.update_data(meeting_id=meeting_id)

    session: Session = SessionLocal()
    try:
        users = session.query(User).filter(User.role != "admin", User.deleted_flag == 0).all()
        if users:
            inline_kb = InlineKeyboardMarkup(inline_keyboard=[])
            for user in users:
                button = InlineKeyboardButton(text=user.first_name, callback_data=f"select_user_{user.id}")
                inline_kb.inline_keyboard.append([button])
            await callback.message.answer("Выберите пользователя для приглашения:", reply_markup=inline_kb)
            await state.set_state(InviteStates.select_user)
        else:
            await callback.message.answer("Нет доступных пользователей для приглашения.")
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

@invitation_router.callback_query(lambda c: c.data.startswith("select_user_"))
async def invite_user(callback: CallbackQuery, state: FSMContext):
    user_id = int(callback.data.split("_")[2])
    data = await state.get_data()
    meeting_id = data.get('meeting_id')

    session = SessionLocal()
    try:
        invitation = MeetingInvitation(
            meeting_id=meeting_id,
            user_id=user_id,
            accepted=None
        )
        session.add(invitation)
        session.commit()

        user = session.query(User).filter(User.id == user_id).first()
        meeting = session.query(Meeting).filter(Meeting.id == meeting_id).first() 
        if user and meeting:
            # Уведомить пользователя и предложить принять или отклонить приглашение
            await callback.bot.send_message(user.telegram_id, f"Вы были приглашены на совещание '{meeting.title}'. Принять приглашение?", reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(text="Принять", callback_data=f"respond_invitation_{invitation.id}_accepted"),
                        InlineKeyboardButton(text="Отклонить", callback_data=f"respond_invitation_{invitation.id}_declined")
                    ]
                ]
            ))
            # Уведомить создателя совещания
            creator = session.query(User).filter(User.id == meeting.creator_id).first()
            if creator:
                await callback.bot.send_message(creator.telegram_id, f"Пользователь {user.first_name} приглашен на совещание '{meeting.title}'.")
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
        await state.clear()

@invitation_router.callback_query(lambda c: c.data.startswith("respond_invitation_"))
async def respond_to_invitation(callback: CallbackQuery):
    invitation_id, response = callback.data.split("_")[2], callback.data.split("_")[3]
    session: Session = SessionLocal()
    try:
        invitation = session.query(MeetingInvitation).filter(MeetingInvitation.id == invitation_id).first()
        if invitation:
            invitation.accepted = response
            session.commit()
            user = session.query(User).filter(User.id == invitation.user_id).first()
            if user:
                if response == "accepted":
                    await callback.bot.send_message(user.telegram_id, f"Ваше приглашение на совещание '{invitation.meeting.title}' было подтверждено.")
                else:
                    await callback.bot.send_message(user.telegram_id, f"Ваше приглашение на совещание '{invitation.meeting.title}' было отклонено.")
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

        