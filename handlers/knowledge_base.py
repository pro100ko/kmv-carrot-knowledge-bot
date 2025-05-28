from aiogram import types
from aiogram.enums import ParseMode
from aiogram.utils.media_group import MediaGroupBuilder
from typing import Optional, Dict, List

from sqlite_db import db  # Import the database instance
from utils.keyboards import (
    get_categories_keyboard,
    get_products_keyboard,
    get_product_navigation_keyboard,
    get_back_to_categories_keyboard
)
from config import MIN_SEARCH_LENGTH, MAX_SEARCH_RESULTS
from utils.message_utils import safe_edit_message

# Глобальный словарь для отслеживания состояния просмотра товаров
product_view_state: Dict[int, Dict[str, int]] = {}  # {user_id: {product_id: current_image_index}}

class ProductViewer:
    """Класс для управления просмотром товаров"""
    
    @staticmethod
    def get_current_state(user_id: int, product_id: int) -> Dict[str, int]:
        """Возвращает текущее состояние просмотра для пользователя и товара"""
        if user_id not in product_view_state:
            product_view_state[user_id] = {}
        if product_id not in product_view_state[user_id]:
            product_view_state[user_id][product_id] = 0
        return product_view_state[user_id]
    
    @staticmethod
    def update_image_index(user_id: int, product_id: int, delta: int) -> int:
        """Обновляет индекс изображения и возвращает новое значение"""
        state = ProductViewer.get_current_state(user_id, product_id)
        if product_id not in state:
            state[product_id] = 0
        images_count = len(db.get_product(product_id).get('image_urls', []))
        state[product_id] = (state[product_id] + delta) % images_count if images_count > 0 else 0
        return state[product_id]
    
    @staticmethod
    def reset_state(user_id: int):
        """Сбрасывает состояние просмотра для пользователя"""
        if user_id in product_view_state:
            del product_view_state[user_id]

async def knowledge_base_handler(
    update: types.Message | types.CallbackQuery,
    context=None
) -> None:
    """Главный обработчик базы знаний"""
    categories = db.get_categories()
    if not categories:
        text = "В базе знаний пока нет категорий товаров."
        keyboard = None
    else:
        text = "📚 <b>База знаний</b>\n\nВыберите категорию товаров:"
        keyboard = get_categories_keyboard(categories)
    
    if isinstance(update, types.CallbackQuery):
        await safe_edit_message(
            message=update.message,
            text=text,
            reply_markup=keyboard
        )
        await update.answer()
    else:
        await update.answer(
            text=text,
            reply_markup=keyboard
        )

async def category_handler(
    query: types.CallbackQuery,
    context=None
) -> None:
    """Обработчик выбора категории"""
    await query.answer()
    category_id = int(query.data.split(':')[1])
    products = db.get_products_by_category(category_id)
    category = next(
        (c for c in db.get_categories() if c['id'] == category_id),
        {'name': 'Категория'}
    )
    
    if not products:
        await safe_edit_message(
            message=query.message,
            text=f"📦 В категории \"{category['name']}\" пока нет товаров.",
            reply_markup=get_back_to_categories_keyboard()
        )
        return
    
    await safe_edit_message(
        message=query.message,
        text=f"📦 <b>{category['name']}</b>\n\nВыберите товар:",
        reply_markup=get_products_keyboard(products, category_id)
    )

async def product_handler(
    query: types.CallbackQuery,
    context=None
) -> None:
    """Обработчик просмотра товара"""
    await query.answer()
    user_id = query.from_user.id
    action, product_id = query.data.split(':')[:2]
    product_id = int(product_id)
    product = db.get_product(product_id)
    
    if not product:
        await safe_edit_message(
            message=query.message,
            text="⚠️ Товар не найден",
            reply_markup=get_back_to_categories_keyboard()
        )
        return
    
    # Обработка навигации по изображениям
    if action == "product":
        ProductViewer.get_current_state(user_id, product_id)  # Инициализация
    elif action == "product_next":
        ProductViewer.update_image_index(user_id, product_id, 1)
    elif action == "product_prev":
        ProductViewer.update_image_index(user_id, product_id, -1)
    
    current_index = product_view_state[user_id][product_id]
    images = product.get('image_urls', [])
    
    # Формирование информации о товаре
    text_parts = [
        f"<b>🏷 {product['name']}</b>",
        f"\n📝 {product['description']}" if product.get('description') else "",
        f"\n💰 <b>Цена:</b> {product['price_info']}" if product.get('price_info') else "",
        f"\n❄️ <b>Хранение:</b> {product['storage_conditions']}" if product.get('storage_conditions') else "",
        f"\n\n🖼 Фото {current_index + 1}/{len(images)}" if len(images) > 1 else ""
    ]
    
    # Отправка сообщения с товаром
    await safe_edit_message(
        message=query.message,
        text="".join(text_parts),
        parse_mode=ParseMode.HTML,
        reply_markup=get_product_navigation_keyboard(product_id, product['category_id'], len(images))
    )
    
    # Отправка медиа (изображения/видео)
    await send_product_media(query.message, product, current_index)

async def send_product_media(
    message: types.Message,
    product: Dict,
    image_index: int = 0
) -> None:
    """Отправляет медиа-контент товара"""
    images = product.get('image_urls', [])
    video_url = product.get('video_url')
    
    try:
        if images:
            if len(images) > 1:
                # Для нескольких изображений используем медиагруппу
                media_group = MediaGroupBuilder()
                for img in images:
                    media_group.add_photo(media=img)
                await message.answer_media_group(media=media_group.build())
            else:
                # Для одного изображения
                await message.answer_photo(
                    photo=images[image_index],
                    caption=f"Фото товара: {product['name']}"
                )
        
        if video_url:
            await message.answer_video(
                video=video_url,
                caption=f"Видео о товаре: {product['name']}"
            )
    except Exception as e:
        await message.answer("⚠️ Не удалось загрузить медиа-файлы товара")

async def search_handler(
    message: types.Message,
    context=None
) -> None:
    """Обработчик поиска товаров"""
    if message.text == "🔍 Поиск":
        await message.answer(
            "🔍 Введите название товара для поиска (минимум 3 символа)\n"
            "Формат: <code>🔍 Название</code>",
            parse_mode=ParseMode.HTML
        )
        return
    
    query_text = message.text[2:].strip()
    if len(query_text) < MIN_SEARCH_LENGTH:
        await message.answer(
            f"🔍 Поисковый запрос должен содержать минимум {MIN_SEARCH_LENGTH} символа",
            reply_markup=get_back_to_categories_keyboard()
        )
        return
    
    products = db.search_products(query_text)[:MAX_SEARCH_RESULTS]
    
    if not products:
        await message.answer(
            f"🔍 По запросу \"{query_text}\" ничего не найдено",
            reply_markup=get_back_to_categories_keyboard()
        )
        return
    
    response = [f"🔍 Результаты поиска \"{query_text}\":\n"]
    buttons = []
    
    for idx, product in enumerate(products, 1):
        response.append(f"{idx}. {product['name']}")
        buttons.append([
            types.InlineKeyboardButton(
                text=product['name'],
                callback_data=f"product:{product['id']}"
            )
        ])
    
    buttons.append([
        types.InlineKeyboardButton(
            text="🔙 К категориям",
            callback_data="knowledge_base"
        )
    ])
    
    await message.answer(
        "\n".join(response),
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=buttons)
    )
