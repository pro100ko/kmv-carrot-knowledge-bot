from typing import Dict, List, Optional, Union, Any
from dataclasses import dataclass
from datetime import datetime
import re
from decimal import Decimal, InvalidOperation
import logging
from enum import Enum

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import (
    DEFAULT_TEST_PASSING_SCORE,
    DEFAULT_TEST_TIME_LIMIT,
    MAX_MESSAGE_LENGTH,
    ADMIN_IDS
)
from logging_config import admin_logger
from sqlite_db import db, DatabaseError
from admin_panel import (
    is_admin,
    edit_message,
    format_admin_message,
    format_error_message,
    AdminTestCallback,
    truncate_message
)
from user_management import user_manager, UserRole, UserState

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Create router for test management
router = Router()

# Constants
MIN_QUESTIONS = 3
MAX_QUESTIONS = 20
MIN_OPTIONS = 2
MAX_OPTIONS = 6
MIN_PASS_SCORE = 70  # Minimum score to pass a test (percentage)

class QuestionType(str, Enum):
    """Types of test questions"""
    SINGLE_CHOICE = "single_choice"
    MULTIPLE_CHOICE = "multiple_choice"
    TEXT = "text"

@dataclass
class Question:
    """Test question data"""
    id: int
    test_id: int
    text: str
    type: QuestionType
    options: List[Dict[str, Any]]  # List of {text: str, is_correct: bool}
    order_num: int
    points: int

@dataclass
class Test:
    """Test data"""
    id: int
    title: str
    description: Optional[str]
    category_id: Optional[int]
    min_pass_score: int
    time_limit: Optional[int]  # Time limit in minutes
    is_active: bool
    created_at: datetime
    updated_at: datetime
    category_name: Optional[str] = None
    questions: Optional[List[Question]] = None

@dataclass
class TestAttempt:
    """Test attempt data"""
    id: int
    user_id: int
    test_id: int
    start_time: datetime
    end_time: Optional[datetime]
    score: Optional[float]
    is_completed: bool
    answers: Dict[int, Any]  # Question ID -> Answer
    test_title: Optional[str] = None
    user_name: Optional[str] = None

class TestForm(StatesGroup):
    """States for test creation form"""
    title = State()
    description = State()
    category = State()
    time_limit = State()
    min_pass_score = State()
    questions = State()

class TestTakingForm(StatesGroup):
    """States for taking a test"""
    answering = State()

class TestManagementError(Exception):
    """Base exception for test management errors"""
    pass

class TestNotFoundError(TestManagementError):
    """Raised when test is not found"""
    pass

class QuestionNotFoundError(TestManagementError):
    """Raised when question is not found"""
    pass

class InvalidTestError(TestManagementError):
    """Raised when test is invalid"""
    pass

