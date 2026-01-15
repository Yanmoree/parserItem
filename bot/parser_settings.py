# bot/parser_settings.py
import json
from pathlib import Path
from typing import Dict, List, Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from config import DATA_DIR

# Состояния для ConversationHandler
SETTING_CHOICE, SETTING_VALUE = range(2)

class ParserSettings:
    """Управление настройками парсера"""
    
    def __init__(self):
        self.settings_file = DATA_DIR / "parser_settings.json"
        self.default_settings = {
            'check_interval': 300,
            'max_age_minutes': 1440,
            'max_pages': 10,
            'rows_per_page': 500,
            'price_currency': 'yuan',
            'yuan_to_rub_rate': 12.5,
            'notify_new_only': True,
            'filter_by_query': True
        }
        self.settings = self._load_settings()
    
    def _load_settings(self) -> Dict:
        """Загрузка настроек из файла"""
        if self.settings_file.exists():
            try:
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    saved = json.load(f)
                    # Объединяем с дефолтными настройками и конвертируем числа
                    merged = {**self.default_settings, **saved}
                    # Конвертируем настройки пагинации в целые числа
                    merged['max_pages'] = int(merged.get('max_pages', 10))
                    merged['rows_per_page'] = int(merged.get('rows_per_page', 100))
                    return merged
            except Exception as e:
                print(f"❌ Ошибка загрузки настроек: {e}")
                return self.default_settings.copy()
        return self.default_settings.copy()
    
    def save_settings(self):
        """Сохранение настроек в файл"""
        DATA_DIR.mkdir(exist_ok=True)
        with open(self.settings_file, 'w', encoding='utf-8') as f:
            json.dump(self.settings, f, ensure_ascii=False, indent=2)
    
    def get(self, key: str, default=None):
        """Получение значения настройки"""
        return self.settings.get(key, default)
    
    def set(self, key: str, value):
        """Установка значения настройки"""
        # Конвертируем настройки пагинации в целые числа перед сохранением
        if key in ['max_pages', 'rows_per_page']:
            try:
                value = int(float(value)) if isinstance(value, (int, float, str)) else int(value)
            except (ValueError, TypeError):
                value = self.default_settings[key]
        
        self.settings[key] = value
        self.save_settings()
    
    def get_all(self) -> Dict:
        """Получение всех настроек"""
        return self.settings.copy()

# Глобальный экземпляр настроек
parser_settings = ParserSettings()

