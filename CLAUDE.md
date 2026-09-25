# CLAUDE.md

Bot Telegram che pubblica le partite Dota 2 di HarlockSP (account 295689331).
Costo zero: GitHub Actions (cron ogni 15 min) + API OpenDota senza chiave.

## Architettura

```
check.yml (cron) → python -m src.main
  main.py      orchestrazione: carica stato → recentMatches → nuove partite → invio → salva stato
  opendota.py  client HTTP con timeout e retry/backoff (429/5xx/rete) → OpenDotaError
  telegram.py  sendMessage HTML, gestione 429 (retry_after) → TelegramError; DryRunSender
  formatter.py funzioni pure per il testo (HTML con escape)
  state.py     state.json: last_match_id, cache eroi; lettura tollerante, scrittura atomica
  config.py    config.yaml + TELEGRAM_TOKEN / TELEGRAM_CHAT_ID da env
```

Regole di comportamento:
- Stato assente o corrotto → primo avvio: salva l'ultima partita e **non invia nulla**.
- Nuove partite = `match_id > last_match_id`, inviate in ordine di `start_time`.
- Lo stato si salva dopo **ogni** invio riuscito, così un errore a metà non genera doppioni.
- Errore OpenDota → log ed exit 0, stato invariato. Errore Telegram → exit 1 (workflow rosso,
  l'owner riceve una mail); il progresso già fatto viene comunque committato (`if: always()`).
- Radiant = `player_slot < 128`; vittoria = `radiant_win == is_radiant`.

## Comandi

```bash
pip install -r requirements-dev.txt
python -m pytest -q                        # test, nessuna chiamata di rete
python -m src.main --dry-run --last 3      # stampa, non invia, non scrive state.json
```

## Convenzioni

- Python 3.12 nel CI (il codice resta compatibile con 3.11), type hints, funzioni piccole.
- Dipendenze minime: solo `requests` e `PyYAML` a runtime; `pytest` e `responses` per i test.
- I test non fanno rete: usano `responses` oppure i fake in `tests/test_main.py`; `sleep` è iniettabile.
- **Mai** loggare il token né l'URL di Telegram (contiene il token): nelle eccezioni usare `from None`.
- `state.json` ha un formato deterministico (chiavi ordinate) così il workflow committa solo se cambia.
- Testi utente, log e commit in italiano; un commit per ogni step logico.
- Roadmap: Fase 2 (modalità in italiano, partite notevoli, streak), Fase 3 (riepiloghi),
  Fase 4 (keep-alive, cache eroi settimanale, più giocatori).
