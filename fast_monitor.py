import asyncio
from parsers.async_goofish import AsyncGoofishParser
from storage.files import load_search_queries, add_seen_ids

class FastMonitor:
    def __init__(self):
        self.parser = AsyncGoofishParser()
        self.queries = []
    
    async def initialize(self):
        await self.parser.initialize()
        self.queries = load_search_queries()
    
    async def check_all_queries_fast(self):
        """Проверка всех запросов быстро (1 страница, 500 товаров)"""
        all_products = []
        
        # Создаем задачи для всех запросов одновременно
        tasks = []
        for query in self.queries:
            task = self.parser.search_async(
                query=query,
                page=1,           # Только первая страница
                rows=500          # Максимум товаров
            )
            tasks.append(task)
        
        # Выполняем все запросы параллельно
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"❌ Ошибка для '{self.queries[i]}': {result}")
            elif result:
                all_products.extend(result)
        
        # Сохраняем ID
        if all_products:
            new_ids = [p.id for p in all_products]
            added = add_seen_ids(new_ids)
            print(f"✅ Найдено {len(all_products)} товаров, новых: {added}")
        
        return all_products