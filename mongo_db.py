
import os
import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, Union
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.errors import PyMongoError
from config import ADMIN_IDS, MONGODB_URI

# Настройка логирования
logger = logging.getLogger(__name__)

# Глобальные переменные для доступа к MongoDB
client = None
db = None
MONGODB_AVAILABLE = False

# Инициализация MongoDB
try:
    if MONGODB_URI:
        client = MongoClient(MONGODB_URI)
        # Проверка соединения
        client.server_info()
        db = client["morkovka_kmv_bot"]
        MONGODB_AVAILABLE = True
        logger.info("MongoDB успешно инициализирована")
    else:
        logger.warning("Строка подключения MongoDB не найдена. Используем заглушки.")
except Exception as e:
    logger.error(f"Ошибка при инициализации MongoDB: {e}")
    client = None
    db = None

# Декоратор для проверки соединения перед запросом
def check_db_before_request(func):
    """Декоратор для проверки соединения перед запросом к базе данных"""
    def wrapper(*args, **kwargs):
        if not db or not MONGODB_AVAILABLE:
            logger.debug(f"MongoDB недоступна. Возвращаем заглушку для {func.__name__}")
            # Возвращаем заглушки в зависимости от имени функции
            if func.__name__.startswith("get_"):
                return _get_stub_data(func.__name__)
            elif func.__name__.startswith("add_") or func.__name__ == "register_user":
                return True
            elif func.__name__.startswith("update_"):
                return True
            elif func.__name__ == "search_products":
                return []
            return False
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Ошибка при выполнении {func.__name__}: {e}")
            # Возвращаем заглушки в случае ошибки
            if func.__name__.startswith("get_"):
                return _get_stub_data(func.__name__)
            elif func.__name__.startswith("add_") or func.__name__ == "register_user":
                return True
            return False
    return wrapper

# Функция для возвращения заглушек данных
def _get_stub_data(func_name):
    """Возвращает заглушки данных в зависимости от имени функции"""
    if func_name == "get_user":
        return {"telegram_id": 0, "first_name": "Test", "is_admin": False}
    elif func_name == "get_all_users":
        return [{"telegram_id": 0, "first_name": "Test", "is_admin": False}]
    elif func_name == "get_categories":
        return [{"id": "1", "name": "Тестовая категория", "description": "Тестовое описание"}]
    elif func_name == "get_products_by_category":
        return [{"id": "1", "name": "Тестовый продукт", "description": "Тестовое описание", "price_info": "100 руб/кг"}]
    elif func_name == "get_product":
        return {"id": "1", "name": "Тестовый продукт", "description": "Тестовое описание", "price_info": "100 руб/кг"}
    elif func_name == "get_tests_list":
        return [{"id": "1", "title": "Тестовый тест", "description": "Тестовое описание"}]
    elif func_name == "get_test":
        return {
            "id": "1", 
            "title": "Тестовый тест", 
            "description": "Тестовое описание",
            "questions": [
                {
                    "question": "Тестовый вопрос", 
                    "options": ["Вариант 1", "Вариант 2", "Вариант 3"], 
                    "correct_option": 0
                }
            ]
        }
    elif func_name == "get_user_test_attempts":
        return []
    return None

# Управление пользователями
@check_db_before_request
def register_user(user_data: Dict[str, Any]) -> bool:
    """Регистрирует нового пользователя или обновляет существующего"""
    try:
        users_collection = db["users"]
        telegram_id = user_data['telegram_id']
        
        # Проверяем, существует ли пользователь
        existing_user = users_collection.find_one({"telegram_id": telegram_id})
        
        if existing_user:
            # Обновляем информацию о пользователе
            users_collection.update_one(
                {"telegram_id": telegram_id},
                {"$set": {
                    "first_name": user_data.get("first_name", ""),
                    "last_name": user_data.get("last_name", ""),
                    "username": user_data.get("username", ""),
                    "last_active": datetime.now()
                }}
            )
        else:
            # Создаем нового пользователя
            new_user = {
                "telegram_id": telegram_id,
                "first_name": user_data.get("first_name", ""),
                "last_name": user_data.get("last_name", ""),
                "username": user_data.get("username", ""),
                "is_admin": telegram_id in ADMIN_IDS,
                "created_at": datetime.now(),
                "last_active": datetime.now()
            }
            users_collection.insert_one(new_user)
        
        return True
    except Exception as e:
        logger.error(f"Ошибка при регистрации пользователя: {e}")
        return False

@check_db_before_request
def get_user(telegram_id: int) -> Optional[Dict[str, Any]]:
    """Получает информацию о пользователе"""
    try:
        users_collection = db["users"]
        user = users_collection.find_one({"telegram_id": telegram_id})
        if user:
            # Преобразуем ObjectId в строку
            user["_id"] = str(user["_id"])
            return user
        return None
    except Exception as e:
        logger.error(f"Ошибка при получении пользователя: {e}")
        return None

