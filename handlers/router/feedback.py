from aiogram import Router
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import Feedback, User
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
import logging

# Инициализация логгера
logger = logging.getLogger(__name__)

guest_router = Router()
admin_router = Router()

class FeedbackStates(StatesGroup):
    waiting_for_feedback = State()

class AdminFeedbackStates(StatesGroup):
    waiting_for_response = State()

@guest_router.message(lambda message: message.text == "Задать вопрос")
async def request_feedback(message: Message, state: FSMContext):
    await message.answer("🟢 Напишите свой вопрос: ")
    await state.set_state(FeedbackStates.waiting_for_feedback)

@guest_router.message(FeedbackStates.waiting_for_feedback)
async def receive_feedback(message: Message, state: FSMContext):
    session: Session = SessionLocal()
    try:
        user = session.query(User).filter(User.telegram_id == message.from_user.id).first()
        if user:
            feedback = Feedback(user_id=user.id, message=message.text)
            if message.text is None:
                await message.bot.send_message(message.from_user.id, 'Сообщение должно быть в текстовом формате! Попробуйте снова.')
                return None
            session.add(feedback)
            session.commit()
            await message.answer("🟢 Спасибо за вопрос!\nВам ответят в ближайшее время.")
            
            # Уведомление администратора о новом вопросе
            admins = session.query(User).filter(User.role == "admin").all()
            for admin in admins:
                inline_kb = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="Ответить", callback_data=f"respond_feedback_{feedback.id}")]
                ])
                await message.bot.send_message(admin.telegram_id, f"🟢 Новый вопрос от {user.first_name}: {message.text}", reply_markup=inline_kb)
        else:
            await message.answer("❌ Произошла ошибка. Попробуйте позже.")
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
    await state.clear()

@admin_router.message(lambda message: message.text == "Ответить на вопросы")
async def show_feedback_list(message: Message):
    session: Session = SessionLocal()
    try:
        feedbacks = session.query(Feedback).filter(Feedback.answered == 0).all() 
        if not feedbacks:
            await message.answer("❌ Нет вопросов для ответа.")
            return

        inline_kb = InlineKeyboardMarkup(inline_keyboard=[])
        for feedback in feedbacks:
            user = session.query(User).filter(User.id == feedback.user_id).first()
            button_text = f"{user.first_name}: {feedback.message[:20]}..."
            button = InlineKeyboardButton(text=button_text, callback_data=f"respond_feedback_{feedback.id}")
            inline_kb.inline_keyboard.append([button])

        await message.answer("Выберите вопрос для ответа:", reply_markup=inline_kb)
    except SQLAlchemyError as e: 
        logger.error(f"SQLAlchemyError: {str(e)}") 
        await message.answer("Произошла ошибка базы данных. Попробуйте позже.") 
    except Exception as e: 
        logger.error(f"Unexpected error: {str(e)}") 
        await message.answer(f"Произошла ошибка: {str(e)}") 
    finally:
        session.close()

# Функция для проверки, был ли уже ответ на вопрос
async def check_if_answered(session: Session, feedback_id: int) -> bool:
    feedback = session.query(Feedback).filter(Feedback.id == feedback_id).first()
    return feedback.answered

@admin_router.callback_query(lambda c: c.data.startswith("respond_feedback_"))
async def ask_for_response(callback: CallbackQuery, state: FSMContext):
    feedback_id = int(callback.data.split("_")[2])

    session: Session = SessionLocal()
    try:
        if await check_if_answered(session, feedback_id):
            await callback.message.answer("Вы уже ответили на этот вопрос.")
        else:
            await state.update_data(feedback_id=feedback_id)
            await callback.message.answer("🟢 Напишите ваш ответ на выбранный вопрос.")
            await state.set_state(AdminFeedbackStates.waiting_for_response)
    except SQLAlchemyError as e: 
        logger.error(f"SQLAlchemyError: {str(e)}") 
        await callback.message.answer("Произошла ошибка базы данных. Попробуйте позже.") 
    except Exception as e: 
        logger.error(f"Unexpected error: {str(e)}") 
        await callback.message.answer(f"Произошла ошибка: {str(e)}") 
    finally:
        session.close()

@admin_router.message(AdminFeedbackStates.waiting_for_response)
async def send_response(message: Message, state: FSMContext):
    session: Session = SessionLocal()
    data = await state.get_data()
    feedback_id = data.get('feedback_id')

    try:
        feedback = session.query(Feedback).filter(Feedback.id == feedback_id).first()
        if feedback:
            user = session.query(User).filter(User.id == feedback.user_id).first()
            if user:
                await message.bot.send_message(user.telegram_id, f"❔ '{feedback.message}'\n❕ {message.text}")
                await message.answer("🟢 Ваш ответ был отправлен пользователю.")
                #session.delete(feedback)
                feedback.answered = 1
                session.commit()
            else:
                await message.answer("❌ Пользователь не найден.")
        else:
            await message.answer("❌ Вопрос не найден.")
    except SQLAlchemyError as e: 
        logger.error(f"SQLAlchemyError: {str(e)}") 
        await message.answer("Произошла ошибка базы данных. Попробуйте позже.") 
    except Exception as e: 
        logger.error(f"Unexpected error: {str(e)}") 
        await message.answer(f"Произошла ошибка: {str(e)}") 
    finally:
        session.close()
    await state.clear()