class TestManagement:
    """Test management class with async support"""
    
    def __init__(self):
        """Initialize test management"""
        self._db = db

    async def create_test(
        self,
        title: str,
        description: Optional[str] = None,
        category_id: Optional[int] = None,
        time_limit: Optional[int] = None,
        min_pass_score: int = MIN_PASS_SCORE
    ) -> Optional[int]:
        """Create a new test"""
        try:
            async with self._db.transaction() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute("""
                        INSERT INTO tests (
                            title, description, category_id,
                            time_limit, min_pass_score,
                            is_active, created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    """, (title, description, category_id, time_limit, min_pass_score))
                    return cursor.lastrowid
        except Exception as e:
            logger.error(f"Error creating test: {e}")
            raise TestManagementError(f"Failed to create test: {e}")

    async def get_test(self, test_id: int, include_questions: bool = False) -> Optional[Test]:
        """Get test by ID"""
        try:
            # Get test data
            test_data = await self._db.execute_one("""
                SELECT t.*, c.name as category_name
                FROM tests t
                LEFT JOIN categories c ON t.category_id = c.id
                WHERE t.id = ?
            """, (test_id,))
            
            if not test_data:
                return None

            test = Test(
                id=test_data["id"],
                title=test_data["title"],
                description=test_data["description"],
                category_id=test_data["category_id"],
                min_pass_score=test_data["min_pass_score"],
                time_limit=test_data["time_limit"],
                is_active=bool(test_data["is_active"]),
                created_at=datetime.fromisoformat(test_data["created_at"]),
                updated_at=datetime.fromisoformat(test_data["updated_at"]),
                category_name=test_data["category_name"]
            )

            if include_questions:
                # Get test questions
                questions_data = await self._db.execute("""
                    SELECT * FROM test_questions
                    WHERE test_id = ?
                    ORDER BY order_num
                """, (test_id,))

                test.questions = [
                    Question(
                        id=q["id"],
                        test_id=q["test_id"],
                        text=q["text"],
                        type=QuestionType(q["type"]),
                        options=json.loads(q["options"]),
                        order_num=q["order_num"],
                        points=q["points"]
                    )
                    for q in questions_data
                ]

            return test

        except Exception as e:
            logger.error(f"Error getting test: {e}")
            raise TestManagementError(f"Failed to get test: {e}")

    async def list_tests(
        self,
        category_id: Optional[int] = None,
        include_inactive: bool = False
    ) -> List[Test]:
        """List tests with optional category filter"""
        try:
            query = """
                SELECT t.*, c.name as category_name
                FROM tests t
                LEFT JOIN categories c ON t.category_id = c.id
                WHERE 1=1
            """
            params = []

            if category_id is not None:
                query += " AND t.category_id = ?"
                params.append(category_id)

            if not include_inactive:
                query += " AND t.is_active = 1"

            query += " ORDER BY t.title"

            tests_data = await self._db.execute(query, tuple(params))
            return [
                Test(
                    id=t["id"],
                    title=t["title"],
                    description=t["description"],
                    category_id=t["category_id"],
                    min_pass_score=t["min_pass_score"],
                    time_limit=t["time_limit"],
                    is_active=bool(t["is_active"]),
                    created_at=datetime.fromisoformat(t["created_at"]),
                    updated_at=datetime.fromisoformat(t["updated_at"]),
                    category_name=t["category_name"]
                )
                for t in tests_data
            ]
        except Exception as e:
            logger.error(f"Error listing tests: {e}")
            raise TestManagementError(f"Failed to list tests: {e}")

    async def add_question(
        self,
        test_id: int,
        text: str,
        type: QuestionType,
        options: List[Dict[str, Any]],
        points: int = 1,
        order_num: Optional[int] = None
    ) -> Optional[int]:
        """Add a question to a test"""
        try:
            # Verify test exists
            test = await self.get_test(test_id)
            if not test:
                raise TestNotFoundError(f"Test {test_id} not found")

            # Validate question
            if not text.strip():
                raise InvalidTestError("Question text cannot be empty")
            if len(options) < MIN_OPTIONS:
                raise InvalidTestError(f"Question must have at least {MIN_OPTIONS} options")
            if len(options) > MAX_OPTIONS:
                raise InvalidTestError(f"Question cannot have more than {MAX_OPTIONS} options")
            if not any(opt.get("is_correct") for opt in options):
                raise InvalidTestError("Question must have at least one correct option")

            # Get next order number if not specified
            if order_num is None:
                last_question = await self._db.execute_one("""
                    SELECT MAX(order_num) as max_order
                    FROM test_questions
                    WHERE test_id = ?
                """, (test_id,))
                order_num = (last_question["max_order"] or 0) + 1

            async with self._db.transaction() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute("""
                        INSERT INTO test_questions (
                            test_id, text, type, options,
                            points, order_num
                        ) VALUES (?, ?, ?, ?, ?, ?)
                    """, (test_id, text, type.value, json.dumps(options), points, order_num))
                    return cursor.lastrowid

        except TestNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error adding question: {e}")
            raise TestManagementError(f"Failed to add question: {e}")

    async def start_test_attempt(
        self,
        user_id: int,
        test_id: int
    ) -> Optional[int]:
        """Start a new test attempt"""
        try:
            # Verify test exists and is active
            test = await self.get_test(test_id)
            if not test:
                raise TestNotFoundError(f"Test {test_id} not found")
            if not test.is_active:
                raise InvalidTestError("Test is not active")

            # Check if user has an incomplete attempt
            incomplete = await self._db.execute_one("""
                SELECT id FROM test_attempts
                WHERE user_id = ? AND test_id = ? AND is_completed = 0
            """, (user_id, test_id))
            if incomplete:
                raise InvalidTestError("You have an incomplete attempt for this test")

            # Create new attempt
            async with self._db.transaction() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute("""
                        INSERT INTO test_attempts (
                            user_id, test_id, start_time,
                            is_completed, answers
                        ) VALUES (?, ?, CURRENT_TIMESTAMP, 0, ?)
                    """, (user_id, test_id, json.dumps({})))
                    attempt_id = cursor.lastrowid

                    # Update user state
                    await user_manager.set_user_state(
                        user_id,
                        UserState.TAKING_TEST,
                        {"attempt_id": attempt_id, "test_id": test_id}
                    )

                    return attempt_id

        except (TestNotFoundError, InvalidTestError):
            raise
        except Exception as e:
            logger.error(f"Error starting test attempt: {e}")
            raise TestManagementError(f"Failed to start test attempt: {e}")

    async def submit_answer(
        self,
        attempt_id: int,
        question_id: int,
        answer: Any
    ) -> bool:
        """Submit an answer for a question"""
        try:
            # Get attempt data
            attempt = await self._db.execute_one("""
                SELECT * FROM test_attempts WHERE id = ?
            """, (attempt_id,))
            if not attempt:
                raise TestNotFoundError(f"Attempt {attempt_id} not found")
            if attempt["is_completed"]:
                raise InvalidTestError("Test attempt is already completed")

            # Get question data
            question = await self._db.execute_one("""
                SELECT * FROM test_questions WHERE id = ?
            """, (question_id,))
            if not question:
                raise QuestionNotFoundError(f"Question {question_id} not found")

            # Update answers
            answers = json.loads(attempt["answers"])
            answers[str(question_id)] = answer

            await self._db.execute("""
                UPDATE test_attempts
                SET answers = ?
                WHERE id = ?
            """, (json.dumps(answers), attempt_id))

            return True

        except (TestNotFoundError, QuestionNotFoundError, InvalidTestError):
            raise
        except Exception as e:
            logger.error(f"Error submitting answer: {e}")
            raise TestManagementError(f"Failed to submit answer: {e}")

    async def complete_test_attempt(
        self,
        attempt_id: int
    ) -> TestAttempt:
        """Complete a test attempt and calculate score"""
        try:
            # Get attempt data
            attempt = await self._db.execute_one("""
                SELECT ta.*, t.title as test_title, u.name as user_name
                FROM test_attempts ta
                JOIN tests t ON ta.test_id = t.id
                JOIN users u ON ta.user_id = u.telegram_id
                WHERE ta.id = ?
            """, (attempt_id,))
            if not attempt:
                raise TestNotFoundError(f"Attempt {attempt_id} not found")
            if attempt["is_completed"]:
                raise InvalidTestError("Test attempt is already completed")

            # Get test questions
            questions = await self._db.execute("""
                SELECT * FROM test_questions
                WHERE test_id = ?
                ORDER BY order_num
            """, (attempt["test_id"],))

            # Calculate score
            answers = json.loads(attempt["answers"])
            total_points = 0
            earned_points = 0

            for question in questions:
                total_points += question["points"]
                answer = answers.get(str(question["id"]))
                if answer is not None:
                    options = json.loads(question["options"])
                    if question["type"] == QuestionType.SINGLE_CHOICE.value:
                        # Single choice: answer must match correct option index
                        correct_index = next(
                            (i for i, opt in enumerate(options) if opt["is_correct"]),
                            None
                        )
                        if correct_index is not None and answer == correct_index:
                            earned_points += question["points"]
                    elif question["type"] == QuestionType.MULTIPLE_CHOICE.value:
                        # Multiple choice: all correct options must be selected
                        correct_indices = {
                            i for i, opt in enumerate(options) if opt["is_correct"]
                        }
                        if set(answer) == correct_indices:
                            earned_points += question["points"]

            # Calculate final score
            score = (earned_points / total_points * 100) if total_points > 0 else 0

            # Update attempt
            async with self._db.transaction() as conn:
                await conn.execute("""
                    UPDATE test_attempts
                    SET end_time = CURRENT_TIMESTAMP,
                        score = ?,
                        is_completed = 1
                    WHERE id = ?
                """, (score, attempt_id))

                # Update user state
                await user_manager.set_user_state(attempt["user_id"], UserState.IDLE)

            # Get updated attempt data
            updated_attempt = await self._db.execute_one("""
                SELECT ta.*, t.title as test_title, u.name as user_name
                FROM test_attempts ta
                JOIN tests t ON ta.test_id = t.id
                JOIN users u ON ta.user_id = u.telegram_id
                WHERE ta.id = ?
            """, (attempt_id,))

            return TestAttempt(
                id=updated_attempt["id"],
                user_id=updated_attempt["user_id"],
                test_id=updated_attempt["test_id"],
                start_time=datetime.fromisoformat(updated_attempt["start_time"]),
                end_time=datetime.fromisoformat(updated_attempt["end_time"]),
                score=updated_attempt["score"],
                is_completed=bool(updated_attempt["is_completed"]),
                answers=json.loads(updated_attempt["answers"]),
                test_title=updated_attempt["test_title"],
                user_name=updated_attempt["user_name"]
            )

        except (TestNotFoundError, InvalidTestError):
            raise
        except Exception as e:
            logger.error(f"Error completing test attempt: {e}")
            raise TestManagementError(f"Failed to complete test attempt: {e}")

    async def get_user_attempts(
        self,
        user_id: int,
        test_id: Optional[int] = None,
        include_incomplete: bool = False
    ) -> List[TestAttempt]:
        """Get user's test attempts"""
        try:
            query = """
                SELECT ta.*, t.title as test_title, u.name as user_name
                FROM test_attempts ta
                JOIN tests t ON ta.test_id = t.id
                JOIN users u ON ta.user_id = u.telegram_id
                WHERE ta.user_id = ?
            """
            params = [user_id]

            if test_id is not None:
                query += " AND ta.test_id = ?"
                params.append(test_id)

            if not include_incomplete:
                query += " AND ta.is_completed = 1"

            query += " ORDER BY ta.start_time DESC"

            attempts_data = await self._db.execute(query, tuple(params))
            return [
                TestAttempt(
                    id=a["id"],
                    user_id=a["user_id"],
                    test_id=a["test_id"],
                    start_time=datetime.fromisoformat(a["start_time"]),
                    end_time=datetime.fromisoformat(a["end_time"]) if a["end_time"] else None,
                    score=a["score"],
                    is_completed=bool(a["is_completed"]),
                    answers=json.loads(a["answers"]),
                    test_title=a["test_title"],
                    user_name=a["user_name"]
                )
                for a in attempts_data
            ]
        except Exception as e:
            logger.error(f"Error getting user attempts: {e}")
            raise TestManagementError(f"Failed to get user attempts: {e}")

