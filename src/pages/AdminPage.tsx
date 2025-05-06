
import React, { useState } from "react";
import MainLayout from "@/layouts/MainLayout";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { PlusCircle, Upload, Trash2, PenLine, Users, BarChart3 } from "lucide-react";

// Mock categories data
const categories = [
  { id: "1", name: "Зелень" },
  { id: "2", name: "Сезонный стол" },
  { id: "3", name: "Основная витрина" },
  { id: "4", name: "Холодильная горка" },
  { id: "5", name: "Экзотика" },
  { id: "6", name: "Ягоды" },
  { id: "7", name: "Орехи/сухофрукты" },
  { id: "8", name: "Бакалея" },
  { id: "9", name: "Бар" },
];

// Mock products
const products = [
  { id: "1", name: "Укроп", category_id: "1", price_info: "60 руб/пучок" },
  { id: "2", name: "Петрушка", category_id: "1", price_info: "50 руб/пучок" },
  { id: "3", name: "Яблоки Гренни Смит", category_id: "3", price_info: "180 руб/кг" },
  { id: "4", name: "Бананы", category_id: "3", price_info: "120 руб/кг" },
];

// Mock users
const users = [
  { id: "1", name: "Иван Петров", telegram_id: 12345678, is_admin: false, last_active: "2023-05-05" },
  { id: "2", name: "Анна Сидорова", telegram_id: 23456789, is_admin: false, last_active: "2023-05-04" },
  { id: "3", name: "Павел Николаев", telegram_id: 34567890, is_admin: true, last_active: "2023-05-06" },
];

// Mock test results
const testResults = [
  { id: "1", user_name: "Иван Петров", test_name: "Основы знаний о фруктах", score: 4, max_score: 5, date: "2023-05-04" },
  { id: "2", user_name: "Анна Сидорова", test_name: "Основы знаний о фруктах", score: 5, max_score: 5, date: "2023-05-03" },
  { id: "3", user_name: "Павел Николаев", test_name: "Экзотические фрукты", score: 7, max_score: 8, date: "2023-05-06" },
];

