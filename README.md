# harlocksp_updates

[![Test](https://github.com/Fanza-vibes/harlocksp_updates/actions/workflows/tests.yml/badge.svg)](https://github.com/Fanza-vibes/harlocksp_updates/actions/workflows/tests.yml)

Aggiornamenti del maestro HarlockSP: un bot che pubblica su un canale Telegram un messaggio
per ogni nuova partita Dota 2 di **HarlockSP**
([Dotabuff](https://www.dotabuff.com/players/295689331) · account ID `295689331`).

**Costo zero**: gira su GitHub Actions ogni 5 minuti e usa l'API gratuita di
[OpenDota](https://docs.opendota.com/). Non serve nessun server.

Cosa fa:
- 📣 **nel canale**: un messaggio per ogni nuova partita (con 🌟 per le partite notevoli e le serie
  di vittorie/sconfitte) e, alle 23, il **riepilogo della giornata** se HarlockSP ha giocato;
- 🔍 **curiosità**: quando OpenDota ha analizzato il replay (di solito 5-30 minuti dopo), arriva in
  risposta alla scheda un secondo messaggio con le chicche della partita: nemesi, vittima preferita,
  multi-kill e rampage, serie di kill, first blood, rimonte o throw, confronti con gli altri giocatori
  dello stesso eroe, % dei danni della squadra, tempo passato da morto (al massimo 5, le più notevoli);
- 💬 **in chat privata con il bot**: chiunque può chiedere `/ultima` o `/riepilogo oggi|settimana|mese`.

Esempio di messaggio:

```
🌟 ✅ IL MAESTRO HA VINTO! 🏆
🔥 3 vittorie di fila! Il maestro è inarrestabile!
👤 HarlockSP
🦸 Eroe: Anti-Mage (Dire)
⚔️ K/D/A: 14/0/12 (KDA 26.0)
💰 GPM/XPM: 742/810 · 🗡 LH: 388
⏱ Durata: 43:10 · 🎮 Classificata · All Pick
🛡 Partita perfetta: 0 morti!
🔗 Dotabuff · OpenDota
```

Quando perde, i pallini rossi crescono con le sconfitte di fila (fino a 5) e la serie viene
sottolineata subito sotto il titolo:

```
🔴🔴🔴 IL MAESTRO HA PERSO ANCORA!
💀 3 SCONFITTE DI FILA! Qualcuno lo consoli…
```

Da 2 sconfitte di fila c'è un avviso, a 3 "Qualcuno lo consoli…", a 4 "Il maestro è in crisi!",
da 5 in su "Allarme rosso". La vittoria che interrompe almeno 3 sconfitte diventa
"💪 Maledizione spezzata".

**Indice**: [Per gli amici](#per-gli-amici) · [Setup passo passo](#setup-passo-passo) ·
[Configurazione](#configurazione) · [Per sviluppatori](#per-sviluppatori) ·
[Risoluzione problemi](#risoluzione-problemi)

## Per gli amici

1. Entrate nel canale **[t.me/harlocksp_updates](https://t.me/harlocksp_updates)**: si può solo leggere.
2. Volete un riepilogo? Aprite **@Harlocksp_updatesbot**, premete **Avvia** e scrivete un comando:

| Comando | Risposta |
|---|---|
| `/ultima` | scheda dell'ultima partita |
| `/riepilogo oggi` | partite di oggi |
| `/riepilogo settimana` | ultimi 7 giorni |
| `/riepilogo mese` | ultimi 30 giorni |

⏳ Il bot non ha un server sempre acceso: legge i messaggi a ogni giro (circa ogni 5-10 minuti),
quindi la risposta può arrivare con qualche minuto di ritardo.

Nelle curiosità compaiono solo i nomi degli eroi, mai i nickname degli altri giocatori né la chat.

Privacy: il bot non salva chi gli scrive (nessun ID o nome nel repository) e i log pubblici
di GitHub riportano solo quante risposte sono state inviate. Risponde a massimo 3 comandi
per persona per giro.

---

## Setup passo passo

### 1. Crea il bot con @BotFather

1. Apri Telegram e cerca **@BotFather** (quello ufficiale, con la spunta blu).
2. Scrivi `/newbot`.
3. Scegli il **nome visualizzato**, per esempio `HarlockSP Updates`.
4. Scegli lo **username**. Deve finire con `bot`, per esempio `harlocksp_updates_bot`.
5. BotFather risponde con il **token**, simile a `1234567890:AAH...`.
   Copialo e **non condividerlo con nessuno**: chi ha il token controlla il bot.
   Se ti sfugge, lo rigeneri con `/revoke` in BotFather.

### 2. Crea il canale e aggiungi il bot come amministratore

1. In Telegram: **Nuovo canale**. Può essere pubblico o privato.
2. Apri il canale → nome in alto → **Amministratori** → **Aggiungi amministratore**.
3. Cerca lo username del bot (`@harlocksp_updates_bot`) e aggiungilo.
4. Il solo permesso che serve è **Pubblica messaggi**. Tutti gli altri puoi toglierli.

### 3. Trova il `TELEGRAM_CHAT_ID`

- **Canale pubblico**: il chat ID è semplicemente `@nomecanale`, per esempio `@harlocksp_updates`.
- **Canale privato**: serve l'ID numerico, che inizia con `-100`. Per ottenerlo:
  1. pubblica un messaggio qualsiasi nel canale;
  2. apri nel browser `https://api.telegram.org/bot<TOKEN>/getUpdates`, sostituendo `<TOKEN>` con il tuo token;
  3. cerca `"channel_post"` → `"chat"` → `"id"`, per esempio `-1001234567890`. Quello è il chat ID.

  Se la risposta è `{"ok":true,"result":[]}`, pubblica un altro messaggio nel canale e ricarica la pagina.

### 4. Configura i Secrets su GitHub

Nel repository vai in **Settings → Secrets and variables → Actions → New repository secret** e crea:

| Nome               | Valore                                   |
|--------------------|------------------------------------------|
| `TELEGRAM_TOKEN`   | il token di BotFather                    |
| `TELEGRAM_CHAT_ID` | `@nomecanale` oppure `-100…`             |

I Secrets non sono mai visibili nei log. Non scriverli mai in un file del repository.

### 5. Abilita GitHub Actions

1. In **Settings → Actions → General**:
   - *Actions permissions*: **Allow all actions and reusable workflows**;
   - *Workflow permissions*: **Read and write permissions**. Serve al bot per salvare `state.json`.
2. Il workflow pianificato parte **solo dal branch predefinito** (`main`): il codice deve essere su `main`.
3. Tieni il repository **pubblico**: per i repository pubblici i minuti di Actions sono gratuiti e illimitati.
   Su un repository privato un controllo ogni 5 minuti supererebbe di molto i 2000 minuti gratuiti al mese.

### 6. Primo avvio manuale

1. Vai in **Actions → Controllo partite → Run workflow**.
2. Al primo avvio il bot **non invia nulla**: salva soltanto l'ultima partita in `state.json` (vedrai
   un commit `Aggiorna state.json`). Così il canale non viene inondato con lo storico.
3. Da lì in poi ogni nuova partita genera un messaggio, di solito entro 5-15 minuti dalla fine.

> Da dove viene il ritardo: il bot controlla ogni 5 minuti, ma GitHub avvia spesso i giri con
> qualche minuto di ritardo (a volte di più nelle ore di punta) e OpenDota può metterci qualche
> minuto a registrare una partita appena finita. Di solito il messaggio arriva 5-15 minuti dopo
> la fine della partita.

**Per provare subito un invio vero**: modifica `state.json` mettendo un `last_match_id` più basso
dell'ultima partita (per esempio l'ID della penultima partita su Dotabuff), fai commit e lancia di nuovo il workflow.

---

## Configurazione

`config.yaml`:

| Chiave         | Significato                         |
|----------------|-------------------------------------|
| `player_id`    | account ID Dota 2 (quello di Dotabuff/OpenDota) |
| `display_name` | nome mostrato nei messaggi          |
| `timezone`     | fuso orario dei riepiloghi (default `Europe/Rome`; il cron di GitHub è in UTC, la conversione la fa il codice) |
| `daily_summary_hour` | ora del riepilogo giornaliero nel canale (default `23`; `null` per disattivarlo) |

### Consigliato in BotFather (facoltativo)

- **Bot Settings → Allow Groups? → Turn off**: nessuno può aggiungere il bot ai gruppi
  (il canale continua a funzionare).
- **Edit Bot → Edit Description**: il testo che gli amici vedono prima di premere Avvia, per esempio
  *"Aggiornamenti Dota 2 di HarlockSP. Scrivi /riepilogo settimana"*.

Il menu dei comandi (il tasto "/" nella chat) viene impostato automaticamente dal bot.

## Per sviluppatori

Questa sezione spiega come è fatto il codice, per chi vuole modificarlo o contribuire.
Le regole di dettaglio per Claude Code sono in [`CLAUDE.md`](CLAUDE.md).

### Idea di fondo

Non c'è nessun server: il bot è un **programma che fa un "giro" e termina**. GitHub Actions
(workflow `check.yml`) lo avvia periodicamente; tutto ciò che deve ricordare tra un giro e l'altro
sta in `state.json`, che il workflow committa nel repository quando cambia.

```
 GitHub Actions (ogni ~5 min)
          │
          ▼
 python -m src.main ──► legge config.yaml + segreti (env) + state.json
          │
          ├─ 1. OpenDota /recentMatches ──► partite nuove? ──► scheda nel canale ──► in coda per le curiosità
          ├─ 2. coda curiosità ──► replay analizzato? ──► curiosità in risposta alla scheda
          ├─ 3. Telegram getUpdates ──► comandi in privato ──► risposte
          └─ 4. dopo le 23 ──► riepilogo della giornata nel canale
          │
          ▼
 salva state.json ──► il workflow fa commit + push (solo se è cambiato)
```

### Struttura del repository

```
src/
├── main.py        orchestrazione di un giro + riga di comando (--dry-run, --last, --comando, --partita)
├── config.py      Config: config.yaml + segreti da variabili d'ambiente
├── state.py       State/Pending: lettura tollerante e scrittura atomica di state.json
├── opendota.py    client HTTP OpenDota (timeout, retry con backoff) → OpenDotaError
├── telegram.py    client Bot API Telegram (gestione 429, token mai nei log) → TelegramError; DryRunSender
├── data.py        MatchData: dati OpenDota di un giro con cache + cache dei nomi degli eroi
├── stats.py       funzioni pure: vittoria, KDA, serie, riepiloghi, finestre temporali
├── formatter.py   funzioni pure: testo HTML delle schede e dei riepiloghi
├── trivia.py      funzioni pure: curiosità di una partita analizzata, con punteggio
├── followup.py    coda delle curiosità: richiesta di analisi a OpenDota e invio in risposta
└── commands.py    comandi in chat privata (/ultima, /riepilogo, /aiuto) e menu dei comandi
tests/             pytest, nessuna chiamata di rete (un file di test per modulo)
config.yaml        opzioni (giocatore, nome, fuso orario, ora del riepilogo)
state.json         memoria del bot tra un giro e l'altro (scritta dal workflow)
.github/workflows/ check.yml (il bot), tests.yml (lint + test su main e PR)
```

I moduli sono a **strati**, e le dipendenze vanno solo verso il basso:

| Strato | Moduli | Regola |
|---|---|---|
| Orchestrazione | `main`, `commands`, `followup` | decidono *cosa* fare in un giro |
| Dati | `data` | recupera e mette in cache i dati di un giro |
| Funzioni pure | `stats`, `formatter`, `trivia` | niente rete né file: input → output, facilissime da testare |
| Input/output | `opendota`, `telegram`, `state`, `config` | parlano con il mondo esterno e trasformano gli errori in eccezioni del progetto |

I client esterni sono passati come parametri e descritti da `Protocol` (`OpenDotaAPI`, `TriviaAPI`,
`Sender`, `Bot`): nei test si sostituiscono con oggetti finti, senza librerie di mocking.

### `state.json`

| Campo | Significato |
|---|---|
| `last_match_id` | ultima partita già pubblicata; le nuove sono quelle con ID maggiore |
| `heroes`, `heroes_updated_at` | cache `{id: nome}` degli eroi, aggiornata ogni 7 giorni o se manca un eroe |
| `pending_trivia` | partite pubblicate in attesa delle curiosità (ID partita, ID messaggio, orario, analisi già chiesta) |
| `telegram_offset` | prossimo messaggio da leggere con `getUpdates` (così nessun comando viene letto due volte) |
| `last_summary_date` | giorno dell'ultimo riepilogo giornaliero |
| `commands_version` | versione del menu comandi già inviata a Telegram |

Il file è pubblico come tutto il repository: **non deve mai contenere dati personali** (chat ID,
nomi, testi degli utenti). Se è mancante o corrotto il bot riparte come al primo avvio, senza inviare
lo storico. Viene riscritto solo se il contenuto cambia, con un formato fisso (diff piccoli).

### API esterne usate

| Chiamata | Quando | Note |
|---|---|---|
| OpenDota `GET /players/{id}/recentMatches` | ogni giro | ultime 20 partite: l'unica chiamata sempre presente |
| OpenDota `GET /players/{id}/matches?date=N` | `/riepilogo settimana\|mese`, riepiloghi | solo se le 20 recenti non bastano |
| OpenDota `GET /matches/{id}` | coda curiosità | analizzata se il campo `version` non è nullo |
| OpenDota `POST /request/{id}` | coda curiosità | chiede l'analisi del replay, una volta per partita (vale 10 chiamate nel limite) |
| OpenDota `GET /heroes` | al massimo una volta per giro | nomi degli eroi |
| Telegram `sendMessage` | schede, curiosità, riepiloghi, risposte | HTML; `reply_parameters` per le curiosità |
| Telegram `getUpdates` | ogni giro | polling breve (`timeout=0`), solo `message` |
| Telegram `setMyCommands` | una volta (per versione) | menu "/" della chat con il bot |

Limiti gratuiti di OpenDota senza chiave: circa 60 chiamate al minuto e 2000 al giorno. Con un giro
ogni 5 minuti il bot ne usa circa 300 al giorno.

### Gestione degli errori

| Errore | Comportamento |
|---|---|
| OpenDota non risponde all'inizio del giro | log, exit 0, stato invariato: si riprova al giro dopo |
| OpenDota non risponde per curiosità o riepiloghi | quella parte viene rimandata, il resto del giro continua |
| Telegram rifiuta la scheda di una partita | exit 1 (workflow rosso, mail al proprietario); il progresso fatto è salvato |
| Telegram rifiuta una risposta privata (es. bot bloccato) | ignorato, non si ritenta |
| `state.json` corrotto | trattato come primo avvio |

Il workflow salva e committa `state.json` anche se il giro fallisce (`if: always()`), e il passo del
bot ha un timeout di 6 minuti, così un blocco non fa perdere il salvataggio.

### Prova in locale

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt

python -m pytest                                  # test (nessuna chiamata di rete)
ruff check src tests && ruff format src tests     # lint e formattazione, come nel CI
mypy src                                          # controllo dei tipi, come nel CI

python -m src.main --dry-run --last 3                          # schede delle ultime 3 partite
python -m src.main --dry-run --comando "/riepilogo settimana"  # risposta a un comando
python -m src.main --dry-run --partita 9015942434              # curiosità di una partita
```

`--dry-run` stampa i messaggi invece di inviarli, **non modifica** `state.json`, non tocca la coda
delle curiosità e non richiede i segreti. Per un invio reale dal tuo PC:

```bash
export TELEGRAM_TOKEN="..." TELEGRAM_CHAT_ID="@nomecanale"
python -m src.main
```

### Test

- Un file di test per modulo (`tests/test_<modulo>.py`); nessun test fa chiamate di rete.
- HTTP simulato con [`responses`](https://github.com/getsentry/responses) nei test dei client;
  negli altri, oggetti finti che implementano i `Protocol`.
- `tests/conftest.py`: `make_match()` costruisce una partita "recente" con valori di default.
- `tests/fixtures_match.py`: una partita **analizzata** con i campi reali dello schema OpenDota,
  per le curiosità.
- Il tempo è sempre passato come parametro (`now=...`), e `sleep` è iniettabile: i test sono
  deterministici e veloci (tutta la suite gira in meno di un secondo).

### Come fare…

**Aggiungere un comando** (es. `/eroi`):
1. in `src/commands.py` aggiungi il ramo in `reply_for()` e una funzione `_eroi(...)` che
   restituisce il testo;
2. aggiungilo a `BOT_COMMANDS` e incrementa `COMMANDS_VERSION` (così il menu "/" si aggiorna da solo);
3. aggiorna `help_text()` e la tabella dei comandi in questo README;
4. aggiungi i test in `tests/test_commands.py`.

**Aggiungere una curiosità**:
1. in `src/trivia.py` scrivi una funzione privata (es. `_nome(match, player, ...) -> Fact | None`)
   che restituisce `None` se il dato manca o non è notevole (mai eccezioni);
2. scegli il punteggio rispetto alle altre (vedi l'ordine indicativo in cima al file) e aggiungila
   alla lista in `facts()`;
3. verifica il nome del campo sullo schema di OpenDota
   ([`MatchResponse.ts`](https://github.com/odota/core/blob/master/svc/api/responses/MatchResponse.ts))
   e aggiungilo a `tests/fixtures_match.py`, con i test in `tests/test_trivia.py`.

**Cambiare testi, emoji o soglie**: sono tutti in `src/formatter.py` (schede, serie, riepiloghi),
`src/trivia.py` (curiosità) e `src/commands.py` (risposte ai comandi), con le soglie come costanti in
maiuscolo in cima ai file. Dopo la modifica aggiorna i test che controllano quei testi.

**Aggiungere un campo a `state.json`**: aggiungilo a `State` e a `State.to_dict()` in
`src/state.py`, validalo in `_parse()` (un valore non valido deve diventare `None`, mai un errore)
e aggiungi un test di andata e ritorno in `tests/test_state.py`.

### Convenzioni

- Python 3.12 nel CI (compatibile 3.11), type hints ovunque, funzioni piccole.
- Ogni modulo, classe e funzione pubblica ha una docstring (controllato da ruff).
- Testi per gli utenti, log, docstring e messaggi di commit **in italiano**.
- Dipendenze minime: a runtime solo `requests`, `PyYAML` e `tzdata`.
- **Sicurezza**: il token Telegram non deve mai finire in log, eccezioni o `repr` (l'URL della Bot API
  lo contiene: per questo gli errori di rete vengono rilanciati con `from None`).
- **Privacy**: repository e log di Actions sono pubblici: si loggano solo conteggi, mai chat ID,
  nomi o testi degli utenti; nelle curiosità solo nomi di eroi.
- Ogni modifica passa da una pull request: il workflow `tests.yml` esegue ruff, mypy e pytest.

## Risoluzione problemi

| Sintomo nel log di Actions                   | Causa probabile |
|----------------------------------------------|-----------------|
| `Variabili d'ambiente mancanti`              | Secrets non creati o con nome sbagliato |
| `HTTP 401 – Unauthorized`                    | token errato o revocato |
| `HTTP 400 – Bad Request: chat not found`     | chat ID errato oppure bot non aggiunto al canale |
| `HTTP 403 – … not enough rights`             | il bot non è amministratore con permesso di pubblicare |
| `OpenDota …: HTTP 5xx dopo 4 tentativi`      | OpenDota temporaneamente giù: si ritenta da solo al giro dopo |
| push rifiutato (`403`) nello step "Salva state.json" | *Workflow permissions* non impostato su "Read and write" |
| il bot non risponde ai comandi               | aspetta il giro successivo (di solito 5-15 min); in Actions controlla che ci siano avvii "schedule" verdi |
| pochi avvii "schedule" (anche ore di buco)   | il cron di GitHub è "best effort" e salta molti giri sui repository poco attivi: la soluzione è una sveglia esterna (es. cron-job.org) che avvia il workflow |
| in Actions ci sono solo avvii manuali, nessuno "schedule" | su un repository nuovo GitHub può impiegare qualche ora ad attivare il cron: nel frattempo usa Run workflow |
| `getUpdates … 409 Conflict`                  | al bot è collegato un webhook o un altro programma che legge i messaggi: va rimosso |
| le curiosità di una partita non arrivano     | OpenDota non è riuscito ad analizzare il replay (capita): dopo 3 ore il bot rinuncia |
| il workflow non parte più da solo            | GitHub disattiva i cron dopo 60 giorni senza attività: riattivalo da Actions |

Nota: se una partita non ha ancora i dati completi o il profilo Dota è privato
("Expose Public Match Data" disattivato nel client Dota), OpenDota potrebbe non restituirla.
