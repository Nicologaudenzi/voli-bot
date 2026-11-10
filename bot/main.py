"""Controllo ogni 30 minuti: voli → offerte → Telegram → coda post Instagram.

Uso:  python -m bot.main
"""
from __future__ import annotations

from datetime import timedelta

from . import deals as dl
from . import images, settings, stays, telegram
from .flights import city_name, fetch_cheapest

MAX_ALERTS_PER_RUN = 8


def caption(deal: dl.Deal, origin_name: str, dest_name: str, st: stays.StayLinks, cfg: dict) -> str:
    f = deal.flight
    sconto = f" (circa -{deal.discount:.0%} rispetto al solito)" if deal.typical_price else ""
    return (
        f"✈️ {origin_name} → {dest_name} a {f.price:.0f}€ andata e ritorno{sconto}\n\n"
        f"📅 {telegram.fmt_day(f.departure)} → {telegram.fmt_day(f.return_date)} · {f.nights} notti\n"
        f"🏨 Con alloggi sotto i {st.max_per_night}€/notte il viaggio resta low cost.\n\n"
        f"👉 Link per prenotare in bio. I prezzi trovati possono cambiare in poche ore.\n"
        f"Salva il post e tagga chi porteresti 👇\n\n"
        f"{cfg['instagram']['hashtags']} #{dest_name.replace(' ', '').lower()}"
    )


def queue_post(db, deal: dl.Deal, origin_name: str, dest_name: str, st, cfg: dict) -> None:
    ig = cfg["instagram"]
    if not ig["enabled"]:
        return
    good = deal.discount >= ig["min_discount_for_post"] or (
        deal.typical_price is None and deal.flight.price <= cfg["deals"]["fallback_max_price"] * 0.75)
    if not good:
        return
    f = deal.flight
    week_ago = (dl.now() - timedelta(days=7)).isoformat()
    if db.execute("SELECT 1 FROM posts WHERE route LIKE ? AND created_at>=?",
                  (f"%-{f.destination}", week_ago)).fetchone():
        return  # stessa destinazione già in coda/pubblicata questa settimana
    name = f"{dl.now():%Y%m%d-%H%M}-{f.origin}-{f.destination}.jpg"
    images.render(deal, origin_name, dest_name, settings.POSTS_DIR / name)
    db.execute(
        "INSERT INTO posts (route, departure, return_date, price, image, caption, created_at) "
        "VALUES (?,?,?,?,?,?,?)",
        (f.route, f.departure.isoformat(), f.return_date.isoformat(), f.price,
         f"posts/{name}", caption(deal, origin_name, dest_name, st, cfg), dl.now().isoformat()))
    db.commit()
    print(f"[instagram] in coda: {name}")


def run() -> None:
    cfg = settings.load_config()
    db = dl.connect()
    sent = 0
    for origin, origin_name in cfg["origins"].items():
        try:
            flights = fetch_cheapest(origin, cfg)
        except Exception as exc:
            print(f"[errore] voli da {origin}: {exc}")
            continue
        found = dl.find_deals(db, flights, cfg)   # confronta PRIMA di salvare i prezzi di oggi
        dl.record(db, flights)
        print(f"{origin_name}: {len(flights)} voli, {len(found)} offerte")
        for deal in found:
            if sent >= MAX_ALERTS_PER_RUN or not dl.is_new(db, deal, cfg):
                continue
            dest_name = city_name(deal.flight.destination)
            st = stays.build(deal.flight, dest_name, cfg)
            telegram.send(telegram.deal_message(deal, st, origin_name))
            dl.mark_sent(db, deal)
            queue_post(db, deal, origin_name, dest_name, st, cfg)
            sent += 1
    print(f"Fatto: {sent} avvisi inviati.")


if __name__ == "__main__":
    run()
