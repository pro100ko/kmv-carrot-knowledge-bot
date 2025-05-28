import logging
from typing import Dict, Optional
from aiogram import types
from aiogram.enums import ParseMode
from sqlite_db import db  # Import the database instance
from utils.keyboards import (
    get_tests_keyboard,
    get_test_question_keyboard,
    get_test_result_keyboard,
    get_back_to_tests_keyboard
)
from utils.message_utils import safe_edit_message

logger = logging.getLogger(__name__)

# Глобальный словарь для хранения текущих тестовых сессий пользователей
user_test_sessions: Dict[int, Dict] = {}

class TestSessionManager:
    """Класс для управления тестовыми сессиями"""
    
    @staticmethod
    def start_session(user_id: int, test_id: str) -> Dict:
        """Создает новую тестовую сессию"""
        user_test_sessions[user_id] = {
            'test_id': test_id,
            'current_question': 0,
            'answers': [],
            'score': 0,
            'start_time': None  # Можно добавить время начала
        }
        return user_test_sessions[user_id]
    
    @staticmethod
    def get_session(user_id: int) -> Optional[Dict]:
        """Возвращает текущую сессию пользователя"""
        return user_test_sessions.get(user_id)
    
    @staticmethod
    def end_session(user_id: int) -> None:
        """Завершает сессию пользователя"""
        if user_id in user_test_sessions:
            del user_test_sessions[user_id]

async def testing_handler(
    update: types.Message | types.CallbackQuery,
    context=None
) -> None:
    """Главный обработчик системы тестирования"""
    try:
        tests = db.get_tests_list()  # Use db instance
        if not tests:
            await handle_no_tests(update)
            return
        
        text = "📝 <b>Доступные тесты</b>\n\nВыберите тест для прохождения:"
        keyboard = get_tests_keyboard(tests)
        
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
            
    except Exception as e:
        logger.error(f"Error in testing handler: {e}")
        await handle_error(update)

async def test_selection_handler(
    query: types.CallbackQuery,
    context=None
) -> None:
    """Обработчик выбора теста"""
    await query.answer()
    test_id = query.data.split(':')[1]
    test = db.get_test(test_id)  # Use db instance
    
    if not test:
        await safe_edit_message(
            message=query.message,
            text="⚠️ Тест не найден",
            reply_markup=get_back_to_tests_keyboard()
        )
        return
    
    # Инициализируем сессию
    session = TestSessionManager.start_session(query.from_user.id, test_id)
    
    # Формируем информацию о тесте
    test_info = [
        f"📚 <b>{test['title']}</b>",
        f"\n\n{test.get('description', '')}",
        f"\n\n🔢 Количество вопросов: {len(test['questions'])}",
        f"\n📊 Проходной балл: {test['passing_score']}%",
        "\n\nНажмите кнопку ниже, чтобы начать тестирование."
    ]
    
    await safe_edit_message(
        message=query.message,
        text="".join(test_info),
        parse_mode=ParseMode.HTML,
        reply_markup=types.InlineKeyboardMarkup(
            inline_keyboard=[[
                types.InlineKeyboardButton(
                    text="▶️ Начать тест",
                    callback_data=f"test_question:{test_id}:start"
                )
            ]]
        )
    )

async def test_question_handler(
    query: types.CallbackQuery,
    context=None
) -> None:
    """Обработчик вопросов теста"""
    await query.answer()
    user_id = query.from_user.id
    parts = query.data.split(':')
    test_id = parts[1]
    action = parts[2]
    
    session = TestSessionManager.get_session(user_id)
    if not session or session['test_id'] != test_id:
        await handle_session_expired(query)
        return
    
    test = db.get_test(test_id)  # Use db instance
    if not test:
        await handle_test_not_found(query)
        return
    
    # Обработка ответа пользователя
async def test_answer_handler(query: CallbackQuery):
    _, test_id, question_idx, answer_idx = query.data.split(':')
    session = TestSessionManager.get_session(query.from_user.id)
    if not session:
        await query.answer("Сессия истекла")
        return
    
    question = get_question(test_id, question_idx)
    if not question:
        await query.answer("Вопрос не найден")
        return
    
    session['answers'].append({
        'question_idx': question_idx,
        'answer_idx': answer_idx,
        'is_correct': answer_idx == question['correct']
    })
    
    # Проверка завершения теста
    if session['current_question'] >= len(test['questions']):
        await finish_test_session(query, session, test)
        return
    
    # Отображение текущего вопроса
    question = test['questions'][session['current_question']]
    question_text = (
        f"❓ <b>Вопрос {session['current_question']+1}/{len(test['questions'])}</b>\n\n"
        f"{question['text']}"
    )
    
    await safe_edit_message(
        message=query.message,
        text=question_text,
        parse_mode=ParseMode.HTML,
        reply_markup=get_test_question_keyboard(
            session['current_question'],
            question['options'],
            test_id
        )
    )

