
import React from "react";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Menu } from "lucide-react";

const Header = () => {
  return (
    <header className="bg-gradient-to-r from-carrot to-carrot-light p-4 shadow-md">
      <div className="container mx-auto flex justify-between items-center">
        <Link to="/" className="flex items-center gap-2">
          <div className="relative">
            <div className="w-10 h-14 bg-carrot rounded-b-full animate-bounce-slow">
              <div className="absolute top-0 left-1/2 -translate-x-1/2 -translate-y-1/3">
                <div className="w-6 h-3 bg-leaf-dark rounded-t-full"></div>
              </div>
            </div>
          </div>
          <h1 className="text-white text-2xl font-bold">Морковка КМВ</h1>
        </Link>
        <div className="hidden md:flex gap-4">
          <Link to="/knowledge">
            <Button variant="ghost" className="text-white hover:bg-carrot-dark">
              База знаний
            </Button>
          </Link>
          <Link to="/testing">
            <Button variant="ghost" className="text-white hover:bg-carrot-dark">
              Тестирование
            </Button>
          </Link>
          <Link to="/admin">
            <Button variant="ghost" className="text-white hover:bg-carrot-dark">
              Админ панель
            </Button>
          </Link>
        </div>
        <Button variant="outline" size="icon" className="md:hidden text-white">
          <Menu className="h-5 w-5" />
        </Button>
      </div>
    </header>
  );
};

export default Header;
