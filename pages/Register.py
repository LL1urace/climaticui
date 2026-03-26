"""
Страница регистрации новых пользователей.
Lifecycle:
1. set_page_config
2. init session_state
3. load cookies
4. если залогинен → redirect в app
5. показать форму регистрации
"""

import streamlit as st
import sys
from pathlib import Path

# set_page_config должен быть ПЕРВЫМ вызовом Streamlit!
st.set_page_config(
    page_title="Регистрация - ClimaticUI",
    page_icon="📝",
    layout="centered"
)

# Добавляем корень проекта в sys.path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Импорты
from utils.auth import register_user, authenticate_user
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
st.title("📝 Регистрация в ClimaticUI")
st.markdown("**Создайте новый аккаунт**")
st.markdown("---")

# Форма регистрации
with st.form("register_form", clear_on_submit=True):
    col1, col2 = st.columns(2)

    with col1:
        username = st.text_input(
            "👤 Имя пользователя *",
            placeholder="Придумайте логин",
            help="Логин должен быть уникальным"
        )
        full_name = st.text_input(
            "📛 Полное имя *",
            placeholder="Иван Иванов"
        )

    with col2:
        email = st.text_input(
            "📧 Email *",
            placeholder="example@email.com"
        )
        password = st.text_input(
            "🔑 Пароль *",
            type="password",
            placeholder="Придумайте пароль"
        )

    password_confirm = st.text_input(
        "🔑 Подтверждение пароля *",
        type="password",
        placeholder="Повторите пароль"
    )

    submit_button = st.form_submit_button("Зарегистрироваться", use_container_width=True)

    if submit_button:
        # Валидация полей
        errors = []

        if not username:
            errors.append("Введите имя пользователя")
        elif len(username) < 3:
            errors.append("Имя пользователя должно быть не менее 3 символов")

        if not email:
            errors.append("Введите email")
        elif "@" not in email or "." not in email:
            errors.append("Введите корректный email")

        if not full_name:
            errors.append("Введите полное имя")

        if not password:
            errors.append("Введите пароль")
        elif len(password) < 6:
            errors.append("Пароль должен быть не менее 6 символов")

        if password != password_confirm:
            errors.append("Пароли не совпадают")

        if errors:
            for error in errors:
                st.error(f"❌ {error}")
        else:
            # Попытка регистрации
            success, message = register_user(username, email, password, full_name)

            if success:
                st.success(f"✅ {message}")
                st.info("Теперь вы можете войти в систему")
                
                # Автоматическая авторизация
                auth_success, user_data = authenticate_user(username, password)
                if auth_success and user_data:
                    st.session_state.logged_in = True
                    st.session_state.user = user_data
                    save_session(user_data['id'], user_data['username'])
                    st.balloons()
                    st.rerun()
            else:
                st.error(f"❌ {message}")

# Ссылка на вход
st.markdown("---")
st.markdown("**Уже есть аккаунт?** [Войти](0_Login)")
