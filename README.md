# harlocksp_updates

[![Test](https://github.com/Fanza-vibes/harlocksp_updates/actions/workflows/tests.yml/badge.svg)](https://github.com/Fanza-vibes/harlocksp_updates/actions/workflows/tests.yml)

Aggiornamenti del maestro **HarlockSP**: un bot Telegram che racconta le partite Dota 2 di
HarlockSP ([Dotabuff](https://www.dotabuff.com/players/295689331)) su un canale per gli amici.
Progetto per divertimento, senza scopo commerciale e a costo zero.

## Cosa fa

- 📣 **Una scheda per ogni partita**: vittoria o sconfitta, eroe, K/D/A, GPM/XPM, durata, modalità e
  link a Dotabuff e OpenDota. Le partite notevoli hanno la 🌟, le serie di vittorie e sconfitte
  vengono sottolineate.
- 🔍 **Curiosità della partita**: dopo qualche minuto arriva, in risposta alla scheda, un secondo
  messaggio con le chicche più notevoli: nemesi, vittima preferita, multi-kill, first blood,
  rimonte, confronti con gli altri giocatori dello stesso eroe.
- 📊 **Riepilogo della giornata** alle 23, nei giorni in cui ha giocato.
- 💬 **Comandi in chat privata** con il bot, per chiedere un riepilogo quando si vuole.
- 🖼 **Immagini e GIF** a scelta, allegate ai messaggi del canale (vittoria, sconfitta, serie di
  fila, giocate speciali, riepilogo): si caricano nelle cartelle di [`media/`](media/LEGGIMI.md).

Esempi:

```
🌟 ✅ IL MAESTRO HA VINTO! 🏆
🔥 3 vittorie di fila! Il maestro è inarrestabile!
👤 HarlockSP
🦸 Eroe: Anti-Mage (Dire)
⚔️ K/D/A: 14/0/12 (KDA 26.0)
💰 GPM/XPM: 742/810 · 🗡 LH: 388
⏱ Durata: 43:10 · 🎮 Classificata · All Pick
🛡 Partita perfetta: 0 morti!
```

```
🔴🔴🔴 IL MAESTRO HA PERSO ANCORA!
💀 3 SCONFITTE DI FILA! Qualcuno lo consoli…
```

## Per gli amici

1. Entrate nel canale **[t.me/harlocksp_updates](https://t.me/harlocksp_updates)**: si può solo leggere.
2. Per un riepilogo su richiesta aprite **@Harlocksp_updatesbot**, premete **Avvia** e scrivete:

| Comando | Risposta |
|---|---|
| `/ultima` | scheda dell'ultima partita |
| `/riepilogo oggi` | partite di oggi |
| `/riepilogo settimana` | ultimi 7 giorni |
| `/riepilogo mese` | ultimi 30 giorni |

Il bot non è sempre online: controlla partite e messaggi a intervalli di qualche minuto, quindi
schede e risposte possono arrivare con un po' di ritardo.

**Privacy**: il bot non salva chi gli scrive e nelle curiosità usa solo i nomi degli eroi, mai i
nickname degli altri giocatori né la chat di gioco.

## Come funziona

Il bot è un programma Python che, a intervalli regolari, legge i dati pubblici delle partite da
[OpenDota](https://www.opendota.com/), pubblica i messaggi su Telegram e si ricorda l'ultima partita
già pubblicata nel file `state.json`, salvato su un branch dedicato (`bot-state`) separato dal codice.
Non serve un server: gira gratuitamente su GitHub Actions.

## Sviluppo

Requisiti: Python 3.11 o successivo.

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt

python -m pytest                                  # test (nessuna chiamata di rete)
ruff check src tests && ruff format src tests     # lint e formattazione
mypy src                                          # controllo dei tipi

python -m src.main --dry-run --last 3                          # schede delle ultime 3 partite
python -m src.main --dry-run --comando "/riepilogo settimana"  # risposta a un comando
python -m src.main --dry-run --partita <match_id>              # curiosità di una partita
```

Con `--dry-run` i messaggi vengono solo stampati: nulla viene inviato o salvato.

Struttura del codice (`src/`):

| Modulo | Ruolo |
|---|---|
| `main.py` | un "giro" del bot e riga di comando |
| `stats.py`, `formatter.py`, `trivia.py` | calcoli e testi dei messaggi (funzioni pure) |
| `commands.py` | comandi in chat privata |
| `followup.py` | invio delle curiosità quando il replay è stato analizzato |
| `data.py` | recupero dei dati delle partite con cache |
| `media.py` | scelta e invio di immagini e GIF da `media/` |
| `opendota.py`, `telegram.py` | client delle API esterne |
| `state.py`, `config.py` | stato tra un giro e l'altro e configurazione |

Ogni modulo, classe e funzione pubblica è documentato da una docstring. Le opzioni del bot
(giocatore, nome, fuso orario, ora del riepilogo) sono in `config.yaml`. Ogni modifica passa da una
pull request, su cui girano automaticamente lint, controllo dei tipi e test.

## Licenza

[MIT](LICENSE)
