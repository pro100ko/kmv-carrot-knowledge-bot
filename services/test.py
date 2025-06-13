"""Test service."""

from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
import json

from database import DatabaseError
from database.models import Test, Question, Option, TestResult
from database.repositories import (
    TestRepository,
    TestResultRepository,
    UserRepository
)
from .base import BaseService

class TestService(BaseService[Test]):
    """Test service."""
    
    def __init__(self):
        """Initialize service."""
        super().__init__(TestRepository())
        self.result_repo = TestResultRepository()
        self.user_repo = UserRepository()
    
    def create_test(
        self,
        user_id: int,
        title: str,
        *,
        description: Optional[str] = None,
        passing_score: int = 70,
        time_limit: int = 0,
        questions: Optional[List[Dict[str, Any]]] = None
    ) -> Test:
        """Create new test.
        
        Args:
            user_id: User ID (test creator).
            title: Test title.
            description: Optional test description.
            passing_score: Minimum score to pass (0-100).
            time_limit: Time limit in minutes (0 for no limit).
            questions: Optional list of questions with options.
            
        Returns:
            Test: Created test instance.
            
        Raises:
            DatabaseError: If creation fails.
            ValueError: If questions are invalid.
        """
        with self._get_session() as session:
            # Create test
            test = self.repository.create(
                session,
                user_id=user_id,
                title=title,
                description=description,
                passing_score=passing_score,
                time_limit=time_limit,
                is_active=True
            )
            
            # Add questions if provided
            if questions:
                self._add_questions(session, test.id, questions)
            
            return test
    
    def _add_questions(
        self,
        session,
        test_id: int,
        questions: List[Dict[str, Any]]
    ) -> None:
        """Add questions to test.
        
        Args:
            session: Database session.
            test_id: Test ID.
            questions: List of questions with options.
            
        Raises:
            ValueError: If questions are invalid.
            DatabaseError: If creation fails.
        """
        for i, q_data in enumerate(questions, 1):
            # Validate question
            if "text" not in q_data:
                raise ValueError(f"Question {i} missing text")
            if "options" not in q_data:
                raise ValueError(f"Question {i} missing options")
            
            # Create question
            question = Question(
                test_id=test_id,
                text=q_data["text"],
                order=i
            )
            session.add(question)
            session.flush()
            
            # Add options
            correct_count = 0
            for j, opt_data in enumerate(q_data["options"], 1):
                if "text" not in opt_data:
                    raise ValueError(f"Option {j} in question {i} missing text")
                if "is_correct" not in opt_data:
                    raise ValueError(f"Option {j} in question {i} missing is_correct")
                
                option = Option(
                    question_id=question.id,
                    text=opt_data["text"],
                    is_correct=opt_data["is_correct"],
                    order=j
                )
                session.add(option)
                
                if opt_data["is_correct"]:
                    correct_count += 1
            
            # Validate question
            if correct_count == 0:
                raise ValueError(f"Question {i} has no correct options")
            if correct_count > 1 and not q_data.get("allow_multiple", False):
                raise ValueError(f"Question {i} has multiple correct options but allow_multiple is False")
    
    def update_test(
        self,
        test_id: int,
        *,
        title: Optional[str] = None,
        description: Optional[str] = None,
        passing_score: Optional[int] = None,
        time_limit: Optional[int] = None,
        is_active: Optional[bool] = None,
        questions: Optional[List[Dict[str, Any]]] = None
    ) -> Optional[Test]:
        """Update test.
        
        Args:
            test_id: Test ID.
            title: Optional new title.
            description: Optional new description.
            passing_score: Optional new passing score.
            time_limit: Optional new time limit.
            is_active: Optional new active status.
            questions: Optional new questions.
            
        Returns:
            Optional[Test]: Updated test instance or None if not found.
            
        Raises:
            DatabaseError: If update fails.
            ValueError: If questions are invalid.
        """
        with self._get_session() as session:
            # Get test
            test = self.repository.get(session, test_id)
            if not test:
                return None
            
            # Update test
            updates = {}
            if title is not None:
                updates["title"] = title
            if description is not None:
                updates["description"] = description
            if passing_score is not None:
                updates["passing_score"] = passing_score
            if time_limit is not None:
                updates["time_limit"] = time_limit
            if is_active is not None:
                updates["is_active"] = is_active
            
            if updates:
                test = self.repository.update(session, test_id, **updates)
            
            # Update questions if provided
            if questions is not None:
                # Delete existing questions
                session.query(Question).where(
                    Question.test_id == test_id
                ).delete()
                
                # Add new questions
                self._add_questions(session, test_id, questions)
            
            return test
    
    def get_test_with_questions(self, test_id: int) -> Optional[Dict[str, Any]]:
        """Get test with questions and options.
        
        Args:
            test_id: Test ID.
            
        Returns:
            Optional[Dict[str, Any]]: Test data or None if not found.
            
        Raises:
            DatabaseError: If query fails.
        """
        with self._get_session() as session:
            # Get test
            test = self.repository.get(session, test_id)
            if not test:
                return None
            
            # Get questions
            questions = session.query(Question).where(
                Question.test_id == test_id,
                Question.is_deleted == False
            ).order_by(Question.order).all()
            
            # Get options for each question
            result = {
                "id": test.id,
                "title": test.title,
                "description": test.description,
                "passing_score": test.passing_score,
                "time_limit": test.time_limit,
                "is_active": test.is_active,
                "created_at": test.created_at.isoformat(),
                "updated_at": test.updated_at.isoformat(),
                "questions": []
            }
            
            for question in questions:
                options = session.query(Option).where(
                    Option.question_id == question.id,
                    Option.is_deleted == False
                ).order_by(Option.order).all()
                
                result["questions"].append({
                    "id": question.id,
                    "text": question.text,
                    "order": question.order,
                    "options": [
                        {
                            "id": option.id,
                            "text": option.text,
                            "is_correct": option.is_correct,
                            "order": option.order
                        }
                        for option in options
                    ]
                })
            
            return result
    
    def submit_test(
        self,
        test_id: int,
        user_id: int,
        answers: List[Dict[str, Any]],
        *,
        time_taken: int
    ) -> Tuple[TestResult, bool]:
        """Submit test answers.
        
        Args:
            test_id: Test ID.
            user_id: User ID.
            answers: List of answers.
            time_taken: Time taken in seconds.
            
        Returns:
            Tuple[TestResult, bool]: (Test result, passed flag)
            
        Raises:
            DatabaseError: If submission fails.
            ValueError: If answers are invalid.
        """
        with self._get_session() as session:
            # Get test
            test = self.repository.get(session, test_id)
            if not test:
                raise ValueError("Test not found")
            
            if not test.is_active:
                raise ValueError("Test is not active")
            
            # Get questions
            questions = session.query(Question).where(
                Question.test_id == test_id,
                Question.is_deleted == False
            ).order_by(Question.order).all()
            
            if len(questions) != len(answers):
                raise ValueError("Number of answers does not match number of questions")
            
            # Calculate score
            total_questions = len(questions)
            correct_answers = 0
            
            for question, answer in zip(questions, answers):
                if "question_id" not in answer:
                    raise ValueError(f"Answer missing question_id")
                if "option_ids" not in answer:
                    raise ValueError(f"Answer missing option_ids")
                
                if answer["question_id"] != question.id:
                    raise ValueError(f"Question ID mismatch")
                
                # Get correct options
                correct_options = session.query(Option).where(
                    Option.question_id == question.id,
                    Option.is_correct == True,
                    Option.is_deleted == False
                ).all()
                
                correct_option_ids = {opt.id for opt in correct_options}
                selected_option_ids = set(answer["option_ids"])
                
                # Check if answer is correct
                if correct_option_ids == selected_option_ids:
                    correct_answers += 1
            
            # Calculate score percentage
            score = int((correct_answers / total_questions) * 100)
            passed = score >= test.passing_score
            
            # Create test result
            result = self.result_repo.create(
                session,
                user_id=user_id,
                test_id=test_id,
                score=score,
                passed=passed,
                time_taken=time_taken,
                answers=json.dumps(answers)
            )
            
            return result, passed
    
    def get_test_results(
        self,
        test_id: int,
        *,
        skip: int = 0,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get test results.
        
        Args:
            test_id: Test ID.
            skip: Number of records to skip.
            limit: Maximum number of records to return.
            
        Returns:
            List[Dict[str, Any]]: List of test results.
            
        Raises:
            DatabaseError: If query fails.
        """
        with self._get_session() as session:
            # Get results
            results = session.query(TestResult).where(
                TestResult.test_id == test_id,
                TestResult.is_deleted == False
            ).order_by(TestResult.created_at.desc()).offset(skip).limit(limit).all()
            
            # Get users
            user_ids = {result.user_id for result in results}
            users = {
                user.id: user
                for user in session.query(User).where(User.id.in_(user_ids)).all()
            }
            
            # Format results
            return [
                {
                    "id": result.id,
                    "user": {
                        "id": users[result.user_id].id,
                        "telegram_id": users[result.user_id].telegram_id,
                        "username": users[result.user_id].username,
                        "first_name": users[result.user_id].first_name,
                        "last_name": users[result.user_id].last_name
                    },
                    "score": result.score,
                    "passed": result.passed,
                    "time_taken": result.time_taken,
                    "answers": json.loads(result.answers),
                    "created_at": result.created_at.isoformat()
                }
                for result in results
            ]
    
    def get_user_test_results(
        self,
        user_id: int,
        *,
        skip: int = 0,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get user's test results.
        
        Args:
            user_id: User ID.
            skip: Number of records to skip.
            limit: Maximum number of records to return.
            
        Returns:
            List[Dict[str, Any]]: List of test results.
            
        Raises:
            DatabaseError: If query fails.
        """
        with self._get_session() as session:
            # Get results
            results = self.result_repo.get_user_results(
                session,
                user_id,
                skip=skip,
                limit=limit
            )
            
            # Get tests
            test_ids = {result.test_id for result in results}
            tests = {
                test.id: test
                for test in session.query(Test).where(Test.id.in_(test_ids)).all()
            }
            
            # Format results
            return [
                {
                    "id": result.id,
                    "test": {
                        "id": tests[result.test_id].id,
                        "title": tests[result.test_id].title,
                        "description": tests[result.test_id].description,
                        "passing_score": tests[result.test_id].passing_score
                    },
                    "score": result.score,
                    "passed": result.passed,
                    "time_taken": result.time_taken,
                    "answers": json.loads(result.answers),
                    "created_at": result.created_at.isoformat()
                }
                for result in results
            ]
    
    def get_test_stats(self, test_id: int) -> Dict[str, Any]:
        """Get test statistics.
        
        Args:
            test_id: Test ID.
            
        Returns:
            Dict[str, Any]: Test statistics.
            
        Raises:
            DatabaseError: If query fails.
        """
        with self._get_session() as session:
            # Get test
            test = self.repository.get(session, test_id)
            if not test:
                return {}
            
            # Get results
            results = session.query(TestResult).where(
                TestResult.test_id == test_id,
                TestResult.is_deleted == False
            ).all()
            
            if not results:
                return {
                    "id": test.id,
                    "title": test.title,
                    "description": test.description,
                    "passing_score": test.passing_score,
                    "time_limit": test.time_limit,
                    "is_active": test.is_active,
                    "created_at": test.created_at.isoformat(),
                    "updated_at": test.updated_at.isoformat(),
                    "total_attempts": 0,
                    "passing_rate": 0,
                    "average_score": 0,
                    "average_time": 0,
                    "best_score": 0,
                    "worst_score": 0
                }
            
            # Calculate statistics
            total_attempts = len(results)
            passing_attempts = sum(1 for r in results if r.passed)
            passing_rate = (passing_attempts / total_attempts) * 100
            average_score = sum(r.score for r in results) / total_attempts
            average_time = sum(r.time_taken for r in results) / total_attempts
            best_score = max(r.score for r in results)
            worst_score = min(r.score for r in results)
            
            return {
                "id": test.id,
                "title": test.title,
                "description": test.description,
                "passing_score": test.passing_score,
                "time_limit": test.time_limit,
                "is_active": test.is_active,
                "created_at": test.created_at.isoformat(),
                "updated_at": test.updated_at.isoformat(),
                "total_attempts": total_attempts,
                "passing_rate": passing_rate,
                "average_score": average_score,
                "average_time": average_time,
                "best_score": best_score,
                "worst_score": worst_score
            } 