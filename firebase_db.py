
import json
import os
from datetime import datetime
from typing import List, Dict, Any, Optional, Union

import firebase_admin
from firebase_admin import credentials, firestore, storage
from google.cloud.firestore_v1.base_query import FieldFilter

from config import FIREBASE_CREDENTIALS, ADMIN_IDS

# Инициализация Firebase
try:
    # Проверяем наличие переменной окружения FIREBASE_CREDENTIALS_JSON
    if os.environ.get("FIREBASE_CREDENTIALS_JSON"):
        try:
            cred_dict = json.loads(os.environ.get("FIREBASE_CREDENTIALS_JSON"))
            cred = credentials.Certificate(cred_dict)
        except Exception as e:
            print(f"Ошибка при чтении FIREBASE_CREDENTIALS_JSON: {e}")
            cred = None
    # Проверяем наличие переменной окружения FIREBASE_CONFIG
    elif os.environ.get("FIREBASE_CONFIG"):
        try:
            cred_dict = json.loads(os.environ.get("FIREBASE_CONFIG"))
            cred = credentials.Certificate(cred_dict)
        except Exception as e:
            print(f"Ошибка при чтении FIREBASE_CONFIG: {e}")
            cred = None
    # Проверяем наличие файла учетных данных
    elif os.path.exists("service_account.json"):
        try:
            cred = credentials.Certificate("service_account.json")
        except Exception as e:
            print(f"Ошибка при чтении service_account.json: {e}")
            cred = None
    elif os.path.exists("morkovka-kmv-bot-31365aded116.json"):
        try:
            cred = credentials.Certificate("morkovka-kmv-bot-31365aded116.json")
        except Exception as e:
            print(f"Ошибка при чтении morkovka-kmv-bot-31365aded116.json: {e}")
            cred = None
    else:
        print("Не найдены учетные данные Firebase")
        cred = None

    # Инициализируем Firebase, если у нас есть учетные данные
    if cred and not firebase_admin._apps:
        firebase_app = firebase_admin.initialize_app(cred, {
            'storageBucket': 'morkovka-kmv-bot.appspot.com'
        })
        db = firestore.client()
        bucket = storage.bucket()
        print("Firebase инициализирован успешно")
    else:
        print("Не удалось инициализировать Firebase. Используем заглушки")
        # Создаем заглушки для тестирования без Firebase
        firebase_app = None
        db = None
        bucket = None
except Exception as e:
    print(f"Критическая ошибка при инициализации Firebase: {e}")
    # Создаем заглушки для тестирования без Firebase
    firebase_app = None
    db = None
    bucket = None

# Добавляем функцию для проверки соединения с Firebase
def check_firebase_connection() -> bool:
    """Проверяет соединение с Firebase"""
    if db is None:
        return False
    try:
        # Пробуем получить список коллекций
        db.collections()
        return True
    except Exception as e:
        print(f"Ошибка при проверке соединения с Firebase: {e}")
        return False

# Вспомогательная функция для проверки наличия соединения перед каждым запросом
def check_db_before_request(func):
    """Декоратор для проверки соединения перед запросом к базе данных"""
    def wrapper(*args, **kwargs):
        if not db:
            print("Предупреждение: Firebase не инициализирован. Операция не может быть выполнена.")
            if func.__name__.startswith("get_"):
                return None if func.__annotations__.get('return') == Optional[Dict[str, Any]] else []
            elif func.__name__.startswith("add_"):
                return None
            elif func.__name__ in ["upload_file", "delete_file"]:
                return None if func.__name__ == "upload_file" else False
            return False
        return func(*args, **kwargs)
    return wrapper

