import asyncio
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta

from aiogram import Bot
from aiogram.types import Message, CallbackQuery

from sqlite_db import db
from config import BOT_TOKEN, ADMIN_IDS
from logging_config import setup_logging

# Setup logging
logger = logging.getLogger(__name__)

class SystemTester:
    """Class for system-wide testing"""
    
    def __init__(self, bot: Bot):
        self.bot = bot
        self.test_results: Dict[str, bool] = {}
        self.test_messages: Dict[str, str] = {}
    
    async def run_all_tests(self) -> Dict[str, bool]:
        """Run all system tests"""
        logger.info("Starting system tests...")
        
        # Test database
        await self.test_database()
        
        # Test user management
        await self.test_user_management()
        
        # Test category management
        await self.test_category_management()
        
        # Test product management
        await self.test_product_management()
        
        # Test search functionality
        await self.test_search_functionality()
        
        # Test test management
        await self.test_test_management()
        
        # Test statistics
        await self.test_statistics()
        
        # Test error handling
        await self.test_error_handling()
        
        logger.info("System tests completed")
        return self.test_results
    
    async def test_database(self) -> None:
        """Test database functionality"""
        try:
            # Test connection
            if not db.check_database_integrity():
                raise Exception("Database integrity check failed")
            
            # Test basic operations
            test_user = {
                'telegram_id': 123456789,
                'first_name': 'Test',
                'last_name': 'User',
                'username': 'testuser'
            }
            
            # Test user operations
            db.register_user(test_user)
            user = db.get_user(test_user['telegram_id'])
            if not user:
                raise Exception("User registration failed")
            
            # Test category operations
            test_category = {
                'name': 'Test Category',
                'description': 'Test Description'
            }
            category_id = db.add_category(test_category)
            if not category_id:
                raise Exception("Category creation failed")
            
            # Test product operations
            test_product = {
                'name': 'Test Product',
                'category_id': category_id,
                'description': 'Test Description',
                'price_info': '100 RUB'
            }
            product_id = db.add_product(test_product)
            if not product_id:
                raise Exception("Product creation failed")
            
            # Test search
            products = db.search_products('Test')
            if not products:
                raise Exception("Product search failed")
            
            # Cleanup test data
            db.delete_product(product_id)
            db.delete_category(category_id)
            
            self.test_results['database'] = True
            self.test_messages['database'] = "Database tests passed successfully"
            
        except Exception as e:
            logger.error(f"Database test failed: {e}")
            self.test_results['database'] = False
            self.test_messages['database'] = f"Database test failed: {e}"
    
    async def test_user_management(self) -> None:
        """Test user management functionality"""
        try:
            # Test admin user creation
            for admin_id in ADMIN_IDS:
                user = db.get_user(admin_id)
                if not user or not user.get('is_admin'):
                    raise Exception(f"Admin user {admin_id} not found or not admin")
            
            # Test user state management
            test_state = "test_state"
            test_data = "test_data"
            if not db.update_user_state(ADMIN_IDS[0], test_state, test_data):
                raise Exception("User state update failed")
            
            state = db.get_user_state(ADMIN_IDS[0])
            if not state or state['state'] != test_state:
                raise Exception("User state retrieval failed")
            
            self.test_results['user_management'] = True
            self.test_messages['user_management'] = "User management tests passed successfully"
            
        except Exception as e:
            logger.error(f"User management test failed: {e}")
            self.test_results['user_management'] = False
            self.test_messages['user_management'] = f"User management test failed: {e}"
    
    async def test_category_management(self) -> None:
        """Test category management functionality"""
        try:
            # Test category creation
            test_category = {
                'name': 'Test Category',
                'description': 'Test Description',
                'order_num': 1
            }
            category_id = db.add_category(test_category)
            if not category_id:
                raise Exception("Category creation failed")
            
            # Test category retrieval
            categories = db.get_categories()
            if not any(c['id'] == category_id for c in categories):
                raise Exception("Category retrieval failed")
            
            # Test category update
            update_data = {
                'name': 'Updated Category',
                'description': 'Updated Description'
            }
            if not db.update_category(category_id, update_data):
                raise Exception("Category update failed")
            
            # Test category deletion
            if not db.delete_category(category_id):
                raise Exception("Category deletion failed")
            
            self.test_results['category_management'] = True
            self.test_messages['category_management'] = "Category management tests passed successfully"
            
        except Exception as e:
            logger.error(f"Category management test failed: {e}")
            self.test_results['category_management'] = False
            self.test_messages['category_management'] = f"Category management test failed: {e}"
    
    async def test_product_management(self) -> None:
        """Test product management functionality"""
        try:
            # Create test category
            category_id = db.add_category({
                'name': 'Test Category',
                'description': 'Test Description'
            })
            
            # Test product creation
            test_product = {
                'name': 'Test Product',
                'category_id': category_id,
                'description': 'Test Description',
                'price_info': '100 RUB',
                'storage_conditions': 'Store in cool place',
                'image_urls': ['http://example.com/test.jpg']
            }
            product_id = db.add_product(test_product)
            if not product_id:
                raise Exception("Product creation failed")
            
            # Test product retrieval
            products = db.get_products_by_category(category_id)
            if not any(p['id'] == product_id for p in products):
                raise Exception("Product retrieval failed")
            
            # Test product update
            update_data = {
                'name': 'Updated Product',
                'description': 'Updated Description',
                'category_id': category_id
            }
            if not db.update_product(product_id, update_data):
                raise Exception("Product update failed")
            
            # Test product deletion
            if not db.delete_product(product_id):
                raise Exception("Product deletion failed")
            
            # Cleanup
            db.delete_category(category_id)
            
            self.test_results['product_management'] = True
            self.test_messages['product_management'] = "Product management tests passed successfully"
            
        except Exception as e:
            logger.error(f"Product management test failed: {e}")
            self.test_results['product_management'] = False
            self.test_messages['product_management'] = f"Product management test failed: {e}"
    
    async def test_search_functionality(self) -> None:
        """Test search functionality"""
        try:
            # Create test data
            category_id = db.add_category({
                'name': 'Search Test Category',
                'description': 'Test Description'
            })
            
            product_id = db.add_product({
                'name': 'Search Test Product',
                'category_id': category_id,
                'description': 'Test Description for Search',
                'price_info': '100 RUB'
            })
            
            # Test search by name
            results = db.search_products('Search Test')
            if not results or not any(p['id'] == product_id for p in results):
                raise Exception("Product search by name failed")
            
            # Test search by description
            results = db.search_products('Description for Search')
            if not results or not any(p['id'] == product_id for p in results):
                raise Exception("Product search by description failed")
            
            # Test search with no results
            results = db.search_products('NonexistentProduct')
            if results:
                raise Exception("Search returned results for nonexistent product")
            
            # Cleanup
            db.delete_product(product_id)
            db.delete_category(category_id)
            
            self.test_results['search'] = True
            self.test_messages['search'] = "Search functionality tests passed successfully"
            
        except Exception as e:
            logger.error(f"Search test failed: {e}")
            self.test_results['search'] = False
            self.test_messages['search'] = f"Search test failed: {e}"
    
    async def test_test_management(self) -> None:
        """Test test management functionality"""
        try:
            # Create test category
            category_id = db.add_category({
                'name': 'Test Category',
                'description': 'Test Description'
            })
            
            # Create test user
            test_user = {
                'telegram_id': 987654321,
                'first_name': 'Test',
                'last_name': 'User'
            }
            db.register_user(test_user)
            user = db.get_user(test_user['telegram_id'])
            
            # Test test creation
            test_data = {
                'title': 'Test Quiz',
                'description': 'Test Description',
                'category_id': category_id,
                'passing_score': 70,
                'time_limit': 30,
                'created_by': user['id'],
                'questions': [
                    {
                        'text': 'Test Question 1',
                        'correct_option': 0,
                        'options': ['Option 1', 'Option 2', 'Option 3']
                    }
                ]
            }
            test_id = db.add_test(test_data)
            if not test_id:
                raise Exception("Test creation failed")
            
            # Test test retrieval
            test = db.get_test(test_id)
            if not test or test['title'] != test_data['title']:
                raise Exception("Test retrieval failed")
            
            # Test test update
            update_data = {
                'title': 'Updated Test',
                'description': 'Updated Description',
                'category_id': category_id,
                'passing_score': 80
            }
            if not db.update_test(test_id, update_data):
                raise Exception("Test update failed")
            
            # Test test deletion
            if not db.delete_test(test_id):
                raise Exception("Test deletion failed")
            
            # Cleanup
            db.delete_category(category_id)
            
            self.test_results['test_management'] = True
            self.test_messages['test_management'] = "Test management tests passed successfully"
            
        except Exception as e:
            logger.error(f"Test management test failed: {e}")
            self.test_results['test_management'] = False
            self.test_messages['test_management'] = f"Test management test failed: {e}"
    
    async def test_statistics(self) -> None:
        """Test statistics functionality"""
        try:
            # Test user statistics
            user_stats = db.get_user_stats()
            if not isinstance(user_stats, dict):
                raise Exception("User statistics retrieval failed")
            
            # Test test statistics
            test_stats = db.get_test_stats()
            if not isinstance(test_stats, dict):
                raise Exception("Test statistics retrieval failed")
            
            # Test database statistics
            db_stats = db.get_database_stats()
            if not isinstance(db_stats, dict):
                raise Exception("Database statistics retrieval failed")
            
            self.test_results['statistics'] = True
            self.test_messages['statistics'] = "Statistics tests passed successfully"
            
        except Exception as e:
            logger.error(f"Statistics test failed: {e}")
            self.test_results['statistics'] = False
            self.test_messages['statistics'] = f"Statistics test failed: {e}"
    
    async def test_error_handling(self) -> None:
        """Test error handling functionality"""
        try:
            # Test invalid user ID
            user = db.get_user(-1)
            if user is not None:
                raise Exception("Invalid user ID handling failed")
            
            # Test invalid category ID
            products = db.get_products_by_category(-1)
            if products is None:
                raise Exception("Invalid category ID handling failed")
            
            # Test invalid product ID
            product = db.get_product(-1)
            if product is not None:
                raise Exception("Invalid product ID handling failed")
            
            # Test invalid test ID
            test = db.get_test(-1)
            if test is not None:
                raise Exception("Invalid test ID handling failed")
            
            self.test_results['error_handling'] = True
            self.test_messages['error_handling'] = "Error handling tests passed successfully"
            
        except Exception as e:
            logger.error(f"Error handling test failed: {e}")
            self.test_results['error_handling'] = False
            self.test_messages['error_handling'] = f"Error handling test failed: {e}"

async def run_system_tests() -> None:
    """Run all system tests and report results"""
    try:
        # Initialize bot
        bot = Bot(token=BOT_TOKEN)
        
        # Create tester
        tester = SystemTester(bot)
        
        # Run tests
        results = await tester.run_all_tests()
        
        # Print results
        print("\n=== System Test Results ===")
        for component, success in results.items():
            status = "✅ PASSED" if success else "❌ FAILED"
            message = tester.test_messages[component]
            print(f"\n{component}: {status}")
            print(f"Message: {message}")
        
        # Close bot
        await bot.session.close()
        
    except Exception as e:
        logger.error(f"System tests failed: {e}")
        raise

if __name__ == "__main__":
    # Setup logging
    setup_logging()
    
    # Run tests
    asyncio.run(run_system_tests()) 