from aiogram import Router, types
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.state import StatesGroup, State
from datetime import datetime, timedelta
from app.models import User, Meeting, MeetingInvitation, Reminder
from app.database import SessionLocal
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
import logging

# Инициализация логгера
logger = logging.getLogger(__name__)

reminder_router = Router()

class ReminderStates(StatesGroup):
    meeting_id = State()
    reminder_time = State()

@reminder_router.callback_query(lambda c: c.data == "create_reminder")
@reminder_router.message(lambda message: message.text == "Добавить напоминание")
async def create_reminder_callback(callback_or_message: types.Union[CallbackQuery, Message], state: FSMContext):
    telegram_id = callback_or_message.from_user.id

    session = SessionLocal() #открытие сессии соединения с бд
    try:
        user = session.query(User).filter(User.telegram_id == telegram_id).first()

        if user and user.deleted_flag == 0:
            if user.role == "admin":
                meetings = session.query(Meeting).order_by(Meeting.scheduled_at).all()
            else:    
                now = datetime.now()
                meetings = session.query(Meeting).join(MeetingInvitation).filter(
                    MeetingInvitation.user_id == user.id,
                    MeetingInvitation.accepted == "accepted",
                    Meeting.scheduled_at >= now
                ).order_by(Meeting.scheduled_at).all()

            if meetings:
                inline_kb = InlineKeyboardMarkup(inline_keyboard=[]) #создание кнопок для совещаний
                for meeting in meetings:
                    button = InlineKeyboardButton(text=meeting.title, callback_data=f"select_meeting_reminder_{meeting.id}")
                    inline_kb.inline_keyboard.append([button])

                if isinstance(callback_or_message, CallbackQuery):
                    await callback_or_message.message.answer("Выберите совещание, для которого хотите добавить напоминание:", reply_markup=inline_kb)
                else:
                    await callback_or_message.answer("Выберите совещание, для которого хотите добавить напоминание:", reply_markup=inline_kb)
                    
                await state.set_state(ReminderStates.meeting_id)
            else:
                no_meetings_message = "Нет доступных совещаний для добавления напоминаний."
                if isinstance(callback_or_message, CallbackQuery):
                    await callback_or_message.message.answer(no_meetings_message)
                else:
                    await callback_or_message.answer(no_meetings_message)
        else:
            no_access_message = "У вас нет доступа."
            if isinstance(callback_or_message, CallbackQuery):
                await callback_or_message.message.answer(no_access_message)
            else:
                await callback_or_message.answer(no_access_message)
    except IntegrityError as e: 
        logger.error(f"IntegrityError: {str(e)}") 
        if isinstance(callback_or_message, CallbackQuery):
            await callback_or_message.message.answer("Произошла ошибка целостности данных. Попробуйте позже.") 
        else:
            await callback_or_message.answer("Произошла ошибка целостности данных. Попробуйте позже.") 
    except SQLAlchemyError as e: 
        logger.error(f"SQLAlchemyError: {str(e)}") 
        if isinstance(callback_or_message, CallbackQuery):
            await callback_or_message.message.answer("Произошла ошибка базы данных. Попробуйте позже.") 
        else: 
            await callback_or_message.answer("Произошла ошибка базы данных. Попробуйте позже.") 
    except Exception as e: 
        logger.error(f"Unexpected error: {str(e)}") 
        if isinstance(callback_or_message, CallbackQuery): 
            await callback_or_message.message.answer(f"Произошла ошибка: {str(e)}") 
        else: 
            await callback_or_message.answer(f"Произошла ошибка: {str(e)}") 
    finally: 
        session.close()

@reminder_router.callback_query(lambda c: c.data.startswith("select_meeting_reminder_"))
async def select_meeting_callback(callback: CallbackQuery, state: FSMContext):
    meeting_id_str = callback.data.split("_")[3]
    if not meeting_id_str.isdigit(): #проверка строки на наличие цифр
        await callback.message.answer("Некорректный идентификатор совещания.")
        return
    
    meeting_id = int(meeting_id_str) 

    session = SessionLocal()
    try:
        meeting = session.query(Meeting).filter(Meeting.id == meeting_id).first()
        if meeting:
            await state.update_data(meeting_id=meeting.id)
            await callback.message.answer("Введите количество минут до начала совещания, когда должно прийти напоминание:")
            await state.set_state(ReminderStates.reminder_time)
        else:
            await callback.message.answer("Совещание не найдено. Попробуйте еще раз.")
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

@reminder_router.message(ReminderStates.reminder_time)
async def process_reminder_time(message: Message, state: FSMContext):
    reminder_time_str = message.text
    data = await state.get_data()
    meeting_id = data.get('meeting_id')
    telegram_id = message.from_user.id

    session = SessionLocal()
    try:
        user = session.query(User).filter(User.telegram_id == telegram_id).first()
        meeting = session.query(Meeting).filter(Meeting.id == meeting_id).first()

        if user and meeting:
            try:
                reminder_time = int(reminder_time_str)
            except ValueError:
                await message.answer("Некорректный формат времени. Пожалуйста, введите количество минут до начала совещания.")
                return

            reminder_datetime = meeting.scheduled_at - timedelta(minutes=reminder_time)
            new_reminder = Reminder(
                meeting_id=meeting.id,
                user_id=user.id,
                reminder_time=reminder_datetime
            )
            session.add(new_reminder)
            session.commit()

            await message.answer(f"Напоминание успешно добавлено. Вы получите уведомление за {reminder_time} минут до начала совещания.")
            await state.clear()
        else:
            await message.answer("Совещание или пользователь не найдены.")
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
