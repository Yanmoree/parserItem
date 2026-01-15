# core/settings.py
import os
from pathlib import Path
from dotenv import load_dotenv
import json

load_dotenv()

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

class Settings:
    def __init__(self):
        # Настройки из .env (по умолчанию)
        self.check_interval = int(os.getenv("CHECK_INTERVAL", 60))
        self.max_age_minutes = int(os.getenv("MAX_AGE_MINUTES", 1440))
        self.max_pages = int(os.getenv("MAX_PAGES", 50))
        self.rows_per_page = int(os.getenv("ROWS_PER_PAGE", 500))
        
        # Настройки из файла (пользовательские)
        self.settings_file = DATA_DIR / "parser_settings.json"
        self.user_settings = self._load_user_settings()
        
        # Объединяем настройки (пользовательские имеют приоритет)
        self._apply_user_settings()
        
        # Конвертируем настройки пагинации в целые числа
        self._convert_to_int_settings()
    
    def _load_user_settings(self):
        """Загрузка пользовательских настроек"""
        if self.settings_file.exists():
            try:
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def _apply_user_settings(self):
        """Применение пользовательских настроек"""
        if self.user_settings:
            self.check_interval = int(self.user_settings.get('check_interval', self.check_interval))
            self.max_age_minutes = int(self.user_settings.get('max_age_minutes', self.max_age_minutes))
            self.max_pages = int(self.user_settings.get('max_pages', self.max_pages))
            self.rows_per_page = int(self.user_settings.get('rows_per_page', self.rows_per_page))
    
    def _convert_to_int_settings(self):
        """Конвертация настроек пагинации в целые числа"""
        try:
            self.max_pages = int(self.max_pages)
        except (ValueError, TypeError):
            self.max_pages = 10
        
        try:
            self.rows_per_page = int(self.rows_per_page)
        except (ValueError, TypeError):
            self.rows_per_page = 100
    
    def reload(self):
        """Перезагрузить настройки"""
        self.__init__()
    
    def save_user_setting(self, key: str, value):
        """Сохранение пользовательской настройки"""
        self.user_settings[key] = value
        with open(self.settings_file, 'w', encoding='utf-8') as f:
            json.dump(self.user_settings, f, ensure_ascii=False, indent=2)
        self._apply_user_settings()
        self._convert_to_int_settings()

# Глобальный экземпляр настроек
settings = Settings()