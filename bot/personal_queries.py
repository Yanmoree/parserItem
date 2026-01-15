# bot/personal_queries.py
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
from storage.files import get_user_queries, save_user_queries, add_user_query, remove_user_query, load_search_queries

async def my_queries_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /myqueries - показать мои запросы"""
    user_id = update.effective_user.id
    queries = get_user_queries(user_id)
    
    if not queries:
        keyboard = [
            [InlineKeyboardButton("➕ Добавить запрос", callback_data="add_query_menu")],
            [InlineKeyboardButton("📋 Показать общие запросы", callback_data="show_global_queries")]
        ]
        
        await update.message.reply_text(
            "📭 У вас нет персональных запросов.\n\n"
            "Используйте кнопки ниже для управления запросами:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    # Создаем кнопки для управления каждым запросом
    keyboard = []
    for query in queries:
        keyboard.append([
            InlineKeyboardButton(f"❌ {query}", callback_data=f"remove_query:{query}")
        ])
    
    keyboard.extend([
        [InlineKeyboardButton("➕ Добавить запрос", callback_data="add_query_menu")],
        [InlineKeyboardButton("🗑️ Очистить все", callback_data="clear_all_queries")],
        [InlineKeyboardButton("📋 Общие запросы", callback_data="show_global_queries")]
    ])
    
    message = "📋 <b>Ваши персональные запросы:</b>\n\n"
    for i, query in enumerate(queries, 1):
        message += f"{i}. {query}\n"
    
    message += f"\n📊 Всего: {len(queries)} запросов\n"
    message += "❌ Нажмите на запрос, чтобы удалить его"
    
    await update.message.reply_text(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )

async def add_query_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /add - добавить запрос"""
    if not context.args:
        await update.message.reply_text(
            "📝 <b>Добавление запроса</b>\n\n"
            "Используйте: /add <i>текст запроса</i>\n\n"
            "<b>Примеры:</b>\n"
            "/add iphone 15\n"
            "/add ноутбук asus\n"
            "/add stone island\n\n"
            "📌 <i>Вы будете получать уведомления только по вашим запросам</i>",
            parse_mode='HTML'
        )
        return
    
    query = ' '.join(context.args)
    user_id = update.effective_user.id
    
    if add_user_query(user_id, query):
        await update.message.reply_text(
            f"✅ Запрос добавлен: <b>{query}</b>\n\n"
            f"Теперь вы будете получать уведомления о новых товарах по этому запросу.",
            parse_mode='HTML'
        )
    else:
        await update.message.reply_text(
            f"ℹ️ У вас уже есть этот запрос: <b>{query}</b>",
            parse_mode='HTML'
        )

async def remove_query_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /remove - удалить запрос"""
    if not context.args:
        await update.message.reply_text(
            "🗑️ <b>Удаление запроса</b>\n\n"
            "Используйте: /remove <i>текст запроса</i>\n\n"
            "Или используйте /myqueries для просмотра и управления",
            parse_mode='HTML'
        )
        return
    
    query = ' '.join(context.args)
    user_id = update.effective_user.id
    
    if remove_user_query(user_id, query):
        await update.message.reply_text(
            f"🗑️ Запрос удален: <b>{query}</b>",
            parse_mode='HTML'
        )
    else:
        await update.message.reply_text(
            f"❌ Запрос не найден: <b>{query}</b>",
            parse_mode='HTML'
        )

async def clear_queries_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /clear - очистить все запросы"""
    user_id = update.effective_user.id
    
    from storage.files import clear_user_queries
    if clear_user_queries(user_id):
        await update.message.reply_text(
            "🗑️ Все ваши запросы очищены.\n"
            "Теперь вы будете использовать общие запросы."
        )
    else:
        await update.message.reply_text(
            "ℹ️ У вас нет персональных запросов."
        )

async def queries_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик нажатий кнопок запросов"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = update.effective_user.id
    
    if data == "add_query_menu":
        # Показать форму добавления запроса
        await query.edit_message_text(
            "📝 <b>Добавление нового запроса</b>\n\n"
            "Введите запрос в формате:\n"
            "<code>/add текст запроса</code>\n\n"
            "<b>Пример:</b>\n"
            "<code>/add nike air force</code>\n"
            "<code>/add macbook pro m3</code>\n\n"
            "Или нажмите /cancel для отмены",
            parse_mode='HTML'
        )
    
    elif data == "show_global_queries":
        # Показать общие запросы
        global_queries = load_search_queries()
        
        if not global_queries:
            await query.edit_message_text("📭 Общие запросы пусты")
            return
        
        message = "📋 <b>Общие запросы (для всех пользователей):</b>\n\n"
        for i, q in enumerate(global_queries, 1):
            message += f"{i}. {q}\n"
        
        message += f"\n📊 Всего: {len(global_queries)} запросов"
        
        keyboard = [
            [InlineKeyboardButton("➕ Добавить в мои запросы", callback_data="copy_global_queries")],
            [InlineKeyboardButton("🔙 Назад к моим запросам", callback_data="back_to_my_queries")]
        ]
        
        await query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )
    
    elif data == "copy_global_queries":
        # Копировать все общие запросы в персональные
        global_queries = load_search_queries()
        user_queries = get_user_queries(user_id)
        
        added_count = 0
        for gq in global_queries:
            if gq not in user_queries:
                user_queries.append(gq)
                added_count += 1
        
        save_user_queries(user_id, user_queries)
        
        await query.edit_message_text(
            f"✅ Добавлено {added_count} запросов из общих в ваши персональные."
        )
    
    elif data == "back_to_my_queries":
        # Вернуться к моим запросам
        await my_queries_command(update, context)
    
    elif data.startswith("remove_query:"):
        # Удалить конкретный запрос
        query_to_remove = data.split(":", 1)[1]
        
        if remove_user_query(user_id, query_to_remove):
            await query.edit_message_text(
                f"🗑️ Запрос удален: <b>{query_to_remove}</b>",
                parse_mode='HTML'
            )
        else:
            await query.answer("Ошибка при удалении запроса")
    
    elif data == "clear_all_queries":
        # Очистить все запросы
        keyboard = [
            [
                InlineKeyboardButton("✅ Да, очистить", callback_data="confirm_clear"),
                InlineKeyboardButton("❌ Нет, отмена", callback_data="cancel_clear")
            ]
        ]
        
        await query.edit_message_text(
            "⚠️ <b>Вы уверены что хотите очистить все ваши запросы?</b>\n\n"
            "После этого вы будете использовать общие запросы.",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )
    
    elif data == "confirm_clear":
        from storage.files import clear_user_queries
        clear_user_queries(user_id)
        
        await query.edit_message_text(
            "🗑️ Все ваши запросы очищены.\n"
            "Теперь вы будете использовать общие запросы."
        )
    
    elif data == "cancel_clear":
        await query.edit_message_text("❌ Очистка отменена.")

# Настройка обработчиков
def setup_personal_handlers(application):
    """Регистрация обработчиков персональных запросов"""
    application.add_handler(CommandHandler("myqueries", my_queries_command))
    application.add_handler(CommandHandler("add", add_query_command))
    application.add_handler(CommandHandler("remove", remove_query_command))
    application.add_handler(CommandHandler("clear", clear_queries_command))
    application.add_handler(CallbackQueryHandler(queries_callback_handler))