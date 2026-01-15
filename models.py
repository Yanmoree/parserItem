# models.py - обновленная версия
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
    def price_rubles(self) -> float:
        """Конвертация в рубли"""
        exchange_rate = 12.5
        return round(self.price * exchange_rate, 2)
    
    @property
    def price_display_rub(self) -> str:
        """Цена в рублях"""
        return f"{self.price_rubles:.2f} руб."
    
    @property
    def telegram_message(self) -> str:
        """Форматированное сообщение для Telegram"""
        from bot.parser_settings import parser_settings
        
        # Выбираем валюту из настроек
        currency = parser_settings.get('price_currency', 'yuan')
        
        if currency == 'rubles':
            price_text = f"💰 <b>{self.price_display_rub}</b> ({self.price_display})"
        else:
            price_text = f"💰 <b>{self.price_display}</b> (~{self.price_display_rub})"
        
        # Создаем ссылку в названии
        title_link = f'<a href="{self.url}">{self.title}</a>'
        
        # Форматируем возраст
        if self.age_minutes < 60:
            age_text = f"{int(self.age_minutes)} мин"
        elif self.age_minutes < 1440:
            age_text = f"{int(self.age_minutes / 60)} ч"
        else:
            age_text = f"{int(self.age_minutes / 1440)} дн"
        
        message = (
            f"{title_link}\n"
            f"{price_text}\n"
            f"📍 {self.location}\n"
            f"⏰ {age_text} назад\n"
            f"🔍 По запросу: {self.query}"
        )
        
        return message
    
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
            'is_original': self.is_original,
            'telegram_message': self.telegram_message  # <-- Добавляем
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