# Create singleton instance
test_manager = TestManagement()

# Command handlers
@router.message(Command("tests"))
async def list_tests_command(message: Message) -> None:
    """Handle /tests command"""
    try:
        # Get category from command args
        args = message.text.split()
        category_id = int(args[1]) if len(args) > 1 else None

        tests = await test_manager.list_tests(category_id=category_id)
        
        if not tests:
            await message.answer(
                "Тесты не найдены." if category_id else
                "Используйте команду в формате:\n/tests <id_категории>"
            )
            return

        # Create keyboard with test buttons
        keyboard = InlineKeyboardBuilder()
        for test in tests:
            keyboard.button(
                text=test.title,
                callback_data=f"test:{test.id}"
            )
        keyboard.adjust(1)  # One button per row

        await message.answer(
            f"Тесты в категории {tests[0].category_name}:" if category_id else
            "Выберите категорию с помощью команды /categories",
            reply_markup=keyboard.as_markup()
        )

    except ValueError:
        await message.answer(
            "Используйте команду в формате:\n/tests <id_категории>"
        )
    except Exception as e:
        logger.error(f"Error in list tests command: {e}")
        await message.answer(f"Произошла ошибка: {e}")

@router.message(Command("my_tests"))
async def my_tests_command(message: Message) -> None:
    """Handle /my_tests command"""
    try:
        attempts = await test_manager.get_user_attempts(message.from_user.id)
        
        if not attempts:
            await message.answer("У вас пока нет завершенных тестов.")
            return

        # Group attempts by test
        test_attempts = {}
        for attempt in attempts:
            if attempt.test_id not in test_attempts:
                test_attempts[attempt.test_id] = []
            test_attempts[attempt.test_id].append(attempt)

        # Format message
        message_text = "<b>Ваши тесты:</b>\n\n"
        for test_id, attempts in test_attempts.items():
            test = attempts[0]  # Get test info from first attempt
            best_score = max(a.score for a in attempts)
            attempts_count = len(attempts)
            
            message_text += (
                f"<b>{test.test_title}</b>\n"
                f"• Попыток: {attempts_count}\n"
                f"• Лучший результат: {best_score:.1f}%\n"
                f"• Последняя попытка: {attempts[0].end_time.strftime('%d.%m.%Y %H:%M')}\n\n"
            )

        # Create keyboard with test buttons
        keyboard = InlineKeyboardBuilder()
        for test_id in test_attempts.keys():
            test = await test_manager.get_test(test_id)
            if test and test.is_active:
                keyboard.button(
                    text=f"Пройти {test.title}",
                    callback_data=f"start_test:{test_id}"
                )
        keyboard.adjust(1)

        await message.answer(
            message_text,
            reply_markup=keyboard.as_markup()
        )

    except Exception as e:
        logger.error(f"Error in my tests command: {e}")
        await message.answer(f"Произошла ошибка: {e}")

