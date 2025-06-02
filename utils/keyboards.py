from aiogram import types
from typing import List, Dict, Optional, Union
from enum import Enum
from config import ADMIN_IDS

class ButtonType(Enum):
    """Типы кнопок для унификации"""
    BACK = "🔙 Назад"
    BACK_TO_CATEGORIES = "🔙 К категориям"
    BACK_TO_TESTS = "🔙 К тестам"
    BACK_TO_MAIN = "🔙 В главное меню"
    BACK_TO_ADMIN = "🔙 В админку"
    CREATE = "➕ Создать"
    NEXT = "➡️"
    PREV = "⬅️"
    SEARCH = "🔍 Поиск"
    STATS = "📊 Статистика"
    KNOWLEDGE_BASE = "🍎 База знаний"
    TESTING = "📝 Тестирование"
    ADMIN_PANEL = "⚙️ Админ панель"

def _create_button(
    text: str, 
    callback_data: Optional[str] = None, 
    url: Optional[str] = None
) -> types.InlineKeyboardButton:
    """Создает кнопку с указанным текстом и данными"""
    if url:
        return types.InlineKeyboardButton(text=text, url=url)
    return types.InlineKeyboardButton(text=text, callback_data=callback_data)

def _add_navigation_buttons(
    buttons: List[List[types.InlineKeyboardButton]],
    back_data: str,
    next_data: Optional[str] = None,
    prev_data: Optional[str] = None
) -> None:
    """Добавляет кнопки навигации в массив кнопок"""
    nav_buttons = []
    if prev_data:
        nav_buttons.append(_create_button(ButtonType.PREV.value, prev_data))
    if next_data:
        nav_buttons.append(_create_button(ButtonType.NEXT.value, next_data))
    if nav_buttons:
        buttons.append(nav_buttons)
    buttons.append([_create_button(ButtonType.BACK.value, back_data)])

def get_main_menu_keyboard() -> types.ReplyKeyboardMarkup:
    """Get main menu keyboard for regular users."""
    return types.ReplyKeyboardMarkup(
        keyboard=[
            [
                types.KeyboardButton(text="📚 Каталог"),
                types.KeyboardButton(text="🔍 Поиск")
            ],
            [
                types.KeyboardButton(text="📝 Тесты"),
                types.KeyboardButton(text="❓ Помощь")
            ],
            [
                types.KeyboardButton(text="👤 Профиль"),
                types.KeyboardButton(text="🚪 Выход")
            ]
        ],
        resize_keyboard=True
    )

def get_admin_menu_keyboard() -> types.ReplyKeyboardMarkup:
    """Get main menu keyboard for administrators."""
    return types.ReplyKeyboardMarkup(
        keyboard=[
            [
                types.KeyboardButton(text="📚 Каталог"),
                types.KeyboardButton(text="🔍 Поиск")
            ],
            [
                types.KeyboardButton(text="📝 Тесты"),
                types.KeyboardButton(text="📊 Статистика")
            ],
            [
                types.KeyboardButton(text="⚙️ Управление"),
                types.KeyboardButton(text="👤 Профиль")
            ],
            [
                types.KeyboardButton(text="🚪 Выход")
            ]
        ],
        resize_keyboard=True
    )

def get_confirm_keyboard(action: str = None) -> types.InlineKeyboardMarkup:
    """Get confirmation keyboard for actions."""
    keyboard = [
        [
            types.InlineKeyboardButton(
                text="✅ Подтвердить",
                callback_data="confirm_action"
            ),
            types.InlineKeyboardButton(
                text="❌ Отмена",
                callback_data="cancel_action"
            )
        ]
    ]
    return types.InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_back_keyboard() -> types.InlineKeyboardMarkup:
    """Get back button keyboard."""
    return types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(
                    text="◀️ Назад",
                    callback_data="back_to_main"
                )
            ]
        ]
    )

