# parsers/goofish.py - ВЕРСИЯ С ДИАГНОСТИКОЙ ПОТЕРЬ И ФОТО
import requests
import json
import time
import hashlib
import re
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from models import Product
from config import (
    GOOFISH_COOKIES_FILE, ROWS_PER_PAGE, 
    REQUEST_TIMEOUT, DEFAULT_USER_AGENT
)
from storage.files import load_seen_ids, add_seen_ids

# Отключаем предупреждения SSL для чистоты логов
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class GoofishParser:
    """Парсер для Goofish с диагностикой потерь данных"""
    
    def __init__(self, cookies_file=None):
        self.base_url = "https://h5api.m.goofish.com/h5/mtop.taobao.idlemtopsearch.pc.search/1.0/"
        self.cookies_file = cookies_file or GOOFISH_COOKIES_FILE
        self.cookies = self._load_cookies()
        self.session = self._create_session()
        self.seen_ids = load_seen_ids()
        
        print(f"✅ Парсер инициализирован. Cookies: {len(self.cookies)}")
        
        # Счетчики для диагностики
        self.stats = {
            'total_api_items': 0,
            'valid_items': 0,
            'invalid_items': 0,
            'filtered_by_query': 0,
            'filtered_by_age': 0,
            'filtered_by_seen': 0,
            'final_products': 0
        }
    
    def _load_cookies(self) -> Dict:
        """Загрузка cookies"""
        if self.cookies_file.exists():
            try:
                with open(self.cookies_file, 'r', encoding='utf-8') as f:
                    cookies = json.load(f)
                
                required = ['_m_h5_tk', 't', 'cookie2']
                missing = [r for r in required if r not in cookies]
                if missing:
                    print(f"⚠️ Отсутствуют важные cookies: {missing}")
                
                return cookies
            except Exception as e:
                print(f"❌ Ошибка загрузки cookies: {e}")
                return {}
        else:
            print(f"❌ Файл {self.cookies_file} не найден")
            return {}
    
    def _create_session(self):
        """Создание HTTP сессии"""
        session = requests.Session()
        if self.cookies:
            session.cookies.update(self.cookies)
        
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://www.goofish.com/',
            'Origin': 'https://www.goofish.com',
            'Accept': 'application/json',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'Content-Type': 'application/x-www-form-urlencoded',
        })
        
        return session
    
    def _make_request(self, query: str, page: int, rows: int) -> Optional[Dict]:
        """Выполнение запроса к API"""
        try:
            timestamp = str(int(time.time() * 1000))
            
            token_full = self.cookies.get('_m_h5_tk', '')
            if '_' not in token_full:
                print("❌ Токен в неправильном формате")
                return None
            
            token = token_full.split('_')[0]
            
            data_dict = {
                "pageNumber": page,
                "keyword": query,
                "fromFilter": False,
                "rowsPerPage": rows,
                "sortValue": "new",
                "sortField": "",
                "customDistance": "",
                "gps": "",
                "propValueStr": {},
                "customGps": "",
                "searchReqFromPage": "pcSearch",
                "extraFilterValue": "{}",
                "userPositionJson": "{}"
            }
            
            data_str = json.dumps(data_dict, separators=(',', ':'))
            
            sign_string = f"{token}&{timestamp}&34839810&{data_str}"
            signature = hashlib.md5(sign_string.encode()).hexdigest()
            
            params = {
                'jsv': '2.7.2',
                'appKey': '34839810',
                't': timestamp,
                'sign': signature,
                'v': '1.0',
                'type': 'originaljson',
                'accountSite': 'xianyu',
                'dataType': 'json',
                'timeout': '20000',
                'api': 'mtop.taobao.idlemtopsearch.pc.search',
                'sessionOption': 'AutoLoginOnly',
                'spm_cnt': 'a21ybx.search.0.0',
                'spm_pre': 'a21ybx.search.searchInput.0',
                'data': data_str
            }
            
            print(f"\n🔧 Запрос: '{query}', стр {page}, rows={rows}")
            
            time.sleep(2)
            
            response = self.session.post(
                self.base_url, 
                params=params, 
                timeout=REQUEST_TIMEOUT,
                verify=False
            )
            
            print(f"   Статус: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                
                if 'ret' in result:
                    ret_val = result['ret']
                    if isinstance(ret_val, list) and len(ret_val) > 0:
                        ret_str = ret_val[0]
                        print(f"   API Ret: {ret_str}")
                        
                        if 'SUCCESS' in ret_str:
                            print(f"✅ УСПЕХ!")
                            return result
                        elif 'RGV587_ERROR' in ret_str:
                            print(f"🚫 RATE LIMIT обнаружен!")
                            time.sleep(30)
                            return None
                
                return result
            else:
                print(f"❌ HTTP ошибка: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Ошибка запроса: {e}")
            import traceback
            traceback.print_exc()
        
        return None
    
    def search(self, query: str, page: int = 1, rows: int = None, 
               only_new: bool = True, max_age_minutes: float = None) -> List[Product]:
        """Поиск товаров с ДИАГНОСТИКОЙ потерь"""
        rows = rows or ROWS_PER_PAGE
        
        # Сбрасываем статистику
        self.stats = {k: 0 for k in self.stats}
        
        print(f"\n🔍 Поиск: '{query}', стр {page}, rows={rows}")
        print(f"   Фильтры: возраст ≤ {max_age_minutes or '∞'} мин, новые: {only_new}")
        
        response = self._make_request(query, page, rows)
        if not response:
            return []
        
        # Шаг 1: Парсинг ответа
        products, parse_stats = self._parse_response_debug(response, query)
        self.stats.update(parse_stats)
        
        print(f"\n📊 ДИАГНОСТИКА ПАРСИНГА:")
        print(f"   📦 Всего элементов в API: {self.stats['total_api_items']}")
        print(f"   ✅ Успешно распарсено: {self.stats['valid_items']}")
        print(f"   ❌ Невалидные/пропущенные: {self.stats['invalid_items']}")
        
        if self.stats['filtered_by_query'] > 0:
            print(f"   🔍 Отфильтровано по запросу: {self.stats['filtered_by_query']}")
        
        # Шаг 2: Фильтрация по возрасту
        if max_age_minutes is not None:
            before = len(products)
            products = [p for p in products if p.age_minutes <= max_age_minutes]
            self.stats['filtered_by_age'] = before - len(products)
            print(f"   ⏳ Отфильтровано по возрасту: {self.stats['filtered_by_age']}")
        
        print(f"   📦 После фильтров: {len(products)} товаров")
        
        # Шаг 3: Фильтрация по новизне
        if only_new:
            new_products = self._filter_new_products(products)
            self.stats['filtered_by_seen'] = len(products) - len(new_products)
            self.stats['final_products'] = len(new_products)
            
            print(f"   🆕 Отфильтровано (уже видели): {self.stats['filtered_by_seen']}")
            print(f"   🎯 ФИНАЛЬНО новых: {self.stats['final_products']}")
            
            return new_products
        
        self.stats['final_products'] = len(products)
        return products
    
    def _parse_response_debug(self, api_response: Dict, query: str) -> Tuple[List[Product], Dict]:
        """Парсинг ответа с ДЕТАЛЬНОЙ диагностикой"""
        products = []
        stats = {
            'total_api_items': 0,
            'valid_items': 0,
            'invalid_items': 0,
            'filtered_by_query': 0,
            'invalid_reasons': {
                'no_data': 0,
                'no_id': 0,
                'no_title': 0,
                'price_error': 0,
                'query_filter': 0,
                'other': 0
            }
        }
        
        if not api_response:
            return products, stats
        
        data = api_response.get('data', {})
        result_list = data.get('resultList', [])
        stats['total_api_items'] = len(result_list)
        
        print(f"\n🔍 АНАЛИЗ {len(result_list)} ЭЛЕМЕНТОВ API:")
        
        for i, item in enumerate(result_list):
            try:
                # Пробуем разные пути к данным
                item_data = None
                data_path = ""
                
                # Путь 1: Основной
                item_data = item.get('data', {}).get('item', {}).get('main', {}).get('clickParam', {}).get('args', {})
                if item_data:
                    data_path = "main.clickParam.args"
                
                # Путь 2: Альтернативный (через exContent)
                if not item_data:
                    ex_content = item.get('data', {}).get('item', {}).get('main', {}).get('exContent', {})
                    if ex_content:
                        item_id = ex_content.get('itemId', '')
                        # Ищем соответствующий элемент с args
                        for elem in result_list:
                            args = elem.get('data', {}).get('item', {}).get('main', {}).get('clickParam', {}).get('args', {})
                            if args.get('id') == item_id:
                                item_data = args
                                data_path = "exContent cross-reference"
                                break
                
                # Путь 3: Прямой доступ к данным
                if not item_data:
                    item_data = item.get('data', {}).get('item', {})
                    if item_data:
                        data_path = "data.item"
                
                # Если вообще нет данных
                if not item_data:
                    stats['invalid_items'] += 1
                    stats['invalid_reasons']['no_data'] += 1
                    
                    if i < 10:  # Логируем только первые 10
                        print(f"   {i:3d}. ❌ НЕТ ДАННЫХ. Структура: {list(item.keys()) if isinstance(item, dict) else type(item)}")
                    continue
                
                # Извлекаем ID
                item_id = item_data.get('id', '')
                if not item_id or item_id == 'None':
                    stats['invalid_items'] += 1
                    stats['invalid_reasons']['no_id'] += 1
                    
                    if i < 10:
                        print(f"   {i:3d}. ❌ НЕТ ID. Путь: {data_path}")
                    continue
                
                # Извлекаем название
                title = ""
                
                # Способ 1: Из detailParams
                detail_params = item_data.get('detailParams', {})
                if isinstance(detail_params, dict):
                    title = detail_params.get('title', '')
                
                # Способ 2: Из exContent
                if not title:
                    ex_content = item.get('data', {}).get('item', {}).get('main', {}).get('exContent', {})
                    if ex_content:
                        detail_params = ex_content.get('detailParams', {})
                        if isinstance(detail_params, dict):
                            title = detail_params.get('title', '')
                
                # Способ 3: Прямое поле title
                if not title:
                    title = item_data.get('title', '')
                
                if not title:
                    stats['invalid_items'] += 1
                    stats['invalid_reasons']['no_title'] += 1
                    
                    if i < 10:
                        print(f"   {i:3d}. ❌ НЕТ НАЗВАНИЯ. ID: {item_id}, Путь: {data_path}")
                    continue
                
                # ФИЛЬТРАЦИЯ ПО ЗАПРОСУ (если включена в настройках)
                from bot.parser_settings import parser_settings
                filter_by_query = parser_settings.get('filter_by_query', True)
                
                if filter_by_query and query and query.lower() not in title.lower():
                    stats['invalid_items'] += 1
                    stats['invalid_reasons']['query_filter'] += 1
                    stats['filtered_by_query'] += 1
                    
                    if i < 10:
                        print(f"   {i:3d}. 🔍 ФИЛЬТР по запросу. Title: {title[:50]}...")
                    continue
                
                # Извлекаем цену
                price_str = item_data.get('price', '0')
                try:
                    price_clean = re.sub(r'[^\d\.]', '', price_str)
                    price = float(price_clean) if price_clean else 0.0
                except:
                    price = 0.0
                    stats['invalid_reasons']['price_error'] += 1
                
                # Время публикации
                publish_time_str = item_data.get('publishTime', '0')
                age_minutes = 99999
                
                if publish_time_str and publish_time_str != '0':
                    try:
                        publish_timestamp = int(publish_time_str)
                        current_time_ms = time.time() * 1000
                        age_minutes = (current_time_ms - publish_timestamp) / (1000 * 60)
                    except:
                        pass
                
                # Локация
                location = item_data.get('area', '')
                if not location:
                    ex_content = item.get('data', {}).get('item', {}).get('main', {}).get('exContent', {})
                    if ex_content:
                        location = ex_content.get('area', '')
                
                # ========== ИЗВЛЕЧЕНИЕ ФОТО ==========
                images = []
                
                # Путь 1: Основной путь к фото
                pic_url = item_data.get('picUrl', '')
                if pic_url and pic_url.startswith('http'):
                    images.append(pic_url)
                
                # Путь 2: Альтернативный путь через pics
                pics_list = item_data.get('pics', [])
                if isinstance(pics_list, list) and pics_list:
                    for pic in pics_list[:3]:  # Берем первые 3 фото
                        if isinstance(pic, dict) and pic.get('picUrl'):
                            img_url = pic['picUrl']
                            if img_url.startswith('http') and img_url not in images:
                                images.append(img_url)
                
                # Путь 3: Попробовать из exContent
                if not images:
                    ex_content = item.get('data', {}).get('item', {}).get('main', {}).get('exContent', {})
                    if ex_content:
                        pic_url = ex_content.get('picUrl', '')
                        if pic_url and pic_url.startswith('http'):
                            images.append(pic_url)
                # =====================================
                
                # Создаем продукт
                product = Product(
                    id=item_id,
                    title=title[:200],
                    price=price,
                    url=f"https://www.goofish.com/item?id={item_id}",
                    location=location,
                    age_minutes=round(age_minutes, 1),
                    query=query,
                    images=images  # <-- Добавляем фото!
                )
                
                products.append(product)
                stats['valid_items'] += 1
                
                # Выводим первые 20 товаров для примера
                if stats['valid_items'] <= 20:
                    photo_info = f" 📸{len(images)}" if images else ""
                    print(f"   {i:3d}. ✅ {title[:50]}... - ¥{price:.2f}{photo_info} (путь: {data_path})")
                
            except Exception as e:
                stats['invalid_items'] += 1
                stats['invalid_reasons']['other'] += 1
                
                if i < 10:
                    print(f"   {i:3d}. ⚠️ Ошибка парсинга: {e}")
        
        # Сводка по невалидным элементам
        print(f"\n📋 ПРИЧИНЫ ПОТЕРЬ:")
        for reason, count in stats['invalid_reasons'].items():
            if count > 0:
                reason_text = {
                    'no_data': 'Нет данных',
                    'no_id': 'Нет ID',
                    'no_title': 'Нет названия',
                    'price_error': 'Ошибка цены',
                    'query_filter': 'Фильтр по запросу',
                    'other': 'Другие ошибки'
                }.get(reason, reason)
                print(f"   • {reason_text}: {count}")
        
        return products, stats
    
    def _filter_new_products(self, products: List[Product]) -> List[Product]:
        """Фильтрация только новых товаров"""
        return [p for p in products if p.id not in self.seen_ids]
    
    def check_cookies(self) -> Tuple[bool, str]:
        """Проверка валидности cookies"""
        required = ['_m_h5_tk', 't', 'cookie2']
        for req in required:
            if req not in self.cookies:
                print(f"❌ Отсутствует cookie: {req}")
                return False, f"Missing cookie: {req}"
        
        return True, "OK"
    
    def test_connection(self) -> bool:
        """Простой тест подключения"""
        try:
            response = self.session.get('https://www.goofish.com', timeout=10)
            print(f"✅ Подключение к Goofish: {response.status_code}")
            return response.status_code == 200
        except Exception as e:
            print(f"❌ Ошибка подключения: {e}")
            return False
    
    def print_detailed_stats(self):
        """Вывод детальной статистики"""
        print(f"\n📊 ДЕТАЛЬНАЯ СТАТИСТИКА ПАРСЕРА:")
        print(f"   📦 Всего из API: {self.stats['total_api_items']}")
        print(f"   ✅ Валидные: {self.stats['valid_items']}")
        print(f"   ❌ Невалидные: {self.stats['invalid_items']}")
        
        if self.stats['filtered_by_query'] > 0:
            print(f"   🔍 Отфильтровано по запросу: {self.stats['filtered_by_query']}")
        
        print(f"   ⏳ Отфильтровано по возрасту: {self.stats['filtered_by_age']}")
        print(f"   📍 Отфильтровано (уже видели): {self.stats['filtered_by_seen']}")
        print(f"   🎯 Финальных товаров: {self.stats['final_products']}")
        
        # Процент успеха
        if self.stats['total_api_items'] > 0:
            success_rate = (self.stats['valid_items'] / self.stats['total_api_items']) * 100
            print(f"   📈 Эффективность парсинга: {success_rate:.1f}%")