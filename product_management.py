import logging
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
import aiofiles
import os
from PIL import Image
import io

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, FSInputFile
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from sqlite_db import db, DatabaseError
from user_management import user_manager, UserRole

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Create router for product management
router = Router()

# Constants
MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB
ALLOWED_IMAGE_TYPES = {'image/jpeg', 'image/png'}
IMAGE_DIR = "product_images"
THUMBNAIL_SIZE = (300, 300)

# Ensure image directory exists
os.makedirs(IMAGE_DIR, exist_ok=True)

@dataclass
class Product:
    """Product data"""
    id: int
    category_id: int
    name: str
    description: Optional[str]
    image_path: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime
    category_name: Optional[str] = None

@dataclass
class Category:
    """Category data"""
    id: int
    name: str
    description: Optional[str]
    image_path: Optional[str]
    order_num: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

class ProductForm(StatesGroup):
    """States for product form"""
    name = State()
    description = State()
    category = State()
    image = State()

class CategoryForm(StatesGroup):
    """States for category form"""
    name = State()
    description = State()
    image = State()
    order = State()

class ProductManagementError(Exception):
    """Base exception for product management errors"""
    pass

class ProductNotFoundError(ProductManagementError):
    """Raised when product is not found"""
    pass

class CategoryNotFoundError(ProductManagementError):
    """Raised when category is not found"""
    pass

class InvalidImageError(ProductManagementError):
    """Raised when image is invalid"""
    pass

