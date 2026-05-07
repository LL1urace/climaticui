"""Auth endpoints."""

from __future__ import annotations

from klimatika_frontend.api import get_api_client


def register(email: str, password: str, full_name: str) -> dict:
    return get_api_client().post("/auth/register", json={"email": email, "password": password, "full_name": full_name})


def login(email: str, password: str) -> dict:
    return get_api_client().post("/auth/login", json={"email": email, "password": password})


def get_current_user() -> dict:
    return get_api_client().get("/users/me")