# Управление пользователями
@check_db_before_request
def register_user(user_data: Dict[str, Any]) -> bool:
    """Регистрирует нового пользователя или обновляет существующего"""
    try:
        user_ref = db.collection('users').document(str(user_data['telegram_id']))
        
        # Проверяем, существует ли пользователь
        user_doc = user_ref.get()
        
        if user_doc.exists:
            # Обновляем информацию о пользователе
            user_ref.update({
                'first_name': user_data.get('first_name', ''),
                'last_name': user_data.get('last_name', ''),
                'username': user_data.get('username', ''),
                'last_active': firestore.SERVER_TIMESTAMP,
            })
        else:
            # Создаем нового пользователя
            user_ref.set({
                'telegram_id': user_data['telegram_id'],
                'first_name': user_data.get('first_name', ''),
                'last_name': user_data.get('last_name', ''),
                'username': user_data.get('username', ''),
                'is_admin': user_data['telegram_id'] in ADMIN_IDS,
                'created_at': firestore.SERVER_TIMESTAMP,
                'last_active': firestore.SERVER_TIMESTAMP,
            })
        
        return True
    except Exception as e:
        print(f"Ошибка при регистрации пользователя: {e}")
        return False

@check_db_before_request
def get_user(telegram_id: int) -> Optional[Dict[str, Any]]:
    """Получает информацию о пользователе"""
    try:
        user_ref = db.collection('users').document(str(telegram_id))
        user_doc = user_ref.get()
        
        if user_doc.exists:
            return user_doc.to_dict()
        return None
    except Exception as e:
        print(f"Ошибка при получении пользователя: {e}")
        return None

@check_db_before_request
def get_all_users() -> List[Dict[str, Any]]:
    """Получает список всех пользователей"""
    try:
        users = []
        users_ref = db.collection('users').stream()
        
        for user_doc in users_ref:
            users.append(user_doc.to_dict())
        
        return users
    except Exception as e:
        print(f"Ошибка при получении списка пользователей: {e}")
        return []

# Управление категориями
@check_db_before_request
def get_categories() -> List[Dict[str, Any]]:
    """Получает список категорий"""
    try:
        categories = []
        categories_ref = db.collection('categories').order_by('order').stream()
        
        for cat_doc in categories_ref:
            category = cat_doc.to_dict()
            category['id'] = cat_doc.id
            categories.append(category)
        
        return categories
    except Exception as e:
        print(f"Ошибка при получении категорий: {e}")
        return []

@check_db_before_request
def add_category(data: Dict[str, Any]) -> Optional[str]:
    """Добавляет новую категорию"""
    try:
        # Получаем максимальное значение order
        categories = db.collection('categories').order_by('order', direction=firestore.Query.DESCENDING).limit(1).stream()
        max_order = 0
        for cat in categories:
            max_order = cat.to_dict().get('order', 0)
        
        # Создаем новую категорию
        new_category = {
            'name': data['name'],
            'description': data.get('description', ''),
            'order': max_order + 1,
        }
        
        # Если есть изображение, сохраняем его
        if 'image_file' in data and data['image_file']:
            image_url = upload_file(data['image_file'], f"categories/{data['name'].lower().replace(' ', '_')}")
            if image_url:
                new_category['image_url'] = image_url
        
        # Добавляем категорию в Firestore
        cat_ref = db.collection('categories').add(new_category)
        return cat_ref.id
    except Exception as e:
        print(f"Ошибка при добавлении категории: {e}")
        return None

# Управление продуктами
@check_db_before_request
def get_products_by_category(category_id: str) -> List[Dict[str, Any]]:
    """Получает список продуктов для указанной категории"""
    try:
        products = []
        products_ref = db.collection('products').where(
            filter=FieldFilter("category_id", "==", category_id)
        ).stream()
        
        for prod_doc in products_ref:
            product = prod_doc.to_dict()
            product['id'] = prod_doc.id
            products.append(product)
        
        return products
    except Exception as e:
        print(f"Ошибка при получении продуктов: {e}")
        return []

@check_db_before_request
def get_product(product_id: str) -> Optional[Dict[str, Any]]:
    """Получает информацию о продукте по ID"""
    try:
        product_ref = db.collection('products').document(product_id)
        product_doc = product_ref.get()
        
        if product_doc.exists:
            product = product_doc.to_dict()
            product['id'] = product_doc.id
            return product
        return None
    except Exception as e:
        print(f"Ошибка при получении продукта: {e}")
        return None

