
import React from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Database, Shield, Layers, FileCode } from "lucide-react";

const FirebaseInfo = () => {
  return (
    <section className="py-16 bg-gray-50">
      <div className="container mx-auto px-4">
        <h2 className="text-3xl font-bold text-center mb-12">
          Структура базы данных Firebase
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-2 gap-8 max-w-5xl mx-auto">
          <Card>
            <CardHeader className="flex flex-row items-center gap-4">
              <Database className="h-8 w-8 text-carrot" />
              <div>
                <CardTitle>Коллекции в Firestore</CardTitle>
                <CardDescription>Основные коллекции в базе данных</CardDescription>
              </div>
            </CardHeader>
            <CardContent>
              <ul className="list-disc pl-6 space-y-2">
                <li>
                  <span className="font-semibold">users</span> - информация о пользователях бота
                </li>
                <li>
                  <span className="font-semibold">categories</span> - категории товаров
                </li>
                <li>
                  <span className="font-semibold">products</span> - детальная информация о товарах
                </li>
                <li>
                  <span className="font-semibold">tests</span> - тесты для проверки знаний
                </li>
                <li>
                  <span className="font-semibold">attempts</span> - результаты прохождения тестов
                </li>
              </ul>
            </CardContent>
          </Card>
          
          <Card>
            <CardHeader className="flex flex-row items-center gap-4">
              <Shield className="h-8 w-8 text-leaf" />
              <div>
                <CardTitle>Безопасность Firebase</CardTitle>
                <CardDescription>Правила доступа и аутентификация</CardDescription>
              </div>
            </CardHeader>
            <CardContent>
              <ul className="list-disc pl-6 space-y-2">
                <li>Аутентификация на основе Firebase Auth</li>
                <li>Ролевая модель (пользователь/администратор)</li>
                <li>Правила доступа к Firestore по ролям</li>
                <li>Защищенное хранение файлов в Storage</li>
                <li>Регулярное резервное копирование данных</li>
              </ul>
            </CardContent>
          </Card>
          
          <Card>
            <CardHeader className="flex flex-row items-center gap-4">
              <Layers className="h-8 w-8 text-carrot" />
              <div>
                <CardTitle>Схема данных</CardTitle>
                <CardDescription>Структура документов в базе</CardDescription>
              </div>
            </CardHeader>
            <CardContent>
              <div className="text-sm overflow-auto">
                <pre className="bg-gray-100 p-3 rounded-md">
{`// Пример документа продукта
{
  "id": "prod_123456",
  "name": "Яблоко Голден",
  "category_id": "cat_fruits",
  "description": "Сладкие желтые яблоки...",
  "price_info": "200 руб/кг",
  "storage_conditions": "4-8°C",
  "image_urls": ["url1.jpg", "url2.jpg"],
  "video_url": "video.mp4",
  "created_at": timestamp,
  "updated_at": timestamp
}`}
                </pre>
              </div>
            </CardContent>
          </Card>
          
          <Card>
            <CardHeader className="flex flex-row items-center gap-4">
              <FileCode className="h-8 w-8 text-leaf" />
              <div>
                <CardTitle>Admin SDK</CardTitle>
                <CardDescription>Работа с Firebase через Python</CardDescription>
              </div>
            </CardHeader>
            <CardContent>
              <div className="text-sm overflow-auto">
                <pre className="bg-gray-100 p-3 rounded-md">
{`# Инициализация Firebase Admin SDK
import firebase_admin
from firebase_admin import credentials, firestore

# Использование сервисного аккаунта
cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred)

# Получение клиента Firestore
db = firestore.client()

# Добавление документа
doc_ref = db.collection('products').document()
doc_ref.set({
    'name': 'Яблоко Голден',
    'category_id': 'cat_fruits',
    # другие поля...
})
`}
                </pre>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </section>
  );
};

export default FirebaseInfo;
