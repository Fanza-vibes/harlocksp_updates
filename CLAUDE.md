# CLAUDE.md

Bot Telegram che pubblica le partite Dota 2 di HarlockSP (account 295689331).
Costo zero: GitHub Actions (cron ogni 5 min, il minimo di GitHub) + API OpenDota senza chiave.

## Architettura

```
check.yml (cron 5 min) → python -m src.main — un giro:
  1. recentMatches (UNA chiamata) → nuove partite nel canale
  2. getUpdates → risposte ai comandi in chat privata
  3. dopo daily_summary_hour (Europe/Rome) → riepilogo del giorno nel canale

  main.py      orchestrazione del giro, CLI (--dry-run, --last, --comando)
  data.py      MatchData: dati OpenDota del giro con cache; usa le recenti se bastano,
               altrimenti /players/{id}/matches?date=N; cache eroi aggiornata ogni 7 giorni
  commands.py  parsing comandi, risposte, limite per chat, menu setMyCommands
  stats.py     funzioni pure: vittoria, KDA, streak, summarize, finestre temporali
  formatter.py funzioni pure per il testo (HTML con escape), nomi modalità in italiano
  opendota.py  client HTTP con timeout e retry/backoff (429/5xx/rete) → OpenDotaError
  telegram.py  sendMessage/getUpdates/setMyCommands, gestione 429 → TelegramError; DryRunSender
  state.py     state.json: last_match_id, cache eroi, telegram_offset, last_summary_date,
               commands_version; lettura tollerante, scrittura atomica
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
- Comandi: solo chat private, max 3 risposte per chat per giro; l'offset avanza anche per i messaggi
  ignorati; se OpenDota è giù l'offset NON avanza (i comandi si evadono al giro dopo).
- Riepilogo giornaliero: finestra [ora X del giorno prima, ora X), partite classificate per ora di
  **fine**; recupera anche se il cron slitta dopo mezzanotte; niente messaggio se non ha giocato.
- **Privacy**: il repo e i log di Actions sono pubblici → mai salvare o loggare chat ID, nomi o testi
  degli utenti (solo conteggi).

## Comandi

```bash
pip install -r requirements-dev.txt
python -m pytest -q                        # test, nessuna chiamata di rete
python -m src.main --dry-run --last 3      # stampa, non invia, non scrive state.json
python -m src.main --dry-run --comando "/riepilogo oggi"   # prova un comando
```

## Convenzioni

- Python 3.12 nel CI (il codice resta compatibile con 3.11), type hints, funzioni piccole.
- Dipendenze minime: solo `requests`, `PyYAML` e `tzdata` a runtime; `pytest` e `responses` per i test.
- I test non fanno rete: usano `responses` oppure i fake in `tests/test_main.py`; `sleep` è iniettabile.
- **Mai** loggare il token né l'URL di Telegram (contiene il token): nelle eccezioni usare `from None`.
- `state.json` ha un formato deterministico (chiavi ordinate) così il workflow committa solo se cambia.
- Testi utente, log e commit in italiano; un commit per ogni step logico.
- Progetto per divertimento, non commerciale: preferire soluzioni semplici a costo zero.
- Roadmap: Fase 4 (keep-alive contro la disattivazione dei cron dopo 60 giorni, più giocatori).
