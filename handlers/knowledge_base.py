
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

import firebase_db
from utils.keyboards import get_categories_keyboard, get_products_keyboard, get_product_navigation_keyboard

# Глобальный словарь для отслеживания индекса текущего изображения продукта
product_image_indices = {}

async def knowledge_base_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик для базы знаний"""
    # Определяем, пришел запрос из inline кнопки или обычного сообщения
    query = update.callback_query
    
    # Получаем категории из Firebase
    categories = firebase_db.get_categories()
    
    if query:
        # Отправляем сообщение с категориями
        await query.answer()
        await query.edit_message_text(
            text="Выберите категорию товаров:",
            reply_markup=get_categories_keyboard(categories)
        )
    else:
        # Если это обычное сообщение, отправляем новое
        await update.message.reply_text(
            text="Выберите категорию товаров:",
            reply_markup=get_categories_keyboard(categories)
        )

async def category_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик для выбора категории"""
    query = update.callback_query
    await query.answer()
    
    # Получаем ID категории из callback_data
    category_id = query.data.split(':')[1]
    
    # Получаем продукты для выбранной категории
    products = firebase_db.get_products_by_category(category_id)
    
    # Если продукты есть, отправляем их список
    if products:
        # Получаем информацию о выбранной категории
        categories = firebase_db.get_categories()
        selected_category = next((c for c in categories if c['id'] == category_id), None)
        
        category_name = selected_category['name'] if selected_category else "Категория"
        
        await query.edit_message_text(
            text=f"Товары в категории \"{category_name}\":",
            reply_markup=get_products_keyboard(products, category_id)
        )
    else:
        # Если продуктов нет, сообщаем об этом
        await query.edit_message_text(
            text="В этой категории пока нет товаров.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Назад к категориям", callback_data="knowledge_base")]
            ])
        )

async def product_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик для просмотра продукта"""
    query = update.callback_query
    await query.answer()
    
    # Проверяем, это запрос на просмотр продукта или навигация между фото
    parts = query.data.split(':')
    command = parts[0]
    product_id = parts[1]
    
    # Получаем информацию о продукте
    product = firebase_db.get_product(product_id)
    
    if not product:
        await query.edit_message_text(
            text="Товар не найден.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Назад к категориям", callback_data="knowledge_base")]
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
    
    # Отправляем фото с подписью, если оно есть
    if product.get('image_urls') and len(product['image_urls']) > 0:
        # Получаем URL текущего изображения
        image_url = product['image_urls'][current_index]
        
        # Создаем клавиатуру для навигации
        keyboard = get_product_navigation_keyboard(product_id, product['category_id'])
        
        # Отправляем фото
        await query.edit_message_text(
            text=product_info,
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard
        )
        
        try:
            # Пытаемся отправить изображение
            await context.bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=image_url,
                reply_markup=keyboard
            )
        except Exception as e:
            # Если не удалось отправить изображение, сообщаем об ошибке
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"Не удалось загрузить изображение: {str(e)}",
                reply_markup=keyboard
            )
    else:
        # Если изображений нет, отправляем только текст
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 К списку товаров", callback_data=f"back_to_products:{product['category_id']}")]
        ])
        
        await query.edit_message_text(
            text=product_info,
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard
        )
    
    # Если есть видео, отправляем его в отдельном сообщении
    if product.get('video_url'):
        try:
            await context.bot.send_video(
                chat_id=update.effective_chat.id,
                video=product['video_url'],
                caption="Видео о товаре"
            )
        except Exception as e:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"Не удалось загрузить видео: {str(e)}"
            )

async def search_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик для поиска товаров"""
    from config import MIN_SEARCH_LENGTH, MAX_SEARCH_RESULTS
    
    # Проверяем, это запрос на начало поиска или уже поисковый запрос
    if update.message.text == "🔍 Поиск":
        # Запрашиваем поисковый запрос
        await update.message.reply_text(
            "Введите название товара для поиска (минимум 3 символа).\n"
            "Формат: 🔍 Название товара"
        )
        return
    
    # Извлекаем поисковый запрос
    query_text = update.message.text[2:].strip()  # Убираем символ 🔍 и пробелы
    
    # Проверяем длину запроса
    if len(query_text) < MIN_SEARCH_LENGTH:
        await update.message.reply_text(
            f"Поисковый запрос должен содержать минимум {MIN_SEARCH_LENGTH} символа.\n"
            "Попробуйте снова. Формат: 🔍 Название товара"
        )
        return
    
    # Выполняем поиск
    products = firebase_db.search_products(query_text)
    
    if products:
        # Ограничиваем количество результатов
        products = products[:MAX_SEARCH_RESULTS]
        
        # Создаем список кнопок с результатами
        buttons = []
        for product in products:
            buttons.append([
                InlineKeyboardButton(product['name'], callback_data=f"product:{product['id']}")
            ])
        
        # Добавляем кнопку возврата
        buttons.append([
            InlineKeyboardButton("🔙 К категориям", callback_data="knowledge_base")
        ])
        
        await update.message.reply_text(
            f"Результаты поиска по запросу \"{query_text}\":",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    else:
        # Если ничего не найдено
        await update.message.reply_text(
            f"По запросу \"{query_text}\" ничего не найдено.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 К категориям", callback_data="knowledge_base")]
            ])
        )
