"""Frío dashboard — local, read-only, password-protected web server.

Serves the same page produced by `dashboard_render.render_html` (which the static
Netlify export also uses). READ-ONLY by design — no endpoints spend money or
launch/publish. Binds to 127.0.0.1 (local) by default.
"""

from __future__ import annotations

import secrets

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from .config import Config
from .dashboard_render import render_html

_security = HTTPBasic()


def create_app(config: Config) -> FastAPI:
    app = FastAPI(title="Frío Dashboard")

    def auth(creds: HTTPBasicCredentials = Depends(_security)) -> None:
        user_ok = secrets.compare_digest(creds.username, config.dashboard_user)
        pw_ok = bool(config.dashboard_password) and secrets.compare_digest(
            creds.password, config.dashboard_password or "")
        if not (user_ok and pw_ok):
            raise HTTPException(status_code=401, detail="Unauthorized",
                                headers={"WWW-Authenticate": "Basic"})

    @app.get("/", response_class=HTMLResponse)
    def home(_=Depends(auth)) -> str:
        return render_html(config)

    @app.get("/healthz")
    def healthz() -> dict:  # unauthenticated liveness check only
        return {"ok": True}

    return app
