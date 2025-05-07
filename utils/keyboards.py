
from aiogram.types import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from typing import List, Dict, Any

def get_main_keyboard(is_admin: bool = False) -> InlineKeyboardMarkup:
    """Создает главную клавиатуру бота"""
    buttons = [
        [
            InlineKeyboardButton(text="🍎 База знаний", callback_data="knowledge_base"),
            InlineKeyboardButton(text="📝 Тестирование", callback_data="testing")
        ]
    ]
    
    # Добавляем кнопку админ-панели для администраторов
    if is_admin:
        buttons.append([InlineKeyboardButton(text="⚙️ Админ панель", callback_data="admin")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_categories_keyboard(categories: List[Dict[str, Any]], with_back: bool = True) -> InlineKeyboardMarkup:
    """Создает клавиатуру с категориями продуктов"""
    buttons = []
    
    # Добавляем кнопки для категорий, по 2 в ряд
    for i in range(0, len(categories), 2):
        row = []
        category = categories[i]
        row.append(InlineKeyboardButton(text=category['name'], callback_data=f"category:{category['id']}"))
        
        # Добавляем вторую категорию в ряд, если она есть
        if i + 1 < len(categories):
            category = categories[i + 1]
            row.append(InlineKeyboardButton(text=category['name'], callback_data=f"category:{category['id']}"))
        
        buttons.append(row)
    
    # Добавляем кнопку поиска и назад
    row = [InlineKeyboardButton(text="🔍 Поиск", callback_data="search")]
    if with_back:
        row.append(InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main"))
    buttons.append(row)
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_products_keyboard(products: List[Dict[str, Any]], category_id: str) -> InlineKeyboardMarkup:
    """Создает клавиатуру со списком продуктов"""
    buttons = []
    
    # Добавляем кнопки для продуктов, по 1 в ряд
    for product in products:
        buttons.append([
            InlineKeyboardButton(text=product['name'], callback_data=f"product:{product['id']}")
        ])
    
    # Добавляем кнопку назад к категориям
    buttons.append([
        InlineKeyboardButton(text="🔙 Назад к категориям", callback_data=f"back_to_category:{category_id}")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_product_navigation_keyboard(product_id: str, category_id: str) -> InlineKeyboardMarkup:
    """Создает клавиатуру для навигации между фото продукта и возврата к списку товаров"""
    buttons = [
        [
            InlineKeyboardButton(text="⬅️ Предыдущее", callback_data=f"product_prev:{product_id}"),
            InlineKeyboardButton(text="Следующее ➡️", callback_data=f"product_next:{product_id}")
        ],
        [
            InlineKeyboardButton(text="🔙 К списку товаров", callback_data=f"back_to_products:{category_id}")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_tests_keyboard(tests: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
    """Создает клавиатуру со списком доступных тестов"""
    buttons = []
    
    # Добавляем кнопки для тестов, по 1 в ряд
    for test in tests:
        buttons.append([
            InlineKeyboardButton(text=test['title'], callback_data=f"test_select:{test['id']}")
        ])
    
    # Добавляем кнопку назад к главному меню
    buttons.append([
        InlineKeyboardButton(text="🔙 В главное меню", callback_data="back_to_main")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_test_question_keyboard(question_idx: int, options: List[str], test_id: str) -> InlineKeyboardMarkup:
    """Создает клавиатуру для вопроса теста"""
    buttons = []
    
    # Добавляем кнопки для вариантов ответа
    for idx, option in enumerate(options):
        buttons.append([
            InlineKeyboardButton(text=f"{idx+1}. {option}", callback_data=f"test_answer:{test_id}:{question_idx}:{idx}")
        ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_test_result_keyboard() -> InlineKeyboardMarkup:
    """Создает клавиатуру для результатов теста"""
    buttons = [
        [
            InlineKeyboardButton(text="🔄 Пройти ещё раз", callback_data="testing")
        ],
        [
            InlineKeyboardButton(text="🏠 В главное меню", callback_data="back_to_main")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_admin_keyboard() -> InlineKeyboardMarkup:
    """Создает клавиатуру для админ-панели"""
    buttons = [
        [
            InlineKeyboardButton(text="📂 Категории", callback_data="admin_categories")
        ],
        [
            InlineKeyboardButton(text="🍎 Товары", callback_data="admin_products")
        ],
        [
            InlineKeyboardButton(text="📝 Тесты", callback_data="admin_tests")
        ],
        [
            InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")
        ],
        [
            InlineKeyboardButton(text="🔙 В главное меню", callback_data="back_to_main")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_admin_categories_keyboard(categories: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
    """Создает клавиатуру для управления категориями"""
    buttons = []
    
    # Добавляем существующие категории
    for category in categories:
        buttons.append([
            InlineKeyboardButton(text=f"🖊️ {category['name']}", callback_data=f"edit_category:{category['id']}")
        ])
    
    # Добавляем кнопки создания и возврата
    buttons.append([InlineKeyboardButton(text="➕ Создать категорию", callback_data="add_category")])
    buttons.append([InlineKeyboardButton(text="🔙 Назад в админ-панель", callback_data="admin")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_admin_products_keyboard(categories: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
    """Создает клавиатуру для выбора категории при управлении товарами"""
    buttons = []
    
    # Добавляем категории для выбора
    for category in categories:
        buttons.append([
            InlineKeyboardButton(text=category['name'], callback_data=f"admin_products_category:{category['id']}")
        ])
    
    # Добавляем кнопку возврата
    buttons.append([InlineKeyboardButton(text="🔙 Назад в админ-панель", callback_data="admin")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_admin_products_list_keyboard(products: List[Dict[str, Any]], category_id: str) -> InlineKeyboardMarkup:
    """Создает клавиатуру со списком товаров для редактирования"""
    buttons = []
    
    # Добавляем существующие товары
    for product in products:
        buttons.append([
            InlineKeyboardButton(text=f"🖊️ {product['name']}", callback_data=f"edit_product:{product['id']}")
        ])
    
    # Добавляем кнопки создания и возврата
    buttons.append([InlineKeyboardButton(text="➕ Создать товар", callback_data=f"add_product:{category_id}")])
    buttons.append([InlineKeyboardButton(text="🔙 Назад к категориям", callback_data="admin_products")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_admin_tests_keyboard(tests: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
    """Создает клавиатуру для управления тестами"""
    buttons = []
    
    # Добавляем существующие тесты
    for test in tests:
        buttons.append([
            InlineKeyboardButton(text=f"🖊️ {test['title']}", callback_data=f"edit_test:{test['id']}")
        ])
    
    # Добавляем кнопки создания и возврата
    buttons.append([InlineKeyboardButton(text="➕ Создать тест", callback_data="add_test")])
    buttons.append([InlineKeyboardButton(text="🔙 Назад в админ-панель", callback_data="admin")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_admin_stats_keyboard() -> InlineKeyboardMarkup:
    """Создает клавиатуру для просмотра статистики"""
    buttons = [
        [
            InlineKeyboardButton(text="👥 Пользователи", callback_data="admin_stats_users")
        ],
        [
            InlineKeyboardButton(text="📝 Тесты", callback_data="admin_stats_tests")
        ],
        [
            InlineKeyboardButton(text="🔙 Назад в админ-панель", callback_data="admin")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)