const AdminPage = () => {
  const [activeTab, setActiveTab] = useState("products");
  const [isEditing, setIsEditing] = useState(false);
  const [currentProduct, setCurrentProduct] = useState<any | null>(null);

  // Product form handlers
  const handleAddProduct = () => {
    setIsEditing(false);
    setCurrentProduct({
      name: "",
      category_id: "",
      description: "",
      price_info: "",
      storage_conditions: "",
    });
  };

  const handleEditProduct = (product: any) => {
    setIsEditing(true);
    setCurrentProduct({ ...product });
  };

  const handleSaveProduct = () => {
    // Save logic would go here
    setCurrentProduct(null);
  };

  const handleCancelEdit = () => {
    setCurrentProduct(null);
  };

  // Render tabs content
  const renderProductsTab = () => (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold">Управление продуктами</h2>
        {!currentProduct && (
          <Button onClick={handleAddProduct} className="bg-carrot hover:bg-carrot-dark">
            <PlusCircle className="mr-2 h-4 w-4" /> Добавить продукт
          </Button>
        )}
      </div>
      
      {currentProduct ? (
        <Card>
          <CardHeader>
            <CardTitle>{isEditing ? "Редактирование" : "Добавление"} продукта</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="product-name">Название продукта</Label>
                <Input
                  id="product-name"
                  placeholder="Введите название продукта"
                  value={currentProduct.name}
                  onChange={(e) => setCurrentProduct({ ...currentProduct, name: e.target.value })}
                />
              </div>
              
              <div className="space-y-2">
                <Label htmlFor="product-category">Категория</Label>
                <Select 
                  value={currentProduct.category_id} 
                  onValueChange={(value) => setCurrentProduct({ ...currentProduct, category_id: value })}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Выберите категорию" />
                  </SelectTrigger>
                  <SelectContent>
                    {categories.map((category) => (
                      <SelectItem key={category.id} value={category.id}>
                        {category.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              
              <div className="space-y-2 md:col-span-2">
                <Label htmlFor="product-description">Описание</Label>
                <Textarea
                  id="product-description"
                  placeholder="Введите описание продукта"
                  value={currentProduct.description || ""}
                  onChange={(e) => setCurrentProduct({ ...currentProduct, description: e.target.value })}
                  rows={4}
                />
              </div>
              
              <div className="space-y-2">
                <Label htmlFor="product-price">Информация о цене</Label>
                <Input
                  id="product-price"
                  placeholder="Например: 100 руб/кг"
                  value={currentProduct.price_info || ""}
                  onChange={(e) => setCurrentProduct({ ...currentProduct, price_info: e.target.value })}
                />
              </div>
              
              <div className="space-y-2">
                <Label htmlFor="product-storage">Условия хранения</Label>
                <Input
                  id="product-storage"
                  placeholder="Например: В холодильнике при 2-4°C"
                  value={currentProduct.storage_conditions || ""}
                  onChange={(e) => setCurrentProduct({ ...currentProduct, storage_conditions: e.target.value })}
                />
              </div>
              
              <div className="space-y-2 md:col-span-2">
                <Label>Изображения продукта</Label>
                <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 flex flex-col items-center">
                  <Upload className="h-8 w-8 text-gray-400 mb-2" />
                  <p className="text-sm text-gray-500 mb-2">Перетащите изображения или нажмите для загрузки</p>
                  <Button variant="outline" size="sm">Выбрать файлы</Button>
                </div>
              </div>
            </div>
          </CardContent>
          <CardFooter className="flex justify-end gap-2">
            <Button variant="outline" onClick={handleCancelEdit}>Отмена</Button>
            <Button className="bg-carrot hover:bg-carrot-dark" onClick={handleSaveProduct}>
              {isEditing ? "Сохранить изменения" : "Добавить продукт"}
            </Button>
          </CardFooter>
        </Card>
      ) : (
        <div className="bg-white rounded-lg shadow">
          <div className="p-4 border-b">
            <div className="flex justify-between items-center">
              <Input 
                placeholder="Поиск продуктов..." 
                className="max-w-sm"
              />
              <Select defaultValue="all">
                <SelectTrigger className="w-[180px]">
                  <SelectValue placeholder="Категория" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Все категории</SelectItem>
                  {categories.map((category) => (
                    <SelectItem key={category.id} value={category.id}>
                      {category.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Название</TableHead>
                <TableHead>Категория</TableHead>
                <TableHead>Цена</TableHead>
                <TableHead className="text-right">Действия</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {products.map((product) => (
                <TableRow key={product.id}>
                  <TableCell className="font-medium">{product.name}</TableCell>
                  <TableCell>
                    {categories.find(c => c.id === product.category_id)?.name}
                  </TableCell>
                  <TableCell>{product.price_info}</TableCell>
                  <TableCell className="text-right">
                    <div className="flex justify-end gap-2">
                      <Button 
                        variant="ghost" 
                        size="icon"
                        onClick={() => handleEditProduct(product)}
                      >
                        <PenLine className="h-4 w-4" />
                      </Button>
                      <Button 
                        variant="ghost" 
                        size="icon"
                        className="text-red-500 hover:text-red-700"
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  );

  const renderTestsTab = () => (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold">Управление тестами</h2>
        <Button className="bg-leaf hover:bg-leaf-dark">
          <PlusCircle className="mr-2 h-4 w-4" /> Создать тест
        </Button>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Основы знаний о фруктах</CardTitle>
            <CardDescription>
              5 вопросов • Создан 04.05.2023
            </CardDescription>
          </CardHeader>
          <CardContent>
            <p className="mb-4">Базовый тест на знание ассортимента фруктов</p>
            <div className="flex items-center text-sm">
              <Users className="h-4 w-4 mr-1 text-gray-500" />
              <span className="text-gray-500">12 прохождений</span>
              <span className="mx-2 text-gray-300">|</span>
              <BarChart3 className="h-4 w-4 mr-1 text-gray-500" />
              <span className="text-gray-500">Ср. результат: 80%</span>
            </div>
          </CardContent>
          <CardFooter className="flex justify-between">
            <Button variant="outline" size="sm">Редактировать</Button>
            <Button variant="outline" size="sm" className="text-red-500 border-red-200 hover:bg-red-50">Удалить</Button>
          </CardFooter>
        </Card>
        
        <Card>
          <CardHeader>
            <CardTitle>Экзотические фрукты</CardTitle>
            <CardDescription>
              8 вопросов • Создан 05.05.2023
            </CardDescription>
          </CardHeader>
          <CardContent>
            <p className="mb-4">Тест на знание экзотических фруктов и их особенностей</p>
            <div className="flex items-center text-sm">
              <Users className="h-4 w-4 mr-1 text-gray-500" />
              <span className="text-gray-500">7 прохождений</span>
              <span className="mx-2 text-gray-300">|</span>
              <BarChart3 className="h-4 w-4 mr-1 text-gray-500" />
              <span className="text-gray-500">Ср. результат: 75%</span>
            </div>
          </CardContent>
          <CardFooter className="flex justify-between">
            <Button variant="outline" size="sm">Редактировать</Button>
            <Button variant="outline" size="sm" className="text-red-500 border-red-200 hover:bg-red-50">Удалить</Button>
          </CardFooter>
        </Card>
      </div>
    </div>
  );

  const renderUsersTab = () => (
    <div>
      <h2 className="text-2xl font-bold mb-6">Управление пользователями</h2>
      
      <Card>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Имя пользователя</TableHead>
              <TableHead>Telegram ID</TableHead>
              <TableHead>Роль</TableHead>
              <TableHead>Последняя активность</TableHead>
              <TableHead className="text-right">Действия</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {users.map((user) => (
              <TableRow key={user.id}>
                <TableCell className="font-medium">{user.name}</TableCell>
                <TableCell>{user.telegram_id}</TableCell>
                <TableCell>
                  {user.is_admin ? (
                    <span className="bg-carrot-light text-carrot-dark text-xs px-2 py-1 rounded-full">
                      Администратор
                    </span>
                  ) : (
                    <span className="bg-gray-100 text-gray-700 text-xs px-2 py-1 rounded-full">
                      Пользователь
                    </span>
                  )}
                </TableCell>
                <TableCell>{user.last_active}</TableCell>
                <TableCell className="text-right">
                  <div className="flex justify-end gap-2">
                    <Button variant="outline" size="sm">
                      {user.is_admin ? "Снять права админа" : "Сделать админом"}
                    </Button>
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Card>
    </div>
  );

  const renderStatsTab = () => (
    <div>
      <h2 className="text-2xl font-bold mb-6">Статистика тестирования</h2>
      
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-lg">Всего прохождений</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">19</div>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-lg">Средний результат</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">78%</div>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-lg">Активных пользователей</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">3</div>
          </CardContent>
        </Card>
      </div>
      
      <Card>
        <CardHeader>
          <CardTitle>Результаты тестов</CardTitle>
          <CardDescription>Последние результаты прохождения тестов</CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Пользователь</TableHead>
                <TableHead>Тест</TableHead>
                <TableHead>Результат</TableHead>
                <TableHead>Дата</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {testResults.map((result) => (
                <TableRow key={result.id}>
                  <TableCell className="font-medium">{result.user_name}</TableCell>
                  <TableCell>{result.test_name}</TableCell>
                  <TableCell>
                    <div className="flex items-center gap-2">
                      <Progress 
                        value={(result.score / result.max_score) * 100}
                        className="w-16 h-2"
                      />
                      <span>
                        {result.score}/{result.max_score} ({Math.round((result.score / result.max_score) * 100)}%)
                      </span>
                    </div>
                  </TableCell>
                  <TableCell>{result.date}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );

  return (
    <MainLayout>
      <div className="container mx-auto py-8">
        <h1 className="text-3xl font-bold mb-8">Административная панель</h1>
        
        <Tabs defaultValue="products" value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="grid w-full grid-cols-2 md:grid-cols-4 mb-6">
            <TabsTrigger value="products">Товары</TabsTrigger>
            <TabsTrigger value="tests">Тесты</TabsTrigger>
            <TabsTrigger value="users">Пользователи</TabsTrigger>
            <TabsTrigger value="stats">Статистика</TabsTrigger>
          </TabsList>
          
          <TabsContent value="products">
            {renderProductsTab()}
          </TabsContent>
          
          <TabsContent value="tests">
            {renderTestsTab()}
          </TabsContent>
          
          <TabsContent value="users">
            {renderUsersTab()}
          </TabsContent>
          
          <TabsContent value="stats">
            {renderStatsTab()}
          </TabsContent>
        </Tabs>
      </div>
    </MainLayout>
  );
};

export default AdminPage;
