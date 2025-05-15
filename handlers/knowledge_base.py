
from aiogram import types
from aiogram.enums import ParseMode

import firebase_db
import sqlite_db

# Определяем, какую базу данных использовать
# Если Firebase доступен, используем его, иначе SQLite
DB_MODULE = firebase_db if firebase_db.FIREBASE_AVAILABLE else sqlite_db

from utils.keyboards import get_categories_keyboard, get_products_keyboard, get_product_navigation_keyboard

# Глобальный словарь для отслеживания индекса текущего изображения продукта
product_image_indices = {}

async def knowledge_base_handler(update: types.Message | types.CallbackQuery, context=None) -> None:
    """Обработчик для базы знаний"""
    # Получаем категории
    categories = DB_MODULE.get_categories()
    
    if isinstance(update, types.CallbackQuery):
        # Отправляем сообщение с категориями
        query = update
        await query.answer()
        await query.message.edit_text(
            text="Выберите категорию товаров:",
            reply_markup=get_categories_keyboard(categories)
        )
    else:
        # Если это обычное сообщение, отправляем новое
        await update.answer(
            text="Выберите категорию товаров:",
            reply_markup=get_categories_keyboard(categories)
        )

async def category_handler(update: types.CallbackQuery, context=None) -> None:
    """Обработчик для выбора категории"""
    query = update
    await query.answer()
    
    # Получаем ID категории из callback_data
    category_id = query.data.split(':')[1]
    
    # Получаем продукты для выбранной категории
    products = DB_MODULE.get_products_by_category(category_id)
    
    # Если продукты есть, отправляем их список
    if products:
        # Получаем информацию о выбранной категории
        categories = DB_MODULE.get_categories()
        selected_category = next((c for c in categories if c['id'] == category_id), None)
        
        category_name = selected_category['name'] if selected_category else "Категория"
        
        await query.message.edit_text(
            text=f"Товары в категории \"{category_name}\":",
            reply_markup=get_products_keyboard(products, category_id)
        )
    else:
        # Если продуктов нет, сообщаем об этом
        await query.message.edit_text(
            text="В этой категории пока нет товаров.",
            reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
                [types.InlineKeyboardButton(text="🔙 Назад к категориям", callback_data="knowledge_base")]
            ])
        )

async def product_handler(update: types.CallbackQuery, context=None) -> None:
    """Обработчик для просмотра продукта"""
    query = update
    await query.answer()
    
    # Проверяем, это запрос на просмотр продукта или навигация между фото
    parts = query.data.split(':')
    command = parts[0]
    product_id = parts[1]
    
    # Получаем информацию о продукте
    product = DB_MODULE.get_product(product_id)
    
    if not product:
        await query.message.edit_text(
            text="Товар не найден.",
            reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
                [types.InlineKeyboardButton(text="🔙 Назад к категориям", callback_data="knowledge_base")]
            ])
        )
        return
    
    # Определяем индекс текущего изображения
    if command == "product":
        # Если это первый просмотр продукта, начинаем с первого изображения
        product_image_indices[product_id] = 0
    elif command == "product_next":
        # Переходим к следующему изображению
        current_index = product_image_indices.get(product_id, 0)
        product_image_indices[product_id] = (current_index + 1) % len(product['image_urls']) if product['image_urls'] else 0
    elif command == "product_prev":
        # Переходим к предыдущему изображению
        current_index = product_image_indices.get(product_id, 0)
        product_image_indices[product_id] = (current_index - 1) % len(product['image_urls']) if product['image_urls'] else 0
    
    # Текущий индекс изображения
    current_index = product_image_indices.get(product_id, 0)
    
    # Строим текст с информацией о продукте
    product_info = f"<b>{product['name']}</b>\n\n"
    
    if product.get('description'):
        product_info += f"{product['description']}\n\n"
    
    if product.get('price_info'):
        product_info += f"<b>Цена:</b> {product['price_info']}\n"
    
    if product.get('storage_conditions'):
        product_info += f"<b>Условия хранения:</b> {product['storage_conditions']}\n"
    
    # Добавляем информацию о текущем изображении, если их несколько
    if product.get('image_urls') and len(product['image_urls']) > 1:
        product_info += f"\nФото {current_index + 1}/{len(product['image_urls'])}"
    
    # Создаем клавиатуру для навигации
    keyboard = get_product_navigation_keyboard(product_id, product['category_id'])
    
    # Отправляем информацию о продукте
    await query.message.edit_text(
        text=product_info,
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard
    )
    
    # Отправляем фото, если оно есть
    if product.get('image_urls') and len(product['image_urls']) > 0:
        # Получаем URL текущего изображения
        image_url = product['image_urls'][current_index]
        
        try:
            # Пытаемся отправить изображение
            await query.message.answer_photo(
                photo=image_url,
                reply_markup=keyboard
            )
        except Exception as e:
            # Если не удалось отправить изображение, сообщаем об ошибке
            await query.message.answer(
                text=f"Не удалось загрузить изображение: {str(e)}",
                reply_markup=keyboard
            )
    
    # Если есть видео, отправляем его в отдельном сообщении
    if product.get('video_url'):
        try:
            await query.message.answer_video(
                video=product['video_url'],
                caption="Видео о товаре"
            )
        except Exception as e:
            await query.message.answer(
                text=f"Не удалось загрузить видео: {str(e)}"
            )

async def search_handler(update: types.Message, context=None) -> None:
    """Обработчик для поиска товаров"""
    from config import MIN_SEARCH_LENGTH, MAX_SEARCH_RESULTS
    
    # Проверяем, это запрос на начало поиска или уже поисковый запрос
    if update.text == "🔍 Поиск":
        # Запрашиваем поисковый запрос
        await update.answer(
            "Введите название товара для поиска (минимум 3 символа).\n"
            "Формат: 🔍 Название товара"
        )
        return
    
    # Извлекаем поисковый запрос
    query_text = update.text[2:].strip()  # Убираем символ 🔍 и пробелы
    
    # Проверяем длину запроса
    if len(query_text) < MIN_SEARCH_LENGTH:
        await update.answer(
            f"Поисковый запрос должен содержать минимум {MIN_SEARCH_LENGTH} символа.\n"
            "Попробуйте снова. Формат: 🔍 Название товара"
        )
        return
    
    # Выполняем поиск
    products = DB_MODULE.search_products(query_text)
    
    if products:
        # Ограничиваем количество результатов
        products = products[:MAX_SEARCH_RESULTS]
        
        # Создаем список кнопок с результатами
        buttons = []
        for product in products:
            buttons.append([
                types.InlineKeyboardButton(text=product['name'], callback_data=f"product:{product['id']}")
            ])
        
        # Добавляем кнопку возврата
        buttons.append([
            types.InlineKeyboardButton(text="🔙 К категориям", callback_data="knowledge_base")
        ])
        
        await update.answer(
            f"Результаты поиска по запросу \"{query_text}\":",
            reply_markup=types.InlineKeyboardMarkup(inline_keyboard=buttons)
        )
    else:
        # Если ничего не найдено
        await update.answer(
            f"По запросу \"{query_text}\" ничего не найдено.",
            reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
                [types.InlineKeyboardButton(text="🔙 К категориям", callback_data="knowledge_base")]
            ])
        )