@check_db_before_request
def add_product(data: Dict[str, Any]) -> Optional[str]:
    """Добавляет новый продукт"""
    try:
        # Создаем новый продукт
        new_product = {
            'name': data['name'],
            'category_id': data['category_id'],
            'description': data.get('description', ''),
            'price_info': data.get('price_info', ''),
            'storage_conditions': data.get('storage_conditions', ''),
            'image_urls': [],
            'created_at': firestore.SERVER_TIMESTAMP,
            'updated_at': firestore.SERVER_TIMESTAMP,
        }
        
        # Если есть изображения, сохраняем их
        if 'image_files' in data and data['image_files']:
            for idx, image_file in enumerate(data['image_files']):
                image_url = upload_file(
                    image_file, 
                    f"products/{data['category_id']}/{data['name'].lower().replace(' ', '_')}_{idx}"
                )
                if image_url:
                    new_product['image_urls'].append(image_url)
        
        # Если есть видео, сохраняем его
        if 'video_file' in data and data['video_file']:
            video_url = upload_file(
                data['video_file'], 
                f"products/{data['category_id']}/{data['name'].lower().replace(' ', '_')}_video"
            )
            if video_url:
                new_product['video_url'] = video_url
        
        # Добавляем продукт в Firestore
        prod_ref = db.collection('products').add(new_product)
        return prod_ref.id
    except Exception as e:
        print(f"Ошибка при добавлении продукта: {e}")
        return None

@check_db_before_request
def update_product(product_id: str, data: Dict[str, Any]) -> bool:
    """Обновляет информацию о продукте"""
    try:
        product_ref = db.collection('products').document(product_id)
        
        # Проверяем, существует ли продукт
        product_doc = product_ref.get()
        if not product_doc.exists:
            return False
        
        # Подготавливаем данные для обновления
        update_data = {
            'name': data.get('name'),
            'category_id': data.get('category_id'),
            'description': data.get('description', ''),
            'price_info': data.get('price_info', ''),
            'storage_conditions': data.get('storage_conditions', ''),
            'updated_at': firestore.SERVER_TIMESTAMP,
        }
        
        # Удаляем None значения
        update_data = {k: v for k, v in update_data.items() if v is not None}
        
        # Если есть новые изображения, добавляем их
        if 'image_files' in data and data['image_files']:
            current_product = product_doc.to_dict()
            image_urls = current_product.get('image_urls', [])
            
            for idx, image_file in enumerate(data['image_files']):
                image_url = upload_file(
                    image_file, 
                    f"products/{data.get('category_id', current_product.get('category_id'))}/{data.get('name', current_product.get('name')).lower().replace(' ', '_')}_{len(image_urls) + idx}"
                )
                if image_url:
                    image_urls.append(image_url)
            
            update_data['image_urls'] = image_urls
        
        # Если есть новое видео, добавляем его
        if 'video_file' in data and data['video_file']:
            current_product = product_doc.to_dict()
            video_url = upload_file(
                data['video_file'], 
                f"products/{data.get('category_id', current_product.get('category_id'))}/{data.get('name', current_product.get('name')).lower().replace(' ', '_')}_video"
            )
            if video_url:
                update_data['video_url'] = video_url
        
        # Обновляем продукт в Firestore
        product_ref.update(update_data)
        return True
    except Exception as e:
        print(f"Ошибка при обновлении продукта: {e}")
        return False

@check_db_before_request
def search_products(query: str) -> List[Dict[str, Any]]:
    """Поиск продуктов по названию"""
    try:
        products = []
        # Firebase не поддерживает полнотекстовый поиск напрямую,
        # поэтому мы загружаем все продукты и фильтруем их в памяти
        products_ref = db.collection('products').stream()
        
        query = query.lower()
        for prod_doc in products_ref:
            product = prod_doc.to_dict()
            product['id'] = prod_doc.id
            
            if query in product['name'].lower():
                products.append(product)
                # Ограничиваем количество результатов
                if len(products) >= 10:
                    break
        
        return products
    except Exception as e:
        print(f"Ошибка при поиске продуктов: {e}")
        return []

# Управление тестами
@check_db_before_request
def get_tests_list() -> List[Dict[str, Any]]:
    """Получает список всех тестов"""
    try:
        tests = []
        tests_ref = db.collection('tests').where(
            filter=FieldFilter("is_active", "==", True)
        ).stream()
        
        for test_doc in tests_ref:
            test = test_doc.to_dict()
            test['id'] = test_doc.id
            tests.append(test)
        
        return tests
    except Exception as e:
        print(f"Ошибка при получении тестов: {e}")
        return []

