"""Flask extension for the Lockally email API.

    from flask import Flask
    from lockally_flask import Lockally

    app = Flask(__name__)
    app.config["LOCKALLY_API_KEY"] = "lk_live_..."   # lk_test_... runs in sandbox
    lockally = Lockally(app)

    @app.post("/signup")
    def signup():
        lockally.send_email(
            from_="alerts@yourdomain.com",
            to="user@example.com",
            subject="Welcome",
            html="<b>Hi!</b>",
        )
        return "", 202

Follows the Flask extension pattern: `Lockally(app)` or `Lockally()` + `init_app(app)`.
The client is stored at `app.extensions["lockally"]`; the module-level `send_email`
proxy uses the current app so blueprints can send without holding a reference.
"""

from __future__ import annotations

from typing import Any

from flask import current_app

from lockally_flask.client import LockallyClient

__version__ = "0.1.0"
__all__ = ["Lockally", "LockallyClient", "send_email"]


class Lockally:
    def __init__(self, app: Any = None, *, api_key: str | None = None,
                 base_url: str | None = None) -> None:
        self._api_key = api_key
        self._base_url = base_url
        if app is not None:
            self.init_app(app)

    def init_app(self, app: Any) -> None:
        api_key = self._api_key or app.config.get("LOCKALLY_API_KEY")
        base_url = self._base_url or app.config.get("LOCKALLY_BASE_URL")
        client = LockallyClient(api_key=api_key, base_url=base_url)
        app.extensions = getattr(app, "extensions", {})
        app.extensions["lockally"] = client

    def send_email(self, **kwargs: Any) -> Any:
        return _client_for(None).send_email(**kwargs)


def _client_for(app: Any) -> LockallyClient:
    target = app or current_app
    try:
        return target.extensions["lockally"]
    except (AttributeError, KeyError):
        raise RuntimeError(
            "Lockally is not initialised on this app — call Lockally(app) or "
            "lockally.init_app(app) first."
        )


def send_email(**kwargs: Any) -> Any:
    """Send via the Lockally client registered on the current Flask app."""
    return _client_for(None).send_email(**kwargs)
