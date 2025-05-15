
# Флаг, указывающий доступность Firebase
FIREBASE_AVAILABLE = False

# Пытаемся импортировать Firebase Admin SDK
try:
    import firebase_admin
    from firebase_admin import credentials, firestore
    import json
    
    # Инициализация Firebase
    try:
        # Путь к файлу сервисного аккаунта
        cred = credentials.Certificate("service_account.json")
        firebase_admin.initialize_app(cred)
        db = firestore.client()
        FIREBASE_AVAILABLE = True
        print("Firebase successfully initialized")
    except Exception as e:
        print(f"Firebase initialization error: {e}")
except ImportError:
    print("Firebase Admin SDK is not installed. Firebase functionality will be disabled.")

# Функции для работы с категориями товаров
def get_categories():
    """Получает список категорий товаров"""
    if not FIREBASE_AVAILABLE:
        # Если Firebase недоступен, используем SQLite
        import sqlite_db
        return sqlite_db.get_categories()
    
    categories = []
    try:
        categories_ref = db.collection('categories').order_by('order')
        docs = categories_ref.stream()
        
        for doc in docs:
            category = doc.to_dict()
            category['id'] = doc.id
            categories.append(category)
    except Exception as e:
        print(f"Error getting categories from Firebase: {e}")
    
    return categories

def get_products_by_category(category_id):
    """Получает список продуктов по ID категории"""
    if not FIREBASE_AVAILABLE:
        # Если Firebase недоступен, используем SQLite
        import sqlite_db
        return sqlite_db.get_products_by_category(category_id)
    
    products = []
    try:
        products_ref = db.collection('products').where('category_id', '==', category_id)
        docs = products_ref.stream()
        
        for doc in docs:
            product = doc.to_dict()
            product['id'] = doc.id
            products.append(product)
    except Exception as e:
        print(f"Error getting products from Firebase: {e}")
    
    return products

def get_product(product_id):
    """Получает информацию о продукте по ID"""
    if not FIREBASE_AVAILABLE:
        # Если Firebase недоступен, используем SQLite
        import sqlite_db
        return sqlite_db.get_product(product_id)
    
    try:
        doc_ref = db.collection('products').document(product_id)
        doc = doc_ref.get()
        
        if doc.exists:
            product = doc.to_dict()
            product['id'] = doc.id
            return product
    except Exception as e:
        print(f"Error getting product from Firebase: {e}")
    
    return None

def search_products(query):
    """Поиск продуктов по названию или описанию"""
    if not FIREBASE_AVAILABLE:
        # Если Firebase недоступен, используем SQLite
        import sqlite_db
        return sqlite_db.search_products(query)
    
    products = []
    try:
        # Firebase не поддерживает полнотекстовый поиск напрямую
        # Поэтому получаем все продукты и фильтруем их на стороне приложения
        products_ref = db.collection('products')
        docs = products_ref.stream()
        
        query = query.lower()
        for doc in docs:
            product = doc.to_dict()
            product['id'] = doc.id
            
            # Проверяем, содержит ли название или описание искомый текст
            if (
                query in product.get('name', '').lower() or 
                query in product.get('description', '').lower()
            ):
                products.append(product)
            
            if len(products) >= 10:  # Ограничиваем результаты
                break
    except Exception as e:
        print(f"Error searching products in Firebase: {e}")
    
    return products
