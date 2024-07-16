from aiogram import Router, types
from aiogram.types import CallbackQuery, Message, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from app.models import Feedback, User, Meeting, MeetingInvitation, MeetingNote, Reminder
from app.database import SessionLocal
from datetime import datetime
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
import logging

# Инициализация логгера
logger = logging.getLogger(__name__)

note_router = Router()

class NoteStates(StatesGroup):
    meeting_title = State()
    note = State()

@note_router.callback_query(lambda c: c.data == "create_note")
@note_router.message(lambda message: message.text == "Добавить заметку")
async def create_note_callback(callback_or_message: types.Union[CallbackQuery, Message], state: FSMContext):
    telegram_id = callback_or_message.from_user.id

    session = SessionLocal()
    try:
        user = session.query(User).filter(User.telegram_id == telegram_id).first()

        if user and user.deleted_flag == 0:
            if user.role == "admin":
                meetings = session.query(Meeting).order_by(Meeting.scheduled_at).all()
            else:    
                now = datetime.now()
                # Получить все совещания, на которые пользователь был приглашен и принял приглашение
                meetings = session.query(Meeting).join(MeetingInvitation).filter(
                    MeetingInvitation.user_id == user.id,
                    MeetingInvitation.accepted == "accepted",
                    Meeting.scheduled_at >= now
                ).order_by(Meeting.scheduled_at).all()

            if meetings:
                inline_kb = InlineKeyboardMarkup(inline_keyboard=[])
                for meeting in meetings:
                    button = InlineKeyboardButton(text=meeting.title, callback_data=f"select_meeting_note_{meeting.id}")
                    inline_kb.inline_keyboard.append([button])

                if isinstance(callback_or_message, CallbackQuery):
                    await callback_or_message.message.answer("Выберите совещание, для которого хотите добавить заметку:", reply_markup=inline_kb)
                else:
                    await callback_or_message.answer("Выберите совещание, для которого хотите добавить заметку:", reply_markup=inline_kb)
                    
                await state.set_state(NoteStates.meeting_title)
            else:
                if isinstance(callback_or_message, CallbackQuery):
                    await callback_or_message.message.answer("Нет доступных совещаний для добавления заметок.")
                else:
                    await callback_or_message.answer("Нет доступных совещаний для добавления заметок.")
        else:
            if isinstance(callback_or_message, CallbackQuery):
                await callback_or_message.message.answer("У вас нет доступа.")
            else:
                await callback_or_message.answer("У вас нет доступа.")
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

@note_router.callback_query(lambda c: c.data.startswith("select_meeting_note_"))
async def select_meeting_callback(callback: CallbackQuery, state: FSMContext):
    meeting_id_str = callback.data.split("_")[3]
    if not meeting_id_str.isdigit():
        await callback.message.answer("Некорректный идентификатор совещания.")
        return

    meeting_id = int(meeting_id_str)

    session = SessionLocal()
    try:
        meeting = session.query(Meeting).filter(Meeting.id == meeting_id).first()
        if meeting:
            await state.update_data(meeting_title=meeting.title)
            await callback.message.answer("Введите текст заметки:")
            await state.set_state(NoteStates.note)
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

@note_router.message(NoteStates.note)
async def process_note_text(message: Message, state: FSMContext):
    note_text = message.text.strip()
    if not note_text:
        await message.answer("Текст заметки не может быть пустым. Попробуйте еще раз.")
        return
    
    data = await state.get_data()
    meeting_title = data.get('meeting_title')
    telegram_id = message.from_user.id

    session = SessionLocal()
    try:
        user = session.query(User).filter(User.telegram_id == telegram_id).first()
        if user and user.deleted_flag == 0:
            meeting = session.query(Meeting).filter(Meeting.title == meeting_title).first()
            if meeting:
                new_note = MeetingNote(
                    meeting_id=meeting.id,
                    user_id=user.id,
                    note=note_text
                )
                session.add(new_note)
                session.commit()

                await message.answer("Заметка успешно добавлена.")
                await state.clear()
            else:
                await message.answer("Совещание не найдено.")
        else:
            await message.answer("Вы не авторизованы или удалены.")
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

# Автоматическое удаление всего, что связано с совещанием
def remove_past_meetings_and_notes():
    session = SessionLocal()
    try:
        now = datetime.now()
        meetings = session.query(Meeting).filter(Meeting.scheduled_at < now).all()
        for meeting in meetings:
            session.query(MeetingNote).filter(MeetingNote.meeting_id == meeting.id).delete()
            session.query(Reminder).filter(Reminder.meeting_id == meeting.id).delete()
            session.query(MeetingInvitation).filter(MeetingInvitation.meeting_id == meeting.id).delete()
            session.delete(meeting)
        session.commit()
    except IntegrityError as e: 
        logger.error(f"IntegrityError: {str(e)}") 
    except SQLAlchemyError as e: 
        logger.error(f"SQLAlchemyError: {str(e)}") 
    except Exception as e: 
        logger.error(f"Unexpected error: {str(e)}") 
    finally: 
        session.close()

remove_past_meetings_and_notes()