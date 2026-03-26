"""
Страница профиля пользователя.
"""

import streamlit as st
import sys
from pathlib import Path

# set_page_config должен быть ПЕРВЫМ вызовом Streamlit!
st.set_page_config(
    page_title="Профиль - ClimaticUI",
    page_icon="👤",
    layout="centered"
)

# Добавляем корень проекта в sys.path для корректного импорта
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from utils.auth import get_user_by_id, verify_password, hash_password, load_users, save_users
from utils.auth_session import (
    init_session_state,
    check_and_restore_session,
    require_auth,
    render_navbar,
    load_css_styles
)
import pandas as pd

# 2. Инициализация session_state
init_session_state()

# 3. Восстановление сессии из cookies
check_and_restore_session()

# 5. Защита страницы - если не авторизован, редирект на login
require_auth()

# 4. Загрузка стилей и навигации
load_css_styles()
render_navbar()


def profile_page():
    """
    Страница профиля пользователя.
    """
    user = st.session_state.user

    # Заголовок страницы
    st.title("👤 Профиль пользователя")
    st.markdown("---")

    # Информация о пользователе
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 📋 Информация об аккаунте")
        st.info(f"""
        **ID:** {user['id']}  
        **Имя пользователя:** {user['username']}  
        **Email:** {user['email']}  
        **Полное имя:** {user['full_name']}  
        **Дата регистрации:** {user['created_at']}
        """)

    with col2:
        st.markdown("### 📊 Статистика")
        st.metric("Дней в системе", "0")  # Можно расширить позже
        st.metric("Последний вход", "Сегодня")

    st.markdown("---")

    # Смена пароля
    st.subheader("🔑 Смена пароля")

    with st.form("change_password_form"):
        current_password = st.text_input(
            "Текущий пароль",
            type="password"
        )
        new_password = st.text_input(
            "Новый пароль",
            type="password"
        )
        confirm_password = st.text_input(
            "Подтвердите новый пароль",
            type="password"
        )

        submit_password = st.form_submit_button("Изменить пароль", use_container_width=True)

        if submit_password:
            if not current_password or not new_password or not confirm_password:
                st.error("❌ Заполните все поля")
            elif len(new_password) < 6:
                st.error("❌ Новый пароль должен быть не менее 6 символов")
            elif new_password != confirm_password:
                st.error("❌ Пароли не совпадают")
            else:
                # Проверяем текущий пароль
                users_df = load_users()
                current_user = users_df[users_df['id'] == user['id']]
                
                if not current_user.empty:
                    stored_hash = current_user.iloc[0]['password_hash']
                    
                    if verify_password(current_password, stored_hash):
                        # Хешируем новый пароль
                        new_hash = hash_password(new_password)
                        
                        # Обновляем в DataFrame
                        users_df.loc[users_df['id'] == user['id'], 'password_hash'] = new_hash
                        
                        if save_users(users_df):
                            st.success("✅ Пароль успешно изменён")
                            st.rerun()
                        else:
                            st.error("❌ Ошибка сохранения")
                    else:
                        st.error("❌ Неверный текущий пароль")

    st.markdown("---")

    # Кнопка выхода
    if st.button("🚪 Выйти из аккаунта", use_container_width=True, type="secondary"):
        st.session_state.logged_in = False
        st.session_state.user = None
        st.rerun()


if __name__ == "__main__":
    profile_page()
