from telegram import Update
from telegram.ext import (
    ContextTypes, 
    CommandHandler, 
    MessageHandler, 
    CallbackQueryHandler,  # <-- ДОБАВИТЬ
    ConversationHandler,    # <-- ДОБАВИТЬ
    filters
)
from bot.parser_settings import (
    settings_command, settings_callback, setting_value_handler, 
    cancel_settings, SETTING_CHOICE, SETTING_VALUE, parser_settings
)
from storage.files import (
    load_search_queries, add_search_query, 
    save_user, add_subscription, get_user_subscriptions
)
from parsers.goofish import GoofishParser

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start"""
    user = update.effective_user
    
    # Сохраняем пользователя
    save_user({
        'id': user.id,
        'username': user.username,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'joined_at': update.message.date.isoformat()
    })
    
    await update.message.reply_text(
        f"👋 Привет, {user.first_name}!\n\n"
        "🤖 <b>Goofish Parser Bot</b>\n\n"
        "Я мониторю новые товары на Goofish.\n"
        "Запросы берутся из файла <code>data/search_queries.txt</code>\n\n"
        "📋 <b>Основные команды:</b>\n"
        "/queries - Показать запросы\n"
        "/add_query - Добавить запрос\n"
        "/search - Поиск сейчас\n"
        "/subscribe - Подписаться\n"
        "/mysubs - Мои подписки\n"
        "/status - Статус\n"
        "/help - Помощь\n"
        "/settings - Настройки парсера",  # <-- ДОБАВИЛИ
        parse_mode='HTML'
    )

async def queries_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать все запросы из файла"""
    queries = load_search_queries()
    
    if not queries:
        await update.message.reply_text("📭 Файл запросов пуст")
        return
    
    message = "📋 <b>Запросы для мониторинга:</b>\n\n"
    for i, query in enumerate(queries, 1):
        message += f"{i}. {query}\n"
    
    message += f"\nВсего: {len(queries)} запросов\n"
    message += "Файл: <code>data/search_queries.txt</code>"
    
    await update.message.reply_text(message, parse_mode='HTML')

async def add_query_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Добавить запрос в файл"""
    if not context.args:
        await update.message.reply_text(
            "📝 Добавление запроса:\n"
            "/add_query <i>текст запроса</i>\n\n"
            "Пример:\n"
            "/add_query iphone 13\n"
            "/add_query ноутбук asus",
            parse_mode='HTML'
        )
        return
    
    query = ' '.join(context.args)
    
    if add_search_query(query):
        await update.message.reply_text(f"✅ Запрос добавлен: <b>{query}</b>", parse_mode='HTML')
    else:
        await update.message.reply_text(f"ℹ️ Запрос уже есть в списке: <b>{query}</b>", parse_mode='HTML')

async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Быстрый поиск"""
    if not context.args:
        await update.message.reply_text(
            "🔍 Быстрый поиск:\n"
            "/search <i>запрос</i>\n\n"
            "Пример:\n"
            "/search iphone\n"
            "/search ноутбук",
            parse_mode='HTML'
        )
        return
    
    query = ' '.join(context.args)
    await update.message.reply_text(f"🔍 Ищу '{query}'...")
    
    try:
        parser = GoofishParser()
        products = parser.search(query, page=1, rows=20)
        
        if not products:
            await update.message.reply_text("😔 Товары не найдены")
            return
        
        # Отправляем первые 3 товара
        for i, product in enumerate(products[:3], 1):
            # Используем правильную валюту из настроек
            currency = parser_settings.get('price_currency', 'yuan')
            exchange_rate = parser_settings.get('yuan_to_rub_rate', 12.5)
            
            if currency == 'rubles':
                price_text = f"💰 <b>{product.price_display_rub}</b> ({product.price_display})"
            else:
                price_text = f"💰 <b>{product.price_display}</b> (~{product.price_display_rub})"
            
            message = (
                f"<b>{i}. {product.title[:80]}...</b>\n"
                f"{price_text}\n"
                f"📍 {product.location}\n"
                f"⏰ {product.age_minutes} мин назад\n"
                f"🔗 {product.url}"
            )
            await update.message.reply_text(message, parse_mode='HTML')
        
        if len(products) > 3:
            await update.message.reply_text(
                f"📊 Найдено товаров: {len(products)}\n"
                f"Показаны первые 3."
            )
            
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {str(e)[:100]}")

async def subscribe_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Подписка на запрос"""
    user_id = update.effective_user.id
    
    if not context.args:
        await update.message.reply_text(
            "📩 Подписка на уведомления:\n"
            "/subscribe <i>запрос</i>\n\n"
            "Пример:\n"
            "/subscribe iphone\n"
            "/subscribe cav empt"
        )
        return
    
    query = ' '.join(context.args)
    
    if add_subscription(user_id, query):
        await update.message.reply_text(
            f"✅ Вы подписались на: <b>{query}</b>\n\n"
            "Новые товары будут приходить автоматически.",
            parse_mode='HTML'
        )
    else:
        await update.message.reply_text(
            f"ℹ️ Вы уже подписаны на: <b>{query}</b>",
            parse_mode='HTML'
        )

async def mysubs_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Мои подписки"""
    user_id = update.effective_user.id
    subscriptions = get_user_subscriptions(user_id)
    
    if not subscriptions:
        await update.message.reply_text(
            "📭 У вас нет подписок.\n"
            "Используйте /subscribe для добавления."
        )
        return
    
    message = "📋 <b>Ваши подписки:</b>\n\n"
    for i, query in enumerate(subscriptions, 1):
        message += f"{i}. {query}\n"
    
    message += f"\nВсего: {len(subscriptions)} подписок"
    
    await update.message.reply_text(message, parse_mode='HTML')

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Статус системы"""
    bot = context.application.bot_data.get('bot_instance')
    
    if not bot or not bot.monitor:
        await update.message.reply_text("❌ Мониторинг не запущен")
        return
    
    stats = bot.monitor.get_stats()
    queries = load_search_queries()
    
    status = "🟢 <b>Активен</b>" if stats['is_running'] else "🔴 <b>Остановлен</b>"
    
    message = (
        f"📊 <b>Статус системы</b>\n\n"
        f"Мониторинг: {status}\n"
        f"Циклов: {stats['cycles']}\n"
        f"Найдено товаров: {stats['total_products']}\n"
        f"Запросов: {len(queries)}\n"
        f"Последняя проверка: {stats['last_check'] or 'никогда'}"
    )
    
    await update.message.reply_text(message, parse_mode='HTML')

def setup_handlers(application, bot_instance):
    """Настройка всех обработчиков"""
    # Сохраняем ссылку на бота и настройки
    application.bot_data['bot_instance'] = bot_instance
    application.bot_data['parser_settings'] = parser_settings
    
    # ConversationHandler для настроек
    settings_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("settings", settings_command)],
        states={
            SETTING_CHOICE: [CallbackQueryHandler(settings_callback)],
            SETTING_VALUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, setting_value_handler)],
        },
        fallbacks=[CommandHandler("cancel", cancel_settings)],
    )
    
    # Регистрируем команды
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", start_command))
    application.add_handler(CommandHandler("queries", queries_command))
    application.add_handler(CommandHandler("add_query", add_query_command))
    application.add_handler(CommandHandler("search", search_command))
    application.add_handler(CommandHandler("subscribe", subscribe_command))
    application.add_handler(CommandHandler("mysubs", mysubs_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(settings_conv_handler)  # Добавляем обработчик настроек