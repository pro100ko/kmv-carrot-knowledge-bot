
import React, { useState } from "react";
import MainLayout from "@/layouts/MainLayout";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Input } from "@/components/ui/input";
import { Search } from "lucide-react";

// Mock data for demo
const categories = [
  { id: "1", name: "Зелень", productCount: 12 },
  { id: "2", name: "Сезонный стол", productCount: 18 },
  { id: "3", name: "Основная витрина", productCount: 24 },
  { id: "4", name: "Холодильная горка", productCount: 15 },
  { id: "5", name: "Экзотика", productCount: 8 },
  { id: "6", name: "Ягоды", productCount: 10 },
  { id: "7", name: "Орехи/сухофрукты", productCount: 14 },
  { id: "8", name: "Бакалея", productCount: 20 },
  { id: "9", name: "Бар", productCount: 6 },
];

const products = [
  { 
    id: "1", 
    name: "Укроп", 
    category_id: "1",
    description: "Свежая зелень укропа, выращенная в экологически чистом районе. Богата витаминами и минералами.",
    price_info: "60 руб/пучок",
    storage_conditions: "В холодильнике, до 5 дней",
    image_url: "/placeholder.svg"
  },
  { 
    id: "2", 
    name: "Петрушка", 
    category_id: "1",
    description: "Свежая петрушка с насыщенным ароматом. Идеально подходит для супов, салатов и гарниров.",
    price_info: "50 руб/пучок",
    storage_conditions: "В холодильнике, до 7 дней",
    image_url: "/placeholder.svg"
  },
  { 
    id: "3", 
    name: "Яблоки Гренни Смит", 
    category_id: "3",
    description: "Кислые зеленые яблоки с хрустящей мякотью. Идеально подходят для выпечки и свежего употребления.",
    price_info: "180 руб/кг",
    storage_conditions: "В холодильнике, до 1 месяца",
    image_url: "/placeholder.svg"
  },
];

