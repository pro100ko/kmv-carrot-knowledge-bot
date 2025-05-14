
import sqlite3
import os
import json
import time
from datetime import datetime
from typing import Dict, List, Any, Optional, Union

# Константы для работы с базой данных
DB_FILE = "morkovka_bot.db"
SQLITE_AVAILABLE = False

def dict_factory(cursor, row):
    """Преобразует строки SQLite в словари"""
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

# Инициализация базы данных
def init_sqlite():
    global SQLITE_AVAILABLE
    
    try:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = dict_factory
        cursor = conn.cursor()
        
        # Создаем таблицы, если они не существуют
        
        # Таблица пользователей
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER UNIQUE,
            first_name TEXT,
            last_name TEXT,
            username TEXT,
            is_admin INTEGER DEFAULT 0,
            created_at TEXT,
            last_active TEXT
        )
        ''')
        
        # Таблица категорий продуктов
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            description TEXT,
            image_url TEXT,
            order_num INTEGER DEFAULT 0
        )
        ''')
        
        # Таблица продуктов
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            category_id INTEGER,
            description TEXT,
            price_info TEXT,
            storage_conditions TEXT,
            created_at TEXT,
            updated_at TEXT,
            FOREIGN KEY (category_id) REFERENCES categories (id)
        )
        ''')
        
        # Таблица изображений продукта
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS product_images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER,
            image_url TEXT,
            FOREIGN KEY (product_id) REFERENCES products (id)
        )
        ''')
        
        # Таблица тестов
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS tests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            description TEXT,
            category_id INTEGER,
            passing_score INTEGER,
            is_active INTEGER DEFAULT 1,
            created_at TEXT,
            created_by INTEGER,
            FOREIGN KEY (category_id) REFERENCES categories (id),
            FOREIGN KEY (created_by) REFERENCES users (id)
        )
        ''')
        
        # Таблица вопросов
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            test_id INTEGER,
            text TEXT,
            correct_option INTEGER,
            explanation TEXT,
            FOREIGN KEY (test_id) REFERENCES tests (id)
        )
        ''')
        
        # Таблица вариантов ответа
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS options (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question_id INTEGER,
            option_text TEXT,
            option_index INTEGER,
            FOREIGN KEY (question_id) REFERENCES questions (id)
        )
        ''')
        
        # Таблица результатов тестирования
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS test_attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            test_id INTEGER,
            score INTEGER,
            max_score INTEGER,
            completed INTEGER DEFAULT 0,
            started_at TEXT,
            completed_at TEXT,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (test_id) REFERENCES tests (id)
        )
        ''')
        
        # Таблица ответов пользователя
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_answers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            attempt_id INTEGER,
            question_id INTEGER,
            selected_option INTEGER,
            is_correct INTEGER,
            FOREIGN KEY (attempt_id) REFERENCES test_attempts (id),
            FOREIGN KEY (question_id) REFERENCES questions (id)
        )
        ''')
        
        conn.commit()
        conn.close()
        
        SQLITE_AVAILABLE = True
        return True
    except Exception as e:
        print(f"Ошибка при инициализации SQLite: {e}")
        SQLITE_AVAILABLE = False
        return False

# Функции для работы с пользователями
def register_user(user_data: Dict[str, Any]) -> bool:
    """Регистрирует или обновляет пользователя в базе данных"""
    if not SQLITE_AVAILABLE:
        return False
    
    try:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = dict_factory
        cursor = conn.cursor()
        
        # Проверяем, существует ли пользователь
        cursor.execute(
            "SELECT * FROM users WHERE telegram_id = ?", 
            (user_data['telegram_id'],)
        )
        existing_user = cursor.fetchone()
        
        now = datetime.now().isoformat()
        
        if existing_user:
            # Обновляем существующего пользователя
            cursor.execute(
                """UPDATE users SET 
                   first_name = ?, last_name = ?, username = ?, last_active = ? 
                   WHERE telegram_id = ?""",
                (
                    user_data.get('first_name', ''),
                    user_data.get('last_name', ''),
                    user_data.get('username', ''),
                    now,
                    user_data['telegram_id']
                )
            )
        else:
            # Добавляем нового пользователя
            cursor.execute(
                """INSERT INTO users 
                   (telegram_id, first_name, last_name, username, created_at, last_active)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    user_data['telegram_id'],
                    user_data.get('first_name', ''),
                    user_data.get('last_name', ''),
                    user_data.get('username', ''),
                    now,
                    now
                )
            )
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Ошибка при регистрации пользователя: {e}")
        return False

def get_user(telegram_id: int) -> Optional[Dict[str, Any]]:
    """Получает данные пользователя по ID Telegram"""
    if not SQLITE_AVAILABLE:
        return None
    
    try:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = dict_factory
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
        user = cursor.fetchone()
        
        conn.close()
        return user
    except Exception as e:
        print(f"Ошибка при получении пользователя: {e}")
        return None

def get_all_users() -> List[Dict[str, Any]]:
    """Получает список всех пользователей"""
    if not SQLITE_AVAILABLE:
        return []
    
    try:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = dict_factory
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM users")
        users = cursor.fetchall()
        
        conn.close()
        return users
    except Exception as e:
        print(f"Ошибка при получении списка пользователей: {e}")
        return []

# Функции для работы с категориями
def add_category(category_data: Dict[str, Any]) -> Optional[int]:
    """Добавляет новую категорию"""
    if not SQLITE_AVAILABLE:
        return None
    
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute(
            """INSERT INTO categories (name, description, image_url, order_num)
               VALUES (?, ?, ?, ?)""",
            (
                category_data.get('name', ''),
                category_data.get('description', ''),
                category_data.get('image_url', ''),
                category_data.get('order', 0)
            )
        )
        
        # Получаем ID добавленной категории
        category_id = cursor.lastrowid
        
        conn.commit()
        conn.close()
        return category_id
    except Exception as e:
        print(f"Ошибка при добавлении категории: {e}")
        return None

def get_categories() -> List[Dict[str, Any]]:
    """Получает список всех категорий"""
    if not SQLITE_AVAILABLE:
        return []
    
    try:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = dict_factory
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM categories ORDER BY order_num")
        categories = cursor.fetchall()
        
        conn.close()
        return categories
    except Exception as e:
        print(f"Ошибка при получении списка категорий: {e}")
        return []

def get_category(category_id: int) -> Optional[Dict[str, Any]]:
    """Получает информацию о категории по ID"""
    if not SQLITE_AVAILABLE:
        return None
    
    try:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = dict_factory
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM categories WHERE id = ?", (category_id,))
        category = cursor.fetchone()
        
        conn.close()
        return category
    except Exception as e:
        print(f"Ошибка при получении категории: {e}")
        return None

# Функции для работы с продуктами
def add_product(product_data: Dict[str, Any]) -> Optional[int]:
    """Добавляет новый продукт"""
    if not SQLITE_AVAILABLE:
        return None
    
    try:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = dict_factory
        cursor = conn.cursor()
        
        now = datetime.now().isoformat()
        
        cursor.execute(
            """INSERT INTO products 
               (name, category_id, description, price_info, storage_conditions, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                product_data.get('name', ''),
                product_data.get('category_id', 0),
                product_data.get('description', ''),
                product_data.get('price_info', ''),
                product_data.get('storage_conditions', ''),
                now,
                now
            )
        )
        
        # Получаем ID добавленного продукта
        product_id = cursor.lastrowid
        
        # Добавляем изображения продукта
        if 'image_urls' in product_data and isinstance(product_data['image_urls'], list):
            for image_url in product_data['image_urls']:
                cursor.execute(
                    "INSERT INTO product_images (product_id, image_url) VALUES (?, ?)",
                    (product_id, image_url)
                )
        
        conn.commit()
        conn.close()
        return product_id
    except Exception as e:
        print(f"Ошибка при добавлении продукта: {e}")
        return None

def get_products_by_category(category_id: int) -> List[Dict[str, Any]]:
    """Получает список продуктов по ID категории"""
    if not SQLITE_AVAILABLE:
        return []
    
    try:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = dict_factory
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM products WHERE category_id = ?", (category_id,))
        products = cursor.fetchall()
        
        # Получаем изображения для каждого продукта
        for product in products:
            cursor.execute(
                "SELECT image_url FROM product_images WHERE product_id = ?", 
                (product['id'],)
            )
            image_urls = [row['image_url'] for row in cursor.fetchall()]
            product['image_urls'] = image_urls
        
        conn.close()
        return products
    except Exception as e:
        print(f"Ошибка при получении списка продуктов: {e}")
        return []

def get_product(product_id: int) -> Optional[Dict[str, Any]]:
    """Получает информацию о продукте по ID"""
    if not SQLITE_AVAILABLE:
        return None
    
    try:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = dict_factory
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM products WHERE id = ?", (product_id,))
        product = cursor.fetchone()
        
        if product:
            # Получаем изображения продукта
            cursor.execute(
                "SELECT image_url FROM product_images WHERE product_id = ?", 
                (product_id,)
            )
            image_urls = [row['image_url'] for row in cursor.fetchall()]
            product['image_urls'] = image_urls
        
        conn.close()
        return product
    except Exception as e:
        print(f"Ошибка при получении продукта: {e}")
        return None

def search_products(query: str) -> List[Dict[str, Any]]:
    """Поиск продуктов по названию или описанию"""
    if not SQLITE_AVAILABLE:
        return []
    
    try:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = dict_factory
        cursor = conn.cursor()
        
        # Поиск по названию и описанию
        search_param = f"%{query}%"
        cursor.execute(
            """SELECT * FROM products 
               WHERE name LIKE ? OR description LIKE ?
               LIMIT 10""",
            (search_param, search_param)
        )
        products = cursor.fetchall()
        
        # Получаем изображения для каждого продукта
        for product in products:
            cursor.execute(
                "SELECT image_url FROM product_images WHERE product_id = ?", 
                (product['id'],)
            )
            image_urls = [row['image_url'] for row in cursor.fetchall()]
            product['image_urls'] = image_urls
        
        conn.close()
        return products
    except Exception as e:
        print(f"Ошибка при поиске продуктов: {e}")
        return []

# Функции для работы с тестами
def add_test(test_data: Dict[str, Any]) -> Optional[int]:
    """Добавляет новый тест"""
    if not SQLITE_AVAILABLE:
        return None
    
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        now = datetime.now().isoformat()
        
        # Добавляем тест
        cursor.execute(
            """INSERT INTO tests 
               (title, description, category_id, passing_score, is_active, created_at, created_by)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                test_data.get('title', ''),
                test_data.get('description', ''),
                test_data.get('category_id'),
                test_data.get('passing_score', 70),
                test_data.get('is_active', 1),
                now,
                test_data.get('created_by')
            )
        )
        
        # Получаем ID добавленного теста
        test_id = cursor.lastrowid
        
        # Добавляем вопросы теста
        if 'questions' in test_data and isinstance(test_data['questions'], list):
            for question_data in test_data['questions']:
                cursor.execute(
                    """INSERT INTO questions 
                       (test_id, text, correct_option, explanation)
                       VALUES (?, ?, ?, ?)""",
                    (
                        test_id,
                        question_data.get('text', ''),
                        question_data.get('correct_option', 0),
                        question_data.get('explanation', '')
                    )
                )
                
                # Получаем ID добавленного вопроса
                question_id = cursor.lastrowid
                
                # Добавляем варианты ответа
                if 'options' in question_data and isinstance(question_data['options'], list):
                    for idx, option_text in enumerate(question_data['options']):
                        cursor.execute(
                            """INSERT INTO options 
                               (question_id, option_text, option_index)
                               VALUES (?, ?, ?)""",
                            (question_id, option_text, idx)
                        )
        
        conn.commit()
        conn.close()
        return test_id
    except Exception as e:
        print(f"Ошибка при добавлении теста: {e}")
        return None

def get_tests_list() -> List[Dict[str, Any]]:
    """Получает список всех тестов"""
    if not SQLITE_AVAILABLE:
        return []
    
    try:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = dict_factory
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM tests WHERE is_active = 1")
        tests = cursor.fetchall()
        
        conn.close()
        return tests
    except Exception as e:
        print(f"Ошибка при получении списка тестов: {e}")
        return []

def get_test(test_id: int) -> Optional[Dict[str, Any]]:
    """Получает информацию о тесте по ID"""
    if not SQLITE_AVAILABLE:
        return None
    
    try:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = dict_factory
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM tests WHERE id = ?", (test_id,))
        test = cursor.fetchone()
        
        if test:
            # Получаем вопросы теста
            cursor.execute("SELECT * FROM questions WHERE test_id = ?", (test_id,))
            questions = cursor.fetchall()
            
            # Получаем варианты ответа для каждого вопроса
            for question in questions:
                cursor.execute(
                    """SELECT option_text, option_index FROM options 
                       WHERE question_id = ? ORDER BY option_index""",
                    (question['id'],)
                )
                options_data = cursor.fetchall()
                options = [''] * len(options_data)
                for option in options_data:
                    options[option['option_index']] = option['option_text']
                question['options'] = options
            
            test['questions'] = questions
        
        conn.close()
        return test
    except Exception as e:
        print(f"Ошибка при получении теста: {e}")
        return None

def save_test_attempt(attempt_data: Dict[str, Any]) -> Optional[int]:
    """Сохраняет результат прохождения теста"""
    if not SQLITE_AVAILABLE:
        return None
    
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        now = datetime.now().isoformat()
        
        cursor.execute(
            """INSERT INTO test_attempts 
               (user_id, test_id, score, max_score, completed, started_at, completed_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                attempt_data.get('user_id'),
                attempt_data.get('test_id'),
                attempt_data.get('score', 0),
                attempt_data.get('max_score', 0),
                attempt_data.get('completed', 0),
                attempt_data.get('started_at', now),
                now if attempt_data.get('completed') else None
            )
        )
        
        # Получаем ID добавленной попытки
        attempt_id = cursor.lastrowid
        
        # Добавляем ответы пользователя
        if 'answers' in attempt_data and isinstance(attempt_data['answers'], list):
            for answer in attempt_data['answers']:
                cursor.execute(
                    """INSERT INTO user_answers 
                       (attempt_id, question_id, selected_option, is_correct)
                       VALUES (?, ?, ?, ?)""",
                    (
                        attempt_id,
                        answer.get('question_id'),
                        answer.get('selected_option'),
                        1 if answer.get('is_correct') else 0
                    )
                )
        
        conn.commit()
        conn.close()
        return attempt_id
    except Exception as e:
        print(f"Ошибка при сохранении результата теста: {e}")
        return None

# Инициализация при импорте модуля
init_sqlite()