@check_db_before_request
def get_test(test_id: str) -> Optional[Dict[str, Any]]:
    """Получает информацию о тесте по ID"""
    try:
        test_ref = db.collection('tests').document(test_id)
        test_doc = test_ref.get()
        
        if test_doc.exists:
            test = test_doc.to_dict()
            test['id'] = test_doc.id
            return test
        return None
    except Exception as e:
        print(f"Ошибка при получении теста: {e}")
        return None

@check_db_before_request
def add_test(data: Dict[str, Any]) -> Optional[str]:
    """Создает новый тест"""
    try:
        # Создаем новый тест
        new_test = {
            'title': data['title'],
            'description': data.get('description', ''),
            'category_id': data.get('category_id'),
            'questions': data['questions'],
            'passing_score': data.get('passing_score', 70),  # По умолчанию 70%
            'is_active': True,
            'created_at': firestore.SERVER_TIMESTAMP,
            'created_by': data.get('created_by'),
        }
        
        # Добавляем тест в Firestore
        test_ref = db.collection('tests').add(new_test)
        return test_ref.id
    except Exception as e:
        print(f"Ошибка при добавлении теста: {e}")
        return None

@check_db_before_request
def save_test_attempt(data: Dict[str, Any]) -> Optional[str]:
    """Сохраняет попытку прохождения теста"""
    try:
        # Создаем новую попытку
        new_attempt = {
            'user_id': data['user_id'],
            'test_id': data['test_id'],
            'score': data.get('score', 0),
            'max_score': data.get('max_score', 0),
            'answers': data.get('answers', []),
            'completed': data.get('completed', False),
            'started_at': firestore.SERVER_TIMESTAMP,
        }
        
        # Если тест завершен, добавляем время завершения
        if data.get('completed'):
            new_attempt['completed_at'] = firestore.SERVER_TIMESTAMP
        
        # Добавляем попытку в Firestore
        attempt_ref = db.collection('test_attempts').add(new_attempt)
        return attempt_ref.id
    except Exception as e:
        print(f"Ошибка при сохранении попытки: {e}")
        return None

@check_db_before_request
def get_user_test_attempts(user_id: str) -> List[Dict[str, Any]]:
    """Получает все попытки прохождения тестов для пользователя"""
    try:
        attempts = []
        attempts_ref = db.collection('test_attempts').where(
            filter=FieldFilter("user_id", "==", user_id)
        ).order_by('started_at', direction=firestore.Query.DESCENDING).stream()
        
        for attempt_doc in attempts_ref:
            attempt = attempt_doc.to_dict()
            attempt['id'] = attempt_doc.id
            attempts.append(attempt)
        
        return attempts
    except Exception as e:
        print(f"Ошибка при получении попыток: {e}")
        return []

# Вспомогательные функции для работы с файлами
@check_db_before_request
def upload_file(file_data: Union[bytes, str], destination_path: str) -> Optional[str]:
    """Загружает файл в Firebase Storage и возвращает URL"""
    try:
        # Создаем blob для загрузки файла
        blob = bucket.blob(destination_path)
        
        # Загружаем файл
        blob.upload_from_string(file_data, content_type='application/octet-stream')
        
        # Делаем файл публичным
        blob.make_public()
        
        # Возвращаем публичный URL
        return blob.public_url
    except Exception as e:
        print(f"Ошибка при загрузке файла: {e}")
        return None

@check_db_before_request
def delete_file(file_url: str) -> bool:
    """Удаляет файл из Firebase Storage"""
    try:
        # Извлекаем путь файла из URL
        # URL примерно такой: https://storage.googleapis.com/morkovka-kmv-bot.appspot.com/path/to/file
        path = file_url.split('morkovka-kmv-bot.appspot.com/')[1]
        
        # Получаем blob и удаляем его
        blob = bucket.blob(path)
        blob.delete()
        
        return True
    except Exception as e:
        print(f"Ошибка при удалении файла: {e}")
        return False
