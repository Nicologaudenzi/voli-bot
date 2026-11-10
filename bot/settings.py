"""Carica config.yaml e le chiavi segrete dalle variabili d'ambiente."""
import os
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
POSTS_DIR = ROOT / "posts"
DB_PATH = DATA_DIR / "prices.db"


def load_config() -> dict:
    with open(ROOT / "config.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _load_dotenv() -> None:
    """Legge un file .env locale (solo per prove sul tuo PC)."""
    env_file = ROOT / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"'))


_load_dotenv()


def env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


TRAVELPAYOUTS_TOKEN = env("TRAVELPAYOUTS_TOKEN")
TRAVELPAYOUTS_MARKER = env("TRAVELPAYOUTS_MARKER")
TELEGRAM_BOT_TOKEN = env("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = env("TELEGRAM_CHAT_ID")
INSTAGRAM_TOKEN = env("INSTAGRAM_TOKEN")
INSTAGRAM_USER_ID = env("INSTAGRAM_USER_ID")
# es. "tuonome/voli-bot": serve per l'indirizzo pubblico delle immagini
GITHUB_REPOSITORY = env("GITHUB_REPOSITORY")
GITHUB_BRANCH = env("GITHUB_BRANCH", "main")
DRY_RUN = env("DRY_RUN", "0") == "1"
