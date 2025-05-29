from typing import Dict, List, Optional, Union, Any
from dataclasses import dataclass
from datetime import datetime
import re
from decimal import Decimal, InvalidOperation

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import (
    DEFAULT_TEST_PASSING_SCORE,
    DEFAULT_TEST_TIME_LIMIT,
    MAX_MESSAGE_LENGTH
)
from logging_config import admin_logger
from sqlite_db import db
from admin_panel import (
    is_admin,
    edit_message,
    format_admin_message,
    format_error_message,
    AdminTestCallback,
    truncate_message
)

# Create router for test management
router = Router()

# States for test forms
class TestForm(StatesGroup):
    name = State()
    description = State()
    passing_score = State()
    time_limit = State()
    questions = State()

class QuestionForm(StatesGroup):
    text = State()
    options = State()
    correct_option = State()

@dataclass
class TestValidation:
    """Test data validation results"""
    is_valid: bool
    errors: List[str]
    data: Optional[Dict[str, Any]] = None

@dataclass
class QuestionValidation:
    """Question data validation results"""
    is_valid: bool
    errors: List[str]
    data: Optional[Dict[str, Any]] = None

def validate_test_name(name: str) -> TestValidation:
    """Validate test name"""
    errors = []
    
    if not name:
        errors.append("Название теста не может быть пустым")
    elif len(name) < 2:
        errors.append("Название теста должно содержать минимум 2 символа")
    elif len(name) > 100:
        errors.append("Название теста не должно превышать 100 символов")
    elif not re.match(r'^[\w\s\-.,!?()]+$', name):
        errors.append("Название теста содержит недопустимые символы")
    
    return TestValidation(
        is_valid=len(errors) == 0,
        errors=errors,
        data={"name": name.strip()} if not errors else None
    )

def validate_test_description(description: str) -> TestValidation:
    """Validate test description"""
    errors = []
    
    if description and len(description) > 1000:
        errors.append("Описание теста не должно превышать 1000 символов")
    elif description and not re.match(r'^[\w\s\-.,!?()\n]+$', description):
        errors.append("Описание теста содержит недопустимые символы")
    
    return TestValidation(
        is_valid=len(errors) == 0,
        errors=errors,
        data={"description": description.strip()} if not errors else None
    )

def validate_passing_score(score: str) -> TestValidation:
    """Validate passing score"""
    errors = []
    
    if not score:
        errors.append("Проходной балл не может быть пустым")
    else:
        try:
            # Try to parse score as decimal
            score_decimal = Decimal(score.replace(',', '.'))
            if score_decimal < 0:
                errors.append("Проходной балл не может быть отрицательным")
            elif score_decimal > 100:
                errors.append("Проходной балл не может превышать 100")
            else:
                # Format score with 2 decimal places
                formatted_score = f"{score_decimal:.2f}"
                return TestValidation(
                    is_valid=True,
                    errors=[],
                    data={"passing_score": formatted_score}
                )
        except InvalidOperation:
            errors.append("Некорректный формат проходного балла")
    
    return TestValidation(
        is_valid=len(errors) == 0,
        errors=errors
    )

def validate_time_limit(time_limit: str) -> TestValidation:
    """Validate time limit"""
    errors = []
    
    if not time_limit:
        errors.append("Временной лимит не может быть пустым")
    else:
        try:
            # Try to parse time limit as integer
            minutes = int(time_limit)
            if minutes < 1:
                errors.append("Временной лимит должен быть не менее 1 минуты")
            elif minutes > 180:
                errors.append("Временной лимит не может превышать 180 минут")
            else:
                return TestValidation(
                    is_valid=True,
                    errors=[],
                    data={"time_limit": minutes}
                )
        except ValueError:
            errors.append("Некорректный формат временного лимита")
    
    return TestValidation(
        is_valid=len(errors) == 0,
        errors=errors
    )

def validate_question_text(text: str) -> QuestionValidation:
    """Validate question text"""
    errors = []
    
    if not text:
        errors.append("Текст вопроса не может быть пустым")
    elif len(text) < 5:
        errors.append("Текст вопроса должен содержать минимум 5 символов")
    elif len(text) > 500:
        errors.append("Текст вопроса не должен превышать 500 символов")
    elif not re.match(r'^[\w\s\-.,!?()\n]+$', text):
        errors.append("Текст вопроса содержит недопустимые символы")
    
    return QuestionValidation(
        is_valid=len(errors) == 0,
        errors=errors,
        data={"text": text.strip()} if not errors else None
    )

