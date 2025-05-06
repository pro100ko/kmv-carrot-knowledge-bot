
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
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
