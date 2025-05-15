
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { Toaster } from 'sonner';
import MainLayout from './layouts/MainLayout';
import Index from './pages/Index';
import NotFound from './pages/NotFound';
import KnowledgePage from './pages/KnowledgePage';
import TestingPage from './pages/TestingPage';
import AdminPage from './pages/AdminPage';

function App() {
  return (
    <Router>
      <MainLayout>
        <Routes>
          <Route path="/" element={<Index />} />
          <Route path="/knowledge" element={<KnowledgePage />} />
          <Route path="/testing" element={<TestingPage />} />
          <Route path="/admin" element={<AdminPage />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </MainLayout>
      <Toaster position="bottom-right" />
    </Router>
  );
}

export default App;