async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /settings - меню настроек"""
    keyboard = [
        [
            InlineKeyboardButton("⏰ Интервал проверки", callback_data="setting_check_interval"),
            InlineKeyboardButton("⏳ Макс. возраст", callback_data="setting_max_age"),
        ],
        [
            InlineKeyboardButton("📄 Страниц", callback_data="setting_max_pages"),
            InlineKeyboardButton("📦 Товаров на стр.", callback_data="setting_rows_page"),
        ],
        [
            InlineKeyboardButton("💰 Валюта", callback_data="setting_currency"),
            InlineKeyboardButton("💱 Курс юаня", callback_data="setting_exchange_rate"),
        ],
        [
            InlineKeyboardButton("🔔 Только новые", callback_data="setting_notify_new"),
            InlineKeyboardButton("🔍 Фильтр по запросу", callback_data="setting_filter_query"),
        ],
        [
            InlineKeyboardButton("📊 Текущие настройки", callback_data="show_current"),
            InlineKeyboardButton("🔄 Сбросить", callback_data="reset_settings"),
        ],
        [InlineKeyboardButton("❌ Закрыть", callback_data="close_settings")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "⚙️ <b>Настройки парсера</b>\n\n"
        "Выберите параметр для изменения:",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )
    
    return SETTING_CHOICE

async def settings_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка нажатий кнопок настроек"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == "close_settings":
        await query.edit_message_text("⚙️ Настройки закрыты")
        return ConversationHandler.END
    
    elif data == "show_current":
        settings = parser_settings.get_all()
        message = "📊 <b>Текущие настройки:</b>\n\n"
        message += f"⏰ Интервал проверки: <code>{settings['check_interval']}</code> сек\n"
        message += f"⏳ Макс. возраст: <code>{settings['max_age_minutes']}</code> мин\n"
        message += f"📄 Макс. страниц: <code>{settings['max_pages']}</code>\n"
        message += f"📦 Товаров на стр.: <code>{settings['rows_per_page']}</code>\n"
        message += f"💰 Валюта: <code>{settings['price_currency']}</code>\n"
        message += f"💱 Курс юаня: <code>{settings['yuan_to_rub_rate']}</code>\n"
        message += f"🔔 Только новые: <code>{settings['notify_new_only']}</code>\n"
        message += f"🔍 Фильтр по запросу: <code>{settings['filter_by_query']}</code>\n\n"
        message += "Выберите параметр для изменения:"
        
        keyboard = query.message.reply_markup.inline_keyboard
        await query.edit_message_text(message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
        return SETTING_CHOICE
    
    elif data == "reset_settings":
        parser_settings.settings = parser_settings.default_settings.copy()
        parser_settings.save_settings()
        await query.edit_message_text("🔄 Настройки сброшены к значениям по умолчанию")
        return ConversationHandler.END
    
    else:
        # Установка значения настройки
        setting_map = {
            "setting_check_interval": ("⏰ Интервал проверки (секунды)", "check_interval", "число"),
            "setting_max_age": ("⏳ Макс. возраст товара (минуты)", "max_age_minutes", "число"),
            "setting_max_pages": ("📄 Макс. страниц для проверки", "max_pages", "целое"),
            "setting_rows_page": ("📦 Товаров на странице", "rows_per_page", "целое"),
            "setting_currency": ("💰 Валюта отображения (yuan/rubles)", "price_currency", "валюта"),
            "setting_exchange_rate": ("💱 Курс юань → рубль", "yuan_to_rub_rate", "число"),
            "setting_notify_new": ("🔔 Уведомлять только о новых товарах", "notify_new_only", "булев"),
            "setting_filter_query": ("🔍 Фильтровать товары по запросу", "filter_by_query", "булев"),
        }
        
        if data in setting_map:
            setting_name, setting_key, setting_type = setting_map[data]
            context.user_data['setting_key'] = setting_key
            context.user_data['setting_type'] = setting_type
            
            await query.edit_message_text(
                f"Введите значение для <b>{setting_name}</b>\n"
                f"Текущее: <code>{parser_settings.get(setting_key)}</code>\n\n"
                f"Примеры:\n"
                f"• Для числа: <code>300</code>\n"
                f"• Для целого: <code>5</code>\n"
                f"• Для валюты: <code>yuan</code> или <code>rubles</code>\n"
                f"• Для булева: <code>да</code>/<code>нет</code> или <code>true</code>/<code>false</code>",
                parse_mode='HTML'
            )
            
            return SETTING_VALUE

async def setting_value_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка введенного значения настройки"""
    user_input = update.message.text.strip()
    setting_key = context.user_data.get('setting_key')
    setting_type = context.user_data.get('setting_type')
    
    try:
        if setting_type == "число":
            value = float(user_input)
            if setting_key in ['check_interval', 'max_age_minutes']:
                value = int(value)  # Целые числа для времени
        
        elif setting_type == "целое":
            value = int(float(user_input)) if '.' in user_input else int(user_input)
        
        elif setting_type == "валюта":
            if user_input.lower() in ['yuan', 'юань', '¥']:
                value = 'yuan'
            elif user_input.lower() in ['rubles', 'рубли', 'rub', 'руб']:
                value = 'rubles'
            else:
                await update.message.reply_text("❌ Неверное значение. Используйте 'yuan' или 'rubles'")
                return SETTING_VALUE
        
        elif setting_type == "булев":
            if user_input.lower() in ['да', 'yes', 'true', '1', 'on']:
                value = True
            elif user_input.lower() in ['нет', 'no', 'false', '0', 'off']:
                value = False
            else:
                await update.message.reply_text("❌ Неверное значение. Используйте 'да' или 'нет'")
                return SETTING_VALUE
        
        else:
            value = user_input
        
        # Сохраняем настройку
        parser_settings.set(setting_key, value)
        
        await update.message.reply_text(
            f"✅ Настройка <b>{setting_key}</b> изменена на: <code>{value}</code>",
            parse_mode='HTML'
        )
        
        # Возвращаем к меню настроек
        return await settings_command(update, context)
        
    except ValueError as e:
        await update.message.reply_text(f"❌ Ошибка: {e}\nПопробуйте снова:")
        return SETTING_VALUE

async def cancel_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена настроек"""
    await update.message.reply_text("⚙️ Настройки отменены")
    return ConversationHandler.END