class ProductManagement:
    """Product management class with async support"""
    
    def __init__(self):
        """Initialize product management"""
        self._db = db

    async def add_category(
        self,
        name: str,
        description: Optional[str] = None,
        image_path: Optional[str] = None,
        order_num: int = 0
    ) -> Optional[int]:
        """Add a new category"""
        try:
            async with self._db.transaction() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute("""
                        INSERT INTO categories (
                            name, description, image_path, order_num,
                            is_active, created_at, updated_at
                        ) VALUES (?, ?, ?, ?, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    """, (name, description, image_path, order_num))
                    return cursor.lastrowid
        except Exception as e:
            logger.error(f"Error adding category: {e}")
            raise ProductManagementError(f"Failed to add category: {e}")

    async def get_category(self, category_id: int) -> Optional[Category]:
        """Get category by ID"""
        try:
            category_data = await self._db.execute_one(
                "SELECT * FROM categories WHERE id = ?",
                (category_id,)
            )
            if not category_data:
                return None

            return Category(
                id=category_data["id"],
                name=category_data["name"],
                description=category_data["description"],
                image_path=category_data["image_path"],
                order_num=category_data["order_num"],
                is_active=bool(category_data["is_active"]),
                created_at=datetime.fromisoformat(category_data["created_at"]),
                updated_at=datetime.fromisoformat(category_data["updated_at"])
            )
        except Exception as e:
            logger.error(f"Error getting category: {e}")
            raise ProductManagementError(f"Failed to get category: {e}")

    async def list_categories(
        self,
        include_inactive: bool = False
    ) -> List[Category]:
        """List categories"""
        try:
            query = "SELECT * FROM categories"
            params = []
            
            if not include_inactive:
                query += " WHERE is_active = 1"
            
            query += " ORDER BY order_num, name"
            
            categories_data = await self._db.execute(query, tuple(params))
            return [
                Category(
                    id=cat["id"],
                    name=cat["name"],
                    description=cat["description"],
                    image_path=cat["image_path"],
                    order_num=cat["order_num"],
                    is_active=bool(cat["is_active"]),
                    created_at=datetime.fromisoformat(cat["created_at"]),
                    updated_at=datetime.fromisoformat(cat["updated_at"])
                )
                for cat in categories_data
            ]
        except Exception as e:
            logger.error(f"Error listing categories: {e}")
            raise ProductManagementError(f"Failed to list categories: {e}")

    async def update_category(
        self,
        category_id: int,
        **updates: Any
    ) -> bool:
        """Update category"""
        try:
            category = await self.get_category(category_id)
            if not category:
                raise CategoryNotFoundError(f"Category {category_id} not found")

            update_data = {}
            allowed_fields = {
                "name", "description", "image_path",
                "order_num", "is_active"
            }

            for field, value in updates.items():
                if field in allowed_fields:
                    update_data[field] = value

            if not update_data:
                return True

            set_clause = ", ".join(f"{field} = ?" for field in update_data.keys())
            query = f"UPDATE categories SET {set_clause} WHERE id = ?"
            params = list(update_data.values()) + [category_id]

            await self._db.execute(query, tuple(params))
            logger.info(f"Successfully updated category {category_id}")
            return True

        except CategoryNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error updating category: {e}")
            raise ProductManagementError(f"Failed to update category: {e}")

    async def delete_category(self, category_id: int) -> bool:
        """Delete category and its products"""
        try:
            async with self._db.transaction() as conn:
                # Delete category images
                category = await self.get_category(category_id)
                if category and category.image_path:
                    try:
                        os.remove(category.image_path)
                    except Exception as e:
                        logger.warning(f"Failed to delete category image: {e}")

                # Delete product images
                products = await self.list_products(category_id=category_id)
                for product in products:
                    if product.image_path:
                        try:
                            os.remove(product.image_path)
                        except Exception as e:
                            logger.warning(f"Failed to delete product image: {e}")

                # Delete category and its products (cascade)
                await conn.execute("DELETE FROM categories WHERE id = ?", (category_id,))
                return True

        except Exception as e:
            logger.error(f"Error deleting category: {e}")
            raise ProductManagementError(f"Failed to delete category: {e}")

    async def add_product(
        self,
        category_id: int,
        name: str,
        description: Optional[str] = None,
        image_path: Optional[str] = None
    ) -> Optional[int]:
        """Add a new product"""
        try:
            # Verify category exists
            category = await self.get_category(category_id)
            if not category:
                raise CategoryNotFoundError(f"Category {category_id} not found")

            async with self._db.transaction() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute("""
                        INSERT INTO products (
                            category_id, name, description, image_path,
                            is_active, created_at, updated_at
                        ) VALUES (?, ?, ?, ?, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    """, (category_id, name, description, image_path))
                    return cursor.lastrowid

        except CategoryNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error adding product: {e}")
            raise ProductManagementError(f"Failed to add product: {e}")

    async def get_product(self, product_id: int) -> Optional[Product]:
        """Get product by ID"""
        try:
            product_data = await self._db.execute_one("""
                SELECT p.*, c.name as category_name
                FROM products p
                LEFT JOIN categories c ON p.category_id = c.id
                WHERE p.id = ?
            """, (product_id,))
            
            if not product_data:
                return None

            return Product(
                id=product_data["id"],
                category_id=product_data["category_id"],
                name=product_data["name"],
                description=product_data["description"],
                image_path=product_data["image_path"],
                is_active=bool(product_data["is_active"]),
                created_at=datetime.fromisoformat(product_data["created_at"]),
                updated_at=datetime.fromisoformat(product_data["updated_at"]),
                category_name=product_data["category_name"]
            )
        except Exception as e:
            logger.error(f"Error getting product: {e}")
            raise ProductManagementError(f"Failed to get product: {e}")

    async def list_products(
        self,
        category_id: Optional[int] = None,
        include_inactive: bool = False
    ) -> List[Product]:
        """List products with optional category filter"""
        try:
            query = """
                SELECT p.*, c.name as category_name
                FROM products p
                LEFT JOIN categories c ON p.category_id = c.id
                WHERE 1=1
            """
            params = []

            if category_id is not None:
                query += " AND p.category_id = ?"
                params.append(category_id)

            if not include_inactive:
                query += " AND p.is_active = 1"

            query += " ORDER BY p.name"

            products_data = await self._db.execute(query, tuple(params))
            return [
                Product(
                    id=prod["id"],
                    category_id=prod["category_id"],
                    name=prod["name"],
                    description=prod["description"],
                    image_path=prod["image_path"],
                    is_active=bool(prod["is_active"]),
                    created_at=datetime.fromisoformat(prod["created_at"]),
                    updated_at=datetime.fromisoformat(prod["updated_at"]),
                    category_name=prod["category_name"]
                )
                for prod in products_data
            ]
        except Exception as e:
            logger.error(f"Error listing products: {e}")
            raise ProductManagementError(f"Failed to list products: {e}")

    async def update_product(
        self,
        product_id: int,
        **updates: Any
    ) -> bool:
        """Update product"""
        try:
            product = await self.get_product(product_id)
            if not product:
                raise ProductNotFoundError(f"Product {product_id} not found")

            update_data = {}
            allowed_fields = {
                "category_id", "name", "description",
                "image_path", "is_active"
            }

            for field, value in updates.items():
                if field in allowed_fields:
                    if field == "category_id":
                        # Verify category exists
                        category = await self.get_category(value)
                        if not category:
                            raise CategoryNotFoundError(f"Category {value} not found")
                    update_data[field] = value

            if not update_data:
                return True

            set_clause = ", ".join(f"{field} = ?" for field in update_data.keys())
            query = f"UPDATE products SET {set_clause} WHERE id = ?"
            params = list(update_data.values()) + [product_id]

            await self._db.execute(query, tuple(params))
            logger.info(f"Successfully updated product {product_id}")
            return True

        except (ProductNotFoundError, CategoryNotFoundError):
            raise
        except Exception as e:
            logger.error(f"Error updating product: {e}")
            raise ProductManagementError(f"Failed to update product: {e}")

    async def delete_product(self, product_id: int) -> bool:
        """Delete product"""
        try:
            # Get product to delete image
            product = await self.get_product(product_id)
            if not product:
                raise ProductNotFoundError(f"Product {product_id} not found")

            async with self._db.transaction() as conn:
                # Delete product image
                if product.image_path:
                    try:
                        os.remove(product.image_path)
                    except Exception as e:
                        logger.warning(f"Failed to delete product image: {e}")

                # Delete product
                await conn.execute("DELETE FROM products WHERE id = ?", (product_id,))
                return True

        except ProductNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error deleting product: {e}")
            raise ProductManagementError(f"Failed to delete product: {e}")

    async def save_image(
        self,
        image_data: bytes,
        filename: str,
        is_category: bool = False
    ) -> Optional[str]:
        """Save and optimize image"""
        try:
            # Validate image
            if len(image_data) > MAX_IMAGE_SIZE:
                raise InvalidImageError("Image size exceeds maximum allowed size")

            # Open and validate image
            try:
                image = Image.open(io.BytesIO(image_data))
                if image.format not in {'JPEG', 'PNG'}:
                    raise InvalidImageError("Invalid image format")
            except Exception as e:
                raise InvalidImageError(f"Invalid image: {e}")

            # Create thumbnail
            image.thumbnail(THUMBNAIL_SIZE, Image.Resampling.LANCZOS)
            
            # Generate unique filename
            prefix = "cat_" if is_category else "prod_"
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            ext = image.format.lower()
            filename = f"{prefix}{timestamp}_{filename}.{ext}"
            filepath = os.path.join(IMAGE_DIR, filename)

            # Save optimized image
            image.save(filepath, optimize=True, quality=85)
            return filepath

        except InvalidImageError:
            raise
        except Exception as e:
            logger.error(f"Error saving image: {e}")
            raise ProductManagementError(f"Failed to save image: {e}")

