
import sqlite3
import os
import logging
from threading import Lock
from datetime import datetime
from typing import Dict, List, Optional, Any, Union

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Константы для работы с базой данных
DB_FILE = "morkovka_bot.db"
DB_TIMEOUT = 30  # seconds for connection timeout

# Блокировка для конкурентного доступа
db_lock = Lock()

def dict_factory(cursor, row):
    """Преобразует строки SQLite в словари"""
    return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}

class Database:
    """Основной класс для работы с базой данных"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.conn = None
        self._initialized = True
        self._initialize_db()

    def _initialize_db(self):
        """Инициализация базы данных и таблиц"""
        try:
            self.conn = sqlite3.connect(
                DB_FILE,
                timeout=DB_TIMEOUT,
                check_same_thread=False
            )
            self.conn.row_factory = dict_factory
            self.conn.execute("PRAGMA foreign_keys = ON")
            
            with db_lock:
                cursor = self.conn.cursor()
        
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
        except Exception as e:
    logger.error(f"Error creating categories table: {e}")
    raise
        
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
        
        # Создаем индексы
                cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_products_category 
                ON products(category_id)
                ''')
                cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_users_telegram 
                ON users(telegram_id)
                ''')
                cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_test_attempts_user 
                ON test_attempts(user_id)
                ''')
                
                self.conn.commit()
                logger.info("Database initialized successfully")
                
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            raise
    
    def _execute(self, query: str, params: tuple = (), commit: bool = False):
        """Универсальный метод выполнения запроса"""
        try:
            with db_lock:
                cursor = self.conn.cursor()
                cursor.execute(query, params)
                if commit:
                    self.conn.commit()
                return cursor
            finally:
            cursor.close()
        except Exception as e:
            logger.error(f"Query failed: {query} - {e}")
            raise

    # === User Operations ===
    def register_user(self, user_data: Dict) -> bool:
        """Регистрирует или обновляет пользователя"""
        now = datetime.now().isoformat()
        params = (
            user_data['telegram_id'],
            user_data.get('first_name', ''),
            user_data.get('last_name', ''),
            user_data.get('username', ''),
            now, now
        )
        
        try:
            # Пытаемся обновить существующего пользователя
            cursor = self._execute(
                '''UPDATE users SET 
                   first_name=?, last_name=?, username=?, last_active=?
                   WHERE telegram_id=?''',
                (params[1], params[2], params[3], params[4], params[0])
            
            if cursor.rowcount == 0:
                # Если пользователь не найден, создаем нового
                self._execute(
                    '''INSERT INTO users 
                       (telegram_id, first_name, last_name, username, created_at, last_active)
                       VALUES (?, ?, ?, ?, ?, ?)''',
                    params, commit=True)
            return True
        except Exception as e:
            logger.error(f"Failed to register user: {e}")
            return False
    
    def get_user(self, telegram_id: int) -> Optional[Dict]:
        """Получает данные пользователя"""
        cursor = self._execute(
            "SELECT * FROM users WHERE telegram_id=?", 
            (telegram_id,))
        return cursor.fetchone()

    # === Category Operations ===
    def add_category(self, category_data: Dict) -> Optional[int]:
        """Добавляет новую категорию"""
        cursor = self._execute(
            '''INSERT INTO categories 
               (name, description, image_url, order_num)
               VALUES (?, ?, ?, ?)''',
            (
                category_data['name'],
                category_data.get('description', ''),
                category_data.get('image_url', ''),
                category_data.get('order_num', 0)
            ), commit=True)
        return cursor.lastrowid
    
    def get_categories(self) -> List[Dict]:
        """Получает список категорий"""
        cursor = self._execute(
            "SELECT * FROM categories ORDER BY order_num")
        return cursor.fetchall()

    # === Product Operations ===
    def add_product(self, product_data: Dict) -> Optional[int]:
        """Добавляет новый продукт"""
        now = datetime.now().isoformat()
        
        try:
            with db_lock:
                self.conn.execute("BEGIN TRANSACTION")
                cursor = self.conn.cursor()
                
                # Добавляем продукт
                cursor.execute(
                    '''INSERT INTO products 
                       (name, category_id, description, price_info, storage_conditions, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?)''',
                    (
                        product_data['name'],
                        product_data['category_id'],
                        product_data.get('description', ''),
                        product_data.get('price_info', ''),
                        product_data.get('storage_conditions', ''),
                        now, now
                    ))
                
                product_id = cursor.lastrowid
                
                # Добавляем изображения
                for image_url in product_data.get('image_urls', []):
                    cursor.execute(
                        "INSERT INTO product_images (product_id, image_url) VALUES (?, ?)",
                        (product_id, image_url))
                
                self.conn.commit()
                return product_id
        except Exception as e:
            self.conn.rollback()
        raise
            logger.error(f"Failed to add product: {e}")
            return None
    
    def get_products_by_category(self, category_id: int) -> List[Dict]:
        """Получает продукты категории"""
        cursor = self._execute('''
            SELECT p.*, 
                   (SELECT GROUP_CONCAT(image_url) 
                    FROM product_images pi 
                    WHERE pi.product_id = p.id) as image_urls
            FROM products p
            WHERE p.category_id = ?
        ''', (category_id,))
        
        products = cursor.fetchall()
        for p in products:
            p['image_urls'] = p['image_urls'].split(',') if p['image_urls'] else []
        return products

def search_products(self, search_query: str, limit: int = 10) -> List[Dict]:
    """
    Поиск продуктов по названию и описанию с пагинацией
    :param search_query: Строка для поиска
    :param limit: Максимальное количество результатов
    :return: Список найденных продуктов с изображениями
    """
    if not search_query or len(search_query.strip()) < 2:
        return []

    safe_query = search_query.strip().replace("%", "").lower()
    search_term = f"%{safe_query}%"
    
    try:
        cursor = self._execute('''
            SELECT p.*, 
                   (SELECT GROUP_CONCAT(image_url) 
                    FROM product_images pi 
                    WHERE pi.product_id = p.id) as image_urls
            FROM products p
            WHERE LOWER(p.name) LIKE ? 
               OR LOWER(p.description) LIKE ?
            LIMIT ?
        ''', (search_term, search_term, limit))
        
        products = cursor.fetchall()
        
        # Преобразуем строку с URL в список
        for product in products:
            product['image_urls'] = (
                product['image_urls'].split(',') 
                if product['image_urls'] 
                else []
            )
        
        return products
    
    except Exception as e:
        logger.error(f"Product search failed for '{search_query}': {e}")
        return []

# === Test Operations ===
    def add_test(self, test_data: Dict) -> Optional[int]:
        """Добавляет новый тест с вопросами"""
        now = datetime.now().isoformat()
        
        try:
            with db_lock:
                cursor = self.conn.cursor()
                
                # Добавляем тест
                cursor.execute(
                    '''INSERT INTO tests 
                       (title, description, category_id, passing_score, is_active, created_at, created_by)
                       VALUES (?, ?, ?, ?, ?, ?, ?)''',
                    (
                        test_data['title'],
                        test_data.get('description', ''),
                        test_data.get('category_id'),
                        test_data.get('passing_score', 70),
                        test_data.get('is_active', 1),
                        now,
                        test_data['created_by']
                    ))
                
                test_id = cursor.lastrowid
                
                # Добавляем вопросы
                for question in test_data.get('questions', []):
                    cursor.execute(
                        '''INSERT INTO questions 
                           (test_id, text, correct_option, explanation)
                           VALUES (?, ?, ?, ?)''',
                        (
                            test_id,
                            question['text'],
                            question['correct_option'],
                            question.get('explanation', '')
                        ))
                    
                    question_id = cursor.lastrowid
                    
                    # Добавляем варианты ответа
                    for idx, option in enumerate(question.get('options', [])):
                        cursor.execute(
                            '''INSERT INTO options 
                               (question_id, option_text, option_index)
                               VALUES (?, ?, ?)''',
                            (question_id, option, idx))
                
                self.conn.commit()
                return test_id
        except Exception as e:
            logger.error(f"Failed to add test: {e}")
            return None
    
    def get_test(self, test_id: int) -> Optional[Dict]:
        """Получает тест с вопросами и вариантами ответов"""
        cursor = self._execute(
            "SELECT * FROM tests WHERE id=?", 
            (test_id,))
        test = cursor.fetchone()
        
        if not test:
            return None
        
        # Получаем вопросы
        cursor = self._execute(
            "SELECT * FROM questions WHERE test_id=?", 
            (test_id,))
        questions = cursor.fetchall()
        
        for q in questions:
            # Получаем варианты ответа
            cursor = self._execute(
                "SELECT option_text FROM options WHERE question_id=? ORDER BY option_index",
                (q['id'],))
            q['options'] = [row['option_text'] for row in cursor.fetchall()]
        
        test['questions'] = questions
        return test
    
    # === Test Attempts ===
    def save_test_attempt(self, attempt_data: Dict) -> Optional[int]:
        """Сохраняет результат тестирования"""
        now = datetime.now().isoformat()
        
        try:
            with db_lock:
                cursor = self.conn.cursor()
                
                cursor.execute(
                    '''INSERT INTO test_attempts 
                       (user_id, test_id, score, max_score, completed, started_at, completed_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?)''',
                    (
                        attempt_data['user_id'],
                        attempt_data['test_id'],
                        attempt_data['score'],
                        attempt_data['max_score'],
                        attempt_data.get('completed', 1),
                        attempt_data.get('started_at', now),
                        now if attempt_data.get('completed', 1) else None
                    ))
                
                attempt_id = cursor.lastrowid
                
                # Сохраняем ответы
                for answer in attempt_data.get('answers', []):
                    cursor.execute(
                        '''INSERT INTO user_answers 
                           (attempt_id, question_id, selected_option, is_correct)
                           VALUES (?, ?, ?, ?)''',
                        (
                            attempt_id,
                            answer['question_id'],
                            answer['selected_option'],
                            1 if answer['is_correct'] else 0
                        ))
                
                self.conn.commit()
                return attempt_id
        except Exception as e:
            logger.error(f"Failed to save test attempt: {e}")
            return None
    
    def close(self):
        """Закрывает соединение с базой данных"""
        if self.conn:
            self.conn.close()
            self.conn = None

# Синглтон экземпляр базы данных
db = Database()

# Инициализация при импорте
if __name__ == '__main__':
    # Тестовая проверка соединения
    try:
        test_conn = sqlite3.connect(DB_FILE)
        test_conn.close()
        logger.info("Database connection test successful")
    except Exception as e:
        logger.error(f"Database connection test failed: {e}")
