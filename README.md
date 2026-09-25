# harlocksp_updates

Aggiornamenti del maestro HarlockSP: un bot che pubblica su un canale Telegram un messaggio
per ogni nuova partita Dota 2 di **HarlockSP**
([Dotabuff](https://www.dotabuff.com/players/295689331) · account ID `295689331`).

**Costo zero**: gira su GitHub Actions ogni 5 minuti e usa l'API gratuita di
[OpenDota](https://docs.opendota.com/). Non serve nessun server.

Cosa fa:
- 📣 **nel canale**: un messaggio per ogni nuova partita (con 🌟 per le partite notevoli e le serie
  di vittorie/sconfitte) e, alle 23, il **riepilogo della giornata** se HarlockSP ha giocato;
- 💬 **in chat privata con il bot**: chiunque può chiedere `/ultima` o `/riepilogo oggi|settimana|mese`.

Esempio di messaggio:

```
🌟 ✅ VITTORIA – HarlockSP
🦸 Eroe: Anti-Mage (Dire)
⚔️ K/D/A: 14/0/12 (KDA 26.0)
💰 GPM/XPM: 742/810 · 🗡 LH: 388
⏱ Durata: 43:10 · 🎮 Classificata · All Pick
🛡 Partita perfetta: 0 morti!
🔥 3 vittorie di fila!
🔗 Dotabuff · OpenDota
```

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

## Prova in locale (dry-run)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt

python -m pytest                          # test (nessuna chiamata di rete)
python -m src.main --dry-run --last 3     # stampa i messaggi delle ultime 3 partite
python -m src.main --dry-run --comando "/riepilogo settimana"   # prova un comando
```

`--dry-run` stampa i messaggi invece di inviarli, **non modifica** `state.json` e non richiede i
segreti. Per un invio reale dal tuo PC:

```bash
export TELEGRAM_TOKEN="..." TELEGRAM_CHAT_ID="@nomecanale"
python -m src.main
```

## Configurazione

`config.yaml`:

| Chiave         | Significato                         |
|----------------|-------------------------------------|
| `player_id`    | account ID Dota 2 (quello di Dotabuff/OpenDota) |
| `display_name` | nome mostrato nei messaggi          |
| `language`     | lingua dei messaggi (per ora `it`)  |
| `timezone`     | fuso orario dei riepiloghi (default `Europe/Rome`; il cron di GitHub è in UTC, la conversione la fa il codice) |
| `daily_summary_hour` | ora del riepilogo giornaliero nel canale (default `23`; `null` per disattivarlo) |

### Consigliato in BotFather (facoltativo)

- **Bot Settings → Allow Groups? → Turn off**: nessuno può aggiungere il bot ai gruppi
  (il canale continua a funzionare).
- **Edit Bot → Edit Description**: il testo che gli amici vedono prima di premere Avvia, per esempio
  *"Aggiornamenti Dota 2 di HarlockSP. Scrivi /riepilogo settimana"*.

Il menu dei comandi (il tasto "/" nella chat) viene impostato automaticamente dal bot.

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
| in Actions ci sono solo avvii manuali, nessuno "schedule" | su un repository nuovo GitHub può impiegare qualche ora ad attivare il cron: nel frattempo usa Run workflow |
| `getUpdates … 409 Conflict`                  | al bot è collegato un webhook o un altro programma che legge i messaggi: va rimosso |
| il workflow non parte più da solo            | GitHub disattiva i cron dopo 60 giorni senza attività: riattivalo da Actions |

Nota: se una partita non ha ancora i dati completi o il profilo Dota è privato
("Expose Public Match Data" disattivato nel client Dota), OpenDota potrebbe non restituirla.