def get_catalog_keyboard(categories: list) -> types.InlineKeyboardMarkup:
    """Get catalog navigation keyboard."""
    keyboard = []
    for category in categories:
        keyboard.append([
            types.InlineKeyboardButton(
                text=category["name"],
                callback_data=f"category_{category['id']}"
            )
        ])
    
    # Add back button
    keyboard.append([
        types.InlineKeyboardButton(
            text="◀️ Назад",
            callback_data="back_to_main"
        )
    ])
    
    return types.InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_product_keyboard(
    product_id: int,
    is_admin: bool = False
) -> types.InlineKeyboardMarkup:
    """Get product view keyboard."""
    keyboard = []
    
    # Add test button if product has tests
    keyboard.append([
        types.InlineKeyboardButton(
            text="📝 Пройти тест",
            callback_data=f"test_product_{product_id}"
        )
    ])
    
    # Add admin controls
    if is_admin:
        keyboard.extend([
            [
                types.InlineKeyboardButton(
                    text="✏️ Редактировать",
                    callback_data=f"edit_product_{product_id}"
                ),
                types.InlineKeyboardButton(
                    text="❌ Удалить",
                    callback_data=f"delete_product_{product_id}"
                )
            ]
        ])
    
    # Add back button
    keyboard.append([
        types.InlineKeyboardButton(
            text="◀️ Назад",
            callback_data="back_to_catalog"
        )
    ])
    
    return types.InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_test_keyboard(
    test_id: int,
    is_admin: bool = False
) -> types.InlineKeyboardMarkup:
    """Get test view keyboard."""
    keyboard = []
    
    # Add start test button
    keyboard.append([
        types.InlineKeyboardButton(
            text="▶️ Начать тест",
            callback_data=f"start_test_{test_id}"
        )
    ])
    
    # Add admin controls
    if is_admin:
        keyboard.extend([
            [
                types.InlineKeyboardButton(
                    text="✏️ Редактировать",
                    callback_data=f"edit_test_{test_id}"
                ),
                types.InlineKeyboardButton(
                    text="📊 Результаты",
                    callback_data=f"test_results_{test_id}"
                )
            ],
            [
                types.InlineKeyboardButton(
                    text="❌ Удалить",
                    callback_data=f"delete_test_{test_id}"
                )
            ]
        ])
    
    # Add back button
    keyboard.append([
        types.InlineKeyboardButton(
            text="◀️ Назад",
            callback_data="back_to_tests"
        )
    ])
    
    return types.InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_admin_control_keyboard() -> types.InlineKeyboardMarkup:
    """Get admin control panel keyboard."""
    return types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(
                    text="👥 Пользователи",
                    callback_data="admin_users"
                ),
                types.InlineKeyboardButton(
                    text="📚 Каталог",
                    callback_data="admin_catalog"
                )
            ],
            [
                types.InlineKeyboardButton(
                    text="📝 Тесты",
                    callback_data="admin_tests"
                ),
                types.InlineKeyboardButton(
                    text="📊 Статистика",
                    callback_data="admin_stats"
                )
            ],
            [
                types.InlineKeyboardButton(
                    text="⚙️ Настройки",
                    callback_data="admin_settings"
                )
            ],
            [
                types.InlineKeyboardButton(
                    text="◀️ Назад",
                    callback_data="back_to_main"
                )
            ]
        ]
    )

def get_pagination_keyboard(
    current_page: int,
    total_pages: int,
    prefix: str
) -> types.InlineKeyboardMarkup:
    """Get pagination keyboard."""
    keyboard = []
    
    # Add page navigation
    nav_buttons = []
    if current_page > 1:
        nav_buttons.append(
            types.InlineKeyboardButton(
                text="◀️",
                callback_data=f"{prefix}_page_{current_page - 1}"
            )
        )
    
    nav_buttons.append(
        types.InlineKeyboardButton(
            text=f"{current_page}/{total_pages}",
            callback_data="ignore"
        )
    )
    
    if current_page < total_pages:
        nav_buttons.append(
            types.InlineKeyboardButton(
                text="▶️",
                callback_data=f"{prefix}_page_{current_page + 1}"
            )
        )
    
    keyboard.append(nav_buttons)
    
    # Add back button
    keyboard.append([
        types.InlineKeyboardButton(
            text="◀️ Назад",
            callback_data=f"back_to_{prefix}"
        )
    ])
    
    return types.InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_main_keyboard(is_admin: bool = False) -> types.ReplyKeyboardMarkup:
    """Основная клавиатура пользователя"""
    buttons = [
        [ButtonType.KNOWLEDGE_BASE.value, ButtonType.TESTING.value],
        [ButtonType.SEARCH.value]
    ]
    
    if is_admin:
        buttons.append([ButtonType.ADMIN_PANEL.value])
    
    return types.ReplyKeyboardMarkup(
        keyboard=[[types.KeyboardButton(text=btn) for btn in row] for row in buttons],
        resize_keyboard=True,
        input_field_placeholder="Выберите действие"
    )

