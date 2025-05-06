
import React from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

const CodeExample = () => {
  return (
    <section className="py-16 bg-gray-50">
      <div className="container mx-auto px-4">
        <h2 className="text-3xl font-bold text-center mb-8">
          Структура кода телеграм-бота
        </h2>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          <Card>
            <CardHeader>
              <CardTitle>handlers/knowledge_base.py</CardTitle>
              <CardDescription>Управление базой знаний</CardDescription>
            </CardHeader>
            <CardContent>
              <pre className="bg-gray-100 p-4 rounded-md overflow-x-auto text-xs">
{`from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
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
`}
              </pre>
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>handlers/testing.py</CardTitle>
              <CardDescription>Система тестирования</CardDescription>
            </CardHeader>
            <CardContent>
              <pre className="bg-gray-100 p-4 rounded-md overflow-x-auto text-xs">
{`from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

import firebase_db
from utils.keyboards import get_tests_keyboard, get_test_question_keyboard, get_test_result_keyboard

# Глобальный словарь для хранения текущих тестовых сессий пользователей
user_test_sessions = {}

async def testing_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик для системы тестирования"""
    query = update.callback_query
    
    # Получаем доступные тесты из Firebase
    tests = firebase_db.get_tests_list()
    
    if query:
        await query.answer()
        await query.edit_message_text(
            text="Выберите тест для проверки знаний:",
            reply_markup=get_tests_keyboard(tests)
        )
    else:
        await update.message.reply_text(
            text="Выберите тест для проверки знаний:",
            reply_markup=get_tests_keyboard(tests)
        )

async def test_selection_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик для выбора теста"""
    query = update.callback_query
    await query.answer()
    
    # Получаем ID теста из callback_data
    test_id = query.data.split(':')[1]
    
    # Получаем информацию о тесте
    test = firebase_db.get_test(test_id)
    
    if not test:
        await query.edit_message_text(
            text="Тест не найден.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 К списку тестов", callback_data="testing")]
            ])
        )
        return
    
    # Создаем новую тестовую сессию для пользователя
    user_id = update.effective_user.id
    user_test_sessions[user_id] = {
        'test_id': test_id,
        'current_question': 0,
        'answers': [],
        'score': 0
    }
    
    # Отправляем информацию о тесте
    test_info = f"<b>{test['title']}</b>\n\n"
    test_info += f"{test.get('description', '')}\n\n"
    test_info += f"Тест содержит {len(test['questions'])} вопросов.\n"
    test_info += f"Для успешного прохождения нужно набрать минимум {test['passing_score']}% правильных ответов.\n\n"
    test_info += "Нажмите на кнопку ниже, чтобы начать тестирование."
    
    await query.edit_message_text(
        text=test_info,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("▶️ Начать тестирование", callback_data=f"test_question:{test_id}:start")]
        ])
    )

async def test_question_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик для вопросов теста"""
    query = update.callback_query
    await query.answer()
    
    # Получаем информацию из callback_data
    parts = query.data.split(':')
    test_id = parts[1]
    
    # Получаем пользовательскую сессию
    user_id = update.effective_user.id
    if user_id not in user_test_sessions:
        # Если сессии нет, возвращаемся к выбору теста
        await query.edit_message_text(
            text="Сессия тестирования истекла. Пожалуйста, начните заново.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 К списку тестов", callback_data="testing")]
            ])
        )
        return
    
    session = user_test_sessions[user_id]
    
    # Получаем информацию о тесте
    test = firebase_db.get_test(test_id)
    
    if not test:
        await query.edit_message_text(
            text="Тест не найден.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 К списку тестов", callback_data="testing")]
            ])
        )
        return
    
    # Если это начало теста или ответ на вопрос
    if parts[2] == 'start':
        # Начинаем тест с первого вопроса
        session['current_question'] = 0
        session['answers'] = []
    else:
        # Обрабатываем ответ пользователя
        question_idx = int(parts[2])
        answer_idx = int(parts[3])
        
        # Проверяем правильность ответа
        is_correct = (answer_idx == test['questions'][question_idx]['correct_option'])
        
        # Сохраняем ответ
        session['answers'].append({
            'question_id': question_idx,
            'selected_option': answer_idx,
            'is_correct': is_correct
        })
        
        # Увеличиваем счетчик правильных ответов, если ответ верный
        if is_correct:
            session['score'] += 1
        
        # Переходим к следующему вопросу
        session['current_question'] = question_idx + 1
    
    # Проверяем, завершен ли тест
    if session['current_question'] >= len(test['questions']):
        # Тест завершен, сохраняем результаты
        attempt_data = {
            'user_id': str(user_id),
            'test_id': test_id,
            'score': session['score'],
            'max_score': len(test['questions']),
            'answers': session['answers'],
            'completed': True
        }
        attempt_id = firebase_db.save_test_attempt(attempt_data)
        
        # Перенаправляем к результатам теста
        await query.edit_message_text(
            text="Тест завершен. Расчет результатов...",
            reply_markup=None
        )
        
        await test_result_handler(update, context)
        return
    
    # Отображаем текущий вопрос
    current_q = test['questions'][session['current_question']]
    question_text = f"<b>Вопрос {session['current_question']+1} из {len(test['questions'])}</b>\n\n"
    question_text += current_q['text']
    
    await query.edit_message_text(
        text=question_text,
        parse_mode=ParseMode.HTML,
        reply_markup=get_test_question_keyboard(
            session['current_question'], 
            current_q['options'], 
            test_id
        )
    )

async def test_result_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик для результатов теста"""
    # Проверяем, это callback или продолжение после завершения теста
    query = None
    if update.callback_query:
        query = update.callback_query
        await query.answer()
    
    # Получаем пользовательскую сессию
    user_id = update.effective_user.id
    if user_id not in user_test_sessions:
        # Если сессии нет, возвращаемся к выбору теста
        message_text = "Сессия тестирования истекла. Пожалуйста, начните заново."
        if query:
            await query.edit_message_text(
                text=message_text,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 К списку тестов", callback_data="testing")]
                ])
            )
        else:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=message_text,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 К списку тестов", callback_data="testing")]
                ])
            )
        return
    
    session = user_test_sessions[user_id]
    
    # Получаем информацию о тесте
    test = firebase_db.get_test(session['test_id'])
    
    if not test:
        message_text = "Информация о тесте не найдена."
        if query:
            await query.edit_message_text(
                text=message_text,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 К списку тестов", callback_data="testing")]
                ])
            )
        else:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=message_text,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 К списку тестов", callback_data="testing")]
                ])
            )
        return
    
    # Рассчитываем результат
    score = session['score']
    max_score = len(test['questions'])
    percentage = (score / max_score) * 100
    passed = percentage >= test['passing_score']
    
    # Создаем текст с результатами
    result_text = f"<b>Результаты теста \"{test['title']}\"</b>\n\n"
    result_text += f"Правильных ответов: {score} из {max_score} ({percentage:.1f}%)\n"
    result_text += f"Проходной балл: {test['passing_score']}%\n\n"
    
    if passed:
        result_text += "🎉 <b>Поздравляем! Вы успешно прошли тест.</b>"
    else:
        result_text += "❌ <b>К сожалению, тест не пройден.</b> Попробуйте еще раз."
    
    # Очищаем сессию пользователя
    del user_test_sessions[user_id]
    
    # Отправляем результаты
    if query:
        await query.edit_message_text(
            text=result_text,
            parse_mode=ParseMode.HTML,
            reply_markup=get_test_result_keyboard()
        )
    else:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=result_text,
            parse_mode=ParseMode.HTML,
            reply_markup=get_test_result_keyboard()
        )
`}
              </pre>
            </CardContent>
          </Card>
        </div>
      </div>
    </section>
  );
};

export default CodeExample;
