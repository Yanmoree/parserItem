#!/usr/bin/env python3
import sys
sys.path.append('.')
from parsers.goofish import GoofishParser

parser = GoofishParser()

# Тестовый поиск
products = parser.search("stone island", page=1, rows=20, max_age_minutes=10000)

print(f"\n📊 Найдено товаров: {len(products)}\n")

for i, product in enumerate(products[:5], 1):  # Первые 5
    print(f"🔹 Товар {i}:")
    print(f"   Название: {product.title[:60]}...")
    print(f"   Цена: {product.price_display}")
    print(f"   Ссылка: {product.url}")
    print(f"   Фото: {len(product.images)} шт")
    
    if product.images:
        print(f"   Первое фото: {product.images[0][:80]}...")
    
    print(f"   Сообщение для Telegram:")
    print(f"   {product.telegram_message}")
    print("-" * 50)