# Callback handlers
@router.callback_query(F.data.startswith("test:"))
async def test_callback(callback: CallbackQuery) -> None:
    """Handle test selection"""
    try:
        test_id = int(callback.data.split(":")[1])
        test = await test_manager.get_test(test_id)
        
        if not test:
            await callback.answer("Тест не найден", show_alert=True)
            return

        # Format message
        message = f"<b>{test.title}</b>\n"
        if test.description:
            message += f"\n{test.description}\n"
        message += f"\nКатегория: {test.category_name or 'Без категории'}"
        if test.time_limit:
            message += f"\nВремя на прохождение: {test.time_limit} мин."
        message += f"\nМинимальный проходной балл: {test.min_pass_score}%"

        # Create keyboard
        keyboard = InlineKeyboardBuilder()
        keyboard.button(
            text="▶️ Начать тест",
            callback_data=f"start_test:{test_id}"
        )
        keyboard.button(
            text="◀️ Назад к тестам",
            callback_data=f"tests:{test.category_id}"
        )
        keyboard.adjust(1)

        await callback.message.edit_text(
            message,
            reply_markup=keyboard.as_markup()
        )

    except Exception as e:
        logger.error(f"Error in test callback: {e}")
        await callback.answer(f"Произошла ошибка: {e}", show_alert=True)

