# states.py
from aiogram.fsm.state import StatesGroup, State

class CategoryForm(StatesGroup):
    name = State()
    description = State()
    image = State()

class ProductForm(StatesGroup):
    name = State()
    category = State()
    description = State()
    price = State()
    storage = State()
    images = State()
    video = State()
