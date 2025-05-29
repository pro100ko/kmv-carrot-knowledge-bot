from aiogram.fsm.state import StatesGroup, State

class CategoryForm(StatesGroup):
    """Состояния для работы с категориями"""
    name = State()  # Создание категории
    edit_name = State()  # Редактирование категории
    confirm_delete = State()  # Подтверждение удаления

class ProductForm(StatesGroup):
    """Состояния для работы с товарами"""
    name = State()  # Создание товара
    description = State()  # Описание товара
    images = State()  # Загрузка изображений
    edit_name = State()  # Редактирование названия
    edit_description = State()  # Редактирование описания
    edit_images = State()  # Редактирование изображений
    confirm_delete = State()  # Подтверждение удаления
    search = State()  # Поиск товаров

class TestForm(StatesGroup):
    """Состояния для работы с тестами"""
    title = State()  # Создание теста
    question = State()  # Добавление вопроса
    options = State()  # Добавление вариантов ответа
    correct_answer = State()  # Указание правильного ответа
    edit_title = State()  # Редактирование названия
    edit_question = State()  # Редактирование вопроса
    edit_options = State()  # Редактирование вариантов
    edit_correct = State()  # Редактирование правильного ответа
    confirm_delete = State()  # Подтверждение удаления

__all__ = ['CategoryForm', 'ProductForm', 'TestForm']
