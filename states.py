from aiogram.fsm.state import StatesGroup, State

class CategoryForm(StatesGroup):
    """Состояния для создания/редактирования категории"""
    name = State()
    description = State()
    image = State()

class ProductForm(StatesGroup):
    """Состояния для создания/редактирования товара"""
    name = State()
    category = State()
    description = State()
    price = State()
    storage = State()
    images = State()
    video = State()
    search = State()  # Added for product search functionality

class TestForm(StatesGroup):
    """Состояния для создания/редактирования теста"""
    title = State()
    description = State()
    category = State()
    questions = State()
    passing_score = State()

__all__ = ['CategoryForm', 'ProductForm', 'TestForm']