def get_categories_keyboard(
    categories: List[Dict],
    back_callback: str = "main_menu"
) -> types.InlineKeyboardMarkup:
    """Клавиатура выбора категорий"""
    buttons = [
        [_create_button(cat['name'], f"category:{cat['id']}")] 
        for cat in categories
    ]
    buttons.append([_create_button(ButtonType.BACK.value, back_callback)])
    return types.InlineKeyboardMarkup(inline_keyboard=buttons)

def get_products_keyboard(
    products: List[Dict],
    category_id: Union[int, str],
    back_callback: str = "knowledge_base"
) -> types.InlineKeyboardMarkup:
    """Клавиатура выбора товаров"""
    buttons = [
        [_create_button(prod['name'], f"product:{prod['id']}")] 
        for prod in products
    ]
    buttons.append([_create_button(ButtonType.BACK_TO_CATEGORIES.value, back_callback)])
    return types.InlineKeyboardMarkup(inline_keyboard=buttons)

def get_product_navigation_keyboard(
    product_id: Union[int, str],
    category_id: Union[int, str],
    total_images: int = 1,
    current_index: int = 0
) -> types.InlineKeyboardMarkup:
    """Клавиатура навигации по товару"""
    buttons = []
    
    if total_images > 1:
        buttons.append([
            _create_button(ButtonType.PREV.value, f"product_prev:{product_id}"),
            _create_button(f"{current_index+1}/{total_images}", "current_image"),
            _create_button(ButtonType.NEXT.value, f"product_next:{product_id}")
        ])
    
    buttons.append([
        _create_button(
            ButtonType.BACK_TO_CATEGORIES.value, 
            f"category:{category_id}"
        )
    ])
    
    return types.InlineKeyboardMarkup(inline_keyboard=buttons)

def get_tests_keyboard(
    tests: List[Dict],
    back_callback: str = "main_menu"
) -> types.InlineKeyboardMarkup:
    """Клавиатура выбора тестов"""
    buttons = [
        [_create_button(test['title'], f"test_select:{test['id']}")] 
        for test in tests
    ]
    buttons.append([_create_button(ButtonType.BACK.value, back_callback)])
    return types.InlineKeyboardMarkup(inline_keyboard=buttons)

def get_test_question_keyboard(
    question_idx: int,
    options: List[str],
    test_id: Union[int, str]
) -> types.InlineKeyboardMarkup:
    """Клавиатура вариантов ответа на вопрос"""
    return types.InlineKeyboardMarkup(inline_keyboard=[
        [_create_button(opt, f"test_answer:{test_id}:{question_idx}:{idx}")]
        for idx, opt in enumerate(options)
    ])

def get_test_result_keyboard(
    test_id: Optional[Union[int, str]] = None,
    passed: bool = False
) -> types.InlineKeyboardMarkup:
    """Клавиатура результатов теста"""
    buttons = []
    
    if test_id and not passed:
        buttons.append([
            _create_button("🔄 Попробовать снова", f"test_select:{test_id}")
        ])
    
    buttons.extend([
        [_create_button(ButtonType.TESTING.value, "testing")],
        [_create_button(ButtonType.BACK_TO_MAIN.value, "main_menu")]
    ])
    
    return types.InlineKeyboardMarkup(inline_keyboard=buttons)

def get_admin_keyboard() -> types.InlineKeyboardMarkup:
    """Клавиатура админ-панели"""
    buttons = [
        [
            _create_button("📂 Категории", "admin_categories"),
            _create_button("🍎 Товары", "admin_products")
        ],
        [
            _create_button("📝 Тесты", "admin_tests"),
            _create_button("📊 Статистика", "admin_stats")
        ],
        [_create_button(ButtonType.BACK_TO_MAIN.value, "main_menu")]
    ]
    return types.InlineKeyboardMarkup(inline_keyboard=buttons)

def get_admin_list_keyboard(
    items: List[Dict],
    item_type: str,
    parent_id: Optional[Union[int, str]] = None,
    create_button: bool = True
) -> types.InlineKeyboardMarkup:
    """Универсальная клавиатура для списков в админке"""
    buttons = [
        [_create_button(item['name'], f"admin_{item_type}_edit:{item['id']}")]
        for item in items
    ]
    
    if create_button:
        callback = f"admin_{item_type}_create"
        if parent_id:
            callback += f":{parent_id}"
        buttons.append([_create_button(ButtonType.CREATE.value + f" {item_type}", callback)])
    
    buttons.append([_create_button(ButtonType.BACK_TO_ADMIN.value, "admin")])
    
    return types.InlineKeyboardMarkup(inline_keyboard=buttons)

