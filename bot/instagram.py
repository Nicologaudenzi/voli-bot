"""Fase 3: pubblicazione automatica su Instagram (API ufficiale di Meta).

Serve un account Instagram Professionale (Business o Creator) e un token
"Instagram API with Instagram Login" con il permesso instagram_business_content_publish.
L'immagine deve essere su un indirizzo pubblico: il bot usa il repository GitHub pubblico.
"""
from __future__ import annotations

import time

import requests

from . import settings

GRAPH = "https://graph.instagram.com/v23.0"


class InstagramError(Exception):
    pass


def public_url(image_rel_path: str) -> str:
    return (f"https://raw.githubusercontent.com/{settings.GITHUB_REPOSITORY}/"
            f"{settings.GITHUB_BRANCH}/{image_rel_path}")


def _call(method: str, path: str, **params) -> dict:
    params["access_token"] = settings.INSTAGRAM_TOKEN
    r = requests.request(method, f"{GRAPH}/{path}", params=params, timeout=60)
    data = r.json() if r.content else {}
    if not r.ok or "error" in data:
        raise InstagramError(str(data.get("error", r.text))[:300])
    return data


def publish(image_url: str, caption: str) -> str:
    """Crea il contenitore, aspetta che Instagram scarichi l'immagine, pubblica."""
    container = _call("POST", f"{settings.INSTAGRAM_USER_ID}/media",
                      image_url=image_url, caption=caption)["id"]
    for _ in range(12):
        status = _call("GET", container, fields="status_code").get("status_code")
        if status == "FINISHED":
            break
        if status == "ERROR":
            raise InstagramError("Instagram non è riuscito a leggere l'immagine")
        time.sleep(5)
    return _call("POST", f"{settings.INSTAGRAM_USER_ID}/media_publish", creation_id=container)["id"]


def refresh_token() -> str | None:
    """Rinnova il token di lunga durata (scade dopo 60 giorni se non rinnovato)."""
    r = requests.get("https://graph.instagram.com/refresh_access_token", timeout=30, params={
        "grant_type": "ig_refresh_token", "access_token": settings.INSTAGRAM_TOKEN})
    if not r.ok:
        raise InstagramError(r.text[:300])
    return r.json().get("access_token")
