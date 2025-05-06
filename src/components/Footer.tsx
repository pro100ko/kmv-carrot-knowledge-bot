
import React from "react";

const Footer = () => {
  return (
    <footer className="bg-gray-100 p-6 mt-auto">
      <div className="container mx-auto">
        <div className="flex flex-col md:flex-row justify-between items-center">
          <div className="mb-4 md:mb-0">
            <p className="text-gray-600 text-sm">
              © {new Date().getFullYear()} Морковка КМВ. Все права защищены.
            </p>
          </div>
          <div className="flex gap-4">
            <a href="#" className="text-carrot hover:text-carrot-dark text-sm">
              Правила использования
            </a>
            <a href="#" className="text-carrot hover:text-carrot-dark text-sm">
              Политика конфиденциальности
            </a>
          </div>
        </div>
      </div>
    </footer>
  );
};

export default Footer;
