# bot/whitelist.py
import os
import json
from pathlib import Path
from typing import List
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
from dotenv import load_dotenv
import re

from config import BASE_DIR

class WhitelistManager:
    """Менеджер whitelist'а и администраторов"""
    
    def __init__(self):
        self.env_file = BASE_DIR / ".env"
        self.admins = self._load_admins()
    
    def _load_admins(self) -> List[int]:
        """Загрузка администраторов из .env"""
        if not self.env_file.exists():
            print(f"⚠️ Файл .env не найден: {self.env_file}")
            return []
        
        load_dotenv(self.env_file)
        admin_ids_str = os.getenv("ADMIN_IDS", "")
        
        if not admin_ids_str:
            return []
        
        # Преобразуем строку в список чисел
        admins = []
        for admin_str in admin_ids_str.split(","):
            admin_str = admin_str.strip()
            if admin_str.isdigit():
                admins.append(int(admin_str))
        
        return admins
    
    def save_admins(self, admin_ids: List[int]):
        """Сохранение администраторов в .env"""
        admin_str = ",".join(str(admin_id) for admin_id in admin_ids)
        
        # Читаем текущий .env
        env_content = ""
        if self.env_file.exists():
            with open(self.env_file, 'r', encoding='utf-8') as f:
                env_content = f.read()
        
        # Ищем существующую строку ADMIN_IDS
        lines = env_content.split('\n')
        admin_line_pattern = re.compile(r'^ADMIN_IDS\s*=\s*.*$')
        
        new_lines = []
        admin_line_found = False
        
        for line in lines:
            if admin_line_pattern.match(line):
                new_lines.append(f"ADMIN_IDS={admin_str}")
                admin_line_found = True
            else:
                new_lines.append(line)
        
        # Если строка не найдена, добавляем в конец
        if not admin_line_found:
            if new_lines and not new_lines[-1].strip():
                new_lines[-1] = f"ADMIN_IDS={admin_str}"
            else:
                new_lines.append(f"ADMIN_IDS={admin_str}")
        
        # Сохраняем файл
        with open(self.env_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(new_lines))
        
        # Обновляем кэш
        self.admins = admin_ids.copy()
        
        print(f"✅ Администраторы сохранены: {admin_ids}")
        return True
    
    def is_admin(self, user_id: int) -> bool:
        """Проверка, является ли пользователь администратором"""
        return user_id in self.admins
    
    def add_admin(self, user_id: int) -> bool:
        """Добавление администратора"""
        if user_id in self.admins:
            return False
        
        self.admins.append(user_id)
        return self.save_admins(self.admins)
    
    def remove_admin(self, user_id: int) -> bool:
        """Удаление администратора"""
        if user_id not in self.admins:
            return False
        
        self.admins.remove(user_id)
        return self.save_admins(self.admins)
    
    def get_admins(self) -> List[int]:
        """Получение списка администраторов"""
        return self.admins.copy()
    
    def get_whitelist(self) -> List[int]:
        """Получение whitelist'а (включая администраторов)"""
        # Здесь можно расширить для отдельного whitelist'а
        return self.get_admins()

# Глобальный экземпляр
whitelist_manager = WhitelistManager()

# Декоратор для проверки админских прав
def admin_required(func):
    """Декоратор для проверки прав администратора"""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        
        if not whitelist_manager.is_admin(user_id):
            await update.message.reply_text(
                "⛔ У вас нет прав для выполнения этой команды.\n"
                "Только администраторы могут управлять whitelist'ом."
            )
            return
        
        return await func(update, context, *args, **kwargs)
    
    return wrapper