# Create singleton instance
product_manager = ProductManagement()

# Command handlers
@router.message(Command("categories"))
async def list_categories_command(message: Message) -> None:
    """Handle /categories command"""
    try:
        categories = await product_manager.list_categories()
        
        if not categories:
            await message.answer("Категории пока не добавлены.")
            return

        # Create keyboard with category buttons
        keyboard = InlineKeyboardBuilder()
        for category in categories:
            keyboard.button(
                text=category.name,
                callback_data=f"category:{category.id}"
            )
        keyboard.adjust(2)  # Two buttons per row

        await message.answer(
            "Выберите категорию:",
            reply_markup=keyboard.as_markup()
        )

    except Exception as e:
        logger.error(f"Error in list categories command: {e}")
        await message.answer(f"Произошла ошибка: {e}")

@router.message(Command("products"))
async def list_products_command(message: Message) -> None:
    """Handle /products command"""
    try:
        # Get category from command args
        args = message.text.split()
        category_id = int(args[1]) if len(args) > 1 else None

        products = await product_manager.list_products(category_id=category_id)
        
        if not products:
            await message.answer(
                "Товары не найдены." if category_id else
                "Используйте команду в формате:\n/products <id_категории>"
            )
            return

        # Create keyboard with product buttons
        keyboard = InlineKeyboardBuilder()
        for product in products:
            keyboard.button(
                text=product.name,
                callback_data=f"product:{product.id}"
            )
        keyboard.adjust(1)  # One button per row

        await message.answer(
            f"Товары в категории {products[0].category_name}:" if category_id else
            "Выберите категорию с помощью команды /categories",
            reply_markup=keyboard.as_markup()
        )

    except ValueError:
        await message.answer(
            "Используйте команду в формате:\n/products <id_категории>"
        )
    except Exception as e:
        logger.error(f"Error in list products command: {e}")
        await message.answer(f"Произошла ошибка: {e}")

