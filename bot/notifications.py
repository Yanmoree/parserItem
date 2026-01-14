# bot/notifications.py
from telegram import Bot
from telegram.constants import ParseMode
from typing import List
from models import Product
from bot.parser_settings import parser_settings
import asyncio

async def send_new_products(bot: Bot, chat_id: int, products: List[Product], query: str = ""):
    """Отправка новых товаров пользователю с учетом настроек валюты"""
    if not products:
        return
    
    # Получаем настройки валюты
    currency = parser_settings.get('price_currency', 'yuan')
    exchange_rate = parser_settings.get('yuan_to_rub_rate', 12.5)
    
    query_text = f" по запросу: <b>{query}</b>\n\n" if query else "\n"
    header = f"🎯 <b>Новые товары</b>{query_text}"
    
    chunk_size = 3
    for i in range(0, len(products), chunk_size):
        chunk = products[i:i + chunk_size]
        message = header if i == 0 else ""
        
        for j, product in enumerate(chunk, 1):
            index = i + j
            
            # Формируем строку цены в зависимости от настройки
            if currency == 'rubles':
                price_text = f"💰 <b>{product.price_display_rub}</b> ({product.price_display})"
            else:
                price_text = f"💰 <b>{product.price_display}</b> (~{product.price_display_rub})"
            
            message += (
                f"<b>{index}. {product.title[:80]}...</b>\n"
                f"{price_text}\n"
                f"📍 {product.location}\n"
                f"⏰ {product.age_minutes} мин назад\n"
                f"🔗 {product.url}\n\n"
            )
        
        try:
            await bot.send_message(
                chat_id=chat_id,
                text=message,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True
            )
            await asyncio.sleep(0.5)
            
        except Exception as e:
            print(f"❌ Ошибка отправки пользователю {chat_id}: {e}")
    
    # Итоговое сообщение
    if len(products) > chunk_size:
        await bot.send_message(
            chat_id=chat_id,
            text=f"📊 Всего новых товаров: <b>{len(products)}</b>",
            parse_mode=ParseMode.HTML
        )