@router.callback_query(F.data.startswith("start_test:"))
async def start_test_callback(callback: CallbackQuery) -> None:
    """Handle test start"""
    try:
        test_id = int(callback.data.split(":")[1])
        
        # Start test attempt
        attempt_id = await test_manager.start_test_attempt(
            callback.from_user.id,
            test_id
        )

        # Get test with questions
        test = await test_manager.get_test(test_id, include_questions=True)
        if not test or not test.questions:
            raise TestNotFoundError("Test or questions not found")

        # Get first question
        question = test.questions[0]
        
        # Format question
        message = (
            f"<b>Вопрос 1 из {len(test.questions)}</b>\n\n"
            f"{question.text}\n\n"
        )

        # Add options
        if question.type in {QuestionType.SINGLE_CHOICE, QuestionType.MULTIPLE_CHOICE}:
            for i, option in enumerate(question.options):
                message += f"{i + 1}. {option['text']}\n"

        # Create keyboard
        keyboard = InlineKeyboardBuilder()
        if question.type == QuestionType.SINGLE_CHOICE:
            for i in range(len(question.options)):
                keyboard.button(
                    text=str(i + 1),
                    callback_data=f"answer:{attempt_id}:{question.id}:{i}"
                )
        keyboard.button(
            text="❌ Отменить тест",
            callback_data=f"cancel_test:{attempt_id}"
        )
        keyboard.adjust(*([1] * len(question.options) + [1]))

        await callback.message.edit_text(
            message,
            reply_markup=keyboard.as_markup()
        )

    except TestNotFoundError as e:
        await callback.answer(str(e), show_alert=True)
    except InvalidTestError as e:
        await callback.answer(str(e), show_alert=True)
    except Exception as e:
        logger.error(f"Error in start test callback: {e}")
        await callback.answer(f"Произошла ошибка: {e}", show_alert=True)

