"""Fase 1: legge i prezzi dei voli dall'API gratuita Travelpayouts/Aviasales."""
from __future__ import annotations

import json
import time
from dataclasses import dataclass
from datetime import date, datetime
from urllib.parse import quote

import requests

from . import settings

API = "https://api.travelpayouts.com"
SESSION = requests.Session()
SESSION.headers.update({"Accept-Encoding": "gzip, deflate", "User-Agent": "voli-bot/1.0"})


@dataclass
class Flight:
    origin: str
    destination: str
    origin_airport: str
    destination_airport: str
    price: float
    airline: str
    departure: date
    return_date: date
    transfers: int
    link: str

    @property
    def nights(self) -> int:
        return (self.return_date - self.departure).days

    @property
    def route(self) -> str:
        return f"{self.origin}-{self.destination}"


def _get(path: str, params: dict) -> dict:
    headers = {"X-Access-Token": settings.TRAVELPAYOUTS_TOKEN.strip()}
    for attempt in range(3):
        r = SESSION.get(API + path, params=params, headers=headers, timeout=30)
        if r.status_code == 429:          # troppe richieste: aspetta e riprova
            time.sleep(5 * (attempt + 1))
            continue
        r.raise_for_status()
        return r.json()
    r.raise_for_status()
    return {}


def _months(n: int) -> list[str]:
    today = date.today()
    out = []
    y, m = today.year, today.month
    for _ in range(n):
        out.append(f"{y:04d}-{m:02d}")
        m += 1
        if m > 12:
            y, m = y + 1, 1
    return out


def _parse_day(value: str) -> date:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).date()


def affiliate_link(link: str) -> str:
    """Trasforma il link Aviasales in link affiliato (commissione su ogni prenotazione)."""
    url = "https://www.aviasales.com" + (link if link.startswith("/") else "/search/" + link)
    if settings.TRAVELPAYOUTS_MARKER:
        sep = "&" if "?" in url else "?"
        url += f"{sep}marker={quote(settings.TRAVELPAYOUTS_MARKER)}"
    return url


def parse_items(items: list[dict]) -> list[Flight]:
    flights = []
    for it in items:
        if not it.get("return_at"):
            continue
        try:
            flights.append(Flight(
                origin=it["origin"],
                destination=it["destination"],
                origin_airport=it.get("origin_airport", it["origin"]),
                destination_airport=it.get("destination_airport", it["destination"]),
                price=float(it["price"]),
                airline=it.get("airline", ""),
                departure=_parse_day(it["departure_at"]),
                return_date=_parse_day(it["return_at"]),
                transfers=max(int(it.get("transfers", 0)), int(it.get("return_transfers", 0))),
                link=affiliate_link(it.get("link", "")),
            ))
        except (KeyError, ValueError):
            continue
    return flights


def fetch_cheapest(origin: str, cfg: dict) -> list[Flight]:
    """Per ogni mese: il volo A/R più economico verso OGNI destinazione da `origin`."""
    results: list[Flight] = []
    for month in _months(cfg["months_ahead"]):
        data = _get("/aviasales/v3/prices_for_dates", {
            "origin": origin,
            "departure_at": month,
            "one_way": "false",
            "unique": "true",
            "sorting": "price",
            "currency": cfg["currency"],
            "market": cfg["market"],
            "limit": 1000,
        })
        results.extend(parse_items(data.get("data") or []))
        time.sleep(0.3)
    trip = cfg["trip"]
    return [
        f for f in results
        if trip["min_nights"] <= f.nights <= trip["max_nights"]
        and f.transfers <= trip["max_transfers"]
        and f.departure >= date.today()
    ]


# ---- Nomi delle città e compagnie (in italiano, salvati in cache) ----
_names: dict[str, dict] = {}


def _load_names(kind: str) -> dict:
    if kind in _names:
        return _names[kind]
    cache = settings.DATA_DIR / f"{kind}.json"
    if cache.exists():
        _names[kind] = json.loads(cache.read_text(encoding="utf-8"))
        return _names[kind]
    mapping = {}
    try:
        r = SESSION.get(f"{API}/data/it/{kind}.json", timeout=60)
        r.raise_for_status()
        for row in r.json():
            if row.get("code"):
                mapping[row["code"]] = {"name": row.get("name") or row["code"],
                                        "country": row.get("country_code", "")}
        settings.DATA_DIR.mkdir(exist_ok=True)
        cache.write_text(json.dumps(mapping, ensure_ascii=False), encoding="utf-8")
    except Exception as exc:   # se fallisce si usano i codici IATA
        print(f"[avviso] nomi {kind} non scaricati: {exc}")
    _names[kind] = mapping
    return mapping


def city_name(code: str) -> str:
    return _load_names("cities").get(code, {}).get("name", code)


def airline_name(code: str) -> str:
    return _load_names("airlines").get(code, {}).get("name", code)