def validate_question_options(options: List[str]) -> QuestionValidation:
    """Validate question options"""
    errors = []
    
    if not options:
        errors.append("Варианты ответов не могут быть пустыми")
    elif len(options) < 2:
        errors.append("Должно быть минимум 2 варианта ответа")
    elif len(options) > 6:
        errors.append("Не может быть более 6 вариантов ответа")
    else:
        # Validate each option
        for i, option in enumerate(options, 1):
            if not option:
                errors.append(f"Вариант ответа {i} не может быть пустым")
            elif len(option) > 200:
                errors.append(f"Вариант ответа {i} не должен превышать 200 символов")
            elif not re.match(r'^[\w\s\-.,!?()]+$', option):
                errors.append(f"Вариант ответа {i} содержит недопустимые символы")
    
    return QuestionValidation(
        is_valid=len(errors) == 0,
        errors=errors,
        data={"options": options} if not errors else None
    )

def get_test_keyboard(
    test_id: int,
    page: int = 1,
    include_questions: bool = True
) -> InlineKeyboardMarkup:
    """Generate keyboard for test view"""
    builder = InlineKeyboardBuilder()
    
    # Get test data
    test = db.get_test(test_id)
    if not test:
        raise ValueError("Тест не найден")
    
    # Add question buttons if requested
    if include_questions:
        questions = db.get_test_questions(test_id)
        for question in questions[:5]:  # Show first 5 questions
            builder.button(
                text=f"❓ {question['text'][:30]}...",
                callback_data=f"question:{question['id']}"
            )
    
    # Add navigation buttons
    if include_questions and len(questions) > 5:
        builder.button(
            text="📝 Все вопросы",
            callback_data=f"test_questions:{test_id}"
        )
    
    # Add admin buttons if user is admin
    if is_admin(test.get('created_by')):
        builder.button(
            text="✏️ Редактировать",
            callback_data=AdminTestCallback(
                action="edit",
                test_id=test_id
            ).pack()
        )
        builder.button(
            text="❓ Управление вопросами",
            callback_data=AdminTestCallback(
                action="manage_questions",
                test_id=test_id
            ).pack()
        )
        builder.button(
            text="✅ Активировать" if not test['is_active'] else "❌ Деактивировать",
            callback_data=AdminTestCallback(
                action="toggle_active",
                test_id=test_id
            ).pack()
        )
        builder.button(
            text="🗑 Удалить",
            callback_data=AdminTestCallback(
                action="delete",
                test_id=test_id
            ).pack()
        )
    
    # Add back button
    builder.button(
        text="◀️ Назад",
        callback_data="testing"
    )
    
    # Adjust layout
    builder.adjust(1)  # One button per row
    return builder.as_markup()

def format_test_message(test: Dict[str, Any]) -> str:
    """Format test message with proper HTML formatting"""
    # Format basic info
    message = (
        f"<b>{test['name']}</b>\n\n"
        f"{test['description'] or 'Нет описания'}\n\n"
        f"<b>Проходной балл:</b> {test['passing_score']}%\n"
        f"<b>Временной лимит:</b> {test['time_limit']} мин.\n"
        f"<b>Статус:</b> {'✅ Активен' if test['is_active'] else '❌ Неактивен'}\n\n"
    )
    
    # Add question count
    questions = db.get_test_questions(test['id'])
    message += f"<b>Вопросов:</b> {len(questions)}\n\n"
    
    # Add statistics if available
    stats = get_test_stats(test['id'])
    if stats:
        message += (
            f"<b>Статистика:</b>\n"
            f"• Всего попыток: {stats['total_attempts']}\n"
            f"• Успешных: {stats['successful_attempts']}\n"
            f"• Средний балл: {stats['average_score']:.1f}%\n"
            f"• Среднее время: {stats['average_time']:.1f} мин.\n\n"
        )
    
    # Add creation info
    message += (
        f"<i>Создано: {test['created_at']}\n"
        f"Последнее обновление: {test['updated_at']}</i>"
    )
    
    return truncate_message(message)

def search_tests(query: str) -> List[Dict[str, Any]]:
    """Search tests by name or description"""
    if not query:
        return []
    
    # Get all tests
    tests = db.get_tests(include_inactive=True)
    
    # Search in name and description
    query = query.lower()
    results = []
    
    for test in tests:
        if (query in test['name'].lower() or
            (test['description'] and query in test['description'].lower())):
            results.append(test)
    
    return results

def get_test_stats(test_id: int) -> Dict[str, Any]:
    """Get test statistics"""
    test = db.get_test(test_id)
    if not test:
        raise ValueError("Тест не найден")
    
    # Get all attempts
    attempts = db.get_test_attempts(test_id)
    total_attempts = len(attempts)
    
    if not total_attempts:
        return None
    
    # Calculate statistics
    successful_attempts = sum(1 for a in attempts if a['score'] >= float(test['passing_score']))
    total_score = sum(a['score'] for a in attempts)
    total_time = sum(a['time_taken'] for a in attempts)
    
    return {
        "test_id": test_id,
        "name": test['name'],
        "total_attempts": total_attempts,
        "successful_attempts": successful_attempts,
        "success_rate": (successful_attempts / total_attempts * 100) if total_attempts else 0,
        "average_score": total_score / total_attempts if total_attempts else 0,
        "average_time": total_time / total_attempts if total_attempts else 0,
        "created_at": test['created_at'],
        "updated_at": test['updated_at']
    }