# Callback handlers
@router.callback_query(F.data.startswith("category:"))
async def category_callback(callback: CallbackQuery) -> None:
    """Handle category selection"""
    try:
        category_id = int(callback.data.split(":")[1])
        category = await product_manager.get_category(category_id)
        
        if not category:
            await callback.answer("Категория не найдена", show_alert=True)
            return

        # Get category products
        products = await product_manager.list_products(category_id=category_id)
        
        # Format message
        message = f"<b>{category.name}</b>\n"
        if category.description:
            message += f"\n{category.description}\n"
        
        if products:
            message += "\n<b>Товары:</b>\n"
            for product in products:
                message += f"• {product.name}\n"
        else:
            message += "\nТовары пока не добавлены."

        # Create keyboard
        keyboard = InlineKeyboardBuilder()
        keyboard.button(
            text="◀️ Назад к категориям",
            callback_data="categories"
        )
        if products:
            keyboard.button(
                text="📋 Список товаров",
                callback_data=f"products:{category_id}"
            )
        keyboard.adjust(1)

        # Send category image if exists
        if category.image_path:
            try:
                await callback.message.answer_photo(
                    FSInputFile(category.image_path),
                    caption=message,
                    reply_markup=keyboard.as_markup()
                )
                await callback.message.delete()
            except Exception as e:
                logger.error(f"Error sending category image: {e}")
                await callback.message.edit_text(
                    message,
                    reply_markup=keyboard.as_markup()
                )
        else:
            await callback.message.edit_text(
                message,
                reply_markup=keyboard.as_markup()
            )

    except Exception as e:
        logger.error(f"Error in category callback: {e}")
        await callback.answer(f"Произошла ошибка: {e}", show_alert=True)

@router.callback_query(F.data.startswith("product:"))
async def product_callback(callback: CallbackQuery) -> None:
    """Handle product selection"""
    try:
        product_id = int(callback.data.split(":")[1])
        product = await product_manager.get_product(product_id)
        
        if not product:
            await callback.answer("Товар не найден", show_alert=True)
            return

        # Format message
        message = f"<b>{product.name}</b>\n"
        if product.description:
            message += f"\n{product.description}\n"
        message += f"\nКатегория: {product.category_name}"

        # Create keyboard
        keyboard = InlineKeyboardBuilder()
        keyboard.button(
            text="◀️ Назад к категории",
            callback_data=f"category:{product.category_id}"
        )
        keyboard.adjust(1)

        # Send product image if exists
        if product.image_path:
            try:
                await callback.message.answer_photo(
                    FSInputFile(product.image_path),
                    caption=message,
                    reply_markup=keyboard.as_markup()
                )
                await callback.message.delete()
            except Exception as e:
                logger.error(f"Error sending product image: {e}")
                await callback.message.edit_text(
                    message,
                    reply_markup=keyboard.as_markup()
                )
        else:
            await callback.message.edit_text(
                message,
                reply_markup=keyboard.as_markup()
            )

    except Exception as e:
        logger.error(f"Error in product callback: {e}")
        await callback.answer(f"Произошла ошибка: {e}", show_alert=True)

def setup_product_handlers(dp: Router):
    """Setup product management handlers"""
    dp.include_router(router)

# Test the module if run directly
if __name__ == "__main__":
    import asyncio

    async def test_product_management():
        try:
            # Test category management
            category_id = await product_manager.add_category(
                name="Test Category",
                description="Test category description"
            )
            print(f"Category added: {category_id}")

            category = await product_manager.get_category(category_id)
            print(f"Category retrieved: {category}")

            # Test product management
            product_id = await product_manager.add_product(
                category_id=category_id,
                name="Test Product",
                description="Test product description"
            )
            print(f"Product added: {product_id}")

            product = await product_manager.get_product(product_id)
            print(f"Product retrieved: {product}")

            # Test listing
            categories = await product_manager.list_categories()
            print(f"Found {len(categories)} categories")

            products = await product_manager.list_products(category_id=category_id)
            print(f"Found {len(products)} products")

        except Exception as e:
            print(f"Test failed: {e}")

    # Run tests
    asyncio.run(test_product_management()) 