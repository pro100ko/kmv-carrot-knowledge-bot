"""Database models."""

from typing import List, Optional
from datetime import datetime
from sqlalchemy import String, Integer, Boolean, DateTime, ForeignKey, Text, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import BaseModel

class User(BaseModel):
    """User model."""
    
    __tablename__ = "users"
    
    telegram_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    username: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    first_name: Mapped[str] = mapped_column(String(64))
    last_name: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False)
    last_activity: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    tests: Mapped[List["Test"]] = relationship(back_populates="user")
    products: Mapped[List["Product"]] = relationship(back_populates="user")
    
    # Indexes
    __table_args__ = (
        Index("idx_user_telegram_id", "telegram_id"),
        Index("idx_user_username", "username"),
        Index("idx_user_last_activity", "last_activity")
    )

class Test(BaseModel):
    """Test model."""
    
    __tablename__ = "tests"
    
    title: Mapped[str] = mapped_column(String(128))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    passing_score: Mapped[int] = mapped_column(Integer, default=70)
    time_limit: Mapped[int] = mapped_column(Integer, default=0)  # 0 means no limit
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    
    # Relationships
    user: Mapped["User"] = relationship(back_populates="tests")
    questions: Mapped[List["Question"]] = relationship(back_populates="test")
    
    # Indexes
    __table_args__ = (
        Index("idx_test_title", "title"),
        Index("idx_test_user_id", "user_id"),
        Index("idx_test_is_active", "is_active")
    )

class Question(BaseModel):
    """Question model."""
    
    __tablename__ = "questions"
    
    text: Mapped[str] = mapped_column(Text)
    test_id: Mapped[int] = mapped_column(Integer, ForeignKey("tests.id"))
    order: Mapped[int] = mapped_column(Integer, default=0)
    
    # Relationships
    test: Mapped["Test"] = relationship(back_populates="questions")
    options: Mapped[List["Option"]] = relationship(back_populates="question")
    
    # Indexes
    __table_args__ = (
        Index("idx_question_test_id", "test_id"),
        Index("idx_question_order", "order")
    )

class Option(BaseModel):
    """Option model."""
    
    __tablename__ = "options"
    
    text: Mapped[str] = mapped_column(Text)
    is_correct: Mapped[bool] = mapped_column(Boolean, default=False)
    question_id: Mapped[int] = mapped_column(Integer, ForeignKey("questions.id"))
    order: Mapped[int] = mapped_column(Integer, default=0)
    
    # Relationships
    question: Mapped["Question"] = relationship(back_populates="options")
    
    # Indexes
    __table_args__ = (
        Index("idx_option_question_id", "question_id"),
        Index("idx_option_order", "order")
    )

class Product(BaseModel):
    """Product model."""
    
    __tablename__ = "products"
    
    name: Mapped[str] = mapped_column(String(128))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    price: Mapped[float] = mapped_column(Integer)  # Price in cents
    image_url: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    category_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("categories.id"), nullable=True)
    
    # Relationships
    user: Mapped["User"] = relationship(back_populates="products")
    category: Mapped[Optional["Category"]] = relationship(back_populates="products")
    
    # Indexes
    __table_args__ = (
        Index("idx_product_name", "name"),
        Index("idx_product_user_id", "user_id"),
        Index("idx_product_category_id", "category_id"),
        Index("idx_product_is_active", "is_active")
    )

class Category(BaseModel):
    """Category model."""
    
    __tablename__ = "categories"
    
    name: Mapped[str] = mapped_column(String(64))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    image_url: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    parent_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("categories.id"), nullable=True)
    
    # Relationships
    products: Mapped[List["Product"]] = relationship(back_populates="category")
    parent: Mapped[Optional["Category"]] = relationship(
        "Category",
        remote_side=[id],
        backref="children"
    )
    
    # Indexes
    __table_args__ = (
        Index("idx_category_name", "name"),
        Index("idx_category_parent_id", "parent_id"),
        Index("idx_category_is_active", "is_active")
    )

class TestResult(BaseModel):
    """Test result model."""
    
    __tablename__ = "test_results"
    
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    test_id: Mapped[int] = mapped_column(Integer, ForeignKey("tests.id"))
    score: Mapped[int] = mapped_column(Integer)
    passed: Mapped[bool] = mapped_column(Boolean)
    time_taken: Mapped[int] = mapped_column(Integer)  # Time taken in seconds
    answers: Mapped[str] = mapped_column(Text)  # JSON string of answers
    
    # Indexes
    __table_args__ = (
        Index("idx_test_result_user_id", "user_id"),
        Index("idx_test_result_test_id", "test_id"),
        Index("idx_test_result_passed", "passed")
    )

class UserActivity(BaseModel):
    """User activity model."""
    
    __tablename__ = "user_activities"
    
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(32))
    details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    
    # Indexes
    __table_args__ = (
        Index("idx_user_activity_user_id", "user_id"),
        Index("idx_user_activity_action", "action"),
        Index("idx_user_activity_created_at", "created_at")
    ) 