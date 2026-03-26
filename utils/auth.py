"""
Модуль аутентификации и авторизации пользователей.
Содержит функции для работы с пользователями, хранения и проверки учётных данных.
"""

import pandas as pd
import bcrypt
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple


def get_data_path() -> Path:
    """
    Возвращает абсолютный путь к папке data.
    """
    current_file = Path(__file__).resolve()
    project_root = current_file.parent.parent
    return project_root / "data"


def get_users_file_path() -> Path:
    """
    Возвращает путь к файлу пользователей.
    """
    return get_data_path() / "users.csv"


def load_users() -> pd.DataFrame:
    """
    Загружает данные о пользователях из CSV файла.

    Returns:
        pd.DataFrame: DataFrame с данными о пользователях или пустой DataFrame при ошибке.
    """
    try:
        users_file = get_users_file_path()

        if not users_file.exists():
            # Создаём пустой файл с заголовками
            df = pd.DataFrame(columns=['id', 'username', 'email', 'password_hash', 'full_name', 'created_at'])
            df.to_csv(users_file, index=False)
            return df

        df = pd.read_csv(users_file)
        return df

    except Exception as e:
        print(f"Ошибка загрузки пользователей: {e}")
        return pd.DataFrame()


def save_users(df: pd.DataFrame) -> bool:
    """
    Сохраняет данные о пользователях в CSV файл.

    Args:
        df: DataFrame с данными о пользователях

    Returns:
        bool: True если успешно, False иначе
    """
    try:
        users_file = get_users_file_path()
        df.to_csv(users_file, index=False)
        return True
    except Exception as e:
        print(f"Ошибка сохранения пользователей: {e}")
        return False


def hash_password(password: str) -> str:
    """
    Хеширует пароль используя bcrypt.

    Args:
        password: Пароль в открытом виде

    Returns:
        str: Хешированный пароль
    """
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def verify_password(password: str, password_hash: str) -> bool:
    """
    Проверяет соответствие пароля хешу.

    Args:
        password: Пароль в открытом виде
        password_hash: Хешированный пароль

    Returns:
        bool: True если пароль верный, False иначе
    """
    try:
        return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
    except Exception:
        return False


def authenticate_user(username: str, password: str) -> Tuple[bool, Optional[dict]]:
    """
    Аутентифицирует пользователя по логину и паролю.

    Args:
        username: Имя пользователя (логин)
        password: Пароль

    Returns:
        Tuple[bool, Optional[dict]]: (успех, данные пользователя или None)
    """
    users_df = load_users()

    if users_df.empty:
        return False, None

    # Ищем пользователя по username или email
    user = users_df[
        (users_df['username'] == username) | 
        (users_df['email'] == username)
    ]

    if user.empty:
        return False, None

    user_data = user.iloc[0]

    # Проверяем пароль
    if verify_password(password, user_data['password_hash']):
        return True, {
            'id': user_data['id'],
            'username': user_data['username'],
            'email': user_data['email'],
            'full_name': user_data['full_name'],
            'created_at': user_data['created_at']
        }

    return False, None


def register_user(username: str, email: str, password: str, full_name: str) -> Tuple[bool, str]:
    """
    Регистрирует нового пользователя.

    Args:
        username: Имя пользователя
        email: Email
        password: Пароль
        full_name: Полное имя

    Returns:
        Tuple[bool, str]: (успех, сообщение)
    """
    users_df = load_users()

    # Проверка на существующего пользователя
    if not users_df.empty:
        if username in users_df['username'].astype(str).values:
            return False, "Пользователь с таким именем уже существует"
        if email in users_df['email'].astype(str).values:
            return False, "Email уже зарегистрирован"

    # Генерируем новый ID
    new_id = int(users_df['id'].max()) + 1 if not users_df.empty and 'id' in users_df.columns else 1

    # Хешируем пароль
    password_hash = hash_password(password)

    # Создаём новую запись (преобразуем id в обычный int)
    new_user = pd.DataFrame([{
        'id': new_id,
        'username': username,
        'email': email,
        'password_hash': password_hash,
        'full_name': full_name,
        'created_at': datetime.now().strftime('%Y-%m-%d')
    }])

    # Добавляем и сохраняем
    if users_df.empty:
        users_df = new_user
    else:
        users_df = pd.concat([users_df, new_user], ignore_index=True)
    
    if save_users(users_df):
        return True, "Пользователь успешно зарегистрирован"
    else:
        return False, "Ошибка сохранения данных"


def get_user_by_id(user_id: int) -> Optional[dict]:
    """
    Получает данные пользователя по ID.

    Args:
        user_id: ID пользователя

    Returns:
        Optional[dict]: Данные пользователя или None
    """
    users_df = load_users()

    if users_df.empty:
        return None

    user = users_df[users_df['id'] == user_id]

    if user.empty:
        return None

    user_data = user.iloc[0]
    return {
        'id': user_data['id'],
        'username': user_data['username'],
        'email': user_data['email'],
        'full_name': user_data['full_name'],
        'created_at': user_data['created_at']
    }