@router.callback_query(F.data.startswith("answer:"))
async def answer_callback(callback: CallbackQuery) -> None:
    """Handle answer submission"""
    try:
        # Parse callback data
        _, attempt_id, question_id, answer = callback.data.split(":")
        attempt_id = int(attempt_id)
        question_id = int(question_id)
        answer = int(answer)

        # Submit answer
        await test_manager.submit_answer(attempt_id, question_id, answer)

        # Get test and current attempt
        attempt = await test_manager._db.execute_one("""
            SELECT * FROM test_attempts WHERE id = ?
        """, (attempt_id,))
        test = await test_manager.get_test(attempt["test_id"], include_questions=True)
        if not test or not test.questions:
            raise TestNotFoundError("Test or questions not found")

        # Get current question index
        current_index = next(
            (i for i, q in enumerate(test.questions) if q.id == question_id),
            None
        )
        if current_index is None or current_index >= len(test.questions) - 1:
            # Last question, complete test
            result = await test_manager.complete_test_attempt(attempt_id)
            
            # Format result message
            message = (
                f"<b>Тест завершен!</b>\n\n"
                f"Ваш результат: {result.score:.1f}%\n"
                f"Минимальный проходной балл: {test.min_pass_score}%\n\n"
            )
            if result.score >= test.min_pass_score:
                message += "✅ Поздравляем! Вы успешно прошли тест!"
            else:
                message += "❌ К сожалению, вы не прошли тест. Попробуйте еще раз!"

            # Create keyboard
            keyboard = InlineKeyboardBuilder()
            keyboard.button(
                text="🔄 Пройти тест снова",
                callback_data=f"start_test:{test.id}"
            )
            keyboard.button(
                text="📋 Мои тесты",
                callback_data="my_tests"
            )
            keyboard.adjust(1)

            await callback.message.edit_text(
                message,
                reply_markup=keyboard.as_markup()
            )
        else:
            # Get next question
            next_question = test.questions[current_index + 1]
            
            # Format question
            message = (
                f"<b>Вопрос {current_index + 2} из {len(test.questions)}</b>\n\n"
                f"{next_question.text}\n\n"
            )

            # Add options
            if next_question.type in {QuestionType.SINGLE_CHOICE, QuestionType.MULTIPLE_CHOICE}:
                for i, option in enumerate(next_question.options):
                    message += f"{i + 1}. {option['text']}\n"

            # Create keyboard
            keyboard = InlineKeyboardBuilder()
            if next_question.type == QuestionType.SINGLE_CHOICE:
                for i in range(len(next_question.options)):
                    keyboard.button(
                        text=str(i + 1),
                        callback_data=f"answer:{attempt_id}:{next_question.id}:{i}"
                    )
            keyboard.button(
                text="❌ Отменить тест",
                callback_data=f"cancel_test:{attempt_id}"
            )
            keyboard.adjust(*([1] * len(next_question.options) + [1]))

            await callback.message.edit_text(
                message,
                reply_markup=keyboard.as_markup()
            )

    except TestNotFoundError as e:
        await callback.answer(str(e), show_alert=True)
    except Exception as e:
        logger.error(f"Error in answer callback: {e}")
        await callback.answer(f"Произошла ошибка: {e}", show_alert=True)

@router.callback_query(F.data.startswith("cancel_test:"))
async def cancel_test_callback(callback: CallbackQuery) -> None:
    """Handle test cancellation"""
    try:
        attempt_id = int(callback.data.split(":")[1])
        
        # Get attempt data
        attempt = await test_manager._db.execute_one("""
            SELECT * FROM test_attempts WHERE id = ?
        """, (attempt_id,))
        if not attempt:
            raise TestNotFoundError("Attempt not found")

        # Update user state
        await user_manager.set_user_state(attempt["user_id"], UserState.IDLE)

        # Delete attempt
        await test_manager._db.execute(
            "DELETE FROM test_attempts WHERE id = ?",
            (attempt_id,)
        )

        await callback.message.edit_text(
            "❌ Тест отменен.",
            reply_markup=InlineKeyboardBuilder()
                .button(text="📋 Мои тесты", callback_data="my_tests")
                .adjust(1)
                .as_markup()
        )

    except TestNotFoundError as e:
        await callback.answer(str(e), show_alert=True)
    except Exception as e:
        logger.error(f"Error in cancel test callback: {e}")
        await callback.answer(f"Произошла ошибка: {e}", show_alert=True)

def setup_test_handlers(dp: Router):
    """Setup test management handlers"""
    dp.include_router(router)

# Test the module if run directly
if __name__ == "__main__":
    import asyncio

    async def test_test_management():
        try:
            # Test test creation
            test_id = await test_manager.create_test(
                title="Test Test",
                description="Test test description",
                time_limit=30
            )
            print(f"Test created: {test_id}")

            # Test question addition
            question_id = await test_manager.add_question(
                test_id=test_id,
                text="Test question?",
                type=QuestionType.SINGLE_CHOICE,
                options=[
                    {"text": "Option 1", "is_correct": True},
                    {"text": "Option 2", "is_correct": False}
                ]
            )
            print(f"Question added: {question_id}")

            # Test test retrieval
            test = await test_manager.get_test(test_id, include_questions=True)
            print(f"Test retrieved: {test}")

            # Test listing
            tests = await test_manager.list_tests()
            print(f"Found {len(tests)} tests")

        except Exception as e:
            print(f"Test failed: {e}")

    # Run tests
    asyncio.run(test_test_management()) 