
// User types
export interface User {
  id: string;
  telegram_id: number;
  first_name: string;
  last_name?: string;
  username?: string;
  is_admin: boolean;
  created_at: Date;
  last_active: Date;
}

// Product categories
export interface Category {
  id: string;
  name: string;
  description?: string;
  image_url?: string;
  order: number;
}

// Product information
export interface Product {
  id: string;
  name: string;
  category_id: string;
  description: string;
  price_info?: string;
  storage_conditions?: string;
  image_urls: string[];
  video_url?: string;
  created_at: Date;
  updated_at: Date;
}

// Test structure
export interface Test {
  id: string;
  title: string;
  description: string;
  category_id?: string;
  questions: Question[];
  passing_score: number;
  is_active: boolean;
  created_at: Date;
  created_by: string;
}

export interface Question {
  id: string;
  text: string;
  options: string[];
  correct_option: number;
  explanation?: string;
}

// Test attempt results
export interface TestAttempt {
  id: string;
  user_id: string;
  test_id: string;
  score: number;
  max_score: number;
  answers: UserAnswer[];
  completed: boolean;
  started_at: Date;
  completed_at?: Date;
}

export interface UserAnswer {
  question_id: string;
  selected_option: number;
  is_correct: boolean;
}
