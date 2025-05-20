# states.py
from aiogram.fsm.state import StatesGroup, State

class CategoryForm(StatesGroup):
    name = State()
    description = State()
    image = State()
