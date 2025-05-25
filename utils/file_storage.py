
import os
import logging
import shutil
from typing import Optional, Union, List
from datetime import datetime
from pathlib import Path

# Настройка логирования
logger = logging.getLogger(__name__)

class FileStorage:
    """Класс для управления файловым хранилищем"""
    
    def __init__(self, base_dir: str = "uploads"):
        """
        Инициализация хранилища
        
        :param base_dir: Базовая директория для хранения файлов
        """
        self.base_dir = Path(base_dir)
        self._ensure_directory_exists()
    
    def _ensure_directory_exists(self) -> None:
        """Создает базовую директорию, если она не существует"""
        try:
            self.base_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.error(f"Failed to create base directory {self.base_dir}: {e}")
            raise
    
    def save_file(
        self,
        file_data: Union[bytes, str],
        destination_path: str,
        overwrite: bool = False
    ) -> Optional[str]:
        """
        Сохраняет файл на диск
        
        :param file_data: Данные файла (bytes или str)
        :param destination_path: Относительный путь для сохранения
        :param overwrite: Перезаписывать ли существующий файл
        :return: URL сохраненного файла или None при ошибке
        """
        try:
            file_path = self.base_dir / destination_path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            if file_path.exists() and not overwrite:
                raise FileExistsError(f"File {file_path} already exists")
            
            mode = "wb" if isinstance(file_data, bytes) else "w"
            with open(file_path, mode) as f:
                f.write(file_data)
            
            return f"/uploads/{destination_path}"
        except Exception as e:
            logger.error(f"Error saving file to {destination_path}: {e}")
            return None
    
    def delete_file(self, file_url: str) -> bool:
        """
        Удаляет файл с диска
        
        :param file_url: URL или относительный путь файла
        :return: True если файл удален, False если ошибка
        """
        try:
            file_path = self._url_to_path(file_url)
            if file_path.exists():
                file_path.unlink()
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting file {file_url}: {e}")
            return False
    
    def delete_directory(self, directory_path: str) -> bool:
        """
        Рекурсивно удаляет директорию
        
        :param directory_path: Относительный путь директории
        :return: True если директория удалена, False если ошибка
        """
        try:
            dir_path = self.base_dir / directory_path
            if dir_path.exists() and dir_path.is_dir():
                shutil.rmtree(dir_path)
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting directory {directory_path}: {e}")
            return False
    
    def get_file_url(self, relative_path: str) -> str:
        """
        Возвращает URL для файла по относительному пути
        
        :param relative_path: Относительный путь файла
        :return: Полный URL файла
        """
        return f"/uploads/{relative_path}"
    
    def list_files(self, directory: str = "") -> List[str]:
        """
        Возвращает список файлов в директории
        
        :param directory: Относительный путь директории
        :return: Список относительных путей файлов
        """
        try:
            dir_path = self.base_dir / directory
            return [
                str(file.relative_to(self.base_dir))
                for file in dir_path.rglob("*")
                if file.is_file()
            ]
        except Exception as e:
            logger.error(f"Error listing files in {directory}: {e}")
            return []
    
    def file_exists(self, file_url: str) -> bool:
        """
        Проверяет существование файла
        
        :param file_url: URL или относительный путь файла
        :return: True если файл существует
        """
        try:
            return self._url_to_path(file_url).exists()
        except Exception as e:
            logger.error(f"Error checking file existence {file_url}: {e}")
            return False
    
    def _url_to_path(self, file_url: str) -> Path:
        """
        Преобразует URL в абсолютный путь
        
        :param file_url: URL или относительный путь
        :return: Объект Path
        """
        if file_url.startswith("/uploads/"):
            return self.base_dir / file_url[9:]
        return self.base_dir / file_url
    
    def get_file_size(self, file_url: str) -> Optional[int]:
        """
        Возвращает размер файла в байтах
        
        :param file_url: URL или относительный путь файла
        :return: Размер файла или None при ошибке
        """
        try:
            return self._url_to_path(file_url).stat().st_size
        except Exception as e:
            logger.error(f"Error getting file size {file_url}: {e}")
            return None
    
    def cleanup_old_files(self, days: int = 30) -> int:
        """
        Удаляет файлы старше указанного количества дней
        
        :param days: Количество дней
        :return: Количество удаленных файлов
        """
        try:
            cutoff_time = datetime.now().timestamp() - days * 86400
            deleted = 0
            
            for file_path in self.base_dir.rglob("*"):
                if file_path.is_file() and file_path.stat().st_mtime < cutoff_time:
                    file_path.unlink()
                    deleted += 1
            
            return deleted
        except Exception as e:
            logger.error(f"Error cleaning up old files: {e}")
            return 0

# Глобальный экземпляр хранилища
storage = FileStorage()
