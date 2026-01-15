#!/usr/bin/env python3
import asyncio
import time
import sys
from pathlib import Path

# Добавляем текущую директорию в путь
sys.path.append(str(Path(__file__).parent))

from telegram.ext import Application
from config import BOT_TOKEN
from bot.handlers import setup_handlers
from bot.notifications import send_new_products
from parsers.goofish import GoofishParser
from storage.files import load_search_queries, add_seen_ids, load_seen_ids, get_user_queries
from utils.auto_refresh import cookies_manager  # Импорт менеджера cookies

# Создаем core/settings.py если его нет
try:
    from core.settings import settings
    SETTINGS_AVAILABLE = True
except ImportError:
    # Если core/settings.py не существует, используем config.py
    from config import CHECK_INTERVAL, MAX_AGE_MINUTES, MAX_PAGES, ROWS_PER_PAGE
    SETTINGS_AVAILABLE = False
    
    class FallbackSettings:
        def __init__(self):
            self.check_interval = int(CHECK_INTERVAL)
            self.max_age_minutes = int(MAX_AGE_MINUTES)
            self.max_pages = int(MAX_PAGES)
            self.rows_per_page = int(ROWS_PER_PAGE)
    
    settings = FallbackSettings()

class SimpleMonitor:
    def __init__(self, bot=None):
        self.bot = bot
        self.is_running = False
        self.cycles = 0
        self.total_products = 0
        self.last_check = None
        self.parser = None
        
        # Используем настройки
        self.settings = settings
        
        print("✅ SimpleMonitor инициализирован с настройками:")
        print(f"   📅 Интервал: {self.settings.check_interval} сек")
        print(f"   ⏳ Макс. возраст: {self.settings.max_age_minutes} мин")
        print(f"   📄 Макс. страниц: {self.settings.max_pages}")
        print(f"   📦 Товаров на стр.: {self.settings.rows_per_page}")
    
    async def initialize_parser(self):
        """Асинхронная инициализация парсера"""
        print("🔄 Инициализация парсера...")
        
        # Инициализируем менеджер cookies
        await cookies_manager.initialize()
        
        self.parser = GoofishParser()
        
        # Проверяем cookies
        is_valid, message = self.parser.check_cookies()
        if not is_valid:
            print(f"❌ Cookies невалидны: {message}")
            print("🔄 Пробую обновить cookies автоматически...")
            success = await cookies_manager.refresh_cookies()
            if not success:
                print("❌ Не могу запустить мониторинг - не удалось обновить cookies")
                return False
        
        print("✅ Парсер готов к работе")
        return True
    
    async def run(self):
        """Запуск мониторинга с учетом интервала из настроек"""
        if not await self.initialize_parser():
            print("❌ Не могу запустить мониторинг - парсер не инициализирован")
            return
        
        self.is_running = True
        print("📊 Мониторинг запущен")
        
        while self.is_running:
            try:
                await self.check_all_users_queries()
                self.cycles += 1
                
                # Используем настройки из settings
                wait_time = self.settings.check_interval
                print(f"⏳ Жду {wait_time} секунд до следующей проверки...")
                await asyncio.sleep(wait_time)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"❌ Ошибка в цикле мониторинга: {e}")
                import traceback
                traceback.print_exc()
                await asyncio.sleep(60)
    
    async def check_all_users_queries(self):
        """Проверка запросов всех пользователей"""
        from storage.files import load_users, load_subscriptions
        
        users = load_users()
        subscriptions = load_subscriptions()
        
        if not users:
            print("📭 Нет пользователей для мониторинга")
            return
        
        print(f"👥 Проверяю запросы {len(users)} пользователей...")
        
        total_found = 0
        
        for user_id_str in users:
            try:
                user_id = int(user_id_str)
                user_queries = get_user_queries(user_id)
                
                if not user_queries:
                    continue
                
                print(f"  👤 Пользователь {user_id}: {len(user_queries)} запросов")
                
                found_products = []
                for query in user_queries:
                    try:
                        new_products = await self.check_query(query)
                        if new_products:
                            found_products.extend(new_products)
                    except Exception as e:
                        print(f"  ❌ Ошибка при проверке запроса '{query}' у пользователя {user_id}: {e}")
                
                # Отправляем товары пользователю
                if found_products and self.bot:
                    # Группируем по запросу
                    products_by_query = {}
                    for product in found_products:
                        if product.query not in products_by_query:
                            products_by_query[product.query] = []
                        products_by_query[product.query].append(product)
                    
                    # Отправляем уведомления для каждого запроса
                    for query, products in products_by_query.items():
                        await self.bot.send_user_new_products(user_id, products, query)
                    
                    total_found += len(found_products)
                    
            except Exception as e:
                print(f"❌ Ошибка при проверке пользователя {user_id_str}: {e}")
        
        # Также проверяем глобальные запросы для всех
        await self.check_global_queries()
        
        self.last_check = time.strftime('%Y-%m-%d %H:%M:%S')
        print(f"✅ Проверка завершена в {self.last_check}. Всего найдено: {total_found}")
    
    async def check_global_queries(self):
        """Проверка глобальных запросов"""
        from storage.files import load_search_queries
        
        queries = load_search_queries()
        if not queries:
            print("📭 Нет глобальных запросов")
            return
        
        print(f"🌐 Проверяю {len(queries)} глобальных запросов...")
        
        found_products = []
        
        for query in queries:
            try:
                new_products = await self.check_query(query)
                if new_products:
                    found_products.extend(new_products)
            except Exception as e:
                print(f"❌ Ошибка при проверке глобального запроса '{query}': {e}")
        
        # Отправляем товары всем пользователям
        if found_products and self.bot:
            # Группируем по запросу
            products_by_query = {}
            for product in found_products:
                if product.query not in products_by_query:
                    products_by_query[product.query] = []
                products_by_query[product.query].append(product)
            
            # Отправляем уведомления для каждого запроса
            for query, products in products_by_query.items():
                await self.bot.send_global_new_products(products, query)
    
    async def check_query(self, query: str):
        """Проверка одного запроса с учетом ВСЕХ настроек"""
        print(f"  📝 Запрос: '{query}'")
        
        all_products = []
        
        # Поиск по нескольким страницам (используем настройки)
        max_pages = int(self.settings.max_pages)
        rows_per_page = int(self.settings.rows_per_page)
        
        for page in range(1, max_pages + 1):
            try:
                print(f"    📄 Страница {page}/{max_pages}")
                
                products = self.parser.search(
                    query=query,
                    page=page,
                    rows=rows_per_page,
                    only_new=True,
                    max_age_minutes=self.settings.max_age_minutes
                )
                
                if not products:
                    print(f"    📭 Нет товаров на странице {page}")
                    break
                
                print(f"    🎯 Найдено: {len(products)} новых")
                all_products.extend(products)
                
                # Пауза между страницами (2 секунды)
                await asyncio.sleep(2)
                
            except Exception as e:
                print(f"    ❌ Ошибка на странице {page}: {e}")
                import traceback
                traceback.print_exc()
                break
        
        # Добавляем ID в seen_ids
        if all_products:
            new_ids = [p.id for p in all_products]
            added = add_seen_ids(new_ids)
            self.total_products += len(all_products)
            print(f"    💾 Сохранено {added} новых ID")
        
        return all_products
    
    def stop(self):
        """Остановка мониторинга"""
        self.is_running = False
        print("🛑 Мониторинг остановлен")
    
    def get_stats(self):
        """Получение статистики"""
        return {
            'is_running': self.is_running,
            'cycles': self.cycles,
            'total_products': self.total_products,
            'last_check': self.last_check
        }

