from aiogram import Router
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

unknow_router = Router()

class UnknowStates(StatesGroup):
    unknown = State()

@unknow_router.message()
async def handle_unknown_command(message: Message, state: FSMContext):
    await message.answer(f"Извините, я вас не понял. Выберите команду из меню бота.")
    await state.set_state(UnknowStates.unknown)

@unknow_router.message()
async def handle_unknown_message(message: Message, state: FSMContext):
    await message.answer(f"Извините, я вас не понял. Выберите команду из меню бота.")
    await state.set_state(UnknowStates.unknown)
