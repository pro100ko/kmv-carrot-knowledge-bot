"""Test handlers for managing and taking tests."""

import logging
from typing import Optional, Dict, List
from datetime import datetime, timedelta

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from utils.keyboards import (
    get_test_keyboard,
    get_confirm_keyboard,
    get_back_keyboard,
    get_pagination_keyboard
)
from utils.db_pool import db_pool
from utils.metrics import metrics_collector
from config import ADMIN_IDS

router = Router()
logger = logging.getLogger(__name__)

class TestStates(StatesGroup):
    """States for test interactions."""
    browsing_tests = State()
    taking_test = State()
    answering_question = State()
    waiting_for_retry = State()

@router.message(Command("tests"))
@router.message(F.text == "📝 Тесты")
async def show_tests(message: Message, state: FSMContext):
    """Show available tests."""
    try:
        # Get available tests
        tests = await db_pool.fetchall(
            """
            SELECT t.*, p.name as product_name, c.name as category_name
            FROM tests t
            JOIN products p ON t.product_id = p.id
            JOIN categories c ON p.category_id = c.id
            WHERE t.is_active = 1
            ORDER BY c.name, p.name, t.name
            """
        )
        
        if not tests:
            await message.answer(
                "😔 Доступных тестов пока нет.",
                reply_markup=get_back_keyboard()
            )
            return
        
        # Group tests by category and product
        tests_by_category = {}
        for test in tests:
            category = test['category_name']
            product = test['product_name']
            
            if category not in tests_by_category:
                tests_by_category[category] = {}
            if product not in tests_by_category[category]:
                tests_by_category[category][product] = []
            
            tests_by_category[category][product].append(test)
        
        # Format tests message
        tests_text = "📝 Доступные тесты:\n\n"
        for category, products in tests_by_category.items():
            tests_text += f"📚 {category}\n"
            for product, product_tests in products.items():
                tests_text += f"\n📦 {product}:\n"
                for test in product_tests:
                    tests_text += f"• {test['name']}\n"
                    if test['description']:
                        tests_text += f"  {test['description']}\n"
                    if test['time_limit']:
                        tests_text += f"  ⏱ {test['time_limit']} мин.\n"
                    if test['passing_score']:
                        tests_text += f"  ✅ Проходной балл: {test['passing_score']}%\n"
        
        # Add pagination if needed
        page = 1
        items_per_page = 5
        total_pages = (len(tests) + items_per_page - 1) // items_per_page
        
        await message.answer(
            tests_text,
            reply_markup=get_pagination_keyboard(
                page,
                total_pages,
                "tests"
            )
        )
        await state.set_state(TestStates.browsing_tests)
        
        # Track metrics
        metrics_collector.increment_message_count()
        
    except Exception as e:
        logger.error(f"Error showing tests: {e}")
        await message.answer(
            "😔 Произошла ошибка при загрузке тестов. Попробуйте позже.",
            reply_markup=get_back_keyboard()
        )

