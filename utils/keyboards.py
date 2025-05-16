
from aiogram import types
from typing import List, Dict, Optional

def get_main_keyboard(is_admin: bool = False) -> types.ReplyKeyboardMarkup:
    """Генерирует основную клавиатуру для пользователя"""
    keyboard = [
        [
            types.KeyboardButton(text="🍎 База знаний"),
            types.KeyboardButton(text="📝 Тестирование")
        ],
        [types.KeyboardButton(text="🔍 Поиск")]
    ]
    
    # Добавляем кнопку админ-панели, если пользователь - админ
    if is_admin:
        keyboard.append([types.KeyboardButton(text="⚙️ Админ панель")])
    
    return types.ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True
    )

def get_categories_keyboard(categories: List[Dict]) -> types.InlineKeyboardMarkup:
    """Генерирует клавиатуру для выбора категорий"""
    buttons = []
    for category in categories:
        buttons.append([
            types.InlineKeyboardButton(
                text=category['name'], 
                callback_data=f"category:{category['id']}"
            )
        ])
    
    # Добавляем кнопку возврата в главное меню
    buttons.append([
        types.InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")
    ])
    
    return types.InlineKeyboardMarkup(inline_keyboard=buttons)

def get_products_keyboard(products: List[Dict], category_id: str) -> types.InlineKeyboardMarkup:
    """Генерирует клавиатуру для выбора товаров в категории"""
    buttons = []
    
    # Добавляем кнопки для каждого продукта
    for product in products:
        buttons.append([
            types.InlineKeyboardButton(
                text=product['name'], 
                callback_data=f"product:{product['id']}"
            )
        ])
    
    # Добавляем кнопку возврата к категориям
    buttons.append([
        types.InlineKeyboardButton(text="🔙 Назад к категориям", callback_data="knowledge_base")
    ])
    
    return types.InlineKeyboardMarkup(inline_keyboard=buttons)

def get_product_navigation_keyboard(product_id: str, category_id: str) -> types.InlineKeyboardMarkup:
    """Генерирует клавиатуру для навигации по изображениям товара"""
    buttons = [
        [
            types.InlineKeyboardButton(text="⬅️", callback_data=f"product_prev:{product_id}"),
            types.InlineKeyboardButton(text="➡️", callback_data=f"product_next:{product_id}")
        ],
        [types.InlineKeyboardButton(text="🔙 Назад к товарам", callback_data=f"category:{category_id}")]
    ]
    
    return types.InlineKeyboardMarkup(inline_keyboard=buttons)

def get_tests_keyboard(tests: List[Dict]) -> types.InlineKeyboardMarkup:
    """Генерирует клавиатуру для выбора тестов"""
    buttons = []
    
    for test in tests:
        buttons.append([
            types.InlineKeyboardButton(
                text=test['title'], 
                callback_data=f"test_select:{test['id']}"
            )
        ])
    
    # Добавляем кнопку возврата
    buttons.append([
        types.InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")
    ])
    
    return types.InlineKeyboardMarkup(inline_keyboard=buttons)

def get_test_question_keyboard(question_idx: int, options: List[str], test_id: str) -> types.InlineKeyboardMarkup:
    """Генерирует клавиатуру с вариантами ответов на вопросы теста"""
    buttons = []
    
    # Добавляем варианты ответов
    for idx, option in enumerate(options):
        buttons.append([
            types.InlineKeyboardButton(
                text=option, 
                callback_data=f"test_answer:{test_id}:{question_idx}:{idx}"
            )
        ])
    
    return types.InlineKeyboardMarkup(inline_keyboard=buttons)

def get_test_result_keyboard() -> types.InlineKeyboardMarkup:
    """Генерирует клавиатуру для показа результатов теста"""
    buttons = [
        [types.InlineKeyboardButton(text="📝 Другие тесты", callback_data="testing")],
        [types.InlineKeyboardButton(text="🔙 В главное меню", callback_data="main_menu")]
    ]
    
    return types.InlineKeyboardMarkup(inline_keyboard=buttons)

