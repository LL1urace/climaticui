"""
Страница авторизации пользователей.
Lifecycle:
1. set_page_config
2. init session_state
3. load cookies
4. если залогинен → redirect в app
5. показать форму логина
"""

import streamlit as st
import sys
from pathlib import Path

# set_page_config должен быть ПЕРВЫМ вызовом Streamlit!
st.set_page_config(
    page_title="Вход в систему - ClimaticUI",
    page_icon="🔐",
    layout="centered"
)

# Добавляем корень проекта в sys.path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Импорты
from utils.auth import authenticate_user
from utils.auth_session import (
    init_session_state,
    check_and_restore_session,
    save_session,
    redirect_if_authenticated,
    render_navbar,
    load_css_styles
)

# 2. Инициализация session_state
init_session_state()

# 3. Восстановление сессии из cookies
check_and_restore_session()

# 4. Если уже авторизован - редирект
redirect_if_authenticated()

# 5. Загрузка стилей и навигации
load_css_styles()
render_navbar()

# Заголовок страницы
st.title("🔐 Вход в ClimaticUI")
st.markdown("**Система анализа климатических данных**")
st.markdown("---")

# Быстрый вход для тестового пользователя
st.subheader("⚡ Быстрый вход")
st.markdown("Нажмите для автоматического входа под тестовым пользователем:")

if st.button("👤 Войти как тестовый пользователь", use_container_width=True, help="admin / password123"):
    st.session_state._quick_login = ("admin", "password123")
    st.rerun()

# Обработка быстрого входа
if hasattr(st.session_state, "_quick_login") and st.session_state._quick_login:
    username, password = st.session_state._quick_login
    success, user_data = authenticate_user(username, password)
    
    if success and user_data:
        st.session_state.logged_in = True
        st.session_state.user = user_data
        save_session(user_data['id'], user_data['username'])
        st.success(f"✅ Успешный вход как {user_data['full_name']}!")
        del st.session_state._quick_login
        st.rerun()
    else:
        st.error("❌ Ошибка быстрого входа")
        del st.session_state._quick_login

st.markdown("---")
with st.form("login_form", clear_on_submit=False):
    username = st.text_input(
        "👤 Имя пользователя или Email",
        placeholder="Введите имя пользователя или email"
    )
    password = st.text_input(
        "🔑 Пароль",
        type="password",
        placeholder="Введите пароль"
    )

    submit_button = st.form_submit_button("Войти", use_container_width=True)

    if submit_button:
        if not username or not password:
            st.error("⚠️ Введите имя пользователя и пароль")
        else:
            success, user_data = authenticate_user(username, password)

            if success and user_data:
                # 6. После логина: устанавливаем state и сохраняем сессию
                st.session_state.logged_in = True
                st.session_state.user = user_data
                save_session(user_data['id'], user_data['username'])
                st.success("✅ Успешный вход!")
                # 7. Используем st.rerun() вместо st.switch_page()
                st.rerun()
            else:
                st.error("❌ Неверное имя пользователя или пароль")

# Ссылка на регистрацию
st.markdown("---")
st.markdown("**Нет аккаунта?** [Зарегистрироваться](Register)")

# Информация для тестовых пользователей
st.markdown("---")
st.markdown("### 📋 Тестовые учётные данные")

with st.expander("Показать все тестовые аккаунты"):
    st.markdown("""
    | Логин | Email | Пароль |
    |-------|-------|--------|
    | admin | admin@climatic.ui | password123 |
    | testuser | test@test.com | password123 |
    | meteorolog | meteorolog@climatic.ui | password123 |
    | analyst | analyst@climatic.ui | password123 |
    """)
