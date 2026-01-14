# utils/cookies.py - полностью переписанный
import json
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright
import time

# Добавляем родительскую директорию в путь для импорта
sys.path.append(str(Path(__file__).parent.parent))

try:
    from config import GOOFISH_COOKIES_FILE, DATA_DIR
except ImportError:
    # Если config не импортируется
    BASE_DIR = Path(__file__).parent.parent
    DATA_DIR = BASE_DIR / "data"
    DATA_DIR.mkdir(exist_ok=True)
    GOOFISH_COOKIES_FILE = DATA_DIR / "goofish_cookies.json"
    print(f"⚠️  Использую путь по умолчанию: {GOOFISH_COOKIES_FILE}")

def get_goofish_cookies():
    """Автоматическое получение cookies Goofish"""
    print("=" * 60)
    print("🔄 АВТОМАТИЧЕСКОЕ ПОЛУЧЕНИЕ COOKIES GOOFISH")
    print("=" * 60)

    with sync_playwright() as p:
        # Запускаем браузер с интерфейсом
        browser = p.chromium.launch(
            headless=False,
            args=['--disable-blink-features=AutomationControlled']
        )
        
        # Создаем контекст с User-Agent
        context = browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        
        page = context.new_page()
        
        print("🌐 Открываю https://www.goofish.com...")
        page.goto('https://www.goofish.com', wait_until='networkidle')
        time.sleep(2)
        
        print("\n" + "=" * 60)
        print("👤 РУЧНОЙ ШАГ: Если требуется вход:")
        print("   1. Войдите в свой аккаунт в открывшемся браузере")
        print("   2. Дождитесь загрузки главной страницы")
        print("   3. Нажмите Enter в этом терминале")
        print("=" * 60)
        
        input("\nНажмите Enter после входа в аккаунт...")
        
        # Делаем дополнительное действие для обновления cookies
        print("🔄 Обновляю страницу...")
        page.reload(wait_until='networkidle')
        time.sleep(3)
        
        # Получаем все cookies
        all_cookies = context.cookies()
        
        # Фильтруем важные cookies для Goofish
        important_keys = [
            '_m_h5_tk', '_m_h5_tk_enc', 
            '_tb_token_', 'cna', 't', 
            'cookie2', 'isg', 'l', 'uc1'
        ]
        goofish_cookies = {}
        
        for cookie in all_cookies:
            if cookie['name'] in important_keys:
                goofish_cookies[cookie['name']] = cookie['value']
                print(f"   ✅ {cookie['name']}: {cookie['value'][:50]}...")
        
        # Проверяем обязательные cookies
        required = ['_m_h5_tk', 't']
        missing = [r for r in required if r not in goofish_cookies]
        
        if missing:
            print(f"\n⚠️  Отсутствуют важные cookies: {missing}")
            print("   Попробуйте полностью войти в аккаунт")
        else:
            print(f"\n✅ Все важные cookies получены!")
        
        # Сохраняем в файл
        with open(GOOFISH_COOKIES_FILE, 'w', encoding='utf-8') as f:
            json.dump(goofish_cookies, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 Сохранено {len(goofish_cookies)} cookies в {GOOFISH_COOKIES_FILE}")
        
        # Показываем что получили
        print("\n🔑 Полученные cookies:")
        for key, value in goofish_cookies.items():
            print(f"   {key}: {value[:50]}...")
        
        # Проверяем _m_h5_tk
        if '_m_h5_tk' in goofish_cookies:
            m_h5_tk = goofish_cookies['_m_h5_tk']
            if '_' in m_h5_tk:
                token, timestamp = m_h5_tk.split('_', 1)
                print(f"\n📊 Анализ _m_h5_tk:")
                print(f"   Токен: {token[:20]}...")
                print(f"   Время: {timestamp}")
        
        browser.close()
    
    print("\n" + "=" * 60)
    print("🎯 ДАЛЬНЕЙШИЕ ШАГИ:")
    print("1. Используйте эти cookies в парсере")
    print("2. Если не работает - обновите через 24 часа")
    print("=" * 60)

def check_cookies():
    """Проверка существования cookies"""
    if GOOFISH_COOKIES_FILE.exists():
        try:
            with open(GOOFISH_COOKIES_FILE, 'r', encoding='utf-8') as f:
                cookies = json.load(f)
                print(f"📂 Загружено {len(cookies)} cookies")
                
                # Проверяем важные
                important = ['_m_h5_tk', 't', 'cookie2']
                for key in important:
                    if key in cookies:
                        print(f"   ✅ {key}: есть")
                    else:
                        print(f"   ❌ {key}: отсутствует")
                
                return len(cookies) > 0
        except Exception as e:
            print(f"❌ Ошибка загрузки cookies: {e}")
            return False
    else:
        print(f"❌ Файл {GOOFISH_COOKIES_FILE} не найден")
        return False

if __name__ == "__main__":
    get_goofish_cookies()

# utils/cookies.py - добавьте эту функцию в конец файла
def refresh_cookies():
    """Получение свежих cookies"""
    print("🔄 Получение свежих cookies...")
    get_goofish_cookies()