@check_db_before_request
def get_all_users() -> List[Dict[str, Any]]:
    """Получает список всех пользователей"""
    try:
        users_collection = db["users"]
        users = list(users_collection.find())
        
        # Преобразуем ObjectId в строку для каждого пользователя
        for user in users:
            user["_id"] = str(user["_id"])
            
        return users
    except Exception as e:
        logger.error(f"Ошибка при получении списка пользователей: {e}")
        return []

# Управление категориями
@check_db_before_request
def get_categories() -> List[Dict[str, Any]]:
    """Получает список категорий"""
    try:
        categories_collection = db["categories"]
        categories = list(categories_collection.find().sort("order", 1))
        
        # Преобразуем ObjectId в строку для каждой категории
        for category in categories:
            category["id"] = str(category["_id"])
            del category["_id"]
            
        return categories
    except Exception as e:
        logger.error(f"Ошибка при получении категорий: {e}")
        return []

@check_db_before_request
def add_category(data: Dict[str, Any]) -> Optional[str]:
    """Добавляет новую категорию"""
    try:
        categories_collection = db["categories"]
        
        # Получаем максимальное значение order
        max_order_doc = categories_collection.find_one(sort=[("order", -1)])
        max_order = max_order_doc.get("order", 0) if max_order_doc else 0
        
        # Создаем новую категорию
        new_category = {
            "name": data["name"],
            "description": data.get("description", ""),
            "order": max_order + 1,
        }
        
        # Если есть изображение, сохраняем его URL
        if "image_url" in data:
            new_category["image_url"] = data["image_url"]
        
        # Добавляем категорию в MongoDB
        result = categories_collection.insert_one(new_category)
        return str(result.inserted_id)
    except Exception as e:
        logger.error(f"Ошибка при добавлении категории: {e}")
        return None

# Управление продуктами
@check_db_before_request
def get_products_by_category(category_id: str) -> List[Dict[str, Any]]:
    """Получает список продуктов для указанной категории"""
    try:
        products_collection = db["products"]
        products = list(products_collection.find({"category_id": category_id}))
        
        # Преобразуем ObjectId в строку для каждого продукта
        for product in products:
            product["id"] = str(product["_id"])
            del product["_id"]
            
        return products
    except Exception as e:
        logger.error(f"Ошибка при получении продуктов: {e}")
        return []

@check_db_before_request
def get_product(product_id: str) -> Optional[Dict[str, Any]]:
    """Получает информацию о продукте по ID"""
    try:
        from bson.objectid import ObjectId
        
        products_collection = db["products"]
        product = products_collection.find_one({"_id": ObjectId(product_id)})
        
        if product:
            product["id"] = str(product["_id"])
            del product["_id"]
            return product
        return None
    except Exception as e:
        logger.error(f"Ошибка при получении продукта: {e}")
        return None

@check_db_before_request
def add_product(data: Dict[str, Any]) -> Optional[str]:
    """Добавляет новый продукт"""
    try:
        products_collection = db["products"]
        
        # Создаем новый продукт
        new_product = {
            "name": data["name"],
            "category_id": data["category_id"],
            "description": data.get("description", ""),
            "price_info": data.get("price_info", ""),
            "storage_conditions": data.get("storage_conditions", ""),
            "image_urls": data.get("image_urls", []),
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }
        
        # Если есть видео URL, сохраняем его
        if "video_url" in data:
            new_product["video_url"] = data["video_url"]
        
        # Добавляем продукт в MongoDB
        result = products_collection.insert_one(new_product)
        return str(result.inserted_id)
    except Exception as e:
        logger.error(f"Ошибка при добавлении продукта: {e}")
        return None

@check_db_before_request
def update_product(product_id: str, data: Dict[str, Any]) -> bool:
    """Обновляет информацию о продукте"""
    try:
        from bson.objectid import ObjectId
        
        products_collection = db["products"]
        
        # Проверяем, существует ли продукт
        existing_product = products_collection.find_one({"_id": ObjectId(product_id)})
        if not existing_product:
            return False
        
        # Подготавливаем данные для обновления
        update_data = {
            "name": data.get("name"),
            "category_id": data.get("category_id"),
            "description": data.get("description", ""),
            "price_info": data.get("price_info", ""),
            "storage_conditions": data.get("storage_conditions", ""),
            "updated_at": datetime.now(),
        }
        
        # Удаляем None значения
        update_data = {k: v for k, v in update_data.items() if v is not None}
        
        # Если есть новые изображения, добавляем их
        if "image_urls" in data:
            update_data["image_urls"] = data["image_urls"]
        
        # Если есть новое видео, добавляем его
        if "video_url" in data:
            update_data["video_url"] = data["video_url"]
        
        # Обновляем продукт в MongoDB
        products_collection.update_one(
            {"_id": ObjectId(product_id)},
            {"$set": update_data}
        )
        return True
    except Exception as e:
        logger.error(f"Ошибка при обновлении продукта: {e}")
        return False

