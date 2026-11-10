"""Invio dei messaggi su Telegram."""
from __future__ import annotations

import html

import requests

from . import settings
from .deals import Deal
from .flights import airline_name, city_name
from .stays import StayLinks

MESI = ["gen", "feb", "mar", "apr", "mag", "giu", "lug", "ago", "set", "ott", "nov", "dic"]


def fmt_day(d) -> str:
    return f"{d.day} {MESI[d.month - 1]}"


def send(text: str, photo_path: str | None = None) -> None:
    if settings.DRY_RUN or not settings.TELEGRAM_BOT_TOKEN:
        print("---- [Telegram, prova] ----\n" + text + "\n")
        return
    base = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}"
    if photo_path:
        with open(photo_path, "rb") as img:
            r = requests.post(f"{base}/sendPhoto", timeout=60, files={"photo": img}, data={
                "chat_id": settings.TELEGRAM_CHAT_ID, "caption": text[:1024], "parse_mode": "HTML"})
    else:
        r = requests.post(f"{base}/sendMessage", timeout=30, json={
            "chat_id": settings.TELEGRAM_CHAT_ID, "text": text,
            "parse_mode": "HTML", "disable_web_page_preview": True})
    if not r.ok:
        print(f"[errore Telegram] {r.status_code} {r.text[:200]}")


def deal_message(deal: Deal, stays: StayLinks, origin_name: str) -> str:
    f = deal.flight
    dest = html.escape(city_name(f.destination))
    scali = "diretto" if f.transfers == 0 else f"{f.transfers} scalo"
    if deal.typical_price:
        prezzo = (f"💰 <b>{f.price:.0f}€ A/R</b> invece di ~{deal.typical_price:.0f}€ "
                  f"(<b>-{deal.discount:.0%}</b>)")
    else:
        prezzo = f"💰 <b>{f.price:.0f}€ A/R</b> (prezzo molto basso)"
    return (
        f"✈️ <b>{html.escape(origin_name)} → {dest}</b>\n"
        f"{prezzo}\n"
        f"📅 {fmt_day(f.departure)} → {fmt_day(f.return_date)} · {f.nights} notti · {scali}\n"
        f"🛫 {html.escape(airline_name(f.airline))} · {f.origin_airport}→{f.destination_airport}\n"
        f"<a href=\"{html.escape(f.link)}\">Prenota il volo</a>\n\n"
        f"🏨 Alloggi fino a {stays.max_per_night}€/notte (max {stays.max_total}€ totali):\n"
        f"<a href=\"{html.escape(stays.booking)}\">Booking</a> · "
        f"<a href=\"{html.escape(stays.airbnb)}\">Airbnb</a>"
    )
