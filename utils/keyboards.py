
from telegram import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from typing import List, Dict, Any

def get_main_keyboard(is_admin: bool = False) -> InlineKeyboardMarkup:
    """Создает главную клавиатуру бота"""
    buttons = [
        [
            InlineKeyboardButton("🍎 База знаний", callback_data="knowledge_base"),
            InlineKeyboardButton("📝 Тестирование", callback_data="testing")
        ]
    ]
    
    # Добавляем кнопку админ-панели для администраторов
    if is_admin:
        buttons.append([InlineKeyboardButton("⚙️ Админ панель", callback_data="admin")])
    
    return InlineKeyboardMarkup(buttons)

def get_categories_keyboard(categories: List[Dict[str, Any]], with_back: bool = True) -> InlineKeyboardMarkup:
    """Создает клавиатуру с категориями продуктов"""
    buttons = []
    
    # Добавляем кнопки для категорий, по 2 в ряд
    for i in range(0, len(categories), 2):
        row = []
        category = categories[i]
        row.append(InlineKeyboardButton(category['name'], callback_data=f"category:{category['id']}"))
        
        # Добавляем вторую категорию в ряд, если она есть
        if i + 1 < len(categories):
            category = categories[i + 1]
            row.append(InlineKeyboardButton(category['name'], callback_data=f"category:{category['id']}"))
        
        buttons.append(row)
    
    # Добавляем кнопку поиска и назад
    row = [InlineKeyboardButton("🔍 Поиск", callback_data="search")]
    if with_back:
        row.append(InlineKeyboardButton("🔙 Назад", callback_data="back_to_main"))
    buttons.append(row)
    
    return InlineKeyboardMarkup(buttons)

def get_products_keyboard(products: List[Dict[str, Any]], category_id: str) -> InlineKeyboardMarkup:
    """Создает клавиатуру со списком продуктов"""
    buttons = []
    
    # Добавляем кнопки для продуктов, по 1 в ряд
    for product in products:
        buttons.append([
            InlineKeyboardButton(product['name'], callback_data=f"product:{product['id']}")
        ])
    
    # Добавляем кнопку назад к категориям
    buttons.append([
        InlineKeyboardButton("🔙 Назад к категориям", callback_data=f"back_to_category:{category_id}")
    ])
    
    return InlineKeyboardMarkup(buttons)

def get_product_navigation_keyboard(product_id: str, category_id: str) -> InlineKeyboardMarkup:
    """Создает клавиатуру для навигации между фото продукта и возврата к списку товаров"""
    buttons = [
        [
            InlineKeyboardButton("⬅️ Предыдущее", callback_data=f"product_prev:{product_id}"),
            InlineKeyboardButton("Следующее ➡️", callback_data=f"product_next:{product_id}")
        ],
        [
            InlineKeyboardButton("🔙 К списку товаров", callback_data=f"back_to_products:{category_id}")
        ]
    ]
    return InlineKeyboardMarkup(buttons)

