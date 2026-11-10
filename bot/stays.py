"""Fase 2: alloggi abbinati al volo.

Le API gratuite per i prezzi degli hotel non esistono più (Hotellook è stata chiusa
a ottobre 2025), quindi il bot crea link di ricerca già filtrati: stesse date del volo,
ordinati dal più economico, con un tetto di prezzo a notte.
Se in futuro ottieni un'API a pagamento o un programma affiliato, basta
aggiungere qui una funzione che restituisce i prezzi.
"""
from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import quote, urlencode

from .flights import Flight


@dataclass
class StayLinks:
    booking: str
    airbnb: str
    max_per_night: int
    nights: int

    @property
    def max_total(self) -> int:
        return self.max_per_night * self.nights


def build(flight: Flight, city: str, cfg: dict) -> StayLinks:
    s = cfg["stays"]
    checkin, checkout = flight.departure.isoformat(), flight.return_date.isoformat()
    booking = "https://www.booking.com/searchresults.it.html?" + urlencode({
        "ss": city,
        "checkin": checkin,
        "checkout": checkout,
        "group_adults": s["adults"],
        "no_rooms": 1,
        "order": "price",
        "nflt": f"price=EUR-min-{s['max_price_per_night']}-1",
    })
    airbnb = f"https://www.airbnb.it/s/{quote(city)}/homes?" + urlencode({
        "checkin": checkin,
        "checkout": checkout,
        "adults": s["adults"],
        "price_max": s["max_price_per_night"],
    })
    return StayLinks(booking, airbnb, s["max_price_per_night"], flight.nights)
