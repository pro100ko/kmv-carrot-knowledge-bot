
import React, { useState } from "react";
import MainLayout from "@/layouts/MainLayout";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Label } from "@/components/ui/label";
import { CheckCircle2, XCircle } from "lucide-react";

// Mock data
const availableTests = [
  { 
    id: "1", 
    title: "Основы знаний о фруктах", 
    description: "Базовый тест на знание ассортимента фруктов", 
    questionCount: 5,
    estimatedTime: "5-7 минут",
    category: "Основная витрина"
  },
  { 
    id: "2", 
    title: "Экзотические фрукты", 
    description: "Тест на знание экзотических фруктов и их особенностей", 
    questionCount: 8,
    estimatedTime: "10-12 минут",
    category: "Экзотика"
  },
  { 
    id: "3", 
    title: "Сезонные овощи", 
    description: "Проверка знаний о сезонных овощах и их свойствах", 
    questionCount: 6,
    estimatedTime: "8-10 минут",
    category: "Сезонный стол"
  },
];

const mockTest = {
  id: "1",
  title: "Основы знаний о фруктах",
  questions: [
    {
      id: "q1",
      text: "Какой фрукт богат витамином C?",
      options: ["Банан", "Апельсин", "Груша", "Авокадо"],
      correctOption: 1
    },
    {
      id: "q2",
      text: "Какой из этих фруктов не относится к цитрусовым?",
      options: ["Лимон", "Мандарин", "Яблоко", "Грейпфрут"],
      correctOption: 2
    },
    {
      id: "q3",
      text: "Какой фрукт содержит наибольшее количество калия?",
      options: ["Банан", "Яблоко", "Киви", "Апельсин"],
      correctOption: 0
    },
    {
      id: "q4",
      text: "Какой фрукт традиционно считается символом здоровья?",
      options: ["Груша", "Персик", "Яблоко", "Виноград"],
      correctOption: 2
    },
    {
      id: "q5",
      text: "Какой фрукт является самым популярным в мире по объему потребления?",
      options: ["Яблоко", "Банан", "Апельсин", "Манго"],
      correctOption: 1
    }
  ]
};