# Command handlers
@router.message(Command("tests"))
async def list_tests_command(message: Message) -> None:
    """Handle /tests command"""
    try:
        tests = db.get_tests()
        
        if not tests:
            await message.answer(
                "Тесты пока не добавлены.",
                parse_mode="HTML"
            )
            return
        
        text = format_admin_message(
            title="📝 Тесты",
            content="\n\n".join(
                f"• {test['name']}\n"
                f"  {test['description'] or 'Нет описания'}\n"
                f"  Вопросов: {len(db.get_test_questions(test['id']))}\n"
                f"  Проходной балл: {test['passing_score']}%"
                for test in tests
            )
        )
        
        # Create keyboard with test buttons
        keyboard = InlineKeyboardBuilder()
        for test in tests:
            keyboard.button(
                text=test['name'],
                callback_data=f"test:{test['id']}"
            )
        keyboard.adjust(1)
        
        await message.answer(text, reply_markup=keyboard.as_markup())
        
    except Exception as e:
        admin_logger.error(f"Error in list tests command: {e}")
        await message.answer(
            format_error_message(e),
            parse_mode="HTML"
        )

# Callback handlers
@router.callback_query(F.data.startswith("test:"))
async def test_callback(callback: CallbackQuery) -> None:
    """Handle test selection callback"""
    try:
        test_id = int(callback.data.split(":")[1])
        test = db.get_test(test_id)
        
        if not test:
            raise ValueError("Тест не найден")
        
        # Update test views
        db.update_test(test_id, {"views": test.get("views", 0) + 1})
        
        # Format and send message
        text = format_test_message(test)
        keyboard = get_test_keyboard(test_id)
        
        await edit_message(callback, text, keyboard)
        
    except Exception as e:
        admin_logger.error(f"Error in test callback: {e}")
        await callback.answer(
            format_error_message(e),
            show_alert=True
        )

@router.callback_query(F.data.startswith("test_questions:"))
async def test_questions_callback(callback: CallbackQuery) -> None:
    """Handle test questions list callback"""
    try:
        test_id = int(callback.data.split(":")[1])
        test = db.get_test(test_id)
        
        if not test:
            raise ValueError("Тест не найден")
        
        questions = db.get_test_questions(test_id)
        
        if not questions:
            await callback.answer(
                "В этом тесте пока нет вопросов.",
                show_alert=True
            )
            return
        
        text = format_admin_message(
            title=f"❓ Вопросы теста {test['name']}",
            content="\n\n".join(
                f"• {q['text']}\n"
                f"  Варианты ответов:\n"
                + "\n".join(f"    {chr(65+i)}. {opt}" for i, opt in enumerate(q['options']))
                + f"\n  Правильный ответ: {chr(65+q['correct_option'])}"
                for q in questions
            )
        )
        
        # Create keyboard with question buttons
        keyboard = InlineKeyboardBuilder()
        for question in questions:
            keyboard.button(
                text=f"❓ {question['text'][:30]}...",
                callback_data=f"question:{question['id']}"
            )
        keyboard.button(
            text="◀️ Назад к тесту",
            callback_data=f"test:{test_id}"
        )
        keyboard.adjust(1)
        
        await edit_message(callback, text, keyboard.as_markup())
        
    except Exception as e:
        admin_logger.error(f"Error in test questions callback: {e}")
        await callback.answer(
            format_error_message(e),
            show_alert=True
        )

# Form handlers
@router.message(TestForm.name)
async def process_test_name(message: Message, state: FSMContext) -> None:
    """Process test name input"""
    try:
        # Validate name
        validation = validate_test_name(message.text)
        if not validation.is_valid:
            await message.answer(
                format_admin_message(
                    title="❌ Ошибка валидации",
                    content="\n".join(validation.errors)
                )
            )
            return
        
        # Save name and request description
        await state.update_data(name=validation.data["name"])
        await state.set_state(TestForm.description)
        
        await message.answer(
            format_admin_message(
                title="📝 Создание теста",
                content="Введите описание теста (или отправьте '-' для пропуска):"
            )
        )
        
    except Exception as e:
        admin_logger.error(f"Error in process test name: {e}")
        await message.answer(
            format_error_message(e),
            parse_mode="HTML"
        )
        await state.clear()

