# parsers/async_goofish.py - асинхронный парсер для ускорения мониторинга
import aiohttp
import asyncio
import aiofiles
import json
import hashlib
import time
import random
from typing import List, Dict, Optional, Tuple
import logging

from models import Product
from config import (
    GOOFISH_COOKIES_FILE, ROWS_PER_PAGE, 
    REQUEST_TIMEOUT, DEFAULT_USER_AGENT,
    MAX_RETRIES, REQUEST_DELAY_MIN, REQUEST_DELAY_MAX, 
    RATE_LIMIT_DELAY, MAX_REQUESTS_PER_HOUR
)
from storage.files import load_seen_ids, add_seen_ids

logger = logging.getLogger(__name__)

class AsyncGoofishParser:
    """Асинхронный парсер для параллельных запросов"""
    
    def __init__(self, cookies_file=None):
        self.cookies_file = cookies_file or GOOFISH_COOKIES_FILE
        self.cookies = None
        self.session = None
        self.seen_ids = set()
        self.semaphore = asyncio.Semaphore(3)  # Максимум 3 одновременных запроса
        self.request_count = 0
        self.success_count = 0
        
    async def initialize(self):
        """Асинхронная инициализация"""
        self.cookies = await self._load_cookies()
        self.seen_ids = load_seen_ids()
        
        # Создаем сессию aiohttp
        self.session = aiohttp.ClientSession(
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': 'https://www.goofish.com/',
                'Accept': 'application/json',
            },
            cookie_jar=aiohttp.CookieJar()
        )
        
        # Добавляем cookies
        if self.cookies:
            for name, value in self.cookies.items():
                self.session.cookie_jar.update_cookies({name: value})
        
        logger.info(f"🔄 Асинхронный парсер инициализирован")
    
    async def _load_cookies(self) -> Dict:
        """Асинхронная загрузка cookies"""
        try:
            async with aiofiles.open(self.cookies_file, 'r', encoding='utf-8') as f:
                content = await f.read()
                cookies = json.loads(content)
            
            # Проверяем обязательные cookies
            required = ['_m_h5_tk', 't', 'cookie2']
            for req in required:
                if req not in cookies:
                    logger.error(f"❌ Отсутствует cookie: {req}")
                    return {}
            
            return cookies
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки cookies: {e}")
            return {}
    
    async def _make_async_request(self, query: str, page: int, rows: int = 20) -> Optional[Dict]:
        """Асинхронный запрос с семафором"""
        async with self.semaphore:
            self.request_count += 1
            
            # Случайная задержка
            delay = random.uniform(REQUEST_DELAY_MIN, REQUEST_DELAY_MAX)
            logger.debug(f"⏳ Задержка для '{query}': {delay:.1f} сек")
            await asyncio.sleep(delay)
            
            for attempt in range(MAX_RETRIES):
                try:
                    if attempt > 0:
                        retry_delay = 5 * (attempt + 1)
                        logger.info(f"   ↻ Повтор {attempt + 1} для '{query}'. Ждем {retry_delay:.1f} сек")
                        await asyncio.sleep(retry_delay)
                    
                    # Подготовка запроса
                    token_full = self.cookies.get('_m_h5_tk', '')
                    if not token_full or '_' not in token_full:
                        logger.error("❌ Токен невалиден")
                        return None
                    
                    token, token_timestamp = token_full.split('_', 1)
                    
                    data_dict = {
                        "pageNumber": page,
                        "keyword": query,
                        "rowsPerPage": rows,
                        "sortValue": "new",
                    }
                    
                    data_str = json.dumps(data_dict, separators=(',', ':'))
                    
                    # Подпись
                    sign_string = f"{token}&{token_timestamp}&34839810&{data_str}"
                    signature = hashlib.md5(sign_string.encode()).hexdigest()
                    
                    # Параметры
                    params = {
                        'jsv': '2.7.2',
                        'appKey': '34839810',
                        't': token_timestamp,
                        'sign': signature,
                        'api': 'mtop.taobao.idlemtopsearch.pc.search',
                        'v': '1.0',
                        'type': 'json',
                        'dataType': 'json',
                        'data': data_str
                    }
                    
                    logger.info(f"📨 Асинхронный запрос: '{query}', стр. {page}")
                    
                    async with self.session.post(
                        "https://h5api.m.goofish.com/h5/mtop.taobao.idlemtopsearch.pc.search/1.0/",
                        params=params,
                        timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
                    ) as response:
                        
                        if response.status == 200:
                            result = await response.json()
                            
                            if 'ret' in result:
                                ret_val = result['ret']
                                if isinstance(ret_val, list) and len(ret_val) > 0:
                                    ret_str = ret_val[0]
                                    
                                    if 'SUCCESS' in ret_str:
                                        self.success_count += 1
                                        logger.info(f"✅ Успех для '{query}'")
                                        return result
                                    
                                    elif 'RGV587_ERROR' in ret_str:
                                        logger.warning(f"🚫 Rate limit для '{query}'")
                                        await asyncio.sleep(RATE_LIMIT_DELAY)
                                        continue
                            
                            return result
                        
                        elif response.status == 429:
                            logger.error(f"❌ 429 для '{query}'")
                            await asyncio.sleep(RATE_LIMIT_DELAY)
                            continue
                        
                        else:
                            logger.error(f"❌ HTTP {response.status} для '{query}'")
                            await asyncio.sleep(10)
                
                except asyncio.TimeoutError:
                    logger.error(f"⏱️ Таймаут для '{query}' (попытка {attempt + 1})")
                    await asyncio.sleep(15)
                
                except Exception as e:
                    logger.error(f"❌ Ошибка для '{query}': {e}")
                    await asyncio.sleep(10)
            
            logger.error(f"🔥 Все попытки исчерпаны для '{query}'")
            return None
    
    async def search_async(self, query: str, page: int = 1, rows: int = 20) -> List[Product]:
        """Асинхронный поиск"""
        logger.info(f"🔍 Асинхронный поиск: '{query}', стр. {page}")
        
        response = await self._make_async_request(query, page, rows)
        if not response:
            return []
        
        products = self._parse_response_simple(response, query)
        new_products = [p for p in products if p.id not in self.seen_ids]
        
        if new_products:
            new_ids = [p.id for p in new_products]
            add_seen_ids(new_ids)
        
        logger.info(f"   ✅ Найдено: {len(products)}, новых: {len(new_products)}")
        return new_products
    
    def _parse_response_simple(self, api_response: Dict, query: str) -> List[Product]:
        """Упрощенный парсинг (можно использовать общий)"""
        products = []
        
        if not api_response:
            return products
        
        data = api_response.get('data', {})
        result_list = data.get('resultList', [])
        
        for item in result_list[:15]:  # Ограничиваем
            try:
                item_data = item.get('data', {}).get('item', {})
                if not item_data:
                    continue
                
                main_data = item_data.get('main', {})
                args = main_data.get('clickParam', {}).get('args', {})
                
                if not args:
                    continue
                
                item_id = args.get('id', '')
                title = args.get('title', '')[:100]
                price_str = args.get('price', '0')
                
                try:
                    price_str = price_str.replace('¥', '').replace('￥', '').strip()
                    price_yuan = float(price_str)
                except:
                    price_yuan = 0
                
                if not item_id or not title:
                    continue
                
                product = Product(
                    id=item_id,
                    title=title,
                    price_yuan=price_yuan,
                    url=f"https://www.goofish.com/item?id={item_id}",
                    location=args.get('area', ''),
                    age_minutes=0,
                    query=query,
                    images=[],
                    is_original=False
                )
                
                products.append(product)
                
            except Exception as e:
                continue
        
        return products
    
    async def search_multiple_queries(self, queries: List[str], max_pages: int = 1) -> Dict[str, List[Product]]:
        """Параллельный поиск по нескольким запросам"""
        results = {}
        
        # Создаем задачи для всех запросов
        tasks = []
        for query in queries:
            for page in range(1, max_pages + 1):
                task = self.search_async(query, page)
                tasks.append(task)
        
        # Выполняем все задачи параллельно
        all_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Обрабатываем результаты
        task_idx = 0
        for query in queries:
            query_results = []
            for page in range(1, max_pages + 1):
                result = all_results[task_idx]
                task_idx += 1
                
                if isinstance(result, Exception):
                    logger.error(f"❌ Ошибка для '{query}' стр. {page}: {result}")
                elif result:
                    query_results.extend(result)
            
            if query_results:
                results[query] = query_results
        
        return results
    
    async def close(self):
        """Закрытие сессии"""
        if self.session:
            await self.session.close()
    
    def get_stats(self) -> Dict:
        """Статистика"""
        success_rate = (self.success_count / self.request_count * 100) if self.request_count > 0 else 0
        
        return {
            'total_requests': self.request_count,
            'successful_requests': self.success_count,
            'success_rate': round(success_rate, 1),
            'active_sessions': self.semaphore._value if self.semaphore else 0,
        }