@router.callback_query(F.data.startswith("test_"))
async def show_test_details(callback: CallbackQuery, state: FSMContext):
    """Show test details and start options."""
    try:
        test_id = int(callback.data.split("_")[1])
        is_admin = callback.from_user.id in ADMIN_IDS
        
        # Get test info
        test = await db_pool.fetchone(
            """
            SELECT t.*, p.name as product_name, c.name as category_name
            FROM tests t
            JOIN products p ON t.product_id = p.id
            JOIN categories c ON p.category_id = c.id
            WHERE t.id = ? AND t.is_active = 1
            """,
            (test_id,)
        )
        
        if not test:
            await callback.answer("Тест не найден")
            return
        
        # Check if user has already taken this test
        last_attempt = await db_pool.fetchone(
            """
            SELECT score, created_at
            FROM test_attempts
            WHERE user_id = ? AND test_id = ?
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (callback.from_user.id, test_id)
        )
        
        # Format test message
        test_text = f"📝 {test['name']}\n"
        test_text += f"📚 Категория: {test['category_name']}\n"
        test_text += f"📦 Товар: {test['product_name']}\n"
        
        if test['description']:
            test_text += f"\n📋 Описание:\n{test['description']}\n"
        
        if test['time_limit']:
            test_text += f"\n⏱ Время на прохождение: {test['time_limit']} мин.\n"
        
        if test['passing_score']:
            test_text += f"✅ Проходной балл: {test['passing_score']}%\n"
        
        if test['max_attempts']:
            test_text += f"🔄 Максимум попыток: {test['max_attempts']}\n"
        
        if last_attempt:
            test_text += f"\n📊 Последняя попытка:\n"
            test_text += f"• Результат: {last_attempt['score']}%\n"
            test_text += f"• Дата: {last_attempt['created_at']}\n"
        
        await callback.message.edit_text(
            test_text,
            reply_markup=get_test_keyboard(
                test_id,
                is_admin=is_admin
            )
        )
        
        # Update state
        await state.set_state(TestStates.browsing_tests)
        await state.update_data(current_test=test_id)
        
        # Track metrics
        metrics_collector.increment_message_count()
        
    except Exception as e:
        logger.error(f"Error showing test details: {e}")
        await callback.message.edit_text(
            "😔 Произошла ошибка при загрузке теста. Попробуйте позже.",
            reply_markup=get_back_keyboard()
        )

@router.callback_query(F.data.startswith("start_test_"))
async def start_test(callback: CallbackQuery, state: FSMContext):
    """Start taking a test."""
    try:
        test_id = int(callback.data.split("_")[2])
        
        # Get test info
        test = await db_pool.fetchone(
            """
            SELECT t.*, p.name as product_name
            FROM tests t
            JOIN products p ON t.product_id = p.id
            WHERE t.id = ? AND t.is_active = 1
            """,
            (test_id,)
        )
        
        if not test:
            await callback.answer("Тест не найден")
            return
        
        # Check if user has exceeded max attempts
        if test['max_attempts']:
            attempts_count = await db_pool.fetchone(
                """
                SELECT COUNT(*) as count
                FROM test_attempts
                WHERE user_id = ? AND test_id = ?
                """,
                (callback.from_user.id, test_id)
            )
            
            if attempts_count['count'] >= test['max_attempts']:
                await callback.message.edit_text(
                    "❌ Вы исчерпали все попытки прохождения этого теста.",
                    reply_markup=get_back_keyboard()
                )
                return
        
        # Get first question
        question = await db_pool.fetchone(
            """
            SELECT *
            FROM test_questions
            WHERE test_id = ?
            ORDER BY question_order
            LIMIT 1
            """,
            (test_id,)
        )
        
        if not question:
            await callback.message.edit_text(
                "❌ В тесте нет вопросов.",
                reply_markup=get_back_keyboard()
            )
            return
        
        # Start test attempt
        attempt_id = await db_pool.execute(
            """
            INSERT INTO test_attempts (user_id, test_id, started_at)
            VALUES (?, ?, ?)
            """,
            (callback.from_user.id, test_id, datetime.now())
        )
        
        # Format question message
        question_text = f"📝 Вопрос {question['question_order']}:\n\n"
        question_text += f"{question['question_text']}\n\n"
        
        if question['question_type'] == 'multiple_choice':
            options = question['options'].split('|')
            for i, option in enumerate(options, 1):
                question_text += f"{i}. {option}\n"
        
        await callback.message.edit_text(
            question_text,
            reply_markup=get_back_keyboard()
        )
        
        # Update state
        await state.set_state(TestStates.answering_question)
        await state.update_data(
            current_test=test_id,
            current_attempt=attempt_id,
            current_question=question['id'],
            question_order=question['question_order']
        )
        
        # Track metrics
        metrics_collector.increment_message_count()
        
    except Exception as e:
        logger.error(f"Error starting test: {e}")
        await callback.message.edit_text(
            "😔 Произошла ошибка при запуске теста. Попробуйте позже.",
            reply_markup=get_back_keyboard()
        )

@router.message(TestStates.answering_question)
async def process_answer(message: Message, state: FSMContext):
    """Process user's answer to a test question."""
    try:
        # Get current test state
        state_data = await state.get_data()
        test_id = state_data['current_test']
        attempt_id = state_data['current_attempt']
        current_question_id = state_data['current_question']
        question_order = state_data['question_order']
        
        # Get current question
        question = await db_pool.fetchone(
            "SELECT * FROM test_questions WHERE id = ?",
            (current_question_id,)
        )
        
        # Process answer
        answer = message.text.strip()
        is_correct = False
        
        if question['question_type'] == 'multiple_choice':
            try:
                answer_index = int(answer) - 1
                options = question['options'].split('|')
                if 0 <= answer_index < len(options):
                    is_correct = options[answer_index] == question['correct_answer']
            except ValueError:
                await message.answer(
                    "❌ Пожалуйста, введите номер правильного варианта ответа.",
                    reply_markup=get_back_keyboard()
                )
                return
        else:
            is_correct = answer.lower() == question['correct_answer'].lower()
        
        # Save answer
        await db_pool.execute(
            """
            INSERT INTO test_answers (
                attempt_id, question_id, user_answer, is_correct
            ) VALUES (?, ?, ?, ?)
            """,
            (attempt_id, current_question_id, answer, is_correct)
        )
        
        # Get next question
        next_question = await db_pool.fetchone(
            """
            SELECT *
            FROM test_questions
            WHERE test_id = ? AND question_order > ?
            ORDER BY question_order
            LIMIT 1
            """,
            (test_id, question_order)
        )
        
        if next_question:
            # Show next question
            question_text = f"📝 Вопрос {next_question['question_order']}:\n\n"
            question_text += f"{next_question['question_text']}\n\n"
            
            if next_question['question_type'] == 'multiple_choice':
                options = next_question['options'].split('|')
                for i, option in enumerate(options, 1):
                    question_text += f"{i}. {option}\n"
            
            await message.answer(
                question_text,
                reply_markup=get_back_keyboard()
            )
            
            # Update state
            await state.update_data(
                current_question=next_question['id'],
                question_order=next_question['question_order']
            )
            
        else:
            # Test completed, calculate score
            total_questions = await db_pool.fetchone(
                "SELECT COUNT(*) as count FROM test_questions WHERE test_id = ?",
                (test_id,)
            )
            
            correct_answers = await db_pool.fetchone(
                """
                SELECT COUNT(*) as count
                FROM test_answers
                WHERE attempt_id = ? AND is_correct = 1
                """,
                (attempt_id,)
            )
            
            score = (correct_answers['count'] / total_questions['count']) * 100
            
            # Update attempt with score
            await db_pool.execute(
                """
                UPDATE test_attempts
                SET completed_at = ?, score = ?
                WHERE id = ?
                """,
                (datetime.now(), score, attempt_id)
            )
            
            # Get test info for passing score
            test = await db_pool.fetchone(
                "SELECT passing_score FROM tests WHERE id = ?",
                (test_id,)
            )
            
            # Format completion message
            completion_text = "📝 Тест завершен!\n\n"
            completion_text += f"📊 Ваш результат: {score:.1f}%\n"
            
            if test['passing_score']:
                if score >= test['passing_score']:
                    completion_text += "✅ Поздравляем! Вы успешно прошли тест!\n"
                else:
                    completion_text += "❌ К сожалению, вы не набрали проходной балл.\n"
            
            await message.answer(
                completion_text,
                reply_markup=get_back_keyboard()
            )
            
            # Clear test state
            await state.clear()
        
        # Track metrics
        metrics_collector.increment_message_count()
        
    except Exception as e:
        logger.error(f"Error processing answer: {e}")
        await message.answer(
            "😔 Произошла ошибка при обработке ответа. Попробуйте позже.",
            reply_markup=get_back_keyboard()
        )
        await state.clear()

@router.callback_query(F.data == "back_to_tests")
async def back_to_tests(callback: CallbackQuery, state: FSMContext):
    """Return to tests list."""
    await state.clear()
    await show_tests(callback.message, state) 