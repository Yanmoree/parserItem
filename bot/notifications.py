# bot/notifications.py - полностью обновленная версия
from telegram import Bot, InputMediaPhoto
from telegram.constants import ParseMode
from typing import List
from models import Product
from bot.parser_settings import parser_settings
import asyncio

async def send_new_products(bot: Bot, chat_id: int, products: List[Product], query: str = ""):
    """Отправка новых товаров с фото и ссылками"""
    if not products:
        return
    
    print(f"📤 Отправляю {len(products)} товаров пользователю {chat_id}")
    
    # Группируем товары по 5 (чтобы не перегружать)
    chunk_size = 5
    sent_count = 0
    
    for i in range(0, len(products), chunk_size):
        chunk = products[i:i + chunk_size]
        
        for product in chunk:
            try:
                await send_single_product(bot, chat_id, product)
                sent_count += 1
                await asyncio.sleep(0.3)  # Задержка между отправками
                
            except Exception as e:
                print(f"❌ Ошибка отправки товара {product.id}: {e}")
                # Пробуем отправить без фото
                try:
                    await send_product_without_photo(bot, chat_id, product)
                    sent_count += 1
                except Exception as e2:
                    print(f"❌ Критическая ошибка: {e2}")
    
    # Итоговое сообщение
    if sent_count > 0:
        query_text = f" по запросу '<b>{query}</b>'" if query else ""
        await bot.send_message(
            chat_id=chat_id,
            text=f"📊 Всего отправлено товаров: <b>{sent_count}</b>{query_text}",
            parse_mode=ParseMode.HTML
        )

async def send_single_product(bot: Bot, chat_id: int, product: Product):
    """Отправка одного товара с фото"""
    
    # Если есть фото - отправляем с фото
    if product.images and len(product.images) > 0:
        try:
            # Берем первое фото
            photo_url = product.images[0]
            
            # Пробуем отправить фото с подписью
            await bot.send_photo(
                chat_id=chat_id,
                photo=photo_url,
                caption=product.telegram_message,
                parse_mode=ParseMode.HTML
            )
            return
            
        except Exception as photo_error:
            print(f"⚠️ Не удалось отправить фото {product.id}: {photo_error}")
            # Пробуем без фото
            await send_product_without_photo(bot, chat_id, product)
    
    else:
        # Если фото нет - просто текст
        await send_product_without_photo(bot, chat_id, product)

async def send_product_without_photo(bot: Bot, chat_id: int, product: Product):
    """Отправка товара без фото (запасной вариант)"""
    await bot.send_message(
        chat_id=chat_id,
        text=product.telegram_message,
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=False  # Включаем превью ссылки
    )

async def send_products_as_group(bot: Bot, chat_id: int, products: List[Product]):
    """Отправка группы товаров как альбома (не рекомендуется для многих товаров)"""
    if not products:
        return
    
    # Создаем медиагруппу (макс 10 фото)
    media_group = []
    for product in products[:10]:  # Ограничиваем 10 товарами
        if product.images and len(product.images) > 0:
            media_group.append(
                InputMediaPhoto(
                    media=product.images[0],
                    caption=product.telegram_message if len(media_group) == 0 else "",
                    parse_mode=ParseMode.HTML
                )
            )
    
    if media_group:
        try:
            await bot.send_media_group(
                chat_id=chat_id,
                media=media_group
            )
        except Exception as e:
            print(f"❌ Ошибка отправки медиагруппы: {e}")
            # Пробуем отправить по одному
            for product in products[:5]:
                await send_single_product(bot, chat_id, product)