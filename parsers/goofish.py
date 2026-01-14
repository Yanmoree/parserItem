# parsers/goofish_fixed.py - ИСПРАВЛЕННАЯ версия на основе рабочего проекта
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

class GoofishParser:
    """Парсер для Goofish - ИСПРАВЛЕННАЯ на основе рабочего проекта"""
    
    def __init__(self, cookies_file=None):
        self.base_url = "https://h5api.m.goofish.com/h5/mtop.taobao.idlemtopsearch.pc.search/1.0/"
        self.cookies_file = cookies_file or GOOFISH_COOKIES_FILE
        self.cookies = self._load_cookies()
        self.session = self._create_session()
        self.seen_ids = load_seen_ids()
        
        print(f"✅ Парсер инициализирован. Cookies: {len(self.cookies)}")
        print(f"✅ Токен: {self.cookies.get('_m_h5_tk', '')[:50]}...")
        
        # Проверяем токен
        self._check_token()
    
    def _load_cookies(self) -> Dict:
        """Загрузка cookies"""
        if self.cookies_file.exists():
            try:
                with open(self.cookies_file, 'r', encoding='utf-8') as f:
                    cookies = json.load(f)
                
                # Проверяем критичные cookies
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
    
    def _check_token(self):
        """Проверка валидности токена"""
        token_full = self.cookies.get('_m_h5_tk', '')
        if '_' not in token_full:
            print("❌ Токен в неправильном формате")
            return
        
        token, token_timestamp = token_full.split('_', 1)
        token_time = int(token_timestamp) / 1000
        current_time = time.time()
        diff = current_time - token_time
        
        print(f"📊 Токен создан: {datetime.fromtimestamp(token_time)}")
        print(f"📊 Текущее время: {datetime.fromtimestamp(current_time)}")
        print(f"📊 Разница: {diff:.0f} секунд ({diff/3600:.1f} часов)")
        
        # Критическая проблема: токен указывает на будущее время!
        if token_time > current_time + 3600:  # Токен в будущем более чем на 1 час
            print("⚠️  КРИТИЧЕСКОЕ ПРЕДУПРЕЖДЕНИЕ: Токен указывает на будущее время!")
            print("🔄 Рекомендуется обновить cookies через utils/cookies.py")
    
    def _make_request(self, query: str, page: int, rows: int) -> Optional[Dict]:
        """Выполнение запроса к API (ИСПРАВЛЕННЫЙ ВАРИАНТ)"""
        try:
            # ВАЖНОЕ ИСПРАВЛЕНИЕ: Используем ТЕКУЩЕЕ время, а не время из токена!
            timestamp = str(int(time.time() * 1000))
            
            token_full = self.cookies.get('_m_h5_tk', '')
            if '_' not in token_full:
                print("❌ Токен в неправильном формате")
                return None
            
            token = token_full.split('_')[0]
            
            # Тело запроса - используем формат из рабочего проекта
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
            
            # Подпись - КРИТИЧНО: token & timestamp & appKey & data
            sign_string = f"{token}&{timestamp}&34839810&{data_str}"
            signature = hashlib.md5(sign_string.encode()).hexdigest()
            
            # Параметры - используем формат из рабочего проекта
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
            
            # DEBUG информация
            print(f"\n🔧 DEBUG Запрос:")
            print(f"   URL: {self.base_url}")
            print(f"   Токен: {token[:20]}...")
            print(f"   Время (ТЕКУЩЕЕ): {timestamp}")
            print(f"   Подпись: {signature}")
            print(f"   Запрос: '{query}'")
            print(f"   Страница: {page}")
            
            # Добавляем задержку для избежания rate limit
            time.sleep(2)
            
            response = self.session.post(
                self.base_url, 
                params=params, 
                timeout=REQUEST_TIMEOUT,
                verify=False  # Отключаем SSL проверку для тестов
            )
            
            print(f"   Статус: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                
                # Сохраняем ответ для отладки
                filename = f"debug_response_fixed_{query}_{int(time.time())}.json"
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(result, f, ensure_ascii=False, indent=2)
                print(f"💾 Ответ сохранен в {filename}")
                
                # Проверяем ответ на ошибки
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
                            print(f"   Ожидание 30 секунд...")
                            time.sleep(30)
                            return None
                        else:
                            print(f"❌ API ошибка: {ret_str}")
                            return None
                
                return result
            else:
                print(f"❌ HTTP ошибка: {response.status_code}")
                print(f"Текст: {response.text[:200]}")
                
        except Exception as e:
            print(f"❌ Ошибка запроса: {e}")
            import traceback
            traceback.print_exc()
        
        return None
    
    def search(self, query: str, page: int = 1, rows: int = None, 
               only_new: bool = True) -> List[Product]:
        """Поиск товаров"""
        rows = rows or ROWS_PER_PAGE
        
        print(f"\n🔍 Поиск: '{query}', страница {page}...")
        
        response = self._make_request(query, page, rows)
        if not response:
            print(f"   ❌ Нет ответа")
            return []
        
        products = self._parse_response_fixed(response, query)
        
        print(f"   ✅ Найдено товаров: {len(products)}")
        
        # Фильтруем только новые товары
        if only_new:
            new_products = self._filter_new_products(products)
            print(f"   🆕 Новых: {len(new_products)}")
            return new_products
        
        return products
    
    def _parse_response_fixed(self, api_response: Dict, query: str) -> List[Product]:
        """Парсинг ответа API (исправленная версия из рабочего проекта)"""
        products = []
        
        if not api_response:
            return products
        
        data = api_response.get('data', {})
        result_list = data.get('resultList', [])
        
        print(f"   📦 Всего элементов в ответе: {len(result_list)}")
        
        for i, item in enumerate(result_list[:15]):  # Ограничиваем для отладки
            try:
                # Основной путь к данным (из рабочего проекта)
                item_data = item.get('data', {}).get('item', {}).get('main', {}).get('clickParam', {}).get('args', {})
                
                # Альтернативный путь (из рабочего проекта)
                if not item_data:
                    ex_content = item.get('data', {}).get('item', {}).get('main', {}).get('exContent', {})
                    if ex_content:
                        item_id = ex_content.get('itemId', '')
                        for elem in result_list:
                            args = elem.get('data', {}).get('item', {}).get('main', {}).get('clickParam', {}).get('args', {})
                            if args.get('id') == item_id:
                                item_data = args
                                break
                
                if not item_data:
                    continue
                
                item_id = item_data.get('id', '')
                if not item_id or item_id == 'None':
                    continue
                
                # Название (из рабочего проекта)
                title = item_data.get('detailParams', {}).get('title', '') if isinstance(item_data.get('detailParams'), dict) else ''
                if not title:
                    ex_content = item.get('data', {}).get('item', {}).get('main', {}).get('exContent', {})
                    if ex_content:
                        title = ex_content.get('detailParams', {}).get('title', '')
                
                if not title:
                    continue
                
                # Фильтр по запросу (опционально)
                if query and query.lower() not in title.lower():
                    continue
                
                # Цена (исправленная конвертация)
                price_str = item_data.get('price', '0')
                try:
                    # Убираем нечисловые символы
                    price_clean = re.sub(r'[^\d\.]', '', price_str)
                    price = float(price_clean) if price_clean else 0.0
                except:
                    price = 0.0
                
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
                
                # Создаем продукт
                product = Product(
                    id=item_id,
                    title=title[:200],
                    price=price,
                    url=f"https://www.goofish.com/item?id={item_id}",
                    location=location,
                    age_minutes=round(age_minutes, 1),
                    query=query
                )
                
                products.append(product)
                print(f"   {i+1}. {title[:50]}... - ¥{price:.2f}")
                
            except Exception as e:
                print(f"   ⚠️ Ошибка парсинга товара: {e}")
                continue
        
        return products
    
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
            # Пробуем сделать простой запрос
            response = self.session.get('https://www.goofish.com', timeout=10)
            print(f"✅ Подключение к Goofish: {response.status_code}")
            return response.status_code == 200
        except Exception as e:
            print(f"❌ Ошибка подключения: {e}")
            return False