
import React from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { FileJson, Server, ShieldCheck, Database } from "lucide-react";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";

const DatabaseInfo = () => {
  return (
    <section className="py-16 bg-white">
      <div className="container mx-auto px-4">
        <h2 className="text-3xl font-bold text-center mb-12">Реализация Telegram бота с SQLite</h2>
        
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
├── sqlite_db.py            # Работа с SQLite
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
└── requirements.txt        # Зависимости проекта`}
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
                    <li>ENVIRONMENT=production</li>
                  </ul>
                </li>
                <li>Нажмите Deploy для запуска бота</li>
              </ol>
            </CardContent>
          </Card>
        </div>
        
        <div className="mt-8">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Database className="h-5 w-5 text-carrot" />
                База данных SQLite
              </CardTitle>
              <CardDescription>Локальное хранилище данных для бота</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="mb-4">
                <p className="text-gray-700">
                  SQLite — это встроенная в проект реляционная база данных, которая не требует отдельного сервера. 
                  Данные хранятся в одном файле на диске, что упрощает развертывание и обслуживание.
                </p>
              </div>
              
              <h4 className="font-semibold mb-2">Основные таблицы базы данных:</h4>
              
              <ul className="list-disc ml-5 space-y-2">
                <li><span className="font-mono bg-gray-100 px-1">users</span> — пользователи бота</li>
                <li><span className="font-mono bg-gray-100 px-1">categories</span> — категории товаров</li>
                <li><span className="font-mono bg-gray-100 px-1">products</span> — товары</li>
                <li><span className="font-mono bg-gray-100 px-1">tests</span> — тесты для обучения</li>
                <li><span className="font-mono bg-gray-100 px-1">test_questions</span> — вопросы тестов</li>
                <li><span className="font-mono bg-gray-100 px-1">test_attempts</span> — попытки прохождения тестов</li>
                <li><span className="font-mono bg-gray-100 px-1">test_answers</span> — ответы пользователей на вопросы</li>
              </ul>
              
              <Collapsible className="w-full mt-6">
                <CollapsibleTrigger className="w-full bg-gray-100 p-3 rounded-md text-left font-medium flex justify-between items-center">
                  <span>Пример структуры таблиц</span>
                  <span className="text-xs text-gray-500">Нажмите, чтобы развернуть</span>
                </CollapsibleTrigger>
                <CollapsibleContent>
                  <pre className="bg-gray-100 p-4 mt-2 rounded-md overflow-x-auto text-xs">
{`-- Пользователи
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    telegram_id INTEGER UNIQUE,
    first_name TEXT,
    last_name TEXT,
    username TEXT,
    is_admin INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Категории товаров
CREATE TABLE categories (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    image_path TEXT,
    order_num INTEGER DEFAULT 0
);

-- Товары
CREATE TABLE products (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    category_id INTEGER,
    description TEXT,
    price_info TEXT,
    storage_conditions TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (category_id) REFERENCES categories (id)
);

-- Изображения товаров
CREATE TABLE product_images (
    id INTEGER PRIMARY KEY,
    product_id INTEGER,
    image_path TEXT NOT NULL,
    order_num INTEGER DEFAULT 0,
    FOREIGN KEY (product_id) REFERENCES products (id)
);

-- Тесты
CREATE TABLE tests (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT,
    category_id INTEGER,
    passing_score INTEGER DEFAULT 70,
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER,
    FOREIGN KEY (category_id) REFERENCES categories (id),
    FOREIGN KEY (created_by) REFERENCES users (id)
);

-- Вопросы тестов
CREATE TABLE test_questions (
    id INTEGER PRIMARY KEY,
    test_id INTEGER,
    question TEXT NOT NULL,
    options TEXT NOT NULL,  -- JSON строка с вариантами ответов
    correct_option INTEGER,
    order_num INTEGER DEFAULT 0,
    FOREIGN KEY (test_id) REFERENCES tests (id)
);

-- Попытки прохождения тестов
CREATE TABLE test_attempts (
    id INTEGER PRIMARY KEY,
    user_id INTEGER,
    test_id INTEGER,
    score INTEGER DEFAULT 0,
    max_score INTEGER DEFAULT 0,
    completed INTEGER DEFAULT 0,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id),
    FOREIGN KEY (test_id) REFERENCES tests (id)
);

-- Ответы на вопросы тестов
CREATE TABLE test_answers (
    id INTEGER PRIMARY KEY,
    attempt_id INTEGER,
    question_id INTEGER,
    selected_option INTEGER,
    is_correct INTEGER DEFAULT 0,
    answered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (attempt_id) REFERENCES test_attempts (id),
    FOREIGN KEY (question_id) REFERENCES test_questions (id)
);`}
                  </pre>
                </CollapsibleContent>
              </Collapsible>
              
              <div className="mt-6">
                <h4 className="font-semibold mb-2">Преимущества использования SQLite:</h4>
                <ul className="list-disc ml-5 space-y-1">
                  <li>Не требует отдельного сервера базы данных</li>
                  <li>Простота настройки и обслуживания</li>
                  <li>Файл базы данных легко переносить и резервировать</li>
                  <li>Высокая производительность для большинства задач</li>
                  <li>Надежность и стабильность работы</li>
                  <li>Нулевая конфигурация — работает "из коробки"</li>
                </ul>
              </div>
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

export default DatabaseInfo;