def get_admin_keyboard() -> types.InlineKeyboardMarkup:
    """Генерирует клавиатуру для админ-панели"""
    buttons = [
        [types.InlineKeyboardButton(text="📂 Управление категориями", callback_data="admin_categories")],
        [types.InlineKeyboardButton(text="🍎 Управление товарами", callback_data="admin_products")],
        [types.InlineKeyboardButton(text="📝 Управление тестами", callback_data="admin_tests")],
        [types.InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
        [types.InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")]
    ]
    
    return types.InlineKeyboardMarkup(inline_keyboard=buttons)

def get_admin_categories_keyboard(categories: List[Dict]) -> types.InlineKeyboardMarkup:
    """Генерирует клавиатуру для управления категориями"""
    buttons = []
    
    # Добавляем существующие категории
    for category in categories:
        buttons.append([
            types.InlineKeyboardButton(
                text=category['name'], 
                callback_data=f"admin_categories_edit:{category['id']}"
            )
        ])
    
    # Добавляем кнопку создания новой категории и возврата
    buttons.append([
        types.InlineKeyboardButton(text="➕ Создать категорию", callback_data="admin_categories_create")
    ])
    buttons.append([
        types.InlineKeyboardButton(text="🔙 Назад", callback_data="admin")
    ])
    
    return types.InlineKeyboardMarkup(inline_keyboard=buttons)

def get_admin_products_keyboard(categories: List[Dict]) -> types.InlineKeyboardMarkup:
    """Генерирует клавиатуру для выбора категории при управлении товарами"""
    buttons = []
    
    # Добавляем кнопки для каждой категории
    for category in categories:
        buttons.append([
            types.InlineKeyboardButton(
                text=category['name'], 
                callback_data=f"admin_products_category:{category['id']}"
            )
        ])
    
    # Добавляем кнопку возврата
    buttons.append([
        types.InlineKeyboardButton(text="🔙 Назад", callback_data="admin")
    ])
    
    # Создать товар
    buttons.append([types.InlineKeyboardButton(
        text="➕ Создать товар", 
        callback_data="create_product"
    )])
    return types.InlineKeyboardMarkup(inline_keyboard=buttons)

def get_admin_products_list_keyboard(products: List[Dict], category_id: str) -> types.InlineKeyboardMarkup:
    """Генерирует клавиатуру со списком товаров для управления"""
    buttons = []
    
    # Добавляем кнопки для каждого товара
    for product in products:
        buttons.append([
            types.InlineKeyboardButton(
                text=product['name'], 
                callback_data=f"admin_products_edit:{product['id']}"
            )
        ])
    
    # Добавляем кнопку создания нового товара и возврата
    buttons.append([
        types.InlineKeyboardButton(
            text="➕ Добавить товар", 
            callback_data=f"admin_products_create:{category_id}"
        )
    ])
    buttons.append([
        types.InlineKeyboardButton(text="🔙 Назад к категориям", callback_data="admin_products")
    ])
    
    return types.InlineKeyboardMarkup(inline_keyboard=buttons)

def get_admin_tests_keyboard(tests: List[Dict]) -> types.InlineKeyboardMarkup:
    """Генерирует клавиатуру для управления тестами"""
    buttons = []
    
    # Добавляем кнопки для каждого теста
    for test in tests:
        buttons.append([
            types.InlineKeyboardButton(
                text=test['title'], 
                callback_data=f"admin_tests_edit:{test['id']}"
            )
        ])
    
    # Добавляем кнопку создания нового теста и возврата
    buttons.append([
        types.InlineKeyboardButton(text="➕ Создать тест", callback_data="admin_tests_create")
    ])
    buttons.append([
        types.InlineKeyboardButton(text="🔙 Назад", callback_data="admin")
    ])
    
    return types.InlineKeyboardMarkup(inline_keyboard=buttons)

def get_admin_stats_keyboard() -> types.InlineKeyboardMarkup:
    """Генерирует клавиатуру для просмотра статистики"""
    buttons = [
        [types.InlineKeyboardButton(text="👥 Пользователи", callback_data="admin_stats_users")],
        [types.InlineKeyboardButton(text="📝 Тестирование", callback_data="admin_stats_tests")],
        [types.InlineKeyboardButton(text="🔙 Назад", callback_data="admin")]
    ]
    
    return types.InlineKeyboardMarkup(inline_keyboard=buttons)
