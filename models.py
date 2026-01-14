# models.py - исправленная версия
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from datetime import datetime

@dataclass
class Product:
    """Модель товара"""
    id: str
    title: str
    price: float  # цена в юанях
    url: str
    site: str = "goofish"
    location: str = ""
    age_minutes: float = 0
    query: str = ""
    images: List[str] = None
    is_original: bool = False
    
    def __post_init__(self):
        # Обрезаем слишком длинные названия
        if len(self.title) > 200:
            self.title = self.title[:197] + "..."
        if self.images is None:
            self.images = []
    
    @property
    def price_display(self) -> str:
        return f"{self.price:.2f} ¥"
    
    @property
    def price_display_yuan(self) -> str:
        return f"{self.price:.2f} ¥"
    
    @property 
    def price_rubles(self) -> float:
        """Конвертация в рубли (примерный курс ~12.5)"""
        exchange_rate = 12.5
        return round(self.price * exchange_rate, 2)
    
    @property
    def price_display_rub(self) -> str:
        """Цена в рублях для отображения"""
        return f"{self.price_rubles:.2f} руб."
    
    def to_dict(self) -> Dict[str, Any]:
        """Конвертация в словарь"""
        return {
            'id': self.id,
            'title': self.title,
            'price': self.price,
            'price_display': self.price_display,
            'price_rubles': self.price_rubles,
            'price_display_rub': self.price_display_rub,
            'url': self.url,
            'site': self.site,
            'location': self.location,
            'age_minutes': self.age_minutes,
            'query': self.query,
            'images': self.images,
            'is_original': self.is_original
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Product':
        """Создание из словаря"""
        return cls(
            id=data.get('id', ''),
            title=data.get('title', ''),
            price=data.get('price', 0),
            url=data.get('url', ''),
            site=data.get('site', 'goofish'),
            location=data.get('location', ''),
            age_minutes=data.get('age_minutes', 0),
            query=data.get('query', ''),
            images=data.get('images', []),
            is_original=data.get('is_original', False)
        )