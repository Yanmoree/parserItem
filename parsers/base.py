from abc import ABC, abstractmethod
from typing import List, Dict
from models import Product

class BaseParser(ABC):
    """Базовый класс парсера"""
    
    def __init__(self, site_name: str):
        self.site_name = site_name
    
    @abstractmethod
    def search(self, query: str, **kwargs) -> List[Product]:
        """Поиск товаров"""
        pass
    
    def filter_new(self, products: List[Product], seen_ids: set) -> List[Product]:
        """Фильтрация новых товаров"""
        return [p for p in products if p.id not in seen_ids]