const TestingPage = () => {
  const [selectedTest, setSelectedTest] = useState<string | null>(null);
  const [currentQuestion, setCurrentQuestion] = useState(0);
  const [answers, setAnswers] = useState<Array<number | null>>(Array(mockTest.questions.length).fill(null));
  const [selectedOption, setSelectedOption] = useState<number | null>(null);
  const [testCompleted, setTestCompleted] = useState(false);
  
  const handleTestSelect = (testId: string) => {
    setSelectedTest(testId);
    setCurrentQuestion(0);
    setAnswers(Array(mockTest.questions.length).fill(null));
    setSelectedOption(null);
    setTestCompleted(false);
  };
  
  const handleOptionSelect = (optionIndex: number) => {
    setSelectedOption(optionIndex);
  };
  
  const handleNextQuestion = () => {
    if (selectedOption !== null) {
      const newAnswers = [...answers];
      newAnswers[currentQuestion] = selectedOption;
      setAnswers(newAnswers);
      
      if (currentQuestion < mockTest.questions.length - 1) {
        setCurrentQuestion(currentQuestion + 1);
        setSelectedOption(null);
      } else {
        setTestCompleted(true);
      }
    }
  };
  
  const calculateScore = () => {
    return answers.reduce((score, answer, index) => {
      if (answer === mockTest.questions[index].correctOption) {
        return score + 1;
      }
      return score;
    }, 0);
  };
  
  const handleRestartTest = () => {
    setCurrentQuestion(0);
    setAnswers(Array(mockTest.questions.length).fill(null));
    setSelectedOption(null);
    setTestCompleted(false);
  };
  
  const handleBackToTests = () => {
    setSelectedTest(null);
    setTestCompleted(false);
  };

  return (
    <MainLayout>
      <div className="container mx-auto py-8">
        <h1 className="text-3xl font-bold mb-8">Система тестирования</h1>
        
        {!selectedTest ? (
          <div>
            <p className="text-gray-600 mb-6">
              Выберите тест для проверки ваших знаний о продуктах компании
            </p>
            
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {availableTests.map(test => (
                <Card key={test.id} className="cursor-pointer hover:shadow-lg transition-shadow" onClick={() => handleTestSelect(test.id)}>
                  <CardHeader>
                    <CardTitle>{test.title}</CardTitle>
                    <CardDescription>Категория: {test.category}</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <p className="mb-4">{test.description}</p>
                    <div className="flex justify-between text-sm text-gray-500">
                      <span>{test.questionCount} вопросов</span>
                      <span>~{test.estimatedTime}</span>
                    </div>
                  </CardContent>
                  <CardFooter>
                    <Button className="w-full bg-leaf hover:bg-leaf-dark">
                      Начать тест
                    </Button>
                  </CardFooter>
                </Card>
              ))}
            </div>
          </div>
        ) : !testCompleted ? (
          <div className="max-w-3xl mx-auto">
            <Card>
              <CardHeader>
                <div className="flex justify-between items-center mb-2">
                  <Button variant="ghost" onClick={handleBackToTests}>
                    Вернуться к списку тестов
                  </Button>
                  <span className="text-sm text-gray-500">
                    Вопрос {currentQuestion + 1} из {mockTest.questions.length}
                  </span>
                </div>
                <Progress value={(currentQuestion / mockTest.questions.length) * 100} className="mb-4" />
                <CardTitle>{mockTest.title}</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="mb-6">
                  <h2 className="text-xl font-semibold mb-4">
                    {mockTest.questions[currentQuestion].text}
                  </h2>
                  
                  <RadioGroup value={selectedOption?.toString()} onValueChange={(value) => handleOptionSelect(parseInt(value))}>
                    {mockTest.questions[currentQuestion].options.map((option, index) => (
                      <div key={index} className="flex items-center space-x-2 mb-2 p-2 hover:bg-gray-50 rounded">
                        <RadioGroupItem value={index.toString()} id={`option-${index}`} />
                        <Label htmlFor={`option-${index}`} className="w-full cursor-pointer">
                          {option}
                        </Label>
                      </div>
                    ))}
                  </RadioGroup>
                </div>
              </CardContent>
              <CardFooter>
                <Button 
                  onClick={handleNextQuestion} 
                  disabled={selectedOption === null}
                  className="w-full bg-carrot hover:bg-carrot-dark"
                >
                  {currentQuestion < mockTest.questions.length - 1 ? "Следующий вопрос" : "Завершить тест"}
                </Button>
              </CardFooter>
            </Card>
          </div>
        ) : (
          <div className="max-w-3xl mx-auto">
            <Card>
              <CardHeader>
                <CardTitle>Результаты теста</CardTitle>
                <CardDescription>{mockTest.title}</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="text-center mb-6">
                  <div className="text-4xl font-bold mb-2">
                    {calculateScore()} из {mockTest.questions.length}
                  </div>
                  <p className="text-lg text-gray-600">
                    {calculateScore() / mockTest.questions.length >= 0.7 
                      ? "Отличный результат! Вы хорошо знаете материал." 
                      : "Вам стоит повторить материал и попробовать еще раз."}
                  </p>
                </div>
                
                <div className="space-y-4">
                  <h3 className="font-semibold">Детализация ответов:</h3>
                  {mockTest.questions.map((question, index) => (
                    <div key={index} className={`p-4 rounded-lg ${answers[index] === question.correctOption ? 'bg-green-50' : 'bg-red-50'}`}>
                      <div className="flex gap-2 items-start mb-2">
                        {answers[index] === question.correctOption ? (
                          <CheckCircle2 className="h-5 w-5 text-green-600 mt-0.5" />
                        ) : (
                          <XCircle className="h-5 w-5 text-red-600 mt-0.5" />
                        )}
                        <h4 className="font-medium">{question.text}</h4>
                      </div>
                      <div className="ml-7">
                        <p>Ваш ответ: {question.options[answers[index] as number]}</p>
                        {answers[index] !== question.correctOption && (
                          <p className="text-green-700">Правильный ответ: {question.options[question.correctOption]}</p>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
              <CardFooter className="flex justify-between">
                <Button variant="outline" onClick={handleBackToTests}>
                  К списку тестов
                </Button>
                <Button onClick={handleRestartTest} className="bg-carrot hover:bg-carrot-dark">
                  Пройти тест заново
                </Button>
              </CardFooter>
            </Card>
          </div>
        )}
      </div>
    </MainLayout>
  );
};

export default TestingPage;
