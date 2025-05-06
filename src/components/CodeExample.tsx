
import React, { useState } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Card, CardContent } from "@/components/ui/card";

const CodeExample = () => {
  const [activeTab, setActiveTab] = useState("setup");

  const codeExamples = {
    setup: `# Установка необходимых зависимостей
pip install python-telegram-bot firebase-admin

# Создание экземпляра бота
from telegram.ext import Application, CommandHandler, MessageHandler, filters

# Инициализация Firebase
import firebase_admin
from firebase_admin import credentials, firestore

cred = credentials.Certificate("path/to/serviceAccountKey.json")
firebase_admin.initialize_app(cred)
db = firestore.client()`,

    main: `# Основной файл main.py
import logging
from telegram.ext import Application, CommandHandler, MessageHandler, filters

from config import BOT_TOKEN
from handlers.user_management import start, register_user
from handlers.knowledge_base import show_categories, show_products
from handlers.testing import start_test, process_answer
from handlers.admin import admin_panel

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

def main():
    """Запуск бота."""
    # Создаем приложение
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Добавляем обработчики
    application.add_handler(CommandHandler("start", start))
    
    # Запускаем бота
    application.run_polling(allowed_updates=Application.ALL_UPDATES)

if __name__ == "__main__":
    main()`,

    database: `# Работа с базой данных (firebase_db.py)
from firebase_admin import firestore

db = firestore.client()

def get_all_categories():
    """Получить все категории товаров."""
    categories_ref = db.collection('categories')
    return [doc.to_dict() for doc in categories_ref.stream()]

def get_products_by_category(category_id):
    """Получить товары по категории."""
    products_ref = db.collection('products').where('category_id', '==', category_id)
    return [doc.to_dict() for doc in products_ref.stream()]

def get_product_by_id(product_id):
    """Получить товар по ID."""
    product_ref = db.collection('products').document(product_id)
    product = product_ref.get()
    return product.to_dict() if product.exists else None`,

    handlers: `# Пример обработчика базы знаний (handlers/knowledge_base.py)
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from firebase_db import get_all_categories, get_products_by_category, get_product_by_id

async def show_categories(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать категории товаров."""
    categories = get_all_categories()
    
    keyboard = []
    for category in categories:
        keyboard.append([
            InlineKeyboardButton(category['name'], callback_data=f"category_{category['id']}")
        ])
    
    # Добавляем кнопку "Назад"
    keyboard.append([InlineKeyboardButton("Назад", callback_data="back_to_main")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Выберите категорию товаров:", reply_markup=reply_markup)`
  };

  return (
    <section className="py-16 bg-white">
      <div className="container mx-auto px-4">
        <h2 className="text-3xl font-bold text-center mb-8">
          Как реализован бот
        </h2>
        <Card className="max-w-4xl mx-auto">
          <CardContent className="p-6">
            <Tabs defaultValue="setup" className="w-full" value={activeTab} onValueChange={setActiveTab}>
              <TabsList className="grid w-full grid-cols-4">
                <TabsTrigger value="setup">Настройка</TabsTrigger>
                <TabsTrigger value="main">Основной код</TabsTrigger>
                <TabsTrigger value="database">База данных</TabsTrigger>
                <TabsTrigger value="handlers">Обработчики</TabsTrigger>
              </TabsList>
              {Object.entries(codeExamples).map(([key, code]) => (
                <TabsContent key={key} value={key} className="mt-4">
                  <div className="bg-gray-900 text-gray-100 p-4 rounded-md overflow-auto">
                    <pre className="text-sm">
                      <code>{code}</code>
                    </pre>
                  </div>
                </TabsContent>
              ))}
            </Tabs>
          </CardContent>
        </Card>
      </div>
    </section>
  );
};

export default CodeExample;
