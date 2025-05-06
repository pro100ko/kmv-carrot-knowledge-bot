
import React from "react";
import { Button } from "@/components/ui/button";
import { Link } from "react-router-dom";

const HeroSection = () => {
  return (
    <section className="bg-gradient-to-b from-white to-orange-50 py-20">
      <div className="container mx-auto px-4">
        <div className="max-w-3xl mx-auto text-center">
          <h1 className="text-4xl md:text-5xl font-bold mb-6 text-gray-900">
            Корпоративный бот обучения <span className="text-carrot">Морковка КМВ</span>
          </h1>
          <p className="text-xl text-gray-700 mb-8">
            Изучайте продукты компании и проходите тестирование для улучшения своих знаний и навыков продаж
          </p>
          <div className="flex flex-col md:flex-row gap-4 justify-center">
            <Link to="/knowledge">
              <Button className="bg-carrot hover:bg-carrot-dark text-white px-8 py-6 text-lg">
                База знаний
              </Button>
            </Link>
            <Link to="/testing">
              <Button className="bg-leaf hover:bg-leaf-dark text-white px-8 py-6 text-lg">
                Тестирование
              </Button>
            </Link>
            <Link to="/admin">
              <Button variant="outline" className="border-carrot text-carrot hover:bg-orange-50 px-8 py-6 text-lg">
                Админ панель
              </Button>
            </Link>
          </div>
        </div>
      </div>
    </section>
  );
};

export default HeroSection;