class GoofishBot:
    """Основной класс бота с мониторингом"""
    
    def __init__(self):
        self.token = BOT_TOKEN
        self.application = None
        self.monitor = SimpleMonitor(bot=self)
        self.monitor_task = None
    
    async def send_user_new_products(self, user_id: int, products, query=""):
        """Отправка новых товаров конкретному пользователю"""
        if not self.application:
            return
        
        try:
            await send_new_products(
                self.application.bot,
                user_id,
                products,
                query
            )
        except Exception as e:
            print(f"❌ Ошибка отправки пользователю {user_id}: {e}")
    
    async def send_global_new_products(self, products, query=""):
        """Отправка новых товаров всем пользователям"""
        if not self.application:
            return
        
        from storage.files import load_users
        users = load_users()
        
        for user_id_str in users:
            try:
                user_id = int(user_id_str)
                await self.send_user_new_products(user_id, products, query)
            except Exception as e:
                print(f"❌ Ошибка отправки пользователю {user_id_str}: {e}")
    
    async def start_monitoring(self):
        """Запуск мониторинга в фоне"""
        self.monitor_task = asyncio.create_task(self.monitor.run())
    
    async def stop_monitoring(self):
        """Остановка мониторинга"""
        if self.monitor_task:
            self.monitor.stop()
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
    
    def run(self):
        """Запуск бота"""
        print("🤖 Запуск Goofish Parser Bot...")
        print("=" * 50)
        
        # Создаем приложение бота
        self.application = Application.builder().token(self.token).build()
        
        # Настраиваем обработчики
        setup_handlers(self.application, self)
        
        # Запускаем бота
        print("✅ Бот запущен")
        print("📊 Мониторинг запускается...")
        print("🛑 Нажмите Ctrl+C для остановки")
        print("=" * 50)
        
        # Используем asyncio.run для правильного запуска
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Запускаем мониторинг в фоне
        loop.create_task(self.start_monitoring())
        
        # Запускаем бота
        self.application.run_polling(
            allowed_updates=None,
            drop_pending_updates=True
        )

def main():
    """Точка входа"""
    bot = GoofishBot()
    
    try:
        bot.run()
    except KeyboardInterrupt:
        print("\n\n👋 Остановка бота...")
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")

if __name__ == "__main__":
    main()