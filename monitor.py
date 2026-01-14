# monitor.py - улучшенная версия с методами run() и stop()
import requests
from bs4 import BeautifulSoup
import time
import re
import asyncio
from typing import List, Dict
from datetime import datetime, timedelta

class GoofishMonitor:
    def __init__(self, bot=None):
        """Инициализация монитора с опциональной ссылкой на бота"""
        self.bot = bot
        self.is_running = False
        self.base_url = "https://goofish.com"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
        })
        print("✅ GoofishMonitor инициализирован")
    
    async def run(self):
        """Асинхронный запуск мониторинга"""
        self.is_running = True
        print("📊 Мониторинг Goofish запущен")
        
        while self.is_running:
            try:
                # Здесь можно добавить логику периодической проверки
                print("🔍 Мониторинг активен...")
                await asyncio.sleep(60)  # Пауза 60 секунд между проверками
                
            except Exception as e:
                print(f"❌ Ошибка в цикле мониторинга: {e}")
                await asyncio.sleep(30)  # Ждем 30 секунд при ошибке
    
    def stop(self):
        """Остановка мониторинга"""
        self.is_running = False
        print("🛑 Мониторинг остановлен")
    
    def get_stats(self):
        """Получение статистики мониторинга"""
        return {
            'is_running': self.is_running,
            'status': 'active' if self.is_running else 'stopped',
            'monitor_type': 'GoofishMonitor'
        }
    
    # Остальные ваши методы остаются без изменений:
    def parse_product_details(self, product_url: str) -> Dict:
        """Парсит детальную информацию о товаре"""
        try:
            response = self.session.get(product_url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Находим все изображения товара
            images = []
            img_elements = soup.find_all('img', {'src': re.compile(r'\.(jpg|jpeg|png|webp)')})
            
            for img in img_elements[:10]:  # Берем первые 10 фото
                img_url = img.get('src')
                if img_url and img_url.startswith('http'):
                    if img_url not in images:
                        images.append(img_url)
            
            # Ищем описание для проверки на оригинал
            description = ""
            desc_elements = soup.find_all(['div', 'p'], class_=re.compile(r'desc|description|detail'))
            for elem in desc_elements:
                if elem.text:
                    description += elem.text + " "
            
            # Проверяем на оригинал по ключевым словам
            original_keywords = ['оригинал', 'original', 'genuine', 'официальный', 'авторизованный', 
                                'заводской', 'brand new', 'new', 'новый']
            is_original = any(keyword.lower() in description.lower() for keyword in original_keywords)
            
            return {
                'images': images[:10],  # Максимум 10 фото
                'description': description[:500],  # Первые 500 символов
                'is_original': is_original,
                'detailed_url': product_url
            }
            
        except Exception as e:
            print(f"❌ Ошибка парсинга деталей товара: {e}")
            return {
                'images': [],
                'description': '',
                'is_original': False,
                'detailed_url': product_url
            }
    
    def search_all_pages(self, query: str, max_minutes: int = 60) -> List[Dict]:
        """Ищет товары по запросу"""
        products = []
        
        try:
            # Энкодим запрос для URL
            encoded_query = requests.utils.quote(query)
            url = f"{self.base_url}/search?q={encoded_query}&sort=new"
            
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Находим все карточки товаров
            product_cards = soup.find_all('div', class_=re.compile(r'product|item|card'))
            
            for card in product_cards[:20]:  # Ограничиваем 20 товарами
                try:
                    product = self._parse_product_card(card, query)
                    if product:
                        # Добавляем детальную информацию
                        details = self.parse_product_details(product['url'])
                        product.update(details)
                        
                        # Фильтруем по времени
                        if product['age_minutes'] <= max_minutes:
                            products.append(product)
                            
                except Exception as e:
                    print(f"❌ Ошибка парсинга карточки: {e}")
                    continue
            
            # Сортируем по новизне
            products.sort(key=lambda x: x['age_minutes'])
            
        except Exception as e:
            print(f"❌ Ошибка поиска товаров: {e}")
        
        return products
    
    def _parse_product_card(self, card, search_query: str) -> Dict:
        """Парсит карточку товара"""
        try:
            # Название и ссылка
            title_elem = card.find('a', href=True)
            if not title_elem:
                return None
                
            title = title_elem.text.strip()
            url = title_elem['href']
            if not url.startswith('http'):
                url = self.base_url + url
            
            # Цена
            price_elem = card.find(class_=re.compile(r'price|cost|amount'))
            price_text = price_elem.text.strip() if price_elem else "0"
            
            # Извлекаем число из цены
            price_match = re.search(r'[\d,\.]+', price_text.replace(',', ''))
            price_yuan = float(price_match.group()) if price_match else 0
            
            # Конвертируем в рубли (примерный курс ~12.5)
            price_rub = round(price_yuan * 12.5, 2)
            
            # ID товара (из URL или хэш)
            product_id = str(abs(hash(url)))  # Простой хэш
            
            # Локация
            location_elem = card.find(class_=re.compile(r'location|city|place'))
            location = location_elem.text.strip() if location_elem else "Не указано"
            
            # Возраст товара (упрощенный вариант)
            age_elem = card.find(class_=re.compile(r'time|age|date'))
            age_text = age_elem.text.strip() if age_elem else "1 час"
            
            # Парсим возраст (пример: "2 часа назад", "1 день назад")
            age_minutes = self._parse_age_to_minutes(age_text)
            
            return {
                'id': product_id,
                'title': title,
                'price_yuan': price_yuan,
                'price_rub': price_rub,
                'price_display': f"¥{price_yuan:.2f} (~{price_rub:.0f} руб)",
                'url': url,
                'location': location,
                'age_minutes': age_minutes,
                'age_text': age_text,
                'search_query': search_query,
                'publish_date': datetime.now().strftime('%Y-%m-%d %H:%M'),
                'images': [],  # Будет заполнено позже
                'is_original': False,  # Будет определено позже
            }
            
        except Exception as e:
            print(f"❌ Ошибка парсинга карточки: {e}")
            return None
    
    def _parse_age_to_minutes(self, age_text: str) -> int:
        """Конвертирует текстовый возраст в минуты"""
        age_text = age_text.lower()
        
        if 'минут' in age_text or 'minute' in age_text:
            match = re.search(r'\d+', age_text)
            return int(match.group()) if match else 5
        elif 'час' in age_text or 'hour' in age_text:
            match = re.search(r'\d+', age_text)
            return int(match.group()) * 60 if match else 60
        elif 'день' in age_text or 'day' in age_text:
            match = re.search(r'\d+', age_text)
            return int(match.group()) * 1440 if match else 1440
        elif 'недел' in age_text or 'week' in age_text:
            match = re.search(r'\d+', age_text)
            return int(match.group()) * 10080 if match else 10080
        else:
            return 60  # По умолчанию 1 час