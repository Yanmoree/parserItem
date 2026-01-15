# utils/auto_refresh.py
import asyncio
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
import logging
from playwright.async_api import async_playwright

from config import GOOFISH_COOKIES_FILE, DATA_DIR

logger = logging.getLogger(__name__)

class CookiesManager:
    """Менеджер для автоматического обновления cookies"""
    
    def __init__(self):
        self.cookies_file = GOOFISH_COOKIES_FILE
        self.refresh_interval = 3600 * 20  # 20 часов (меньше чем срок жизни cookies)
        self.last_refresh = None
        self.is_refreshing = False
        
    async def initialize(self):
        """Инициализация менеджера cookies"""
        await self.check_and_refresh_cookies()
        
        # Запускаем периодическую проверку
        asyncio.create_task(self.periodic_refresh())
        
    async def check_and_refresh_cookies(self):
        """Проверка и обновление cookies при необходимости"""
        if self.is_refreshing:
            logger.info("Обновление cookies уже выполняется...")
            return
        
        try:
            if not self.cookies_file.exists():
                logger.warning("Файл cookies не найден. Создаем новый...")
                await self.refresh_cookies()
                return
            
            # Проверяем валидность существующих cookies
            cookies_valid = await self.validate_cookies()
            
            if not cookies_valid:
                logger.info("Cookies невалидны. Обновляем...")
                await self.refresh_cookies()
            else:
                logger.info("Cookies валидны")
                self.last_refresh = datetime.now()
                
        except Exception as e:
            logger.error(f"Ошибка проверки cookies: {e}")
            await self.refresh_cookies()
    
    async def validate_cookies(self) -> bool:
        """Проверка валидности cookies"""
        try:
            with open(self.cookies_file, 'r', encoding='utf-8') as f:
                cookies = json.load(f)
            
            # Проверяем обязательные cookies
            required = ['_m_h5_tk', 't', 'cookie2']
            for req in required:
                if req not in cookies:
                    logger.warning(f"Отсутствует обязательный cookie: {req}")
                    return False
            
            # Проверяем timestamp в _m_h5_tk
            m_h5_tk = cookies.get('_m_h5_tk', '')
            if '_' not in m_h5_tk:
                logger.warning("Неправильный формат _m_h5_tk")
                return False
            
            # Извлекаем timestamp
            token, timestamp_str = m_h5_tk.split('_', 1)
            try:
                timestamp = int(timestamp_str)
                current_time = int(time.time() * 1000)
                
                # Cookies обычно живут 24 часа (86400000 мс)
                age_ms = current_time - timestamp
                max_age_ms = 86400000  # 24 часа
                
                logger.info(f"Возраст cookies: {age_ms/1000/60:.1f} минут")
                
                # Если cookies старше 22 часов - пора обновлять
                if age_ms > (max_age_ms - 7200000):  # 22 часа
                    logger.warning(f"Cookies скоро устареют (возраст: {age_ms/1000/3600:.1f} часов)")
                    return False
                    
                return True
                
            except ValueError:
                logger.warning("Не удалось извлечь timestamp из cookies")
                return False
                
        except Exception as e:
            logger.error(f"Ошибка валидации cookies: {e}")
            return False
    
    async def refresh_cookies(self):
        """Обновление cookies через Playwright"""
        if self.is_refreshing:
            logger.info("Обновление уже выполняется...")
            return
        
        self.is_refreshing = True
        
        try:
            logger.info("🔄 Начинаю обновление cookies...")
            
            cookies = await self.get_fresh_cookies()
            
            if cookies:
                # Сохраняем cookies
                with open(self.cookies_file, 'w', encoding='utf-8') as f:
                    json.dump(cookies, f, ensure_ascii=False, indent=2)
                
                self.last_refresh = datetime.now()
                logger.info(f"✅ Cookies обновлены! Сохранено {len(cookies)} cookies")
                
                # Проверяем новые cookies
                is_valid = await self.validate_cookies()
                if not is_valid:
                    logger.error("❌ Новые cookies невалидны!")
                    return False
                    
                return True
            else:
                logger.error("❌ Не удалось получить cookies")
                return False
                
        except Exception as e:
            logger.error(f"❌ Ошибка обновления cookies: {e}")
            import traceback
            traceback.print_exc()
            return False
            
        finally:
            self.is_refreshing = False
    
    async def get_fresh_cookies(self):
        """Получение свежих cookies через Playwright (асинхронная версия)"""
        async with async_playwright() as p:
            # Запускаем браузер в headless режиме (без интерфейса)
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--no-sandbox',
                    '--disable-dev-shm-usage'
                ]
            )
            
            # Создаем контекст
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                viewport={'width': 1920, 'height': 1080}
            )
            
            page = await context.new_page()
            
            try:
                logger.info("🌐 Открываю Goofish...")
                await page.goto('https://www.goofish.com', wait_until='networkidle')
                await asyncio.sleep(3)
                
                # Проверяем, нужен ли вход
                login_elements = await page.query_selector_all('text=登录')
                if login_elements:
                    logger.warning("⚠️ Требуется вход в аккаунт. Cookies могут быть неполными.")
                    logger.warning("   Для полных cookies необходимо зайти в аккаунт вручную.")
                
                # Ждем немного для загрузки cookies
                await asyncio.sleep(5)
                
                # Делаем еще один запрос для обновления cookies
                await page.reload(wait_until='networkidle')
                await asyncio.sleep(3)
                
                # Получаем все cookies
                all_cookies = await context.cookies()
                
                # Фильтруем важные cookies для Goofish
                important_keys = [
                    '_m_h5_tk', '_m_h5_tk_enc', 
                    '_tb_token_', 'cna', 't', 
                    'cookie2', 'isg', 'l', 'uc1', 'x5sec'
                ]
                goofish_cookies = {}
                
                for cookie in all_cookies:
                    if cookie['name'] in important_keys:
                        goofish_cookies[cookie['name']] = cookie['value']
                        logger.debug(f"   ✅ {cookie['name']}: {cookie['value'][:30]}...")
                
                # Проверяем обязательные cookies
                required = ['_m_h5_tk', 't']
                missing = [r for r in required if r not in goofish_cookies]
                
                if missing:
                    logger.warning(f"⚠️ Отсутствуют важные cookies: {missing}")
                    logger.warning("   Cookies могут работать неполноценно")
                
                return goofish_cookies
                
            except Exception as e:
                logger.error(f"❌ Ошибка получения cookies: {e}")
                return None
                
            finally:
                await browser.close()
    
    async def periodic_refresh(self):
        """Периодическое обновление cookies"""
        while True:
            try:
                await asyncio.sleep(self.refresh_interval)
                
                logger.info("🔄 Проверка необходимости обновления cookies...")
                await self.check_and_refresh_cookies()
                
            except Exception as e:
                logger.error(f"Ошибка в periodic_refresh: {e}")
                await asyncio.sleep(300)  # Ждем 5 минут при ошибке
    
    def get_status(self):
        """Получение статуса cookies"""
        return {
            'last_refresh': self.last_refresh.isoformat() if self.last_refresh else None,
            'is_refreshing': self.is_refreshing,
            'cookies_file': str(self.cookies_file),
            'refresh_interval_hours': self.refresh_interval / 3600
        }

# Глобальный экземпляр
cookies_manager = CookiesManager()