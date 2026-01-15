# bot/handlers.py - ОБНОВИТЬ импорты и функцию setup_handlers
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, 
    CommandHandler, 
    MessageHandler, 
    CallbackQueryHandler,
    ConversationHandler,
    filters
)
from bot.parser_settings import (
    settings_command, settings_callback, setting_value_handler, 
    cancel_settings, SETTING_CHOICE, SETTING_VALUE, parser_settings
)
from bot.whitelist import whitelist_manager, setup_whitelist_handlers  # Импорт whitelist
from bot.personal_queries import setup_personal_handlers
from storage.files import (
    load_search_queries, save_user, 
    get_user_queries
)
from parsers.goofish import GoofishParser
from utils.auto_refresh import cookies_manager  # Импорт менеджера cookies

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обновленная команда /start с проверкой whitelist'а"""
    user = update.effective_user
    user_id = user.id
    
    # Проверка whitelist'а
    if not whitelist_manager.is_admin(user_id):
        await update.message.reply_text(
            "⛔ <b>Доступ запрещен</b>\n\n"
            "Ваш ID не находится в whitelist'е бота.\n"
            "Обратитесь к администратору для получения доступа.\n\n"
            f"🆔 <b>Ваш ID:</b> <code>{user_id}</code>\n\n"
            "Отправьте этот ID администратору для добавления в whitelist.",
            parse_mode='HTML'
        )
        return
    
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
        "🤖 <b>Goofish Parser Bot (Персональные подписки)</b>\n\n"
        "🔔 <b>ВАЖНО:</b> Теперь вы будете получать уведомления "
        "<u>только по вашим персональным запросам</u>!\n\n"
        "📋 <b>Управление запросами:</b>\n"
        "/myqueries - Мои запросы\n"
        "/add - Добавить запрос\n"
        "/remove - Удалить запрос\n"
        "/clear - Очистить все\n\n"
        "🔍 <b>Поиск:</b>\n"
        "/search - Быстрый поиск\n\n"
        "⚙️ <b>Настройки:</b>\n"
        "/status - Статус\n"
        "/settings - Настройки парсера\n"
        "/cookies_status - Статус cookies\n"
        "/help - Помощь",
        parse_mode='HTML'
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /help"""
    await update.message.reply_text(
        "ℹ️ <b>Помощь по боту:</b>\n\n"
        "🔔 <b>Как это работает:</b>\n"
        "1. Добавьте свои запросы через /add\n"
        "2. Бот будет мониторить новые товары\n"
        "3. Получайте уведомления только по вашим запросам\n\n"
        "📋 <b>Основные команды:</b>\n"
        "/myqueries - Управление запросами\n"
        "/add - Добавить запрос\n"
        "/remove - Удалить запрос\n"
        "/clear - Очистить все\n"
        "/search - Быстрый поиск\n"
        "/status - Статус системы\n"
        "/settings - Настройки парсера\n"
        "/cookies_status - Статус cookies\n"
        "/whitelist - Управление whitelist'ом (админы)\n"
        "/id - Получить свой ID\n\n"
        "💡 <b>Совет:</b>\n"
        "Используйте /myqueries для удобного управления запросами",
        parse_mode='HTML'
    )

async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Быстрый поиск (не зависит от подписок)"""
    if not context.args:
        await update.message.reply_text(
            "🔍 <b>Быстрый поиск</b>\n\n"
            "Используйте: /search <i>запрос</i>\n\n"
            "<b>Примеры:</b>\n"
            "/search iphone 15\n"
            "/search macbook pro\n\n"
            "<i>Этот поиск не влияет на ваши подписки</i>",
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

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Статус системы с информацией о пользователе"""
    bot = context.application.bot_data.get('bot_instance')
    
    if not bot or not bot.monitor:
        await update.message.reply_text("❌ Мониторинг не запущен")
        return
    
    stats = bot.monitor.get_stats()
    user_id = update.effective_user.id
    
    # Получаем запросы пользователя
    user_queries = get_user_queries(user_id)
    global_queries = load_search_queries()
    
    status = "🟢 <b>Активен</b>" if stats['is_running'] else "🔴 <b>Остановлен</b>"
    
    message = (
        f"📊 <b>Статус системы</b>\n\n"
        f"Мониторинг: {status}\n"
        f"Циклов: {stats['cycles']}\n"
        f"Найдено товаров: {stats['total_products']}\n"
        f"Общих запросов: {len(global_queries)}\n"
        f"<b>Ваших запросов: {len(user_queries)}</b>\n"
        f"Последняя проверка: {stats['last_check'] or 'никогда'}\n\n"
    )
    
    if user_queries:
        message += "<b>Ваши запросы:</b>\n"
        for i, q in enumerate(user_queries[:5], 1):
            message += f"{i}. {q}\n"
        if len(user_queries) > 5:
            message += f"... и еще {len(user_queries) - 5}\n"
    else:
        message += "📭 <i>У вас нет персональных запросов</i>\n"
        message += "Используйте /add чтобы добавить"
    
    await update.message.reply_text(message, parse_mode='HTML')

async def cookies_status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /cookies_status"""
    status = cookies_manager.get_status()
    
    message = "🍪 <b>Статус Cookies:</b>\n\n"
    message += f"🔄 Обновление: {'⏳ В процессе' if status['is_refreshing'] else '✅ Не активно'}\n"
    message += f"📅 Последнее обновление: {status['last_refresh'] or 'никогда'}\n"
    message += f"⏱️ Интервал обновления: {status['refresh_interval_hours']:.1f} часов\n"
    message += f"📁 Файл: <code>{status['cookies_file']}</code>"
    
    keyboard = [[
        InlineKeyboardButton("🔄 Принудительно обновить", callback_data="force_refresh_cookies")
    ]]
    
    await update.message.reply_text(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )

async def cookies_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик нажатий кнопок статуса cookies"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "force_refresh_cookies":
        # Проверяем права администратора
        if not whitelist_manager.is_admin(query.from_user.id):
            await query.answer("⛔ Только администраторы могут обновлять cookies")
            return
        
        await query.edit_message_text("🔄 Принудительно обновляю cookies...")
        
        success = await cookies_manager.refresh_cookies()
        
        if success:
            await query.edit_message_text("✅ Cookies успешно обновлены!")
        else:
            await query.edit_message_text("❌ Не удалось обновить cookies")
    
    # Для других callback'ов cookies
    elif query.data.startswith("cookies_"):
        await query.answer("Команда в разработке")

async def get_id_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /id - получить свой ID для добавления в whitelist"""
    user = update.effective_user
    
    await update.message.reply_text(
        f"🆔 <b>Ваш ID:</b> <code>{user.id}</code>\n\n"
        f"📝 <b>Имя:</b> {user.first_name or ''} {user.last_name or ''}\n"
        f"👤 <b>Username:</b> @{user.username if user.username else 'не указан'}\n\n"
        "Отправьте этот ID администратору для добавления в whitelist.",
        parse_mode='HTML'
    )

def setup_handlers(application, bot_instance):
    """Настройка всех обработчиков"""
    # Сохраняем ссылку на бота
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
    
    # Регистрируем основные команды (доступные всем в whitelist'е)
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("search", search_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("id", get_id_command))
    application.add_handler(CommandHandler("cookies_status", cookies_status_command))
    
    # Регистрируем обработчики whitelist'а (только для админов)
    setup_whitelist_handlers(application)
    
    # Регистрируем обработчики настроек
    application.add_handler(settings_conv_handler)
    
    # Регистрируем обработчики персональных запросов
    setup_personal_handlers(application)
    
    # Регистрируем обработчик для cookies callback'ов
    application.add_handler(CallbackQueryHandler(cookies_callback_handler, pattern="^force_refresh_cookies$"))
    application.add_handler(CallbackQueryHandler(cookies_callback_handler, pattern="^cookies_"))