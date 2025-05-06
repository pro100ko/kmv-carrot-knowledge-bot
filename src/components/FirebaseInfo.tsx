
import React from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { FileJson, Server, ShieldCheck } from "lucide-react";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";

const FirebaseInfo = () => {
  return (
    <section className="py-16 bg-white">
      <div className="container mx-auto px-4">
        <h2 className="text-3xl font-bold text-center mb-12">Реализация Telegram бота с Firebase</h2>
        
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <FileJson className="h-5 w-5 text-carrot" />
                Структура проекта
              </CardTitle>
              <CardDescription>Как организованы файлы и папки бота</CardDescription>
            </CardHeader>
            <CardContent>
              <pre className="bg-gray-100 p-4 rounded-md overflow-x-auto text-sm">
{`morkovka-bot/
├── config.py               # Конфигурация бота
├── main.py                 # Основной файл бота
├── firebase_db.py          # Работа с Firebase
├── handlers/
│   ├── __init__.py
│   ├── user_management.py  # Управление пользователями
│   ├── knowledge_base.py   # База знаний
│   ├── testing.py          # Система тестирования
│   └── admin.py            # Админ-панель
├── utils/
│   ├── __init__.py
│   ├── keyboards.py        # Клавиатуры бота
│   └── helpers.py          # Вспомогательные функции
├── requirements.txt        # Зависимости проекта
└── service_account.json    # Ключ для доступа к Firebase`}
              </pre>
            </CardContent>
          </Card>
          
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Server className="h-5 w-5 text-carrot" />
                Настройка на Render.com
              </CardTitle>
              <CardDescription>Подключение бота к серверу</CardDescription>
            </CardHeader>
            <CardContent>
              <ol className="list-decimal pl-5 space-y-3">
                <li>Зарегистрируйтесь на <a href="https://render.com" className="text-carrot hover:underline">render.com</a></li>
                <li>Создайте новый Web Service и подключите репозиторий с GitHub</li>
                <li>Укажите тип: Web Service</li>
                <li>Выберите ветку для деплоя (обычно main)</li>
                <li>Укажите команду для установки: <code>pip install -r requirements.txt</code></li>
                <li>Укажите команду для запуска: <code>python main.py</code></li>
                <li>Добавьте переменные окружения:
                  <ul className="list-disc ml-5 mt-2">
                    <li>BOT_TOKEN</li>
                    <li>ADMIN_IDS</li>
                    <li>WEBHOOK_URL (URL вашего приложения на render.com)</li>
                  </ul>
                </li>
                <li>Загрузите файл service_account.json как секретный файл</li>
                <li>Нажмите Deploy для запуска бота</li>
              </ol>
            </CardContent>
          </Card>
        </div>
        
        <div className="mt-8">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <ShieldCheck className="h-5 w-5 text-carrot" />
                Основные файлы кода бота
              </CardTitle>
              <CardDescription>Примеры ключевых файлов для запуска бота</CardDescription>
            </CardHeader>
            <CardContent>
              <Collapsible className="w-full">
                <CollapsibleTrigger className="w-full bg-gray-100 p-3 rounded-md text-left font-medium flex justify-between items-center">
                  <span>config.py</span>
                  <span className="text-xs text-gray-500">Нажмите, чтобы развернуть</span>
                </CollapsibleTrigger>
                <CollapsibleContent>
                  <pre className="bg-gray-100 p-4 mt-2 rounded-md overflow-x-auto text-xs">
{`import os
import json
from typing import List, Dict, Any

# Токен бота и ID администраторов
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8127758206:AAErKt-s-ztq3xgu5M9sqP2esZWyhowXvNI")
ADMIN_IDS = [int(id) for id in os.environ.get("ADMIN_IDS", "340877389").split()]

# Настройки webhook (для размещения на хостинге)
WEBHOOK_HOST = os.environ.get("WEBHOOK_URL", "https://your-app-name.onrender.com")
WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"

# Настройки Firebase
FIREBASE_CREDENTIALS = os.environ.get("FIREBASE_CREDENTIALS", "service_account.json")
FIREBASE_DATABASE_URL = "https://morkovka-kmv-bot.firebaseio.com"

# Основные категории товаров
PRODUCT_CATEGORIES = [
    "Зелень", "Сезонный стол", "Основная витрина", "Холодильная горка", 
    "Экзотика", "Ягоды", "Орехи/сухофрукты", "Бакалея", "Бар"
]

# Настройки поиска
MIN_SEARCH_LENGTH = 3  # Минимальная длина запроса для поиска
MAX_SEARCH_RESULTS = 10  # Максимальное количество результатов поиска`}
                  </pre>
                </CollapsibleContent>
              </Collapsible>
              
              <Collapsible className="w-full mt-4">
                <CollapsibleTrigger className="w-full bg-gray-100 p-3 rounded-md text-left font-medium flex justify-between items-center">
                  <span>firebase_db.py</span>
                  <span className="text-xs text-gray-500">Нажмите, чтобы развернуть</span>
                </CollapsibleTrigger>
                <CollapsibleContent>
                  <pre className="bg-gray-100 p-4 mt-2 rounded-md overflow-x-auto text-xs">
{`import json
import os
from datetime import datetime
from typing import List, Dict, Any, Optional, Union

import firebase_admin
from firebase_admin import credentials, firestore, storage
from google.cloud.firestore_v1.base_query import FieldFilter

from config import FIREBASE_CREDENTIALS, ADMIN_IDS

# Инициализация Firebase
try:
    # Если переменная окружения существует как JSON строка
    if os.environ.get("FIREBASE_CREDENTIALS_JSON"):
        cred_dict = json.loads(os.environ.get("FIREBASE_CREDENTIALS_JSON"))
        cred = credentials.Certificate(cred_dict)
    # Если есть путь к файлу
    else:
        cred = credentials.Certificate(FIREBASE_CREDENTIALS)
    
    firebase_app = firebase_admin.initialize_app(cred, {
        'storageBucket': 'morkovka-kmv-bot.appspot.com'
    })
    db = firestore.client()
    bucket = storage.bucket()
except Exception as e:
    print(f"Ошибка инициализации Firebase: {e}")
    # Создаем заглушки для тестирования без Firebase
    firebase_app = None
    db = None
    bucket = None

# Управление пользователями
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
        return False`}
                  </pre>
                </CollapsibleContent>
              </Collapsible>
              
              <Collapsible className="w-full mt-4">
                <CollapsibleTrigger className="w-full bg-gray-100 p-3 rounded-md text-left font-medium flex justify-between items-center">
                  <span>main.py</span>
                  <span className="text-xs text-gray-500">Нажмите, чтобы развернуть</span>
                </CollapsibleTrigger>
                <CollapsibleContent>
                  <pre className="bg-gray-100 p-4 mt-2 rounded-md overflow-x-auto text-xs">
{`import logging
import os
import sys
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from telegram.constants import ParseMode

# Импортируем настройки
from config import BOT_TOKEN, WEBHOOK_URL, WEBHOOK_PATH

# Импортируем обработчики
from handlers.user_management import register_user_handler, start
from handlers.knowledge_base import knowledge_base_handler, category_handler, product_handler, search_handler
from handlers.testing import testing_handler, test_selection_handler, test_question_handler, test_result_handler
from handlers.admin import admin_handler, admin_categories_handler, admin_products_handler, admin_tests_handler, admin_stats_handler

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

def main() -> None:
    """Запуск бота"""
    # Создаем объект приложения
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Регистрируем обработчики
    # Обработчики для команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", start))
    
    # Регистрируем обработчики кнопок
    application.add_handler(CallbackQueryHandler(knowledge_base_handler, pattern="^knowledge_base$"))
    application.add_handler(CallbackQueryHandler(category_handler, pattern="^category:"))
    application.add_handler(CallbackQueryHandler(product_handler, pattern="^product:"))
    
    application.add_handler(CallbackQueryHandler(testing_handler, pattern="^testing$"))
    application.add_handler(CallbackQueryHandler(test_selection_handler, pattern="^test_select:"))
    application.add_handler(CallbackQueryHandler(test_question_handler, pattern="^test_answer:"))
    application.add_handler(CallbackQueryHandler(test_result_handler, pattern="^test_result:"))
    
    application.add_handler(CallbackQueryHandler(admin_handler, pattern="^admin$"))
    application.add_handler(CallbackQueryHandler(admin_categories_handler, pattern="^admin_categories"))
    application.add_handler(CallbackQueryHandler(admin_products_handler, pattern="^admin_products"))
    application.add_handler(CallbackQueryHandler(admin_tests_handler, pattern="^admin_tests"))
    application.add_handler(CallbackQueryHandler(admin_stats_handler, pattern="^admin_stats"))
    
    # Обработчик для поиска
    application.add_handler(MessageHandler(filters.Regex(r'^\🔍 Поиск$'), search_handler))
    application.add_handler(MessageHandler(filters.Regex(r'^\🔍 .*'), search_handler))
    
    # Обработчик для всех остальных сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, register_user_handler))
    
    # Запускаем бота
    if os.environ.get("ENVIRONMENT") == "production":
        # На продакшн-сервере используем webhook
        application.run_webhook(
            listen="0.0.0.0",
            port=int(os.environ.get("PORT", 8443)),
            url_path=WEBHOOK_PATH,
            webhook_url=WEBHOOK_URL
        )
        logger.info(f"Webhook установлен на {WEBHOOK_URL}")
    else:
        # Локально используем polling
        application.run_polling(allowed_updates=Update.ALL_TYPES)
        logger.info("Бот запущен в режиме polling")
    
if __name__ == '__main__':
    main()`}
                  </pre>
                </CollapsibleContent>
              </Collapsible>
              
              <Collapsible className="w-full mt-4">
                <CollapsibleTrigger className="w-full bg-gray-100 p-3 rounded-md text-left font-medium flex justify-between items-center">
                  <span>handlers/user_management.py</span>
                  <span className="text-xs text-gray-500">Нажмите, чтобы развернуть</span>
                </CollapsibleTrigger>
                <CollapsibleContent>
                  <pre className="bg-gray-100 p-4 mt-2 rounded-md overflow-x-auto text-xs">
{`from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

import firebase_db
from config import ADMIN_IDS
from utils.keyboards import get_main_keyboard

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /start"""
    user = update.effective_user
    
    # Регистрируем пользователя
    user_data = {
        'telegram_id': user.id,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'username': user.username,
    }
    firebase_db.register_user(user_data)
    
    # Отправляем приветственное сообщение
    welcome_message = (
        f"👋 Добро пожаловать в бот «Морковка КМВ», {user.first_name}!\n\n"
        "🥕 Здесь вы найдете актуальную информацию о продуктах компании и сможете проверить свои знания."
    )
    
    # Проверяем, является ли пользователь администратором
    is_admin = user.id in ADMIN_IDS
    
    # Создаем клавиатуру для пользователя
    keyboard = get_main_keyboard(is_admin)
    
    # Отправляем сообщение с клавиатурой
    await update.message.reply_text(
        welcome_message,
        reply_markup=keyboard
    )

async def register_user_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик для регистрации пользователя и обработки неизвестных сообщений"""
    user = update.effective_user
    
    # Регистрируем пользователя
    user_data = {
        'telegram_id': user.id,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'username': user.username,
    }
    firebase_db.register_user(user_data)
    
    # Обрабатываем текстовые команды для основных функций
    message_text = update.message.text
    
    if message_text == "🍎 База знаний":
        # Выполняем то же, что и при нажатии на кнопку knowledge_base
        await knowledge_base_handler(update, context)
    elif message_text == "📝 Тестирование":
        # Выполняем то же, что и при нажатии на кнопку testing
        await testing_handler(update, context)
    elif message_text == "⚙️ Админ панель" and user.id in ADMIN_IDS:
        # Выполняем то же, что и при нажатии на кнопку admin
        await admin_handler(update, context)
    else:
        # Для неизвестных команд отправляем основное меню
        is_admin = user.id in ADMIN_IDS
        keyboard = get_main_keyboard(is_admin)
        
        await update.message.reply_text(
            "Выберите действие из меню:",
            reply_markup=keyboard
        )

# Импорт здесь, чтобы избежать циклических зависимостей
from handlers.knowledge_base import knowledge_base_handler
from handlers.testing import testing_handler
from handlers.admin import admin_handler`}
                  </pre>
                </CollapsibleContent>
              </Collapsible>
              
              <Collapsible className="w-full mt-4">
                <CollapsibleTrigger className="w-full bg-gray-100 p-3 rounded-md text-left font-medium flex justify-between items-center">
                  <span>utils/keyboards.py</span>
                  <span className="text-xs text-gray-500">Нажмите, чтобы развернуть</span>
                </CollapsibleTrigger>
                <CollapsibleContent>
                  <pre className="bg-gray-100 p-4 mt-2 rounded-md overflow-x-auto text-xs">
{`from telegram import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from typing import List, Dict, Any

def get_main_keyboard(is_admin: bool = False) -> InlineKeyboardMarkup:
    """Создает главную клавиатуру бота"""
    buttons = [
        [
            InlineKeyboardButton("🍎 База знаний", callback_data="knowledge_base"),
            InlineKeyboardButton("📝 Тестирование", callback_data="testing")
        ]
    ]
    
    # Добавляем кнопку админ-панели для администраторов
    if is_admin:
        buttons.append([InlineKeyboardButton("⚙️ Админ панель", callback_data="admin")])
    
    return InlineKeyboardMarkup(buttons)

def get_categories_keyboard(categories: List[Dict[str, Any]], with_back: bool = True) -> InlineKeyboardMarkup:
    """Создает клавиатуру с категориями продуктов"""
    buttons = []
    
    # Добавляем кнопки для категорий, по 2 в ряд
    for i in range(0, len(categories), 2):
        row = []
        category = categories[i]
        row.append(InlineKeyboardButton(category['name'], callback_data=f"category:{category['id']}"))
        
        # Добавляем вторую категорию в ряд, если она есть
        if i + 1 < len(categories):
            category = categories[i + 1]
            row.append(InlineKeyboardButton(category['name'], callback_data=f"category:{category['id']}"))
        
        buttons.append(row)
    
    # Добавляем кнопку поиска и назад
    row = [InlineKeyboardButton("🔍 Поиск", callback_data="search")]
    if with_back:
        row.append(InlineKeyboardButton("🔙 Назад", callback_data="back_to_main"))
    buttons.append(row)
    
    return InlineKeyboardMarkup(buttons)

def get_products_keyboard(products: List[Dict[str, Any]], category_id: str) -> InlineKeyboardMarkup:
    """Создает клавиатуру со списком продуктов"""
    buttons = []
    
    # Добавляем кнопки для продуктов, по 1 в ряд
    for product in products:
        buttons.append([
            InlineKeyboardButton(product['name'], callback_data=f"product:{product['id']}")
        ])
    
    # Добавляем кнопку назад к категориям
    buttons.append([
        InlineKeyboardButton("🔙 Назад к категориям", callback_data=f"back_to_category:{category_id}")
    ])
    
    return InlineKeyboardMarkup(buttons)

def get_product_navigation_keyboard(product_id: str, category_id: str) -> InlineKeyboardMarkup:
    """Создает клавиатуру для навигации между фото продукта и возврата к списку товаров"""
    buttons = [
        [
            InlineKeyboardButton("⬅️ Предыдущее", callback_data=f"product_prev:{product_id}"),
            InlineKeyboardButton("Следующее ➡️", callback_data=f"product_next:{product_id}")
        ],
        [
            InlineKeyboardButton("🔙 К списку товаров", callback_data=f"back_to_products:{category_id}")
        ]
    ]
    return InlineKeyboardMarkup(buttons)

def get_tests_keyboard(tests: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
    """Создает клавиатуру со списком доступных тестов"""
    buttons = []
    
    # Добавляем кнопки для тестов, по 1 в ряд
    for test in tests:
        buttons.append([
            InlineKeyboardButton(test['title'], callback_data=f"test_select:{test['id']}")
        ])
    
    # Добавляем кнопку назад к главному меню
    buttons.append([
        InlineKeyboardButton("🔙 В главное меню", callback_data="back_to_main")
    ])
    
    return InlineKeyboardMarkup(buttons)

def get_test_question_keyboard(question_idx: int, options: List[str], test_id: str) -> InlineKeyboardMarkup:
    """Создает клавиатуру для вопроса теста"""
    buttons = []
    
    # Добавляем кнопки для вариантов ответа
    for idx, option in enumerate(options):
        buttons.append([
            InlineKeyboardButton(f"{idx+1}. {option}", callback_data=f"test_answer:{test_id}:{question_idx}:{idx}")
        ])
    
    return InlineKeyboardMarkup(buttons)

def get_test_result_keyboard() -> InlineKeyboardMarkup:
    """Создает клавиатуру для результатов теста"""
    buttons = [
        [
            InlineKeyboardButton("🔄 Пройти ещё раз", callback_data="testing")
        ],
        [
            InlineKeyboardButton("🏠 В главное меню", callback_data="back_to_main")
        ]
    ]
    return InlineKeyboardMarkup(buttons)

def get_admin_keyboard() -> InlineKeyboardMarkup:
    """Создает клавиатуру для админ-панели"""
    buttons = [
        [
            InlineKeyboardButton("📂 Категории", callback_data="admin_categories")
        ],
        [
            InlineKeyboardButton("🍎 Товары", callback_data="admin_products")
        ],
        [
            InlineKeyboardButton("📝 Тесты", callback_data="admin_tests")
        ],
        [
            InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")
        ],
        [
            InlineKeyboardButton("🔙 В главное меню", callback_data="back_to_main")
        ]
    ]
    return InlineKeyboardMarkup(buttons)

def get_admin_categories_keyboard(categories: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
    """Создает клавиатуру для управления категориями"""
    buttons = []
    
    # Добавляем существующие категории
    for category in categories:
        buttons.append([
            InlineKeyboardButton(f"🖊️ {category['name']}", callback_data=f"edit_category:{category['id']}")
        ])
    
    # Добавляем кнопки создания и возврата
    buttons.append([InlineKeyboardButton("➕ Создать категорию", callback_data="add_category")])
    buttons.append([InlineKeyboardButton("🔙 Назад в админ-панель", callback_data="admin")])
    
    return InlineKeyboardMarkup(buttons)

def get_admin_products_keyboard(categories: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
    """Создает клавиатуру для выбора категории при управлении товарами"""
    buttons = []
    
    # Добавляем категории для выбора
    for category in categories:
        buttons.append([
            InlineKeyboardButton(category['name'], callback_data=f"admin_products_category:{category['id']}")
        ])
    
    # Добавляем кнопку возврата
    buttons.append([InlineKeyboardButton("🔙 Назад в админ-панель", callback_data="admin")])
    
    return InlineKeyboardMarkup(buttons)

def get_admin_products_list_keyboard(products: List[Dict[str, Any]], category_id: str) -> InlineKeyboardMarkup:
    """Создает клавиатуру со списком товаров для редактирования"""
    buttons = []
    
    # Добавляем существующие товары
    for product in products:
        buttons.append([
            InlineKeyboardButton(f"🖊️ {product['name']}", callback_data=f"edit_product:{product['id']}")
        ])
    
    # Добавляем кнопки создания и возврата
    buttons.append([InlineKeyboardButton("➕ Создать товар", callback_data=f"add_product:{category_id}")])
    buttons.append([InlineKeyboardButton("🔙 Назад к категориям", callback_data="admin_products")])
    
    return InlineKeyboardMarkup(buttons)

def get_admin_tests_keyboard(tests: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
    """Создает клавиатуру для управления тестами"""
    buttons = []
    
    # Добавляем существующие тесты
    for test in tests:
        buttons.append([
            InlineKeyboardButton(f"🖊️ {test['title']}", callback_data=f"edit_test:{test['id']}")
        ])
    
    # Добавляем кнопки создания и возврата
    buttons.append([InlineKeyboardButton("➕ Создать тест", callback_data="add_test")])
    buttons.append([InlineKeyboardButton("🔙 Назад в админ-панель", callback_data="admin")])
    
    return InlineKeyboardMarkup(buttons)

def get_admin_stats_keyboard() -> InlineKeyboardMarkup:
    """Создает клавиатуру для просмотра статистики"""
    buttons = [
        [
            InlineKeyboardButton("👥 Пользователи", callback_data="admin_stats_users")
        ],
        [
            InlineKeyboardButton("📝 Тесты", callback_data="admin_stats_tests")
        ],
        [
            InlineKeyboardButton("🔙 Назад в админ-панель", callback_data="admin")
        ]
    ]
    return InlineKeyboardMarkup(buttons)`}
                  </pre>
                </CollapsibleContent>
              </Collapsible>
            </CardContent>
          </Card>
        </div>
        
        <div className="mt-12 text-center">
          <p className="mb-4 text-lg text-gray-600">
            Полный исходный код для телеграм бота с документацией доступен на GitHub:
          </p>
          <a href="https://github.com" className="inline-flex items-center bg-carrot hover:bg-carrot-dark text-white px-6 py-3 rounded-lg font-medium transition-colors">
            <svg className="w-5 h-5 mr-2" fill="currentColor" viewBox="0 0 24 24" aria-hidden="true">
              <path fillRule="evenodd" d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" clipRule="evenodd" />
            </svg>
            Код на GitHub
          </a>
        </div>
      </div>
    </section>
  );
};

export default FirebaseInfo;
