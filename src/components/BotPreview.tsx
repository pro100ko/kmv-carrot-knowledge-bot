
import React from "react";
import { Card, CardContent } from "@/components/ui/card";

const BotPreview = () => {
  return (
    <section className="py-16 bg-gray-50">
      <div className="container mx-auto px-4">
        <h2 className="text-3xl font-bold text-center mb-8">
          Предварительный просмотр бота
        </h2>
        <div className="flex flex-col md:flex-row justify-center items-center gap-8">
          <Card className="w-full max-w-xs border-2 border-gray-200 overflow-hidden">
            <CardContent className="p-0">
              <div className="bg-gray-200 px-4 py-2">
                <div className="flex items-center">
                  <div className="w-8 h-8 rounded-full bg-carrot flex items-center justify-center text-white font-bold">М</div>
                  <span className="ml-2 font-medium">Морковка КМВ</span>
                </div>
              </div>
              <div className="p-4 bg-gray-100 h-96 overflow-y-auto">
                <div className="mb-4">
                  <div className="bg-white rounded-lg p-3 shadow-sm mb-2 max-w-[80%]">
                    <p>Добро пожаловать в бот Морковка КМВ! Выберите действие:</p>
                  </div>
                  <div className="flex flex-col gap-2">
                    <button className="bg-carrot text-white rounded-lg px-3 py-2 text-left">
                      База знаний
                    </button>
                    <button className="bg-leaf text-white rounded-lg px-3 py-2 text-left">
                      Тестирование
                    </button>
                    <button className="bg-gray-300 text-gray-700 rounded-lg px-3 py-2 text-left">
                      Админ панель
                    </button>
                  </div>
                </div>
                
                <div className="mb-4 flex justify-end">
                  <div className="bg-carrot-light text-white rounded-lg p-3 shadow-sm mb-2 max-w-[80%]">
                    <p>База знаний</p>
                  </div>
                </div>
                
                <div className="mb-4">
                  <div className="bg-white rounded-lg p-3 shadow-sm mb-2 max-w-[80%]">
                    <p>Выберите категорию товаров:</p>
                  </div>
                  <div className="flex flex-col gap-2">
                    <button className="bg-gray-200 text-gray-700 rounded-lg px-3 py-2 text-left">
                      Зелень
                    </button>
                    <button className="bg-gray-200 text-gray-700 rounded-lg px-3 py-2 text-left">
                      Сезонный стол
                    </button>
                    <button className="bg-gray-200 text-gray-700 rounded-lg px-3 py-2 text-left">
                      Основная витрина
                    </button>
                    <button className="bg-gray-200 text-gray-700 rounded-lg px-3 py-2 text-left">
                      Больше категорий...
                    </button>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
          
          <div className="max-w-md">
            <h3 className="text-2xl font-bold mb-4">Телеграм-бот для обучения сотрудников</h3>
            <p className="text-gray-700 mb-4">
              Интерактивный бот предоставляет доступ к информационным карточкам о всех товарах компании и позволяет тестировать знания сотрудников.
            </p>
            <ul className="list-disc pl-5 space-y-2 text-gray-700">
              <li>Удобная навигация по категориям продуктов</li>
              <li>Подробные карточки товаров с фото и описанием</li>
              <li>Система тестирования для проверки знаний</li>
              <li>Административная панель для управления контентом</li>
              <li>Статистика и рейтинг сотрудников</li>
            </ul>
          </div>
        </div>
      </div>
    </section>
  );
};

export default BotPreview;
