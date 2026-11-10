"""Pubblica su Instagram i post in coda (dopo che le immagini sono online su GitHub).

Uso:  python -m bot.publish
"""
from __future__ import annotations

from datetime import datetime, timedelta

from . import deals as dl
from . import instagram, settings, telegram


def _meta(db, key: str) -> str | None:
    row = db.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
    return row["value"] if row else None


def _set_meta(db, key: str, value: str) -> None:
    db.execute("INSERT OR REPLACE INTO meta VALUES (?,?)", (key, value))
    db.commit()


def maybe_refresh_token(db) -> None:
    last = _meta(db, "ig_token_refreshed")
    if last and dl.now() - datetime.fromisoformat(last) < timedelta(days=7):
        return
    try:
        new = instagram.refresh_token()
        _set_meta(db, "ig_token_refreshed", dl.now().isoformat())
        if new and new != settings.INSTAGRAM_TOKEN:
            telegram.send("🔑 Il token Instagram è stato rinnovato con un valore nuovo: "
                          "aggiornalo nei Secrets di GitHub (INSTAGRAM_TOKEN).\n\n"
                          f"<code>{new}</code>")
    except instagram.InstagramError as exc:
        telegram.send(f"⚠️ Rinnovo token Instagram fallito: {exc}")


def run() -> None:
    cfg = settings.load_config()
    ig = cfg["instagram"]
    db = dl.connect()
    if not ig["enabled"] or not settings.INSTAGRAM_TOKEN:
        print("Instagram non configurato: salto.")
        return
    if settings.DRY_RUN:
        rows = db.execute("SELECT * FROM posts WHERE status='pending'").fetchall()
        print(f"[prova] {len(rows)} post in coda, nessuna pubblicazione.")
        return

    maybe_refresh_token(db)

    day_ago = (dl.now() - timedelta(days=1)).isoformat()
    published_today = db.execute(
        "SELECT COUNT(*) c FROM posts WHERE status='published' AND published_at>=?", (day_ago,)
    ).fetchone()["c"]
    if published_today >= ig["max_posts_per_day"]:
        return
    last = db.execute("SELECT MAX(published_at) t FROM posts WHERE status='published'").fetchone()["t"]
    if last and dl.now() - datetime.fromisoformat(last) < timedelta(hours=ig["min_hours_between_posts"]):
        return

    # scarta i post di voli ormai partiti o troppo vecchi
    today = dl.now().date().isoformat()
    db.execute("UPDATE posts SET status='expired' WHERE status='pending' AND "
               "(departure<=? OR created_at<?)", (today, (dl.now() - timedelta(days=2)).isoformat()))
    db.commit()

    post = db.execute("SELECT * FROM posts WHERE status='pending' ORDER BY price ASC LIMIT 1").fetchone()
    if not post:
        return
    try:
        media_id = instagram.publish(instagram.public_url(post["image"]), post["caption"])
        db.execute("UPDATE posts SET status='published', published_at=? WHERE id=?",
                   (dl.now().isoformat(), post["id"]))
        telegram.send(f"📸 Pubblicato su Instagram: {post['route']} a {post['price']:.0f}€ (id {media_id})")
    except instagram.InstagramError as exc:
        db.execute("UPDATE posts SET status='error', error=? WHERE id=?", (str(exc), post["id"]))
        telegram.send(f"⚠️ Pubblicazione Instagram fallita ({post['route']}): {exc}")
    db.commit()


if __name__ == "__main__":
    run()
