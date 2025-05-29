import sqlite3
import os
import logging
from threading import Lock
from datetime import datetime
from typing import Dict, List, Optional, Any, Union, Tuple
from contextlib import contextmanager

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Константы для работы с базой данных
DB_FILE = "morkovka_bot.db"
DB_TIMEOUT = 30  # seconds for connection timeout
DB_BACKUP_DIR = "backups"  # directory for database backups

# Флаг доступности SQLite
SQLITE_AVAILABLE = True

# Блокировка для конкурентного доступа
db_lock = Lock()

def dict_factory(cursor, row):
    """Преобразует строки SQLite в словари"""
    return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}

class DatabaseError(Exception):
    """Base exception for database errors"""
    pass

class DatabaseConnectionError(DatabaseError):
    """Raised when database connection fails"""
    pass

class DatabaseQueryError(DatabaseError):
    """Raised when a database query fails"""
    pass

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
        self._connection_attempts = 0
        self._max_connection_attempts = 3
        
        try:
        self._initialize_db()
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            global SQLITE_AVAILABLE
            SQLITE_AVAILABLE = False
            raise DatabaseConnectionError(f"Database initialization failed: {e}")

    def _initialize_db(self):
        """Инициализация базы данных и таблиц"""
        try:
            # Ensure backup directory exists
            os.makedirs(DB_BACKUP_DIR, exist_ok=True)
            
            # Create backup before any schema changes
            self._backup_database()
            
            self.conn = sqlite3.connect(
                DB_FILE,
                timeout=DB_TIMEOUT,
                check_same_thread=False,
                isolation_level=None  # Enable autocommit mode
            )
            self.conn.row_factory = dict_factory
            self.conn.execute("PRAGMA foreign_keys = ON")
            self.conn.execute("PRAGMA journal_mode = WAL")  # Enable Write-Ahead Logging
            self.conn.execute("PRAGMA synchronous = NORMAL")  # Better performance with WAL
            
            with self._get_cursor() as cursor:
                # Create tables if they don't exist
                self._create_tables(cursor)
                
            logger.info("Database initialized successfully")
            
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            if self.conn:
                try:
                    self.conn.close()
                except:
                    pass
                self.conn = None
            raise DatabaseConnectionError(f"Database initialization failed: {e}")

    def _backup_database(self):
        """Create a backup of the database before making changes"""
        if not os.path.exists(DB_FILE):
            return
            
        backup_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = os.path.join(DB_BACKUP_DIR, f"backup_{backup_time}.db")
        
        try:
            # Create a backup using SQLite's backup API
            source = sqlite3.connect(DB_FILE)
            destination = sqlite3.connect(backup_file)
            
            source.backup(destination)
            
            destination.close()
            source.close()
            
            logger.info(f"Database backup created: {backup_file}")
        except Exception as e:
            logger.error(f"Failed to create database backup: {e}")

    @contextmanager
    def _get_cursor(self):
        """Context manager for database cursor"""
        cursor = None
        try:
            with db_lock:
                if not self._check_connection():
                    self._reconnect()
                cursor = self.conn.cursor()
                yield cursor
                self.conn.commit()
        except Exception as e:
            if self.conn:
                self.conn.rollback()
            raise DatabaseQueryError(f"Database operation failed: {e}")
        finally:
            if cursor:
                cursor.close()

    def _reconnect(self):
        """Attempt to reconnect to the database"""
        if self._connection_attempts >= self._max_connection_attempts:
            raise DatabaseConnectionError("Max connection attempts reached")
            
        self._connection_attempts += 1
        logger.warning(f"Attempting to reconnect to database (attempt {self._connection_attempts})")
        
        try:
            if self.conn:
                try:
                    self.conn.close()
                except:
                    pass
                self.conn = None
            
            self.conn = sqlite3.connect(
                DB_FILE,
                timeout=DB_TIMEOUT,
                check_same_thread=False,
                isolation_level=None
            )
            self.conn.row_factory = dict_factory
            self.conn.execute("PRAGMA foreign_keys = ON")
            self.conn.execute("PRAGMA journal_mode = WAL")
            self.conn.execute("PRAGMA synchronous = NORMAL")
            
            self._connection_attempts = 0
            logger.info("Database reconnected successfully")
        except Exception as e:
            logger.error(f"Database reconnection failed: {e}")
            raise DatabaseConnectionError(f"Failed to reconnect to database: {e}")

    def _check_connection(self) -> bool:
        """Check if the database connection is alive"""
        try:
            with db_lock:
                if not self.conn:
                    return False
                # Try a simple query
                self.conn.execute("SELECT 1")
                return True
        except Exception:
            return False

    def _execute(self, query: str, params: tuple = None, commit: bool = False) -> List[Dict]:
        """Execute a database query with proper cursor management and return results"""
        with self._get_cursor() as cursor:
            try:
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                return cursor.fetchall()
            except Exception as e:
                logger.error(f"Database error executing query: {query}, params: {params}, error: {e}")
                raise DatabaseQueryError(f"Query execution failed: {e}")

    def _execute_one(self, query: str, params: tuple = None, commit: bool = False) -> Optional[Dict]:
        """Execute a database query and return a single result"""
        with self._get_cursor() as cursor:
            try:
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                return cursor.fetchone()
            except Exception as e:
                logger.error(f"Database error executing query: {query}, params: {params}, error: {e}")
                raise DatabaseQueryError(f"Query execution failed: {e}")

    def _execute_many(self, query: str, params_list: List[tuple], commit: bool = False) -> None:
        """Execute multiple database queries in a transaction"""
        with self._get_cursor() as cursor:
            try:
                cursor.executemany(query, params_list)
            except Exception as e:
                logger.error(f"Database error executing many queries: {query}, error: {e}")
                raise DatabaseQueryError(f"Batch query execution failed: {e}")

    # === User Operations ===
    def register_user(self, user_data: Dict) -> bool:
        """Register or update a user"""
        now = datetime.now().isoformat()
        try:
            # Try to update existing user
            result = self._execute_one(
                '''UPDATE users SET 
                   first_name=?, last_name=?, username=?, last_active=?
                   WHERE telegram_id=?''',
                (
                    user_data.get('first_name', ''),
                    user_data.get('last_name', ''),
                    user_data.get('username', ''),
                    now,
                    user_data['telegram_id']
                )
            )
            
            if not result:
                # If user not found, create new one
                self._execute_one(
                    '''INSERT INTO users 
                       (telegram_id, first_name, last_name, username, created_at, last_active)
                       VALUES (?, ?, ?, ?, ?, ?)''',
                    (
                        user_data['telegram_id'],
                        user_data.get('first_name', ''),
                        user_data.get('last_name', ''),
                        user_data.get('username', ''),
                        now,
                        now
                    ),
                    commit=True
                )
            return True
        except DatabaseError as e:
            logger.error(f"Failed to register user: {e}")
            return False
    
    def get_user(self, telegram_id: int) -> Optional[Dict]:
        """Get user data by telegram_id"""
        try:
            return self._execute_one(
                "SELECT * FROM users WHERE telegram_id=?", 
                (telegram_id,)
            )
        except DatabaseError as e:
            logger.error(f"Failed to get user: {e}")
            return None

    def update_user_state(self, telegram_id: int, state: str, state_data: str = None) -> bool:
        """Update user's state and state data"""
        try:
            self._execute_one(
                '''UPDATE users 
                   SET state=?, state_data=?, last_active=datetime('now')
                   WHERE telegram_id=?''',
                (state, state_data, telegram_id),
                commit=True
            )
            return True
        except DatabaseError as e:
            logger.error(f"Failed to update user state: {e}")
            return False

    def get_user_state(self, telegram_id: int) -> Optional[Dict]:
        """Get user's current state and state data"""
        try:
            return self._execute_one(
                "SELECT state, state_data FROM users WHERE telegram_id=?",
                (telegram_id,)
            )
        except DatabaseError as e:
            logger.error(f"Failed to get user state: {e}")
            return None

    # === Category Operations ===
    def add_category(self, category_data: Dict) -> Optional[int]:
        """Add a new category"""
        try:
            now = datetime.now().isoformat()
            result = self._execute_one(
                '''INSERT INTO categories 
                   (name, description, image_url, order_num, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?)''',
                (
                    category_data['name'],
                    category_data.get('description', ''),
                    category_data.get('image_url', ''),
                    category_data.get('order_num', 0),
                    now,
                    now
                ),
                commit=True
            )
            return result['id'] if result else None
        except DatabaseError as e:
            logger.error(f"Failed to add category: {e}")
            return None

    def get_categories(self, include_inactive: bool = False) -> List[Dict]:
        """Get list of categories"""
        try:
            query = "SELECT * FROM categories"
            if not include_inactive:
                query += " WHERE is_active = 1"
            query += " ORDER BY order_num, name"
            return self._execute(query)
        except DatabaseError as e:
            logger.error(f"Failed to get categories: {e}")
            return []

    def update_category(self, category_id: int, category_data: Dict) -> bool:
        """Update category data"""
        try:
            self._execute_one(
                '''UPDATE categories 
                   SET name=?, description=?, image_url=?, order_num=?, is_active=?
                   WHERE id=?''',
                (
                    category_data['name'],
                    category_data.get('description', ''),
                    category_data.get('image_url', ''),
                    category_data.get('order_num', 0),
                    category_data.get('is_active', 1),
                    category_id
                ),
                commit=True
            )
            return True
        except DatabaseError as e:
            logger.error(f"Failed to update category: {e}")
            return False

    def delete_category(self, category_id: int) -> bool:
        """Delete a category and all its products"""
        try:
            self._execute_one(
                "DELETE FROM categories WHERE id=?",
                (category_id,),
                commit=True
            )
            return True
        except DatabaseError as e:
            logger.error(f"Failed to delete category: {e}")
            return False

    # === Product Operations ===
    def add_product(self, product_data: Dict) -> Optional[int]:
        """Add a new product with images"""
        try:
            now = datetime.now().isoformat()
            with self._get_cursor() as cursor:
                # Add product
                cursor.execute(
                    '''INSERT INTO products 
                       (name, category_id, description, price_info, storage_conditions, 
                        created_at, updated_at, is_active)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                    (
                        product_data['name'],
                        product_data['category_id'],
                        product_data.get('description', ''),
                        product_data.get('price_info', ''),
                        product_data.get('storage_conditions', ''),
                        now,
                        now,
                        product_data.get('is_active', 1)
                    )
                )
                product_id = cursor.lastrowid
                
                # Add images
                if product_data.get('image_urls'):
                    image_data = [
                        (product_id, url, idx, now)
                        for idx, url in enumerate(product_data['image_urls'])
                    ]
                    cursor.executemany(
                        '''INSERT INTO product_images 
                           (product_id, image_url, order_num, created_at)
                           VALUES (?, ?, ?, ?)''',
                        image_data
                    )
                
                self.conn.commit()
                return product_id
        except DatabaseError as e:
            logger.error(f"Failed to add product: {e}")
            return None

    def get_products_by_category(self, category_id: int, include_inactive: bool = False) -> List[Dict]:
        """Get products by category"""
        try:
            query = '''
                SELECT p.*, 
                       (SELECT GROUP_CONCAT(image_url) 
                        FROM product_images pi 
                        WHERE pi.product_id = p.id
                        ORDER BY pi.order_num) as image_urls
                FROM products p
                WHERE p.category_id = ?
            '''
            if not include_inactive:
                query += " AND p.is_active = 1"
            query += " ORDER BY p.name"
            
            products = self._execute(query, (category_id,))
            
            # Convert image_urls string to list
            for p in products:
                p['image_urls'] = p['image_urls'].split(',') if p['image_urls'] else []
            
            return products
        except DatabaseError as e:
            logger.error(f"Failed to get products: {e}")
            return []

    def update_product(self, product_id: int, product_data: Dict) -> bool:
        """Update product data"""
        try:
            now = datetime.now().isoformat()
            with self._get_cursor() as cursor:
                # Update product
                cursor.execute(
                    '''UPDATE products 
                       SET name=?, category_id=?, description=?, price_info=?,
                           storage_conditions=?, is_active=?, updated_at=?
                       WHERE id=?''',
                    (
                        product_data['name'],
                        product_data['category_id'],
                        product_data.get('description', ''),
                        product_data.get('price_info', ''),
                        product_data.get('storage_conditions', ''),
                        product_data.get('is_active', 1),
                        now,
                        product_id
                    )
                )
                
                # Update images if provided
                if 'image_urls' in product_data:
                    # Delete old images
                    cursor.execute(
                        "DELETE FROM product_images WHERE product_id=?",
                        (product_id,)
                    )
                    
                    # Add new images
                    if product_data['image_urls']:
                        image_data = [
                            (product_id, url, idx, now)
                            for idx, url in enumerate(product_data['image_urls'])
                        ]
                        cursor.executemany(
                            '''INSERT INTO product_images 
                               (product_id, image_url, order_num, created_at)
                               VALUES (?, ?, ?, ?)''',
                            image_data
                        )
                
                self.conn.commit()
                return True
        except DatabaseError as e:
            logger.error(f"Failed to update product: {e}")
            return False

    def delete_product(self, product_id: int) -> bool:
        """Delete a product and its images"""
        try:
            self._execute_one(
                "DELETE FROM products WHERE id=?",
                (product_id,),
                commit=True
            )
            return True
        except DatabaseError as e:
            logger.error(f"Failed to delete product: {e}")
            return False

    # === Test Operations ===
    def add_test(self, test_data: Dict) -> Optional[int]:
        """Add a new test with questions and options"""
        try:
            now = datetime.now().isoformat()
            with self._get_cursor() as cursor:
                # Add test
                cursor.execute(
                    '''INSERT INTO tests 
                       (title, description, category_id, passing_score, time_limit,
                        is_active, created_at, updated_at, created_by)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                    (
                        test_data['title'],
                        test_data.get('description', ''),
                        test_data.get('category_id'),
                        test_data.get('passing_score', 70),
                        test_data.get('time_limit', 0),
                        test_data.get('is_active', 1),
                        now,
                        now,
                        test_data['created_by']
                    )
                )
                test_id = cursor.lastrowid
                
                # Add questions and options
                for q_idx, question in enumerate(test_data.get('questions', [])):
                    cursor.execute(
                        '''INSERT INTO questions 
                           (test_id, text, correct_option, explanation, order_num,
                            created_at, updated_at)
                           VALUES (?, ?, ?, ?, ?, ?, ?)''',
                        (
                            test_id,
                            question['text'],
                            question['correct_option'],
                            question.get('explanation', ''),
                            q_idx,
                            now,
                            now
                        )
                    )
                    question_id = cursor.lastrowid
                    
                    # Add options
                    option_data = [
                        (question_id, option, idx, now)
                        for idx, option in enumerate(question.get('options', []))
                    ]
                    cursor.executemany(
                        '''INSERT INTO options 
                           (question_id, option_text, option_index, created_at)
                           VALUES (?, ?, ?, ?)''',
                        option_data
                    )
                
                self.conn.commit()
                return test_id
        except DatabaseError as e:
            logger.error(f"Failed to add test: {e}")
            return None

    def get_test(self, test_id: int) -> Optional[Dict]:
        """Get test with questions and options"""
        try:
            # Get test data
            test = self._execute_one(
                "SELECT * FROM tests WHERE id=?", 
                (test_id,)
            )
            
            if not test:
                return None
            
            # Get questions
            questions = self._execute(
                "SELECT * FROM questions WHERE test_id=? ORDER BY order_num",
                (test_id,)
            )
            
            # Get options for each question
            for q in questions:
                options = self._execute(
                    "SELECT * FROM options WHERE question_id=? ORDER BY option_index",
                    (q['id'],)
                )
                q['options'] = [opt['option_text'] for opt in options]
            
            test['questions'] = questions
            return test
        except DatabaseError as e:
            logger.error(f"Failed to get test: {e}")
            return None

    def get_tests_list(self, include_inactive: bool = False) -> List[Dict]:
        """Get list of all tests with statistics"""
        try:
            query = '''
                SELECT t.*, 
                       (SELECT COUNT(*) FROM questions WHERE test_id = t.id) as questions_count,
                       (SELECT COUNT(*) FROM test_attempts WHERE test_id = t.id) as attempts_count,
                       (SELECT COUNT(*) FROM test_attempts 
                        WHERE test_id = t.id AND completed = 1) as completed_attempts,
                       (SELECT AVG(CAST(score AS FLOAT) / max_score * 100)
                        FROM test_attempts 
                        WHERE test_id = t.id AND completed = 1) as avg_score
                FROM tests t
            '''
            if not include_inactive:
                query += " WHERE t.is_active = 1"
            query += " ORDER BY t.created_at DESC"
            
            return self._execute(query)
        except DatabaseError as e:
            logger.error(f"Failed to get tests list: {e}")
            return []

    def update_test(self, test_id: int, test_data: Dict) -> bool:
        """Update test data"""
        try:
            now = datetime.now().isoformat()
            with self._get_cursor() as cursor:
                # Update test
                cursor.execute(
                    '''UPDATE tests 
                       SET title=?, description=?, category_id=?, passing_score=?,
                           time_limit=?, is_active=?, updated_at=?
                       WHERE id=?''',
                    (
                        test_data['title'],
                        test_data.get('description', ''),
                        test_data.get('category_id'),
                        test_data.get('passing_score', 70),
                        test_data.get('time_limit', 0),
                        test_data.get('is_active', 1),
                        now,
                        test_id
                    )
                )
                
                # Update questions if provided
                if 'questions' in test_data:
                    # Delete old questions (and their options via CASCADE)
                    cursor.execute(
                        "DELETE FROM questions WHERE test_id=?",
                        (test_id,)
                    )
                    
                    # Add new questions
                    for q_idx, question in enumerate(test_data['questions']):
                        cursor.execute(
                            '''INSERT INTO questions 
                               (test_id, text, correct_option, explanation, order_num,
                                created_at, updated_at)
                               VALUES (?, ?, ?, ?, ?, ?, ?)''',
                            (
                                test_id,
                                question['text'],
                                question['correct_option'],
                                question.get('explanation', ''),
                                q_idx,
                                now,
                                now
                            )
                        )
                        question_id = cursor.lastrowid
                        
                        # Add options
                        option_data = [
                            (question_id, option, idx, now)
                            for idx, option in enumerate(question.get('options', []))
                        ]
                        cursor.executemany(
                            '''INSERT INTO options 
                               (question_id, option_text, option_index, created_at)
                               VALUES (?, ?, ?, ?)''',
                            option_data
                        )
                
                self.conn.commit()
                return True
        except DatabaseError as e:
            logger.error(f"Failed to update test: {e}")
            return False

    def delete_test(self, test_id: int) -> bool:
        """Delete a test and all its questions and options"""
        try:
            self._execute_one(
                "DELETE FROM tests WHERE id=?",
                (test_id,),
                commit=True
            )
            return True
        except DatabaseError as e:
            logger.error(f"Failed to delete test: {e}")
            return False

    # === Test Attempts ===
    def save_test_attempt(self, attempt_data: Dict) -> Optional[int]:
        """Save test attempt with answers"""
        try:
            now = datetime.now().isoformat()
            with self._get_cursor() as cursor:
                # Add attempt
                cursor.execute(
                    '''INSERT INTO test_attempts 
                       (user_id, test_id, score, max_score, completed,
                        started_at, completed_at, time_spent)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                    (
                        attempt_data['user_id'],
                        attempt_data['test_id'],
                        attempt_data['score'],
                        attempt_data['max_score'],
                        attempt_data.get('completed', 1),
                        attempt_data.get('started_at', now),
                        now if attempt_data.get('completed', 1) else None,
                        attempt_data.get('time_spent', 0)
                    )
                )
                attempt_id = cursor.lastrowid
                
                # Add answers
                if attempt_data.get('answers'):
                    answer_data = [
                        (
                            attempt_id,
                            answer['question_id'],
                            answer['selected_option'],
                            1 if answer['is_correct'] else 0,
                            answer.get('answer_time', 0),
                            now
                        )
                        for answer in attempt_data['answers']
                    ]
                    cursor.executemany(
                        '''INSERT INTO user_answers 
                           (attempt_id, question_id, selected_option, is_correct,
                            answer_time, created_at)
                           VALUES (?, ?, ?, ?, ?, ?)''',
                        answer_data
                    )
                
                self.conn.commit()
                return attempt_id
        except DatabaseError as e:
            logger.error(f"Failed to save test attempt: {e}")
            return None

    def get_user_attempts(self, user_id: int, test_id: Optional[int] = None) -> List[Dict]:
        """Get user's test attempts"""
        try:
            query = '''
                SELECT ta.*, t.title as test_title,
                       (SELECT COUNT(*) FROM user_answers 
                        WHERE attempt_id = ta.id) as total_answers,
                       (SELECT COUNT(*) FROM user_answers 
                        WHERE attempt_id = ta.id AND is_correct = 1) as correct_answers
                FROM test_attempts ta
                JOIN tests t ON ta.test_id = t.id
                WHERE ta.user_id = ?
            '''
            params = [user_id]
            
            if test_id:
                query += " AND ta.test_id = ?"
                params.append(test_id)
            
            query += " ORDER BY ta.started_at DESC"
            
            return self._execute(query, tuple(params))
        except DatabaseError as e:
            logger.error(f"Failed to get user attempts: {e}")
            return []

    def get_attempt_details(self, attempt_id: int) -> Optional[Dict]:
        """Get detailed information about a test attempt"""
        try:
            # Get attempt data
            attempt = self._execute_one(
                '''SELECT ta.*, t.title as test_title, t.passing_score,
                          u.first_name, u.last_name, u.username
                   FROM test_attempts ta
                   JOIN tests t ON ta.test_id = t.id
                   JOIN users u ON ta.user_id = u.id
                   WHERE ta.id = ?''',
                (attempt_id,)
            )
            
            if not attempt:
                return None
            
            # Get answers
            answers = self._execute(
                '''SELECT ua.*, q.text as question_text, q.explanation,
                          (SELECT option_text FROM options 
                           WHERE question_id = q.id AND option_index = ua.selected_option) 
                           as selected_option_text
                   FROM user_answers ua
                   JOIN questions q ON ua.question_id = q.id
                   WHERE ua.attempt_id = ?
                   ORDER BY ua.id''',
                (attempt_id,)
            )
            
            attempt['answers'] = answers
            return attempt
        except DatabaseError as e:
            logger.error(f"Failed to get attempt details: {e}")
            return None

    # === Statistics ===
    def get_test_stats(self) -> Dict:
        """Get test statistics"""
        try:
            stats = self._execute_one('''
                SELECT 
                    COUNT(DISTINCT t.id) as total_tests,
                    COUNT(DISTINCT ta.user_id) as total_users,
                    COUNT(DISTINCT ta.id) as total_attempts,
                    COUNT(DISTINCT CASE WHEN ta.completed = 1 THEN ta.id END) as completed_attempts,
                    AVG(CASE WHEN ta.completed = 1 
                        THEN CAST(ta.score AS FLOAT) / ta.max_score * 100 
                        ELSE NULL END) as avg_score,
                    AVG(ta.time_spent) as avg_time_spent
                FROM tests t
                LEFT JOIN test_attempts ta ON t.id = ta.test_id
            ''')
            
            return stats or {
                'total_tests': 0,
                'total_users': 0,
                'total_attempts': 0,
                'completed_attempts': 0,
                'avg_score': 0,
                'avg_time_spent': 0
            }
        except DatabaseError as e:
            logger.error(f"Failed to get test stats: {e}")
            return {
                'total_tests': 0,
                'total_users': 0,
                'total_attempts': 0,
                'completed_attempts': 0,
                'avg_score': 0,
                'avg_time_spent': 0
            }

    def get_user_stats(self) -> Dict:
        """Get user statistics"""
        try:
            stats = self._execute_one('''
                SELECT 
                    COUNT(*) as total_users,
                    COUNT(CASE WHEN is_admin = 1 THEN 1 END) as admin_users,
                    COUNT(CASE WHEN last_active >= datetime('now', '-7 days') THEN 1 END) as active_users_7d,
                    COUNT(CASE WHEN last_active >= datetime('now', '-30 days') THEN 1 END) as active_users_30d,
                    COUNT(DISTINCT CASE WHEN last_active >= datetime('now', '-7 days') 
                         THEN telegram_id END) as unique_active_users_7d,
                    COUNT(DISTINCT CASE WHEN last_active >= datetime('now', '-30 days') 
                         THEN telegram_id END) as unique_active_users_30d
                FROM users
            ''')
            
            return stats or {
                'total_users': 0,
                'admin_users': 0,
                'active_users_7d': 0,
                'active_users_30d': 0,
                'unique_active_users_7d': 0,
                'unique_active_users_30d': 0
            }
        except DatabaseError as e:
            logger.error(f"Failed to get user stats: {e}")
            return {
                'total_users': 0,
                'admin_users': 0,
                'active_users_7d': 0,
                'active_users_30d': 0,
                'unique_active_users_7d': 0,
                'unique_active_users_30d': 0
            }

    def _create_tables(self, cursor: sqlite3.Cursor):
        """Create database tables if they don't exist"""
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
            last_active TEXT,
            last_command TEXT,
            state TEXT,
            state_data TEXT
        )
        ''')
        
        # Таблица категорий продуктов
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            description TEXT,
            image_url TEXT,
            order_num INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            created_at TEXT,
            updated_at TEXT
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
            is_active INTEGER DEFAULT 1,
            created_at TEXT,
            updated_at TEXT,
            FOREIGN KEY (category_id) REFERENCES categories (id) ON DELETE CASCADE
        )
        ''')
        
        # Таблица изображений продукта
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS product_images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER,
            image_url TEXT,
            order_num INTEGER DEFAULT 0,
            created_at TEXT,
            FOREIGN KEY (product_id) REFERENCES products (id) ON DELETE CASCADE
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
            time_limit INTEGER,
            is_active INTEGER DEFAULT 1,
            created_at TEXT,
            updated_at TEXT,
            created_by INTEGER,
            FOREIGN KEY (category_id) REFERENCES categories (id) ON DELETE SET NULL,
            FOREIGN KEY (created_by) REFERENCES users (id) ON DELETE SET NULL
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
            order_num INTEGER DEFAULT 0,
            created_at TEXT,
            updated_at TEXT,
            FOREIGN KEY (test_id) REFERENCES tests (id) ON DELETE CASCADE
        )
        ''')
        
        # Таблица вариантов ответа
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS options (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question_id INTEGER,
            option_text TEXT,
            option_index INTEGER,
            created_at TEXT,
            FOREIGN KEY (question_id) REFERENCES questions (id) ON DELETE CASCADE
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
            time_spent INTEGER,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
            FOREIGN KEY (test_id) REFERENCES tests (id) ON DELETE CASCADE
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
            answer_time INTEGER,
            created_at TEXT,
            FOREIGN KEY (attempt_id) REFERENCES test_attempts (id) ON DELETE CASCADE,
            FOREIGN KEY (question_id) REFERENCES questions (id) ON DELETE CASCADE
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
                
        cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_test_attempts_test 
        ON test_attempts(test_id)
        ''')
        
        cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_questions_test 
        ON questions(test_id)
        ''')
        
        cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_options_question 
        ON options(question_id)
        ''')
        
        cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_user_answers_attempt 
        ON user_answers(attempt_id)
        ''')
        
        cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_user_answers_question 
        ON user_answers(question_id)
        ''')
        
        cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_product_images_product 
        ON product_images(product_id)
        ''')
        
        # Add triggers for updated_at timestamps
        cursor.execute('''
        CREATE TRIGGER IF NOT EXISTS update_category_timestamp 
        AFTER UPDATE ON categories
        BEGIN
            UPDATE categories SET updated_at = datetime('now') 
            WHERE id = NEW.id;
        END
        ''')
        
        cursor.execute('''
        CREATE TRIGGER IF NOT EXISTS update_product_timestamp 
        AFTER UPDATE ON products
        BEGIN
            UPDATE products SET updated_at = datetime('now') 
            WHERE id = NEW.id;
        END
        ''')
        
        cursor.execute('''
        CREATE TRIGGER IF NOT EXISTS update_test_timestamp 
        AFTER UPDATE ON tests
        BEGIN
            UPDATE tests SET updated_at = datetime('now') 
            WHERE id = NEW.id;
        END
        ''')
        
        cursor.execute('''
        CREATE TRIGGER IF NOT EXISTS update_question_timestamp 
        AFTER UPDATE ON questions
        BEGIN
            UPDATE questions SET updated_at = datetime('now') 
            WHERE id = NEW.id;
        END
        ''')

    def close(self):
        """Close database connection and cleanup"""
            with db_lock:
            if self.conn:
                try:
                    # Create final backup before closing
                    self._backup_database()
                    
                    # Close WAL mode
                    self.conn.execute("PRAGMA journal_mode = DELETE")
                    
                    # Close connection
                    self.conn.close()
                    logger.info("Database connection closed successfully")
        except Exception as e:
                    logger.error(f"Failed to close database connection: {e}")
                finally:
                    self.conn = None

    def vacuum(self):
        """Vacuum the database to reclaim space and optimize performance"""
        try:
            with self._get_cursor() as cursor:
                cursor.execute("VACUUM")
            logger.info("Database vacuum completed successfully")
            return True
        except DatabaseError as e:
            logger.error(f"Failed to vacuum database: {e}")
            return False

    def get_database_size(self) -> int:
        """Get the current size of the database file in bytes"""
        try:
            return os.path.getsize(DB_FILE)
        except Exception as e:
            logger.error(f"Failed to get database size: {e}")
            return 0

    def get_backup_files(self) -> List[Dict]:
        """Get list of database backup files with their sizes and timestamps"""
        try:
            backups = []
            for filename in os.listdir(DB_BACKUP_DIR):
                if filename.startswith("backup_") and filename.endswith(".db"):
                    filepath = os.path.join(DB_BACKUP_DIR, filename)
                    try:
                        timestamp = datetime.strptime(
                            filename[7:-3],  # Remove 'backup_' prefix and '.db' suffix
                            "%Y%m%d_%H%M%S"
                        )
                        backups.append({
                            'filename': filename,
                            'path': filepath,
                            'size': os.path.getsize(filepath),
                            'created_at': timestamp.isoformat()
                        })
                    except ValueError:
                        continue
            
            return sorted(backups, key=lambda x: x['created_at'], reverse=True)
    except Exception as e:
            logger.error(f"Failed to get backup files: {e}")
        return []

    def cleanup_old_backups(self, keep_last_n: int = 5) -> bool:
        """Remove old backup files keeping only the last N backups"""
        try:
            backups = self.get_backup_files()
            if len(backups) <= keep_last_n:
                return True
            
            for backup in backups[keep_last_n:]:
                try:
                    os.remove(backup['path'])
                    logger.info(f"Removed old backup: {backup['filename']}")
                except Exception as e:
                    logger.error(f"Failed to remove backup {backup['filename']}: {e}")
            
            return True
        except Exception as e:
            logger.error(f"Failed to cleanup old backups: {e}")
            return False

    def check_database_integrity(self) -> bool:
        """Check database integrity using SQLite's integrity check"""
        try:
            with self._get_cursor() as cursor:
                cursor.execute("PRAGMA integrity_check")
                result = cursor.fetchone()
                if result and result['integrity_check'] == 'ok':
                    logger.info("Database integrity check passed")
                    return True
                else:
                    logger.error("Database integrity check failed")
                    return False
        except DatabaseError as e:
            logger.error(f"Failed to check database integrity: {e}")
            return False

    def get_database_stats(self) -> Dict:
        """Get database statistics including size, number of records, etc."""
        try:
            stats = {
                'size_bytes': self.get_database_size(),
                'backup_count': len(self.get_backup_files()),
                'tables': {}
            }
            
            with self._get_cursor() as cursor:
                # Get list of tables
                cursor.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name NOT LIKE 'sqlite_%'
                """)
                tables = [row['name'] for row in cursor.fetchall()]
                
                # Get record count for each table
                for table in tables:
                    cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
                    result = cursor.fetchone()
                    stats['tables'][table] = result['count'] if result else 0
            
            return stats
        except DatabaseError as e:
            logger.error(f"Failed to get database stats: {e}")
            return {
                'size_bytes': 0,
                'backup_count': 0,
                'tables': {}
            }

    def search_products(self, query: str) -> List[Dict]:
        """Search products by name or description"""
        try:
            search_query = f"%{query}%"
            products = self._execute('''
                SELECT p.*, 
                       c.name as category_name,
                       (SELECT GROUP_CONCAT(image_url) 
                        FROM product_images pi 
                        WHERE pi.product_id = p.id
                        ORDER BY pi.order_num) as image_urls
                FROM products p
                LEFT JOIN categories c ON p.category_id = c.id
                WHERE (p.name LIKE ? OR p.description LIKE ?)
                AND p.is_active = 1
                ORDER BY 
                    CASE 
                        WHEN p.name LIKE ? THEN 1  -- Exact name match
                        WHEN p.name LIKE ? THEN 2  -- Name starts with query
                        ELSE 3                     -- Contains query
                    END,
                    p.name
                LIMIT 50
            ''', (search_query, search_query, query, f"{query}%"))
            
            # Convert image_urls string to list
            for p in products:
                p['image_urls'] = p['image_urls'].split(',') if p['image_urls'] else []
            
            return products
        except DatabaseError as e:
            logger.error(f"Failed to search products: {e}")
            return []

# Синглтон экземпляр базы данных
db = Database()

# Инициализация при импорте
if __name__ == '__main__':
    # Тестовая проверка соединения и целостности
    try:
        if db.check_database_integrity():
            logger.info("Database connection and integrity test successful")
            
            # Print database stats
            stats = db.get_database_stats()
            logger.info("Database statistics:")
            logger.info(f"Size: {stats['size_bytes'] / 1024:.2f} KB")
            logger.info(f"Backup files: {stats['backup_count']}")
            logger.info("Table record counts:")
            for table, count in stats['tables'].items():
                logger.info(f"  {table}: {count} records")
        else:
            logger.error("Database integrity check failed")
    except Exception as e:
        logger.error(f"Database test failed: {e}")
