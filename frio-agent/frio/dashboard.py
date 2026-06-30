"""Frío dashboard — private, login-protected web app (IntoSpirit).

A real session login (signed cookie), not an HTTP-Basic popup. Confidential by
default: every data route requires an authenticated session; unauthenticated
requests are redirected to the login page. READ-ONLY — no endpoint spends money or
launches/publishes. Runs as a real server (Render + Postgres) or locally.

Roadmap: this is the single-tenant (IntoSpirit) version; it's structured so the
auth layer can grow into multi-tenant client logins (each client sees only their
own Frío Agent data) without reworking the rest.
"""

from __future__ import annotations

import secrets

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette.middleware.sessions import SessionMiddleware

from .config import Config
from .dashboard_render import render_html

_LOGIN_CSS = """
body{font-family:system-ui,Arial,sans-serif;background:#0f1115;color:#e6e6e6;
display:flex;min-height:100vh;align-items:center;justify-content:center;margin:0}
.box{background:#161a22;border:1px solid #262b36;border-radius:14px;padding:32px;width:320px}
h1{font-size:20px;margin:0 0 4px}.sub{color:#9aa4b2;font-size:13px;margin:0 0 18px}
input{width:100%;box-sizing:border-box;padding:11px;border-radius:8px;border:1px solid #2a2f3a;
background:#0f1115;color:#e6e6e6;font-size:14px;margin-bottom:12px}
button{width:100%;padding:11px;border:0;border-radius:8px;background:#6d5dfc;color:#fff;
font-size:14px;font-weight:600;cursor:pointer}.err{color:#ff6b6b;font-size:13px;margin:0 0 12px}
"""


def _login_html(brand: str, error: str = "") -> str:
    err = f"<p class=err>{error}</p>" if error else ""
    return (f"<!doctype html><html><head><meta charset=utf-8>"
            f"<meta name=viewport content='width=device-width,initial-scale=1'>"
            f"<title>{brand} · Frío</title><style>{_LOGIN_CSS}</style></head><body>"
            f"<div class=box><h1>🧊 Frío · {brand}</h1>"
            f"<p class=sub>Panel privado — acceso restringido</p>{err}"
            f"<form method=post action='/login'>"
            f"<input type=password name=password placeholder='Contraseña' autofocus required>"
            f"<button>Entrar</button></form></div></body></html>")


def create_app(config: Config) -> FastAPI:
    app = FastAPI(title="Frío Dashboard")
    secret = config.dashboard_session_secret or secrets.token_hex(32)
    app.add_middleware(SessionMiddleware, secret_key=secret, same_site="lax",
                       https_only=config.dashboard_secure_cookies)

    def authed(request: Request) -> bool:
        return request.session.get("auth") is True

    @app.get("/login", response_class=HTMLResponse)
    def login_page() -> str:
        return _login_html(config.dashboard_brand)

    @app.post("/login")
    def login(request: Request, password: str = Form(...)):
        ok = bool(config.dashboard_password) and secrets.compare_digest(
            password, config.dashboard_password or "")
        if not ok:
            return HTMLResponse(_login_html(config.dashboard_brand, "Contraseña incorrecta"),
                                status_code=401)
        request.session["auth"] = True
        return RedirectResponse("/", status_code=303)

    @app.get("/logout")
    def logout(request: Request):
        request.session.clear()
        return RedirectResponse("/login", status_code=303)

    @app.get("/", response_class=HTMLResponse)
    def home(request: Request):
        if not authed(request):
            return RedirectResponse("/login", status_code=303)
        return HTMLResponse(render_html(config)
                            + "<div style='padding:0 24px 24px'>"
                              "<a href='/logout' style='color:#9aa4b2'>Cerrar sesión</a></div>")

    @app.get("/healthz")
    def healthz() -> dict:  # unauthenticated liveness check only
        return {"ok": True}

    return app