@router.message(TestForm.description)
async def process_test_description(message: Message, state: FSMContext) -> None:
    """Process test description input"""
    try:
        # Get saved data
        data = await state.get_data()
        
        # Validate description
        description = None if message.text == "-" else message.text
        validation = validate_test_description(description) if description else TestValidation(True, [])
        
        if not validation.is_valid:
            await message.answer(
                format_admin_message(
                    title="❌ Ошибка валидации",
                    content="\n".join(validation.errors)
                )
            )
            return
        
        # Save description and request passing score
        await state.update_data(description=validation.data["description"] if description else None)
        await state.set_state(TestForm.passing_score)
        
        await message.answer(
            format_admin_message(
                title="📝 Создание теста",
                content=f"Введите проходной балл (от 0 до 100, по умолчанию {DEFAULT_TEST_PASSING_SCORE}%):"
            )
        )
        
    except Exception as e:
        admin_logger.error(f"Error in process test description: {e}")
        await message.answer(
            format_error_message(e),
            parse_mode="HTML"
        )
        await state.clear()

@router.message(TestForm.passing_score)
async def process_passing_score(message: Message, state: FSMContext) -> None:
    """Process passing score input"""
    try:
        # Get saved data
        data = await state.get_data()
        
        # Handle default value
        if message.text == "-":
            score = str(DEFAULT_TEST_PASSING_SCORE)
        else:
            score = message.text
        
        # Validate score
        validation = validate_passing_score(score)
        if not validation.is_valid:
            await message.answer(
                format_admin_message(
                    title="❌ Ошибка валидации",
                    content="\n".join(validation.errors)
                )
            )
            return
        
        # Save score and request time limit
        await state.update_data(passing_score=validation.data["passing_score"])
        await state.set_state(TestForm.time_limit)
        
        await message.answer(
            format_admin_message(
                title="📝 Создание теста",
                content=f"Введите временной лимит в минутах (от 1 до 180, по умолчанию {DEFAULT_TEST_TIME_LIMIT}):"
            )
        )
        
    except Exception as e:
        admin_logger.error(f"Error in process passing score: {e}")
        await message.answer(
            format_error_message(e),
            parse_mode="HTML"
        )
        await state.clear()

@router.message(TestForm.time_limit)
async def process_time_limit(message: Message, state: FSMContext) -> None:
    """Process time limit input"""
    try:
        # Get saved data
        data = await state.get_data()
        
        # Handle default value
        if message.text == "-":
            time_limit = str(DEFAULT_TEST_TIME_LIMIT)
        else:
            time_limit = message.text
        
        # Validate time limit
        validation = validate_time_limit(time_limit)
        if not validation.is_valid:
            await message.answer(
                format_admin_message(
                    title="❌ Ошибка валидации",
                    content="\n".join(validation.errors)
                )
            )
            return
        
        # Create test
        test_data = {
            "name": data["name"],
            "description": data["description"],
            "passing_score": data["passing_score"],
            "time_limit": validation.data["time_limit"],
            "created_by": message.from_user.id,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "is_active": True
        }
        
        test_id = db.add_test(test_data)
        
        # Send success message
        test = db.get_test(test_id)
        text = format_admin_message(
            title="✅ Тест создан",
            content=format_test_message(test)
        )
        keyboard = get_test_keyboard(test_id)
        
        await message.answer(text, reply_markup=keyboard)
        await state.clear()
        
    except Exception as e:
        admin_logger.error(f"Error in process time limit: {e}")
        await message.answer(
            format_error_message(e),
            parse_mode="HTML"
        )
        await state.clear()

# Search handler
@router.message(Command("search_test"))
async def search_test_command(message: Message) -> None:
    """Handle /search_test command"""
    try:
        # Get search query
        query = message.text.replace("/search_test", "").strip()
        
        if not query:
            await message.answer(
                format_admin_message(
                    title="🔍 Поиск тестов",
                    content="Используйте команду в формате:\n/search_test <запрос>"
                )
            )
            return
        
        # Search tests
        results = search_tests(query)
        
        if not results:
            await message.answer(
                format_admin_message(
                    title="🔍 Поиск тестов",
                    content=f"По запросу '{query}' ничего не найдено."
                )
            )
            return
        
        # Format results
        text = format_admin_message(
            title=f"🔍 Результаты поиска: {query}",
            content="\n\n".join(
                f"• {test['name']}\n"
                f"  {test['description'] or 'Нет описания'}\n"
                f"  Вопросов: {len(db.get_test_questions(test['id']))}\n"
                f"  Проходной балл: {test['passing_score']}%"
                for test in results
            )
        )
        
        # Create keyboard with test buttons
        keyboard = InlineKeyboardBuilder()
        for test in results:
            keyboard.button(
                text=test['name'],
                callback_data=f"test:{test['id']}"
            )
        keyboard.adjust(1)
        
        await message.answer(text, reply_markup=keyboard.as_markup())
        
    except Exception as e:
        admin_logger.error(f"Error in search test command: {e}")
        await message.answer(
            format_error_message(e),
            parse_mode="HTML"
        ) 