def get_admin_categories_keyboard(
    categories: List[Dict],
    back_callback: str = "admin"
) -> types.InlineKeyboardMarkup:
    """Клавиатура управления категориями"""
    buttons = []
    
    # Добавляем кнопки категорий
    for cat in categories:
        buttons.append([
            _create_button(cat['name'], f"admin_category_edit:{cat['id']}")
        ])
    
    # Добавляем кнопку создания
    buttons.append([
        _create_button(ButtonType.CREATE.value + " категорию", "create_category")
    ])
    
    # Добавляем кнопку возврата
    buttons.append([
        _create_button(ButtonType.BACK_TO_ADMIN.value, back_callback)
    ])
    
    return types.InlineKeyboardMarkup(inline_keyboard=buttons)

def get_admin_products_keyboard(
    categories: List[Dict],
    back_callback: str = "admin"
) -> types.InlineKeyboardMarkup:
    """Клавиатура управления товарами"""
    buttons = []
    
    # Добавляем кнопки категорий
    for cat in categories:
        buttons.append([
            _create_button(cat['name'], f"admin_products_category:{cat['id']}")
        ])
    
    # Добавляем кнопку поиска
    buttons.append([
        _create_button(ButtonType.SEARCH.value, "admin_search_products")
    ])
    
    # Добавляем кнопку возврата
    buttons.append([
        _create_button(ButtonType.BACK_TO_ADMIN.value, back_callback)
    ])
    
    return types.InlineKeyboardMarkup(inline_keyboard=buttons)

def get_admin_products_list_keyboard(
    products: List[Dict],
    category_id: Union[int, str],
    back_callback: str = "admin_products"
) -> types.InlineKeyboardMarkup:
    """Клавиатура списка товаров в категории"""
    buttons = []
    
    # Добавляем кнопки товаров
    for prod in products:
        buttons.append([
            _create_button(prod['name'], f"admin_product_edit:{prod['id']}")
        ])
    
    # Добавляем кнопку создания товара
    buttons.append([
        _create_button(ButtonType.CREATE.value + " товар", f"create_product:{category_id}")
    ])
    
    # Добавляем кнопку возврата
    buttons.append([
        _create_button(ButtonType.BACK_TO_CATEGORIES.value, back_callback)
    ])
    
    return types.InlineKeyboardMarkup(inline_keyboard=buttons)

def get_admin_tests_keyboard(
    tests: List[Dict],
    back_callback: str = "admin"
) -> types.InlineKeyboardMarkup:
    """Клавиатура управления тестами"""
    buttons = [
        [_create_button(test['title'], f"admin_test_edit:{test['id']}")] 
        for test in tests
    ]
    buttons.append([_create_button(ButtonType.CREATE.value + " тест", "create_test")])
    buttons.append([_create_button(ButtonType.BACK_TO_ADMIN.value, "admin")])
    return types.InlineKeyboardMarkup(inline_keyboard=buttons)

def get_admin_stats_keyboard(
    back_callback: str = "admin"
) -> types.InlineKeyboardMarkup:
    """Клавиатура статистики"""
    buttons = [
        [
            _create_button("👥 Пользователи", "admin_stats_users"),
            _create_button("📝 Тесты", "admin_stats_tests")
        ],
        [_create_button(ButtonType.BACK_TO_ADMIN.value, "admin")]
    ]
    return types.InlineKeyboardMarkup(inline_keyboard=buttons)

def get_cancel_keyboard(
    cancel_callback: str = "cancel"
) -> types.InlineKeyboardMarkup:
    """Клавиатура отмены действия"""
    return types.InlineKeyboardMarkup(inline_keyboard=[
        [_create_button("❌ Отменить", cancel_callback)]
    ])

def get_back_to_categories_keyboard(
    back_callback: str = "knowledge_base"
) -> types.InlineKeyboardMarkup:
    """Клавиатура возврата к списку категорий"""
    return types.InlineKeyboardMarkup(inline_keyboard=[
        [_create_button(ButtonType.BACK_TO_CATEGORIES.value, back_callback)]
    ])

def get_back_to_tests_keyboard(
    back_callback: str = "testing"
) -> types.InlineKeyboardMarkup:
    """Клавиатура возврата к списку тестов"""
    return types.InlineKeyboardMarkup(inline_keyboard=[
        [_create_button(ButtonType.BACK_TO_TESTS.value, back_callback)]
    ])
