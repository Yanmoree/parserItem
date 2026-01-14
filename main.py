#!/usr/bin/env python3
import asyncio
import sys
from pathlib import Path

# Добавляем текущую директорию в путь
sys.path.append(str(Path(__file__).parent))

from telegram.ext import Application
from config import BOT_TOKEN
from bot.handlers import setup_handlers
from bot.notifications import send_new_products
from parsers.goofish import GoofishParser
from storage.files import load_search_queries, add_seen_ids, load_seen_ids
import time

class SimpleMonitor:
    """Простой мониторинг с парсером"""
    
    def __init__(self, bot=None):
        self.bot = bot
        self.is_running = False
        self.cycles = 0
        self.total_products = 0
        self.last_check = None
        self.parser = None  # Инициализируем позже
        
        print("✅ SimpleMonitor инициализирован")
    
    async def initialize_parser(self):
        """Асинхронная инициализация парсера"""
        print("🔄 Инициализация парсера...")
        self.parser = GoofishParser()
        
        # Проверяем cookies
        is_valid, message = self.parser.check_cookies()
        if not is_valid:
            print(f"❌ Cookies невалидны: {message}")
            return False
        
        print("✅ Парсер готов к работе")
        return True
    
    async def run(self):
        """Запуск мониторинга"""
        if not await self.initialize_parser():
            print("❌ Не могу запустить мониторинг - парсер не инициализирован")
            return
        
        self.is_running = True
        print("📊 Мониторинг запущен")
        
        while self.is_running:
            try:
                await self.check_all_queries()
                self.cycles += 1
                
                # Ждем между проверками
                from config import CHECK_INTERVAL
                print(f"⏳ Жду {CHECK_INTERVAL} секунд до следующей проверки...")
                await asyncio.sleep(CHECK_INTERVAL)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"❌ Ошибка в цикле мониторинга: {e}")
                await asyncio.sleep(60)
    
    async def check_all_queries(self):
        """Проверка всех запросов"""
        queries = load_search_queries()
        if not queries:
            print("📭 Нет запросов для мониторинга")
            return
        
        print(f"🔍 Проверяю {len(queries)} запросов...")
        
        found_products = []
        
        for query in queries:
            try:
                new_products = await self.check_query(query)
                if new_products:
                    found_products.extend(new_products)
            except Exception as e:
                print(f"❌ Ошибка при проверке запроса '{query}': {e}")
        
        # Отправляем все найденные товары
        if found_products and self.bot and self.bot.application:
            # Группируем по запросу
            products_by_query = {}
            for product in found_products:
                if product.query not in products_by_query:
                    products_by_query[product.query] = []
                products_by_query[product.query].append(product)
            
            # Отправляем уведомления
            for query, products in products_by_query.items():
                await self.bot.send_new_products(products, query)
        
        self.last_check = time.strftime('%Y-%m-%d %H:%M:%S')
        print(f"✅ Проверка завершена в {self.last_check}. Найдено: {len(found_products)}")
    
    async def check_query(self, query: str):
        """Проверка одного запроса"""
        print(f"  📝 Запрос: '{query}'")
        
        try:
            # Используем парсер для поиска (только 1 страница, чтобы не превышать лимит)
            from config import ROWS_PER_PAGE
            products = self.parser.search(query, page=1, rows=ROWS_PER_PAGE, only_new=True)
            
            if products:
                print(f"    🎯 Найдено новых: {len(products)}")
                
                # Добавляем в просмотренные
                new_ids = [p.id for p in products]
                added = add_seen_ids(new_ids)
                self.total_products += len(products)
                
                return products
            else:
                print(f"    📭 Новых товаров нет")
                return []
                
        except Exception as e:
            print(f"    ❌ Ошибка: {e}")
            return []
    
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
    
    async def send_new_products(self, products, query=""):
        """Отправка новых товаров всем подписчикам"""
        if not self.application:
            return
        
        # Временно отправляем только админам
        from config import ADMIN_IDS
        for admin_id in ADMIN_IDS:
            try:
                await send_new_products(
                    self.application.bot,
                    admin_id,
                    products,
                    query
                )
            except Exception as e:
                print(f"❌ Ошибка отправки админу {admin_id}: {e}")
    
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