import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Базовые пути
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

# Telegram
BOT_TOKEN = os.getenv("BOT_TOKEN", "8404858867:AAF6AkEToZgCktCdZsPV62jgEqK1vul_QFg")
ADMIN_IDS = [int(x.strip()) for x in os.getenv("ADMIN_IDS", "1080595280").split(",") if x.strip()]

# Файлы данных
SEARCH_QUERIES_FILE = DATA_DIR / "search_queries.txt"
GOOFISH_COOKIES_FILE = DATA_DIR / "goofish_cookies.json"
RESULTS_FILE = DATA_DIR / "results.txt"
USERS_FILE = DATA_DIR / "users.json"
SUBSCRIPTIONS_FILE = DATA_DIR / "subscriptions.json"
SEEN_IDS_FILE = DATA_DIR / "seen_ids.json"
PARSER_SETTINGS_FILE = DATA_DIR / "parser_settings.json"  # Новый файл настроек

# Настройки парсера по умолчанию
REQUEST_TIMEOUT = 30
MAX_RETRIES = 3
DEFAULT_USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'

# Настройки мониторинга (будут переопределяться из файла настроек)
CHECK_INTERVAL = 20
MAX_AGE_MINUTES = 1440
MAX_PAGES = 50
ROWS_PER_PAGE = 500
DEFAULT_QUERIES = ["cav"]

ROLE_ADMIN = "admin"
ROLE_USER = "user"
WHITELIST_FILE = DATA_DIR / "whitelist.json"
USER_SETTINGS_DIR = DATA_DIR / "user_settings"
USER_SETTINGS_DIR.mkdir(exist_ok=True)