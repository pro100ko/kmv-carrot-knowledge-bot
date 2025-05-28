from aiogram import types
from typing import List, Dict, Optional, Union
from enum import Enum

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
        ["📂 Категории", "🍎 Товары"],
        ["📝 Тесты", "📊 Статистика"],
        [ButtonType.BACK_TO_MAIN.value]
    ]
    return types.InlineKeyboardMarkup(inline_keyboard=[
        [_create_button(text, f"admin_{text.split()[1].lower()}") for text in row]
        for row in buttons
    ])

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

def get_pagination_keyboard(page, total_pages, prefix):
    buttons = []
    if page > 1:
        buttons.append(types.InlineKeyboardButton(
            text="⬅️",
            callback_data=f"{prefix}:page:{page-1}"
        ))
    buttons.append(types.InlineKeyboardButton(
        text=f"{page}/{total_pages}",
        callback_data="current_page"
    ))
    if page < total_pages:
        buttons.append(types.InlineKeyboardButton(
            text="➡️",
            callback_data=f"{prefix}:page:{page+1}"
        ))
    return types.InlineKeyboardMarkup(inline_keyboard=[buttons])

def get_confirmation_keyboard(
    confirm_text: str = "✅ Подтвердить",
    confirm_callback: str = "confirm",
    cancel_text: str = "❌ Отменить",
    cancel_callback: str = "cancel"
) -> types.InlineKeyboardMarkup:
    """Клавиатура подтверждения действия"""
    return types.InlineKeyboardMarkup(inline_keyboard=[
        [
            _create_button(confirm_text, confirm_callback),
            _create_button(cancel_text, cancel_callback)
        ]
    ])

def get_admin_categories_keyboard(
    categories: List[Dict],
    back_callback: str = "admin"
) -> types.InlineKeyboardMarkup:
    """Клавиатура управления категориями в админке"""
    buttons = [
        [_create_button(cat['name'], f"admin_category_edit:{cat['id']}")] 
        for cat in categories
    ]
    buttons.append([_create_button(ButtonType.CREATE.value + " категорию", "create_category")])
    buttons.append([_create_button(ButtonType.BACK_TO_ADMIN.value, back_callback)])
    return types.InlineKeyboardMarkup(inline_keyboard=buttons)

def get_admin_products_keyboard(
    categories: List[Dict],
    back_callback: str = "admin"
) -> types.InlineKeyboardMarkup:
    """Клавиатура выбора категории товаров в админке"""
    buttons = [
        [_create_button(cat['name'], f"admin_products_category:{cat['id']}")] 
        for cat in categories
    ]
    buttons.append([_create_button(ButtonType.SEARCH.value, "admin_search_products")])
    buttons.append([_create_button(ButtonType.BACK_TO_ADMIN.value, back_callback)])
    return types.InlineKeyboardMarkup(inline_keyboard=buttons)

def get_admin_products_list_keyboard(
    products: List[Dict],
    category_id: Optional[Union[int, str]] = None,
    back_callback: str = "admin_products"
) -> types.InlineKeyboardMarkup:
    """Клавиатура списка товаров в админке"""
    buttons = [
        [_create_button(prod['name'], f"admin_product_edit:{prod['id']}")] 
        for prod in products
    ]
    if category_id:
        buttons.append([_create_button(ButtonType.CREATE.value + " товар", f"create_product:{category_id}")])
    else:
        buttons.append([_create_button(ButtonType.CREATE.value + " товар", "create_product")])
    buttons.append([_create_button(ButtonType.BACK_TO_CATEGORIES.value, back_callback)])
    return types.InlineKeyboardMarkup(inline_keyboard=buttons)

def get_admin_tests_keyboard(
    tests: List[Dict],
    back_callback: str = "admin"
) -> types.InlineKeyboardMarkup:
    """Клавиатура управления тестами в админке"""
    buttons = [
        [_create_button(test['title'], f"admin_test_edit:{test['id']}")] 
        for test in tests
    ]
    buttons.append([_create_button(ButtonType.CREATE.value + " тест", "create_test")])
    buttons.append([_create_button(ButtonType.BACK_TO_ADMIN.value, back_callback)])
    return types.InlineKeyboardMarkup(inline_keyboard=buttons)

def get_admin_stats_keyboard(
    back_callback: str = "admin"
) -> types.InlineKeyboardMarkup:
    """Клавиатура статистики в админке"""
    buttons = [
        [_create_button("👥 Пользователи", "admin_stats_users")],
        [_create_button("📝 Тесты", "admin_stats_tests")],
        [_create_button(ButtonType.BACK_TO_ADMIN.value, back_callback)]
    ]
    return types.InlineKeyboardMarkup(inline_keyboard=buttons)

def get_cancel_keyboard(
    cancel_callback: str = "cancel"
) -> types.InlineKeyboardMarkup:
    """Клавиатура отмены действия"""
    return types.InlineKeyboardMarkup(inline_keyboard=[
        [_create_button("❌ Отменить", cancel_callback)]
    ])
