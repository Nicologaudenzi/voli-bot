# Voli Sottoprezzo – bot

Ogni 30 minuti controlla i voli A/R da **Milano, Roma, Napoli e Bari**, riconosce quelli molto sotto il prezzo tipico, ti avvisa su **Telegram** con i link agli alloggi abbinati (**Booking** e **Airbnb**, stesse date, filtrati per prezzo) e pubblica le offerte migliori su **Instagram** in automatico. Costo: 0 €.

```
GitHub Actions (ogni 30 min, gratis)
   │
   ├─ bot.main     → API Travelpayouts → storico prezzi (SQLite) → offerte
   │                 → Telegram (volo + link alloggi) → grafica JPEG in coda
   ├─ git push     → immagini online su raw.githubusercontent.com
   └─ bot.publish  → Instagram (max 3 post al giorno, ogni 4 ore)
```

| File | Cosa fa |
|---|---|
| `config.yaml` | Città, mesi, soglie di sconto, notti, tetto €/notte, limiti Instagram |
| `bot/flights.py` | Fase 1 – prezzi voli (API gratuita Travelpayouts/Aviasales) |
| `bot/deals.py` | Fase 1 – storico prezzi e riconoscimento offerte |
| `bot/stays.py` | Fase 2 – link Booking/Airbnb filtrati sulle date del volo |
| `bot/telegram.py` | Messaggi Telegram |
| `bot/images.py` | Fase 3 – grafica 1080×1350 per Instagram |
| `bot/instagram.py`, `bot/publish.py` | Fase 3 – pubblicazione automatica e rinnovo token |
| `.github/workflows/bot.yml` | Esecuzione ogni 30 minuti |
| `tests/test_offline.py` | Prova completa senza internet |

## Configurazione passo passo (circa 1 ora)

### 1. Travelpayouts (dati voli + guadagno sugli acquisti)
1. Registrati su travelpayouts.com e unisciti al programma **Aviasales**.
2. Da *Profilo → API token* copia il **token** → `TRAVELPAYOUTS_TOKEN`.
3. Copia il tuo **marker** (ID partner) → `TRAVELPAYOUTS_MARKER`. Serve per ricevere le commissioni sui voli prenotati dai tuoi link.

### 2. Bot Telegram
1. Su Telegram scrivi a **@BotFather** → `/newbot` → copia il token → `TELEGRAM_BOT_TOKEN`.
2. Scrivi un messaggio qualsiasi al tuo bot, poi apri `https://api.telegram.org/bot<TOKEN>/getUpdates` e copia `chat.id` → `TELEGRAM_CHAT_ID`.
3. Facoltativo: crea un **canale pubblico**, aggiungi il bot come amministratore e usa l'ID del canale (`@nomecanale`): così le offerte arrivano anche ai follower.

### 3. Instagram (pubblicazione automatica)
1. Crea la pagina Instagram e trasformala in **account professionale** (Impostazioni → Tipo di account → Creator o Business).
2. Su developers.facebook.com crea un'app di tipo **Business**, aggiungi il prodotto **Instagram** → *API setup with Instagram login*.
3. Aggiungi il tuo account Instagram, concedi `instagram_business_basic` e `instagram_business_content_publish`, premi **Generate token**.
4. Copia il token → `INSTAGRAM_TOKEN` e l'ID dell'account → `INSTAGRAM_USER_ID`.
5. Il bot rinnova il token ogni settimana; se Meta ne genera uno nuovo te lo manda su Telegram da aggiornare nei Secrets.

### 4. GitHub (il "server" gratuito)
1. Crea un repository **pubblico** (es. `voli-bot`) e caricaci tutti i file di questa cartella (tranne `.env`).
   Deve essere pubblico: così l'esecuzione è gratuita senza limiti di minuti e Instagram può scaricare le immagini.
2. *Settings → Secrets and variables → Actions → New repository secret*: aggiungi le 6 chiavi qui sopra.
3. *Actions* → abilita i workflow → apri **Voli sottoprezzo** → **Run workflow** per la prima prova.

Da quel momento parte da solo ogni 30 minuti. I token restano segreti anche se il repository è pubblico.

## I primi giorni
Il bot impara il prezzo tipico di ogni tratta. Nei primi **7 giorni** segnala solo i voli sotto **60 € A/R** (`fallback_max_price`); dopo usa lo sconto rispetto alla mediana (`discount: 0.35` = 35%). Su Instagram vanno solo le offerte con almeno il 40% di sconto.

## Prova sul tuo PC
```bash
pip install -r requirements.txt
python -m tests.test_offline        # prova completa con dati simulati
cp .env.example .env                # inserisci TRAVELPAYOUTS_TOKEN, lascia DRY_RUN=1
python -m bot.main                  # dati veri, stampa a schermo senza inviare
```

## Note
- I prezzi arrivano dalla cache delle ricerche fatte dagli utenti Aviasales nelle ultime 48 ore: sono reali ma vanno verificati al momento della prenotazione (il link apre la ricerca aggiornata).
- GitHub può ritardare di qualche minuto le esecuzioni programmate, e le disattiva dopo 60 giorni senza attività nel repository: qui non succede perché il bot salva i dati a ogni giro.
- Instagram accetta solo immagini JPEG e i link nelle didascalie non sono cliccabili: metti nella bio il link al canale Telegram o a una pagina di link.
