
import React from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { BookOpen, TestTube, Search, User, Settings } from "lucide-react";

const features = [
  {
    title: "База знаний",
    description: "Подробная информация о продуктах компании, организованная по категориям",
    icon: <BookOpen className="h-10 w-10 text-carrot" />
  },
  {
    title: "Система тестирования",
    description: "Проверьте свои знания с помощью интерактивных тестов по материалам",
    icon: <TestTube className="h-10 w-10 text-leaf" />
  },
  {
    title: "Поиск продуктов",
    description: "Быстрый и удобный поиск по всем продуктам в базе знаний",
    icon: <Search className="h-10 w-10 text-carrot" />
  },
  {
    title: "Профили пользователей",
    description: "Отслеживайте свой прогресс обучения и результаты тестирования",
    icon: <User className="h-10 w-10 text-leaf" />
  },
  {
    title: "Управление контентом",
    description: "Административная панель для создания и редактирования продуктов",
    icon: <Settings className="h-10 w-10 text-carrot" />
  }
];

const FeatureSection = () => {
  return (
    <section className="py-16 bg-white">
      <div className="container mx-auto px-4">
        <h2 className="text-3xl font-bold text-center mb-12">Возможности бота</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
          {features.map((feature, index) => (
            <Card key={index} className="hover:shadow-lg transition-shadow">
              <CardHeader className="flex flex-col items-center text-center">
                {feature.icon}
                <CardTitle className="mt-4">{feature.title}</CardTitle>
              </CardHeader>
              <CardContent>
                <CardDescription className="text-center text-base">
                  {feature.description}
                </CardDescription>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </section>
  );
};

export default FeatureSection;
