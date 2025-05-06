
from typing import List, Dict, Any, Union, Optional
from datetime import datetime
import json

def format_date(dt: Union[datetime, None]) -> str:
    """Форматирует дату в читаемый вид"""
    if dt is None:
        return "N/A"
    return dt.strftime("%d.%m.%Y %H:%M")

def create_chunks(items: List[Any], chunk_size: int) -> List[List[Any]]:
    """Разбивает список на чанки указанного размера"""
    return [items[i:i + chunk_size] for i in range(0, len(items), chunk_size)]

def safe_get(data: Dict[str, Any], key: str, default: Any = None) -> Any:
    """Безопасно получает значение из словаря по ключу"""
    return data.get(key, default)

def truncate_text(text: str, max_length: int = 100) -> str:
    """Сокращает текст до указанной длины, добавляя многоточие"""
    if len(text) <= max_length:
        return text
    return text[:max_length] + "..."

def calculate_percentage(value: Union[int, float], total: Union[int, float]) -> float:
    """Вычисляет процент от общего значения"""
    if total == 0:
        return 0
    return (value / total) * 100

def serialize_for_firebase(data: Dict[str, Any]) -> Dict[str, Any]:
    """Сериализует данные для сохранения в Firebase"""
    serialized = {}
    for key, value in data.items():
        # Конвертируем datetime в строку
        if isinstance(value, datetime):
            serialized[key] = value.isoformat()
        # Конвертируем сложные объекты в JSON строки
        elif not isinstance(value, (str, int, float, bool, list, dict)) and value is not None:
            serialized[key] = json.dumps(value)
        else:
            serialized[key] = value
    return serialized

def deserialize_from_firebase(data: Dict[str, Any]) -> Dict[str, Any]:
    """Десериализует данные из Firebase"""
    deserialized = {}
    for key, value in data.items():
        # Пытаемся распарсить JSON строки
        if isinstance(value, str):
            try:
                deserialized[key] = json.loads(value)
            except (json.JSONDecodeError, ValueError):
                deserialized[key] = value
        else:
            deserialized[key] = value
    return deserialized
