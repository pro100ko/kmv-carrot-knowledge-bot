from typing import List, Dict, Any, Union, Optional
from datetime import datetime
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

def format_date(dt: Optional[datetime]) -> str:
    """Форматирует дату в читаемый вид"""
    if dt is None:
        return "N/A"
    return dt.strftime("%d.%m.%Y %H:%M")

def create_chunks(items: List[Any], chunk_size: int) -> List[List[Any]]:
    """Разбивает список на чанки указанного размера"""
    return [items[i:i + chunk_size] for i in range(0, len(items), chunk_size)]

def safe_get(data: Dict[str, Any], key: str, default: Any = None) -> Any:
    """Безопасно получает значение из словаря по ключу"""
    try:
        return data.get(key, default)
    except AttributeError:
        logger.warning(f"Attempt to get key '{key}' from non-dict object")
        return default

def truncate_text(text: str, max_length: int = 100, ellipsis: str = "...") -> str:
    """Сокращает текст до указанной длины, добавляя многоточие"""
    if not isinstance(text, str):
        return str(text)
    if len(text) <= max_length:
        return text
    return text[:max_length - len(ellipsis)] + ellipsis

def calculate_percentage(value: Union[int, float], total: Union[int, float]) -> float:
    """Вычисляет процент от общего значения"""
    try:
        if total == 0:
            return 0.0
        return round((value / total) * 100, 2)
    except TypeError:
        logger.warning("Invalid types for percentage calculation")
        return 0.0

def prepare_for_sqlite(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Подготавливает данные для сохранения в SQLite:
    - Конвертирует datetime в строки
    - Сериализует сложные объекты в JSON
    - Обрабатывает Path объекты
    """
    prepared = {}
    for key, value in data.items():
        if value is None:
            prepared[key] = None
        elif isinstance(value, datetime):
            prepared[key] = value.isoformat()
        elif isinstance(value, Path):
            prepared[key] = str(value)
        elif isinstance(value, (str, int, float, bool)):
            prepared[key] = value
        else:
            try:
                prepared[key] = json.dumps(value, ensure_ascii=False)
            except (TypeError, ValueError):
                logger.warning(f"Could not serialize value for key '{key}'")
                prepared[key] = str(value)
    return prepared

def parse_from_sqlite(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Парсит данные, полученные из SQLite:
    - Пытается десериализовать JSON строки
    - Конвертирует строки дат в datetime
    """
    parsed = {}
    for key, value in data.items():
        if value is None:
            parsed[key] = None
        elif isinstance(value, str):
            # Пробуем распарсить JSON
            if (value.startswith('{') and value.endswith('}')) or \
               (value.startswith('[') and value.endswith(']')):
                try:
                    parsed[key] = json.loads(value)
                    continue
                except json.JSONDecodeError:
                    pass
            
            # Пробуем распарсить дату
            try:
                parsed[key] = datetime.fromisoformat(value)
                continue
            except ValueError:
                pass
            
            parsed[key] = value
        else:
            parsed[key] = value
    return parsed

def validate_file_path(file_path: Union[str, Path], base_dir: Path = None) -> Optional[Path]:
    """
    Проверяет и нормализует путь к файлу:
    - Преобразует в Path объект
    - Проверяет нахождение внутри базовой директории (если указана)
    - Проверяет существование файла
    """
    try:
        path = Path(file_path) if isinstance(file_path, str) else file_path
        
        if base_dir is not None:
            path = base_dir / path
            if not path.resolve().is_relative_to(base_dir.resolve()):
                logger.warning(f"Attempt to access file outside base directory: {file_path}")
                return None
        
        return path if path.exists() else None
    except Exception as e:
        logger.warning(f"Invalid file path {file_path}: {e}")
        return None

def dict_factory(cursor, row) -> Dict[str, Any]:
    """Фабрика для преобразования строк SQLite в словари"""
    return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}

def generate_where_clause(filters: Dict[str, Any]) -> tuple:
    """
    Генерирует WHERE условие и параметры для SQL запроса
    Возвращает кортеж: (where_clause, params_dict)
    """
    if not filters:
        return "", {}
    
    conditions = []
    params = {}
    
    for idx, (key, value) in enumerate(filters.items()):
        if value is None:
            conditions.append(f"{key} IS NULL")
        elif isinstance(value, (list, tuple)):
            placeholders = ", ".join([f":{key}_{i}" for i in range(len(value))])
            conditions.append(f"{key} IN ({placeholders})")
            params.update({f"{key}_{i}": val for i, val in enumerate(value)})
        else:
            conditions.append(f"{key} = :{key}")
            params[key] = value
    
    where_clause = "WHERE " + " AND ".join(conditions)
    return where_clause, params