async def test_result_handler(
    query: types.CallbackQuery,
    context=None
) -> None:
    """Обработчик результатов теста"""
    await query.answer()
    user_id = query.from_user.id
    session = TestSessionManager.get_session(user_id)
    
    if not session:
        await handle_session_expired(query)
        return
    
    test = db.get_test(session['test_id'])
    if not test:
        await handle_test_not_found(query)
        return
    
    score = session['score']
    max_score = len(test['questions'])
    percentage = (score / max_score) * 100
    passed = percentage >= test['passing_score']
    
    result_text = [
        f"📊 <b>Результаты теста \"{test['title']}\"</b>",
        f"\n\n✅ Правильных ответов: {score}/{max_score} ({percentage:.1f}%)",
        f"\n🎯 Проходной балл: {test['passing_score']}%",
        "\n\n🎉 <b>Тест пройден!</b>" if passed else "\n\n❌ <b>Тест не пройден</b>"
    ]
    
    # Показ истории попыток
    attempts = get_test_attempts(user_id, session['test_id'])
    if attempts:
        result_text.append("\n\n📅 Ваши предыдущие попытки:")
        for idx, attempt in enumerate(attempts[:3], 1):  # Показываем последние 3 попытки
            attempt_percent = (attempt['score'] / attempt['max_score']) * 100
            result_text.append(
                f"\n{idx}. {attempt['score']}/{attempt['max_score']} ({attempt_percent:.1f}%) - "
                f"{'✅' if attempt_percent >= test['passing_score'] else '❌'}"
            )
    
    TestSessionManager.end_session(user_id)
    
    await safe_edit_message(
        message=query.message,
        text="".join(result_text),
        parse_mode=ParseMode.HTML,
        reply_markup=get_test_result_keyboard(test_id, passed)
    )

async def finish_test_session(
    query: types.CallbackQuery,
    session: Dict,
    test: Dict
) -> None:
    """Завершает тестовую сессию и сохраняет результаты"""
    attempt_data = {
        'user_id': str(query.from_user.id),
        'test_id': session['test_id'],
        'score': session['score'],
        'max_score': len(test['questions']),
        'answers': session['answers'],
        'completed': True
    }
    
    if not save_test_attempt(attempt_data):
        logger.error(f"Failed to save test attempt for user {query.from_user.id}")
    
    await safe_edit_message(
        message=query.message,
        text="📝 Подсчет результатов...",
        reply_markup=None
    )
    await test_result_handler(query)

async def handle_no_tests(target: types.Message | types.CallbackQuery) -> None:
    """Обработчик отсутствия тестов"""
    text = "ℹ️ В данный момент нет доступных тестов."
    if isinstance(target, types.CallbackQuery):
        await safe_edit_message(
            message=target.message,
            text=text,
            reply_markup=get_back_to_tests_keyboard()
        )
        await target.answer()
    else:
        await target.answer(text)

async def handle_session_expired(query: types.CallbackQuery) -> None:
    """Обработчик истекшей сессии"""
    await safe_edit_message(
        message=query.message,
        text="⚠️ Ваша тестовая сессия истекла. Пожалуйста, начните заново.",
        reply_markup=get_back_to_tests_keyboard()
    )

async def handle_test_not_found(query: types.CallbackQuery) -> None:
    """Обработчик отсутствия теста"""
    await safe_edit_message(
        message=query.message,
        text="⚠️ Тест не найден. Возможно, он был удален.",
        reply_markup=get_back_to_tests_keyboard()
    )

async def handle_error(target: types.Message | types.CallbackQuery) -> None:
    """Обработчик ошибок"""
    text = "⚠️ Произошла ошибка при обработке теста. Пожалуйста, попробуйте позже."
    if isinstance(target, types.CallbackQuery):
        await safe_edit_message(
            message=target.message,
            text=text,
            reply_markup=get_back_to_tests_keyboard()
        )
        await target.answer()
    else:
        await target.answer(text)
