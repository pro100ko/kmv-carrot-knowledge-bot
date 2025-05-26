
from aiogram.fsm.state import StatesGroup, State

class ProductForm(StatesGroup):
    name = State()
    category = State()
    description = State()
    price = State()
    storage = State()
    images = State()
    video = State()

class TestForm(StatesGroup):
    title = State()
    description = State()
    category = State()
    questions = State()
    passing_score = State()
