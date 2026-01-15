# storage/files.py
import json
from pathlib import Path
from typing import Dict, List, Set
from config import (
    SEARCH_QUERIES_FILE, USERS_FILE, SUBSCRIPTIONS_FILE, 
    SEEN_IDS_FILE, DEFAULT_QUERIES, DATA_DIR
)

# ==================== Управление поисковыми запросами ====================

def load_search_queries() -> List[str]:
    """Загрузка запросов из текстового файла"""
    if not SEARCH_QUERIES_FILE.exists():
        # Создаем файл с запросами по умолчанию
        save_search_queries(DEFAULT_QUERIES)
        return DEFAULT_QUERIES
    
    try:
        queries = []
        with open(SEARCH_QUERIES_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    queries.append(line)
        
        return queries if queries else DEFAULT_QUERIES
    except Exception as e:
        print(f"❌ Ошибка загрузки запросов: {e}")
        return DEFAULT_QUERIES

def save_search_queries(queries: List[str]):
    """Сохранение запросов в файл"""
    try:
        with open(SEARCH_QUERIES_FILE, 'w', encoding='utf-8') as f:
            for query in queries:
                f.write(f"{query}\n")
        print(f"💾 Сохранено {len(queries)} запросов в {SEARCH_QUERIES_FILE}")
    except Exception as e:
        print(f"❌ Ошибка сохранения запросов: {e}")

def add_search_query(query: str):
    """Добавление нового запроса"""
    queries = load_search_queries()
    if query not in queries:
        queries.append(query)
        save_search_queries(queries)
        return True
    return False

# ==================== Управление просмотренными ID ====================

def load_seen_ids() -> Set[str]:
    """Загрузка ID просмотренных товаров"""
    if not SEEN_IDS_FILE.exists():
        return set()
    
    try:
        with open(SEEN_IDS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return set(data.get('seen_ids', []))
    except:
        return set()

def save_seen_ids(seen_ids: Set[str]):
    """Сохранение ID просмотренных товаров"""
    try:
        data = {'seen_ids': list(seen_ids)}
        with open(SEEN_IDS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"❌ Ошибка сохранения seen_ids: {e}")

def add_seen_ids(new_ids: List[str]):
    """Добавление новых ID в кэш"""
    seen_ids = load_seen_ids()
    before = len(seen_ids)
    seen_ids.update(new_ids)
    save_seen_ids(seen_ids)
    return len(seen_ids) - before

# ==================== Управление пользователями ====================

def load_users() -> Dict:
    """Загрузка пользователей"""
    if not USERS_FILE.exists():
        return {}
    
    try:
        with open(USERS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}

def save_user(user_data: Dict):
    """Сохранение пользователя"""
    users = load_users()
    user_id = str(user_data['id'])
    users[user_id] = user_data
    
    try:
        with open(USERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(users, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"❌ Ошибка сохранения пользователя: {e}")

# ==================== Управление подписками ====================

def load_subscriptions() -> Dict:
    """Загрузка подписок (персональных запросов)"""
    if not SUBSCRIPTIONS_FILE.exists():
        return {}
    
    try:
        with open(SUBSCRIPTIONS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data
    except:
        return {}

def get_user_queries(user_id: int) -> List[str]:
    """Получение запросов конкретного пользователя"""
    subscriptions = load_subscriptions()
    user_key = str(user_id)
    
    # Если у пользователя есть персональные запросы - возвращаем их
    if user_key in subscriptions:
        return subscriptions[user_key]
    
    # Если нет - возвращаем глобальные запросы
    return load_search_queries()

def save_user_queries(user_id: int, queries: List[str]):
    """Сохранение запросов пользователя"""
    subscriptions = load_subscriptions()
    subscriptions[str(user_id)] = queries
    
    try:
        with open(SUBSCRIPTIONS_FILE, 'w', encoding='utf-8') as f:
            json.dump(subscriptions, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"❌ Ошибка сохранения запросов пользователя: {e}")
        return False

def add_user_query(user_id: int, query: str) -> bool:
    """Добавление запроса пользователю"""
    queries = get_user_queries(user_id)
    if query not in queries:
        queries.append(query)
        return save_user_queries(user_id, queries)
    return False

def remove_user_query(user_id: int, query: str) -> bool:
    """Удаление запроса у пользователя"""
    queries = get_user_queries(user_id)
    if query in queries:
        queries.remove(query)
        return save_user_queries(user_id, queries)
    return False

def clear_user_queries(user_id: int) -> bool:
    """Очистка всех запросов пользователя"""
    subscriptions = load_subscriptions()
    user_key = str(user_id)
    
    if user_key in subscriptions:
        del subscriptions[user_key]
        
        try:
            with open(SUBSCRIPTIONS_FILE, 'w', encoding='utf-8') as f:
                json.dump(subscriptions, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"❌ Ошибка очистки запросов пользователя: {e}")
    
    return False

# ==================== Утилиты ====================

def save_json(data, filepath: Path):
    """Универсальное сохранение JSON"""
    filepath.parent.mkdir(exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_json(filepath: Path, default=None):
    """Универсальная загрузка JSON"""
    if default is None:
        default = {}
    
    try:
        if filepath.exists():
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
    except:
        pass
    
    return default