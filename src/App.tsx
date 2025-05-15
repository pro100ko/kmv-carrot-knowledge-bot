
import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import MainLayout from './layouts/MainLayout';
import Index from './pages/Index';
import KnowledgePage from './pages/KnowledgePage';
import TestingPage from './pages/TestingPage';
import AdminPage from './pages/AdminPage';
import NotFound from './pages/NotFound';
import './App.css';

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<MainLayout />}>
          <Route index element={<Index />} />
          <Route path="knowledge" element={<KnowledgePage />} />
          <Route path="testing" element={<TestingPage />} />
          <Route path="admin" element={<AdminPage />} />
          <Route path="*" element={<NotFound />} />
        </Route>
      </Routes>
    </Router>
  );
}

export default App;
