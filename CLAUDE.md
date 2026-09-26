# CLAUDE.md

Bot Telegram che pubblica le partite Dota 2 di HarlockSP (account 295689331).
Costo zero: GitHub Actions (cron ogni 5 min, il minimo di GitHub) + API OpenDota senza chiave.

## Architettura

```
check.yml (cron 5 min) → python -m src.main — un giro:
  1. recentMatches (UNA chiamata) → nuove partite nel canale (+ in coda per le curiosità)
  2. partite in coda: /matches/{id}; se non analizzata → POST /request/{id} (una volta);
     se analizzata → curiosità in risposta alla scheda; max 3 per giro, rinuncia dopo 3 ore
  3. getUpdates → risposte ai comandi in chat privata
  4. dopo daily_summary_hour (Europe/Rome) → riepilogo del giorno nel canale

  main.py      orchestrazione del giro, CLI (--dry-run, --last, --comando, --partita)
  followup.py  coda delle curiosità (state.pending_trivia): richiesta analisi, invio in risposta
  trivia.py    funzioni pure: curiosità con punteggio da una partita analizzata, top 5
  data.py      MatchData: dati OpenDota del giro con cache; usa le recenti se bastano,
               altrimenti /players/{id}/matches?date=N; cache eroi aggiornata ogni 7 giorni
  commands.py  parsing comandi, risposte, limite per chat, menu setMyCommands
  stats.py     funzioni pure: vittoria, KDA, streak, summarize, finestre temporali
  formatter.py funzioni pure per il testo (HTML con escape), nomi modalità in italiano
  opendota.py  client HTTP con timeout e retry/backoff (429/5xx/rete) → OpenDotaError
  telegram.py  sendMessage/getUpdates/setMyCommands, gestione 429 → TelegramError; DryRunSender
  state.py     state.json: last_match_id, cache eroi, telegram_offset, last_summary_date,
               commands_version, pending_trivia; lettura tollerante, scrittura atomica
  config.py    config.yaml + TELEGRAM_TOKEN / TELEGRAM_CHAT_ID da env
```

Regole di comportamento:
- Stato assente o corrotto → primo avvio: salva l'ultima partita e **non invia nulla**.
- Nuove partite = `match_id > last_match_id`, inviate in ordine di `start_time`.
- Lo stato si salva dopo **ogni** invio riuscito, così un errore a metà non genera doppioni.
- Errore OpenDota → log ed exit 0, stato invariato. Errore Telegram → exit 1 (workflow rosso,
  l'owner riceve una mail); il progresso già fatto viene comunque committato (`if: always()`).
- Radiant = `player_slot < 128`; vittoria = `radiant_win == is_radiant`.
- Streak calcolata dalle ultime 20 partite (nessuno stato da mantenere).
- Titolo: "IL MAESTRO HA VINTO!" / "IL MAESTRO HA PERSO!" (🔴 ripetuto per le sconfitte di fila, max 5);
  riga della serie subito sotto il titolo (formatter.streak_lines).
- Comandi: solo chat private, max 3 risposte per chat per giro; l'offset avanza anche per i messaggi
  ignorati; se OpenDota è giù l'offset NON avanza (i comandi si evadono al giro dopo).
- Riepilogo giornaliero: finestra [ora X del giorno prima, ora X), partite classificate per ora di
  **fine**; recupera anche se il cron slitta dopo mezzanotte; niente messaggio se non ha giocato.
- Curiosità: campi OpenDota verificati su odota/core (svc/api/responses/MatchResponse.ts); partita
  analizzata ⇔ `version` non nullo; campo mancante = curiosità saltata, mai un errore. Solo nomi di
  eroi (killed_by/killed usano chiavi "npc_dota_hero_*"), mai nickname o chat. Fixture in
  tests/fixtures_match.py.
- **Privacy**: il repo e i log di Actions sono pubblici → mai salvare o loggare chat ID, nomi o testi
  degli utenti (solo conteggi).

## Comandi

```bash
pip install -r requirements-dev.txt
python -m pytest                           # test, nessuna chiamata di rete
ruff check src tests && ruff format src tests   # lint + formattazione (config in pyproject.toml)
python -m src.main --dry-run --last 3      # stampa, non invia, non scrive state.json
python -m src.main --dry-run --comando "/riepilogo oggi"   # prova un comando
python -m src.main --dry-run --partita <match_id>           # curiosità di una partita vera
```

## Convenzioni

- Python 3.12 nel CI (il codice resta compatibile con 3.11), type hints, funzioni piccole.
- Stile: ruff (lint + format) controllato nel CI; tipi verificabili con `mypy src`.
- GitHub Actions alla major più recente (Node 24); Dependabot propone gli aggiornamenti ogni mese.
- Dipendenze minime: solo `requests`, `PyYAML` e `tzdata` a runtime; `pytest`, `responses` e `ruff` per sviluppo e test.
- I test non fanno rete: usano `responses` oppure i fake in `tests/test_main.py`; `sleep` è iniettabile.
- **Mai** loggare il token né l'URL di Telegram (contiene il token): nelle eccezioni usare `from None`.
- `state.json` ha un formato deterministico (ordine fisso dei campi, eroi in ordine numerico) così il
  workflow committa solo se cambia; `save_state` non riscrive il file se il contenuto è identico.
- Testi utente, log e commit in italiano; un commit per ogni step logico.
- Progetto per divertimento, non commerciale: preferire soluzioni semplici a costo zero.
- Roadmap: Fase 4 (keep-alive contro la disattivazione dei cron dopo 60 giorni, più giocatori).
