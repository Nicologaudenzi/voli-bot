"""Fase 1: storico prezzi (SQLite) e riconoscimento delle offerte sottoprezzo."""
from __future__ import annotations

import sqlite3
import statistics
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from . import settings
from .flights import Flight

SCHEMA = """
CREATE TABLE IF NOT EXISTS prices (
    route TEXT, month TEXT, day TEXT, price REAL, seen_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_prices ON prices(route, month, day);
CREATE TABLE IF NOT EXISTS alerts (
    route TEXT, departure TEXT, return_date TEXT, price REAL, sent_at TEXT
);
CREATE TABLE IF NOT EXISTS posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    route TEXT, departure TEXT, return_date TEXT, price REAL,
    image TEXT, caption TEXT, status TEXT DEFAULT 'pending',
    created_at TEXT, published_at TEXT, error TEXT
);
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT);
"""


def now() -> datetime:
    return datetime.now(timezone.utc)


def connect() -> sqlite3.Connection:
    settings.DATA_DIR.mkdir(exist_ok=True)
    db = sqlite3.connect(settings.DB_PATH)
    db.row_factory = sqlite3.Row
    db.executescript(SCHEMA)
    return db


@dataclass
class Deal:
    flight: Flight
    typical_price: float | None   # None = ancora senza storico
    discount: float               # 0.45 = 45% sotto il prezzo tipico

    @property
    def saving(self) -> float:
        return (self.typical_price or self.flight.price) - self.flight.price


def record(db: sqlite3.Connection, flights: list[Flight]) -> None:
    ts = now()
    db.executemany(
        "INSERT INTO prices VALUES (?,?,?,?,?)",
        [(f.route, f.departure.strftime("%Y-%m"), ts.date().isoformat(), f.price, ts.isoformat())
         for f in flights],
    )
    # pulizia: tiene solo gli ultimi 120 giorni
    db.execute("DELETE FROM prices WHERE seen_at < ?", ((ts - timedelta(days=120)).isoformat(),))
    db.commit()


def typical_price(db: sqlite3.Connection, route: str, month: str, cfg: dict) -> float | None:
    """Mediana dei minimi giornalieri (giorni precedenti a oggi) per tratta e mese."""
    since = (now() - timedelta(days=cfg["deals"]["history_window_days"])).date().isoformat()
    today = now().date().isoformat()
    rows = db.execute(
        "SELECT day, MIN(price) p FROM prices WHERE route=? AND month=? AND day>=? AND day<? GROUP BY day",
        (route, month, since, today),
    ).fetchall()
    if len(rows) < cfg["deals"]["min_history_days"]:
        return None
    return statistics.median(r["p"] for r in rows)


def find_deals(db: sqlite3.Connection, flights: list[Flight], cfg: dict) -> list[Deal]:
    d = cfg["deals"]
    deals = []
    for f in flights:
        if f.price > d["hard_max_price"]:
            continue
        typ = typical_price(db, f.route, f.departure.strftime("%Y-%m"), cfg)
        if typ:
            disc = 1 - f.price / typ
            if disc >= d["discount"]:
                deals.append(Deal(f, typ, disc))
        elif f.price <= d["fallback_max_price"]:
            deals.append(Deal(f, None, 0.0))
    deals.sort(key=lambda x: (-x.discount, x.flight.price))
    return deals


def is_new(db: sqlite3.Connection, deal: Deal, cfg: dict) -> bool:
    """Evita di mandare due volte la stessa offerta (a meno che il prezzo scenda)."""
    f = deal.flight
    since = (now() - timedelta(hours=cfg["deals"]["renotify_after_hours"])).isoformat()
    row = db.execute(
        "SELECT MIN(price) p FROM alerts WHERE route=? AND departure=? AND return_date=? AND sent_at>=?",
        (f.route, f.departure.isoformat(), f.return_date.isoformat(), since),
    ).fetchone()
    return row["p"] is None or f.price < row["p"]


def mark_sent(db: sqlite3.Connection, deal: Deal) -> None:
    f = deal.flight
    db.execute("INSERT INTO alerts VALUES (?,?,?,?,?)",
               (f.route, f.departure.isoformat(), f.return_date.isoformat(), f.price, now().isoformat()))
    db.commit()
