# Immagini e GIF del canale

Metti in queste cartelle le immagini o le GIF da allegare ai messaggi del canale.
Se in una cartella ci sono più file, il bot ne sceglie uno **a caso** ogni volta.
Se una cartella è vuota, il messaggio viene inviato come solo testo.

| Cartella | Quando si usa |
|---|---|
| `vittoria/` | scheda di una partita vinta |
| `sconfitta/` | scheda di una partita persa |
| `serie_vittorie/` | vittoria con 3 o più vittorie di fila (se vuota: `vittoria/`) |
| `serie_sconfitte/` | sconfitta con 3 o più sconfitte di fila (se vuota: `sconfitta/`) |
| `maledizione_spezzata/` | vittoria dopo 3 o più sconfitte di fila (se vuota: `vittoria/`) |
| `giocate_speciali/` | curiosità con ULTRA KILL o RAMPAGE |
| `riepilogo/` | riepilogo della giornata delle 23 |

**Formati**: immagini `.jpg`, `.jpeg`, `.png`, `.webp` (fino a 10 MB); animazioni `.gif` o `.mp4`
(fino a 50 MB, meglio file piccoli). Gli altri file vengono ignorati.

**Come caricarli da GitHub**: apri la cartella → **Add file** → **Upload files** → trascina i file →
**Commit changes**. Per toglierne uno: aprilo → icona del cestino → **Commit changes**.

Il repository è pubblico: i file qui dentro sono visibili a tutti.
