from aiogram import Router
from aiogram.types import CallbackQuery, Message, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from datetime import datetime
from typing import Union
from app.models import User, Meeting, Reminder,  MeetingNote, MeetingInvitation
from app.database import SessionLocal
import app.keyboards as kb
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
import logging

# Инициализация логгера
logger = logging.getLogger(__name__)

meeting_router = Router()

class MeetingStates(StatesGroup):
    title = State()
    description = State()
    scheduled_at = State()

class DeleteMeetingStates(StatesGroup):
    choose_meeting = State()

@meeting_router.callback_query(lambda c: c.data == "meeting_management")
async def meeting_management(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Выберите действие для управления совещаниями:", reply_markup=kb.next_admin_keyboard())

@meeting_router.message(lambda message: message.text == "Создать совещание")
async def create_meeting(message: Message, state: FSMContext):
    session = SessionLocal()
    telegram_id = message.from_user.id

    try:
        user = session.query(User).filter(User.telegram_id == telegram_id).first()
        if user and user.role == 'admin':
            await message.answer("Введите название совещания:")
            await state.set_state(MeetingStates.title)
        else:
            await message.answer("У вас нет прав для создания совещаний.")
    except IntegrityError as e:
        logger.error(f"IntegrityError: {str(e)}")
        await message.answer("Произошла ошибка целостности данных. Попробуйте позже.")
    except SQLAlchemyError as e:
        logger.error(f"SQLAlchemyError: {str(e)}")
        await message.answer("Произошла ошибка базы данных. Попробуйте позже.")
    except Exception as e:
        await message.answer(f"Ошибка при проверке пользователя: {str(e)}")
    finally:
        session.close()

@meeting_router.message(MeetingStates.title)
async def process_meeting_title(message: Message, state: FSMContext):
    await state.update_data(meeting_title=message.text)
    await message.answer("Введите описание совещания:")
    await state.set_state(MeetingStates.description)

@meeting_router.message(MeetingStates.description)
async def process_meeting_description(message: Message, state: FSMContext):
    await state.update_data(meeting_description=message.text)
    await message.answer("Введите дату и время проведения совещания (в формате ГГГГ-ММ-ДД ЧЧ:ММ):")
    await state.set_state(MeetingStates.scheduled_at)

@meeting_router.message(MeetingStates.scheduled_at)
async def process_meeting_scheduled_at(message: Message, state: FSMContext):
    scheduled_at_str = message.text
    data = await state.get_data()
    meeting_title = data['meeting_title']
    meeting_description = data['meeting_description']
    telegram_id = message.from_user.id
    created_by = datetime.now()

    session = SessionLocal()
    try:
        user = session.query(User).filter(User.telegram_id == telegram_id).first()
        if not user:
            await message.answer("Пользователь не найден.")
            return

        try:
            scheduled_at = datetime.strptime(scheduled_at_str, "%Y-%m-%d %H:%M")
        except ValueError as ve:
            await message.answer("Некорректный формат даты. Пожалуйста, используйте формат ГГГГ-ММ-ДД ЧЧ:ММ.")
            return

        new_meeting = Meeting(
            title=meeting_title,
            description=meeting_description,
            created_by=created_by,
            scheduled_at=scheduled_at,
            creator_id=user.id
        )
        session.add(new_meeting)
        session.commit()

        user.is_meeting_creator = 1
        session.commit()

        await message.answer("Совещание успешно создано.")
        await state.clear()
    except IntegrityError as e:
        logger.error(f"IntegrityError: {str(e)}")
        await message.answer("Произошла ошибка целостности данных. Попробуйте позже.")
    except SQLAlchemyError as e:
        logger.error(f"SQLAlchemyError: {str(e)}")
        await message.answer("Произошла ошибка базы данных. Попробуйте позже.")
    except Exception as e:
        session.rollback()
        await message.answer(f"Ошибка при создании совещания: {str(e)}")
    finally:
        session.close()

@meeting_router.message(lambda message: message.text == "Удалить совещание")
async def delete_meeting(message: Message, state: FSMContext):
    session = SessionLocal()
    telegram_id = message.from_user.id

    try:
        user = session.query(User).filter(User.telegram_id == telegram_id).first()
        if user and user.role == 'admin':
            meetings = session.query(Meeting).filter(Meeting.creator_id == user.id).all()
            if meetings:
                inline_kb = InlineKeyboardMarkup(inline_keyboard=[])
                for meeting in meetings:
                    button = InlineKeyboardButton(text=meeting.title, callback_data=f"delete_meeting_{meeting.id}")
                    inline_kb.inline_keyboard.append([button])
                await message.answer("Выберите совещание, которое хотите удалить:", reply_markup=inline_kb)
                await state.set_state(DeleteMeetingStates.choose_meeting)
            else:
                await message.answer("У вас нет созданных совещаний.")
        else:
            await message.answer("У вас нет прав для удаления совещаний.")
    finally:
        session.close()

@meeting_router.callback_query(lambda c: c.data.startswith("delete_meeting_"))
async def process_delete_meeting(callback: CallbackQuery, state: FSMContext):
    meeting_id = int(callback.data.split("_")[2])

    session = SessionLocal()
    try:
        meeting = session.query(Meeting).filter(Meeting.id == meeting_id).first()
        if meeting:
            session.delete(meeting)
            session.commit()
            await callback.message.answer("Совещание успешно удалено.")
        else:
            await callback.message.answer("Совещание не найдено.")
    except IntegrityError as e:
        logger.error(f"IntegrityError: {str(e)}")
        await callback.message.answer("Произошла ошибка целостности данных. Попробуйте позже.")
    except SQLAlchemyError as e:
        logger.error(f"SQLAlchemyError: {str(e)}")
        await callback.message.answer("Произошла ошибка базы данных. Попробуйте позже.")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        await callback.message.answer(f"Ошибка при удалении совещания: {str(e)}")
    finally:
        await state.clear()
        session.close()

@meeting_router.callback_query(lambda c: c.data == "list_meeting")
@meeting_router.message(lambda message: message.text == "Просмотреть совещания")
async def list_meetings(event: Union[Message, CallbackQuery]):
    session = SessionLocal()
    try:
        now = datetime.now()
        user_id = event.from_user.id if isinstance(event, Message) else event.message.chat.id
        
        # Найти пользователя по Telegram ID
        user = session.query(User).filter(User.telegram_id == user_id).first()
        if not user:
            response = "Пользователь не найден."
            if isinstance(event, Message):
                await event.answer(response)
            else:
                await event.message.answer(response)
            return

        if user.role == "admin":
            meetings = session.query(Meeting).order_by(Meeting.scheduled_at).all()
        else:
            # Получить все совещания, на которые пользователь был приглашен и принял приглашение
            meetings = session.query(Meeting).join(MeetingInvitation).filter(
                MeetingInvitation.user_id == user.id,
                MeetingInvitation.accepted == "accepted"
            ).order_by(Meeting.scheduled_at).all()

        if meetings:
            response = "Список совещаний:\n"
            for meeting in meetings:
                #if meeting.scheduled_at < now:
                    # Удаление прошедших совещаний и связанных данных
                    #session.query(MeetingNote).filter(MeetingNote.meeting_id == meeting.id).delete()
                    #session.query(Reminder).filter(Reminder.meeting_id == meeting.id).delete()
                    #session.query(MeetingInvitation).filter(MeetingInvitation.meeting_id == meeting.id).delete()
                    #session.delete(meeting)
                    #session.commit()
                    #continue

                scheduled_at = meeting.scheduled_at.strftime("%Y-%m-%d %H:%M")
                response += f"Название: {meeting.title}\nОписание: {meeting.description}\nДата и время: {scheduled_at}\n"

                notes = session.query(MeetingNote).filter(MeetingNote.meeting_id == meeting.id).all()
                if notes:
                    response += "Заметки:\n"
                    for note in notes:
                        response += f"- {note.note}\n"
                
                reminders = session.query(Reminder).filter(Reminder.meeting_id == meeting.id).all()
                if reminders:
                    response += "Напоминания:\n"
                    for reminder in reminders:
                        reminder_time = reminder.reminder_time.strftime("%Y-%m-%d %H:%M")
                        response += f"- {reminder_time}\n"
                
                response += "\n"
        else:
            response = "Совещания не найдены."

        if isinstance(event, Message):
            await event.answer(response)
        else:
            await event.message.answer(response)
    except IntegrityError as e:
        logger.error(f"IntegrityError: {str(e)}")
        await event.answer("Произошла ошибка целостности данных. Попробуйте позже.")
    except SQLAlchemyError as e:
        logger.error(f"SQLAlchemyError: {str(e)}")
        await event.answer("Произошла ошибка базы данных. Попробуйте позже.")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        await event.answer(f"Ошибка при получении списка совещаний: {str(e)}")
    finally:
        session.close()

@meeting_router.message(lambda message: message.text == "🔙 Назад")
async def go_back(message: Message):
    telegram_id = message.from_user.id
    session = SessionLocal()
    try:
        user = session.query(User).filter(User.telegram_id == telegram_id).first()
        if user and user.role == 'admin':
            await message.answer("Выберите действие:", reply_markup=kb.admin_keyboard())
        else:
            await message.answer("Выберите действие:", reply_markup=kb.guest_keyboard())
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        await message.answer(f"Ошибка при обработке запроса: {str(e)}")
    finally:
        session.close()