# Команды для управления whitelist'ом
@admin_required
async def whitelist_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /whitelist - управление whitelist'ом"""
    keyboard = [
        [
            InlineKeyboardButton("👥 Список пользователей", callback_data="whitelist_show"),
            InlineKeyboardButton("➕ Добавить пользователя", callback_data="whitelist_add")
        ],
        [
            InlineKeyboardButton("➖ Удалить пользователя", callback_data="whitelist_remove"),
            InlineKeyboardButton("📊 Статус", callback_data="whitelist_status")
        ],
        [
            InlineKeyboardButton("🔄 Обновить из .env", callback_data="whitelist_reload"),
            InlineKeyboardButton("❌ Закрыть", callback_data="whitelist_close")
        ]
    ]
    
    await update.message.reply_text(
        "👑 <b>Управление Whitelist'ом</b>\n\n"
        "Здесь вы можете управлять списком пользователей, "
        "которые имеют доступ к боту.\n\n"
        "Выберите действие:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )

@admin_required
async def whitelist_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик нажатий кнопок whitelist'а"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == "whitelist_show":
        # Показать список пользователей
        users = whitelist_manager.get_whitelist()
        
        if not users:
            await query.edit_message_text("📭 Whitelist пуст.")
            return
        
        message = "👥 <b>Пользователи в whitelist'е:</b>\n\n"
        for i, user_id in enumerate(users, 1):
            message += f"{i}. <code>{user_id}</code>\n"
        
        message += f"\n📊 Всего: {len(users)} пользователей"
        
        await query.edit_message_text(message, parse_mode='HTML')
    
    elif data == "whitelist_add":
        # Добавить пользователя
        await query.edit_message_text(
            "➕ <b>Добавление пользователя в whitelist</b>\n\n"
            "Введите ID пользователя в формате:\n"
            "<code>/add_user 1234567890</code>\n\n"
            "Чтобы получить ID пользователя, попросите его отправить команду /id",
            parse_mode='HTML'
        )
    
    elif data == "whitelist_remove":
        # Удалить пользователя
        users = whitelist_manager.get_whitelist()
        
        if not users:
            await query.edit_message_text("📭 Whitelist пуст. Нечего удалять.")
            return
        
        # Создаем кнопки для удаления каждого пользователя
        keyboard = []
        for user_id in users:
            keyboard.append([
                InlineKeyboardButton(f"❌ Удалить {user_id}", callback_data=f"remove_user:{user_id}")
            ])
        
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="whitelist_back")])
        
        await query.edit_message_text(
            "➖ <b>Удаление пользователя из whitelist'а</b>\n\n"
            "Выберите пользователя для удаления:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )
    
    elif data == "whitelist_status":
        # Статус whitelist'а
        users = whitelist_manager.get_whitelist()
        
        message = "📊 <b>Статус Whitelist'а:</b>\n\n"
        message += f"👥 Пользователей: {len(users)}\n"
        message += f"📁 Файл настроек: <code>{whitelist_manager.env_file}</code>\n\n"
        
        if users:
            message += "<b>Текущие пользователи:</b>\n"
            for user_id in users[:10]:  # Показываем первые 10
                message += f"• <code>{user_id}</code>\n"
            
            if len(users) > 10:
                message += f"... и еще {len(users) - 10}"
        
        await query.edit_message_text(message, parse_mode='HTML')
    
    elif data == "whitelist_reload":
        # Перезагрузить из .env
        whitelist_manager._load_admins()
        await query.answer("✅ Whitelist перезагружен из .env")
    
    elif data == "whitelist_close":
        await query.edit_message_text("👑 Управление whitelist'ом закрыто")
    
    elif data == "whitelist_back":
        # Вернуться к главному меню
        return await whitelist_command(update, context)
    
    elif data.startswith("remove_user:"):
        # Удалить конкретного пользователя
        user_id_str = data.split(":", 1)[1]
        try:
            user_id = int(user_id_str)
            
            if whitelist_manager.remove_admin(user_id):
                await query.answer(f"✅ Пользователь {user_id} удален из whitelist'а")
                await query.edit_message_text(f"✅ Пользователь <code>{user_id}</code> удален из whitelist'а", parse_mode='HTML')
            else:
                await query.answer("❌ Пользователь не найден в whitelist'е")
        
        except ValueError:
            await query.answer("❌ Неверный формат ID пользователя")

@admin_required
async def add_user_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /add_user - добавить пользователя в whitelist"""
    if not context.args:
        await update.message.reply_text(
            "➕ <b>Добавление пользователя в whitelist</b>\n\n"
            "Используйте: /add_user <i>ID_пользователя</i>\n\n"
            "<b>Пример:</b>\n"
            "/add_user 1234567890\n\n"
            "Чтобы получить ID пользователя, попросите его отправить команду /id",
            parse_mode='HTML'
        )
        return
    
    try:
        user_id = int(context.args[0])
        
        if whitelist_manager.add_admin(user_id):
            await update.message.reply_text(
                f"✅ Пользователь <code>{user_id}</code> добавлен в whitelist",
                parse_mode='HTML'
            )
        else:
            await update.message.reply_text(
                f"ℹ️ Пользователь <code>{user_id}</code> уже есть в whitelist'е",
                parse_mode='HTML'
            )
            
    except ValueError:
        await update.message.reply_text("❌ Неверный формат ID пользователя. Используйте числа.")

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

# Настройка обработчиков
def setup_whitelist_handlers(application):
    """Регистрация обработчиков whitelist'а"""
    application.add_handler(CommandHandler("whitelist", whitelist_command))
    application.add_handler(CommandHandler("add_user", add_user_command))
    application.add_handler(CallbackQueryHandler(whitelist_callback_handler, pattern="^whitelist_"))
    application.add_handler(CallbackQueryHandler(whitelist_callback_handler, pattern="^remove_user:"))