def get_tests_keyboard(tests: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
    """Создает клавиатуру со списком доступных тестов"""
    buttons = []
    
    # Добавляем кнопки для тестов, по 1 в ряд
    for test in tests:
        buttons.append([
            InlineKeyboardButton(test['title'], callback_data=f"test_select:{test['id']}")
        ])
    
    # Добавляем кнопку назад к главному меню
    buttons.append([
        InlineKeyboardButton("🔙 В главное меню", callback_data="back_to_main")
    ])
    
    return InlineKeyboardMarkup(buttons)

def get_test_question_keyboard(question_idx: int, options: List[str], test_id: str) -> InlineKeyboardMarkup:
    """Создает клавиатуру для вопроса теста"""
    buttons = []
    
    # Добавляем кнопки для вариантов ответа
    for idx, option in enumerate(options):
        buttons.append([
            InlineKeyboardButton(f"{idx+1}. {option}", callback_data=f"test_answer:{test_id}:{question_idx}:{idx}")
        ])
    
    return InlineKeyboardMarkup(buttons)

def get_test_result_keyboard() -> InlineKeyboardMarkup:
    """Создает клавиатуру для результатов теста"""
    buttons = [
        [
            InlineKeyboardButton("🔄 Пройти ещё раз", callback_data="testing")
        ],
        [
            InlineKeyboardButton("🏠 В главное меню", callback_data="back_to_main")
        ]
    ]
    return InlineKeyboardMarkup(buttons)

def get_admin_keyboard() -> InlineKeyboardMarkup:
    """Создает клавиатуру для админ-панели"""
    buttons = [
        [
            InlineKeyboardButton("📂 Категории", callback_data="admin_categories")
        ],
        [
            InlineKeyboardButton("🍎 Товары", callback_data="admin_products")
        ],
        [
            InlineKeyboardButton("📝 Тесты", callback_data="admin_tests")
        ],
        [
            InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")
        ],
        [
            InlineKeyboardButton("🔙 В главное меню", callback_data="back_to_main")
        ]
    ]
    return InlineKeyboardMarkup(buttons)

def get_admin_categories_keyboard(categories: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
    """Создает клавиатуру для управления категориями"""
    buttons = []
    
    # Добавляем существующие категории
    for category in categories:
        buttons.append([
            InlineKeyboardButton(f"🖊️ {category['name']}", callback_data=f"edit_category:{category['id']}")
        ])
    
    # Добавляем кнопки создания и возврата
    buttons.append([InlineKeyboardButton("➕ Создать категорию", callback_data="add_category")])
    buttons.append([InlineKeyboardButton("🔙 Назад в админ-панель", callback_data="admin")])
    
    return InlineKeyboardMarkup(buttons)

def get_admin_products_keyboard(categories: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
    """Создает клавиатуру для выбора категории при управлении товарами"""
    buttons = []
    
    # Добавляем категории для выбора
    for category in categories:
        buttons.append([
            InlineKeyboardButton(category['name'], callback_data=f"admin_products_category:{category['id']}")
        ])
    
    # Добавляем кнопку возврата
    buttons.append([InlineKeyboardButton("🔙 Назад в админ-панель", callback_data="admin")])
    
    return InlineKeyboardMarkup(buttons)

def get_admin_products_list_keyboard(products: List[Dict[str, Any]], category_id: str) -> InlineKeyboardMarkup:
    """Создает клавиатуру со списком товаров для редактирования"""
    buttons = []
    
    # Добавляем существующие товары
    for product in products:
        buttons.append([
            InlineKeyboardButton(f"🖊️ {product['name']}", callback_data=f"edit_product:{product['id']}")
        ])
    
    # Добавляем кнопки создания и возврата
    buttons.append([InlineKeyboardButton("➕ Создать товар", callback_data=f"add_product:{category_id}")])
    buttons.append([InlineKeyboardButton("🔙 Назад к категориям", callback_data="admin_products")])
    
    return InlineKeyboardMarkup(buttons)

def get_admin_tests_keyboard(tests: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
    """Создает клавиатуру для управления тестами"""
    buttons = []
    
    # Добавляем существующие тесты
    for test in tests:
        buttons.append([
            InlineKeyboardButton(f"🖊️ {test['title']}", callback_data=f"edit_test:{test['id']}")
        ])
    
    # Добавляем кнопки создания и возврата
    buttons.append([InlineKeyboardButton("➕ Создать тест", callback_data="add_test")])
    buttons.append([InlineKeyboardButton("🔙 Назад в админ-панель", callback_data="admin")])
    
    return InlineKeyboardMarkup(buttons)

def get_admin_stats_keyboard() -> InlineKeyboardMarkup:
    """Создает клавиатуру для просмотра статистики"""
    buttons = [
        [
            InlineKeyboardButton("👥 Пользователи", callback_data="admin_stats_users")
        ],
        [
            InlineKeyboardButton("📝 Тесты", callback_data="admin_stats_tests")
        ],
        [
            InlineKeyboardButton("🔙 Назад в админ-панель", callback_data="admin")
        ]
    ]
    return InlineKeyboardMarkup(buttons)