@check_db_before_request
def search_products(query: str) -> List[Dict[str, Any]]:
    """Поиск продуктов по названию"""
    try:
        products_collection = db["products"]
        
        # Используем регулярное выражение для поиска по части имени
        regex_query = {"name": {"$regex": query, "$options": "i"}}
        products = list(products_collection.find(regex_query).limit(10))
        
        # Преобразуем ObjectId в строку для каждого продукта
        for product in products:
            product["id"] = str(product["_id"])
            del product["_id"]
            
        return products
    except Exception as e:
        logger.error(f"Ошибка при поиске продуктов: {e}")
        return []

# Управление тестами
@check_db_before_request
def get_tests_list() -> List[Dict[str, Any]]:
    """Получает список всех тестов"""
    try:
        tests_collection = db["tests"]
        tests = list(tests_collection.find({"is_active": True}))
        
        # Преобразуем ObjectId в строку для каждого теста
        for test in tests:
            test["id"] = str(test["_id"])
            del test["_id"]
            
        return tests
    except Exception as e:
        logger.error(f"Ошибка при получении тестов: {e}")
        return []

@check_db_before_request
def get_test(test_id: str) -> Optional[Dict[str, Any]]:
    """Получает информацию о тесте по ID"""
    try:
        from bson.objectid import ObjectId
        
        tests_collection = db["tests"]
        test = tests_collection.find_one({"_id": ObjectId(test_id)})
        
        if test:
            test["id"] = str(test["_id"])
            del test["_id"]
            return test
        return None
    except Exception as e:
        logger.error(f"Ошибка при получении теста: {e}")
        return None

@check_db_before_request
def add_test(data: Dict[str, Any]) -> Optional[str]:
    """Создает новый тест"""
    try:
        tests_collection = db["tests"]
        
        # Создаем новый тест
        new_test = {
            "title": data["title"],
            "description": data.get("description", ""),
            "category_id": data.get("category_id"),
            "questions": data["questions"],
            "passing_score": data.get("passing_score", 70),  # По умолчанию 70%
            "is_active": True,
            "created_at": datetime.now(),
            "created_by": data.get("created_by"),
        }
        
        # Добавляем тест в MongoDB
        result = tests_collection.insert_one(new_test)
        return str(result.inserted_id)
    except Exception as e:
        logger.error(f"Ошибка при добавлении теста: {e}")
        return None

@check_db_before_request
def save_test_attempt(data: Dict[str, Any]) -> Optional[str]:
    """Сохраняет попытку прохождения теста"""
    try:
        attempts_collection = db["test_attempts"]
        
        # Создаем новую попытку
        new_attempt = {
            "user_id": data["user_id"],
            "test_id": data["test_id"],
            "score": data.get("score", 0),
            "max_score": data.get("max_score", 0),
            "answers": data.get("answers", []),
            "completed": data.get("completed", False),
            "started_at": datetime.now(),
        }
        
        # Если тест завершен, добавляем время завершения
        if data.get("completed"):
            new_attempt["completed_at"] = datetime.now()
        
        # Добавляем попытку в MongoDB
        result = attempts_collection.insert_one(new_attempt)
        return str(result.inserted_id)
    except Exception as e:
        logger.error(f"Ошибка при сохранении попытки: {e}")
        return None

@check_db_before_request
def get_user_test_attempts(user_id: str) -> List[Dict[str, Any]]:
    """Получает все попытки прохождения тестов для пользователя"""
    try:
        attempts_collection = db["test_attempts"]
        attempts = list(attempts_collection.find({"user_id": user_id}).sort("started_at", -1))
        
        # Преобразуем ObjectId в строку для каждой попытки
        for attempt in attempts:
            attempt["id"] = str(attempt["_id"])
            del attempt["_id"]
            
        return attempts
    except Exception as e:
        logger.error(f"Ошибка при получении попыток: {e}")
        return []

# Вспомогательные функции для работы с файлами - тут нужно реализовать хранение на своем сервере или использовать другой сервис
def upload_file(file_data: Union[bytes, str], destination_path: str) -> Optional[str]:
    """Загружает файл и возвращает URL"""
    # Здесь нужно реализовать загрузку файла на ваш сервер
    # Это заглушка
    logger.warning("Функция upload_file не реализована для MongoDB")
    return None

def delete_file(file_url: str) -> bool:
    """Удаляет файл"""
    # Здесь нужно реализовать удаление файла с вашего сервера
    # Это заглушка
    logger.warning("Функция delete_file не реализована для MongoDB")
    return False
