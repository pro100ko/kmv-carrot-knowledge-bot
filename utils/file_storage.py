
import os
import logging
from typing import Optional, Union
from datetime import datetime

# Настройка логирования
logger = logging.getLogger(__name__)

# Директория для хранения файлов
UPLOAD_DIR = os.environ.get("UPLOAD_DIR", "uploads")

# Создаем директорию, если её нет
if not os.path.exists(UPLOAD_DIR):
    try:
        os.makedirs(UPLOAD_DIR)
    except Exception as e:
        logger.error(f"Ошибка при создании директории для загрузок: {e}")

def save_file(file_data: Union[bytes, str], destination_path: str) -> Optional[str]:
    """Сохраняет файл на диск и возвращает URL"""
    try:
        # Создаем поддиректории при необходимости
        dir_path = os.path.join(UPLOAD_DIR, os.path.dirname(destination_path))
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
        
        # Полный путь к файлу
        file_path = os.path.join(UPLOAD_DIR, destination_path)
        
        # Записываем файл
        mode = "wb" if isinstance(file_data, bytes) else "w"
        with open(file_path, mode) as f:
            f.write(file_data)
        
        # Возвращаем относительный URL
        return f"/uploads/{destination_path}"
    except Exception as e:
        logger.error(f"Ошибка при сохранении файла: {e}")
        return None

def delete_file(file_url: str) -> bool:
    """Удаляет файл с диска"""
    try:
        # Извлекаем путь к файлу из URL
        if file_url.startswith("/uploads/"):
            file_path = os.path.join(UPLOAD_DIR, file_url[9:])
        else:
            file_path = os.path.join(UPLOAD_DIR, file_url)
        
        # Удаляем файл, если он существует
        if os.path.exists(file_path):
            os.remove(file_path)
            return True
        return False
    except Exception as e:
        logger.error(f"Ошибка при удалении файла: {e}")
        return False
