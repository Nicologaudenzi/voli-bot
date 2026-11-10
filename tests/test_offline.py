"""Prova completa senza internet: simula 10 giorni di prezzi e un crollo di prezzo.

Uso:  python -m tests.test_offline
"""
import os
import sqlite3
import tempfile
from datetime import date, timedelta
from pathlib import Path

os.environ["DRY_RUN"] = "1"

from bot import deals as dl, main, settings  # noqa: E402
from bot import flights as fl  # noqa: E402

tmp = Path(tempfile.mkdtemp())
settings.DATA_DIR = tmp
settings.DB_PATH = tmp / "prices.db"
settings.POSTS_DIR = tmp / "posts"
fl._names["cities"] = {"LIS": {"name": "Lisbona"}, "BCN": {"name": "Barcellona"}}
fl._names["airlines"] = {"FR": {"name": "Ryanair"}, "TP": {"name": "TAP Air Portugal"}}

dep = date.today() + timedelta(days=40)
ret = dep + timedelta(days=4)


def item(dest, price, airline="FR"):
    return {"origin": "MIL", "destination": dest, "origin_airport": "BGY", "destination_airport": dest,
            "price": price, "airline": airline, "departure_at": f"{dep}T07:00:00+01:00",
            "return_at": f"{ret}T20:00:00+01:00", "transfers": 0, "return_transfers": 0,
            "link": f"/search/MIL{dep:%d%m}{dest}{ret:%d%m}1?t=test"}


# 1) storico: 10 giorni con Lisbona ~120€ e Barcellona ~70€
db = dl.connect()
month = dep.strftime("%Y-%m")
for i in range(1, 11):
    day = (date.today() - timedelta(days=i)).isoformat()
    db.execute("INSERT INTO prices VALUES (?,?,?,?,?)", ("MIL-LIS", month, day, 115 + i, day))
    db.execute("INSERT INTO prices VALUES (?,?,?,?,?)", ("MIL-BCN", month, day, 68 + i % 3, day))
db.commit()

# 2) oggi Lisbona crolla a 39€, Barcellona resta normale
fake = fl.parse_items([item("LIS", 39, "TP"), item("BCN", 69)])
main.fetch_cheapest = lambda origin, cfg: fake if origin == "MIL" else []
main.run()

posts = sqlite3.connect(settings.DB_PATH).execute("SELECT route, price, image FROM posts").fetchall()
alerts = sqlite3.connect(settings.DB_PATH).execute("SELECT route, price FROM alerts").fetchall()
print("Avvisi:", alerts)
print("Post in coda:", posts)
assert alerts == [("MIL-LIS", 39.0)], "deve segnalare solo Lisbona"
assert len(posts) == 1 and (settings.POSTS_DIR / Path(posts[0][2]).name).exists()

# 3) secondo giro: la stessa offerta NON deve essere rimandata
main.run()
assert len(sqlite3.connect(settings.DB_PATH).execute("SELECT * FROM alerts").fetchall()) == 1
print("\nOK: tutti i controlli superati. Immagine di prova:", settings.POSTS_DIR)