const KnowledgePage = () => {
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [selectedProduct, setSelectedProduct] = useState<any | null>(null);

  const filteredProducts = selectedCategory 
    ? products.filter(product => product.category_id === selectedCategory)
    : searchQuery.length >= 3
      ? products.filter(product => 
          product.name.toLowerCase().includes(searchQuery.toLowerCase())
        )
      : [];

  const handleSearch = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchQuery(e.target.value);
    setSelectedCategory(null);
  };

  const handleCategoryClick = (categoryId: string) => {
    setSelectedCategory(categoryId);
    setSearchQuery("");
    setSelectedProduct(null);
  };

  const handleProductClick = (product: any) => {
    setSelectedProduct(product);
  };

  const handleBackToProducts = () => {
    setSelectedProduct(null);
  };

  const handleBackToCategories = () => {
    setSelectedCategory(null);
    setSelectedProduct(null);
  };

  return (
    <MainLayout>
      <div className="container mx-auto py-8">
        <h1 className="text-3xl font-bold mb-8">База знаний</h1>
        
        <div className="mb-6">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" />
            <Input
              className="pl-10"
              placeholder="Поиск товаров (минимум 3 символа)"
              value={searchQuery}
              onChange={handleSearch}
            />
          </div>
          {searchQuery.length > 0 && searchQuery.length < 3 && (
            <p className="text-sm text-red-500 mt-1">Введите минимум 3 символа для поиска</p>
          )}
        </div>

        {!selectedProduct ? (
          <div>
            {selectedCategory ? (
              <div>
                <div className="flex items-center mb-6">
                  <Button variant="ghost" onClick={handleBackToCategories} className="mr-2">
                    Назад к категориям
                  </Button>
                  <h2 className="text-2xl font-semibold">
                    {categories.find(c => c.id === selectedCategory)?.name}
                  </h2>
                </div>
                
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                  {filteredProducts.map(product => (
                    <Card key={product.id} className="cursor-pointer hover:shadow-lg transition-shadow" onClick={() => handleProductClick(product)}>
                      <CardHeader>
                        <CardTitle>{product.name}</CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="aspect-square bg-gray-100 rounded-md mb-4 flex items-center justify-center">
                          <img src={product.image_url} alt={product.name} className="max-h-full max-w-full object-contain" />
                        </div>
                        <CardDescription className="line-clamp-2">
                          {product.description}
                        </CardDescription>
                      </CardContent>
                      <CardFooter>
                        <p className="text-sm text-gray-500">{product.price_info}</p>
                      </CardFooter>
                    </Card>
                  ))}
                </div>
                
                {filteredProducts.length === 0 && (
                  <p className="text-center py-12 text-gray-500">
                    В этой категории пока нет товаров
                  </p>
                )}
              </div>
            ) : searchQuery.length >= 3 ? (
              <div>
                <h2 className="text-2xl font-semibold mb-6">
                  Результаты поиска: {filteredProducts.length} {filteredProducts.length === 1 ? 'товар' : filteredProducts.length >= 2 && filteredProducts.length <= 4 ? 'товара' : 'товаров'}
                </h2>
                
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                  {filteredProducts.map(product => (
                    <Card key={product.id} className="cursor-pointer hover:shadow-lg transition-shadow" onClick={() => handleProductClick(product)}>
                      <CardHeader>
                        <CardTitle>{product.name}</CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="aspect-square bg-gray-100 rounded-md mb-4 flex items-center justify-center">
                          <img src={product.image_url} alt={product.name} className="max-h-full max-w-full object-contain" />
                        </div>
                        <CardDescription className="line-clamp-2">
                          {product.description}
                        </CardDescription>
                      </CardContent>
                      <CardFooter>
                        <p className="text-sm text-gray-500">{product.price_info}</p>
                      </CardFooter>
                    </Card>
                  ))}
                </div>
                
                {filteredProducts.length === 0 && (
                  <p className="text-center py-12 text-gray-500">
                    По вашему запросу ничего не найдено
                  </p>
                )}
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {categories.map(category => (
                  <Card key={category.id} className="cursor-pointer hover:shadow-lg transition-shadow" onClick={() => handleCategoryClick(category.id)}>
                    <CardHeader>
                      <CardTitle>{category.name}</CardTitle>
                      <CardDescription>
                        {category.productCount} {category.productCount === 1 ? 'товар' : category.productCount >= 2 && category.productCount <= 4 ? 'товара' : 'товаров'}
                      </CardDescription>
                    </CardHeader>
                    <CardContent className="flex justify-center">
                      <div className="w-20 h-20 bg-gray-100 rounded-full flex items-center justify-center">
                        <span className="text-2xl font-bold text-carrot">{category.name.charAt(0)}</span>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </div>
        ) : (
          <div>
            <Button variant="ghost" onClick={handleBackToProducts} className="mb-6">
              Назад к списку товаров
            </Button>
            
            <Card className="max-w-4xl mx-auto">
              <CardHeader>
                <CardTitle className="text-2xl">{selectedProduct.name}</CardTitle>
                <CardDescription>
                  Категория: {categories.find(c => c.id === selectedProduct.category_id)?.name}
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Tabs defaultValue="info">
                  <TabsList className="grid w-full grid-cols-2">
                    <TabsTrigger value="info">Информация</TabsTrigger>
                    <TabsTrigger value="media">Медиа</TabsTrigger>
                  </TabsList>
                  
                  <TabsContent value="info" className="space-y-4 mt-4">
                    <div>
                      <h3 className="font-semibold mb-2">Описание:</h3>
                      <p>{selectedProduct.description}</p>
                    </div>
                    
                    {selectedProduct.price_info && (
                      <div>
                        <h3 className="font-semibold mb-2">Информация о цене:</h3>
                        <p>{selectedProduct.price_info}</p>
                      </div>
                    )}
                    
                    {selectedProduct.storage_conditions && (
                      <div>
                        <h3 className="font-semibold mb-2">Условия хранения:</h3>
                        <p>{selectedProduct.storage_conditions}</p>
                      </div>
                    )}
                  </TabsContent>
                  
                  <TabsContent value="media" className="space-y-4 mt-4">
                    <div>
                      <h3 className="font-semibold mb-2">Изображения:</h3>
                      <div className="aspect-video bg-gray-100 rounded-md mb-4 flex items-center justify-center">
                        <img src={selectedProduct.image_url} alt={selectedProduct.name} className="max-h-full max-w-full object-contain" />
                      </div>
                    </div>
                  </TabsContent>
                </Tabs>
              </CardContent>
            </Card>
          </div>
        )}
      </div>
    </MainLayout>
  );
};

export default KnowledgePage;
