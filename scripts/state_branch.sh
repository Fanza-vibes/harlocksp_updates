#!/usr/bin/env bash
# Stato del bot su un branch dedicato, separato dal codice.
#
#   state_branch.sh load   copia state.json dal branch dello stato nella cartella di lavoro
#                          (se il branch non esiste, nessuno stato: il bot fa il primo avvio e non invia nulla)
#   state_branch.sh save   se state.json è cambiato, lo committa sul branch dello stato e fa push
#
# Così su main arrivano solo modifiche al codice, mai i salvataggi automatici del bot.
# Il workflow usa `concurrency`, quindi un solo giro alla volta scrive sul branch.
set -euo pipefail

BRANCH="${STATE_BRANCH:-bot-state}"
FILE="state.json"
WORKTREE="${RUNNER_TEMP:-/tmp}/bot-state"

# 0 = il branch esiste, 2 = non esiste, altro = errore (es. rete): mai confondere un errore
# con "branch assente", altrimenti si ripartirebbe da uno stato vuoto.
branch_status() {
  local rc=0
  git ls-remote --exit-code --heads origin "$BRANCH" >/dev/null 2>&1 || rc=$?
  echo "$rc"
}

load() {
  case "$(branch_status)" in
    0)
      git fetch --quiet --depth=1 origin "$BRANCH"
      git show "FETCH_HEAD:$FILE" > "$FILE"
      echo "Stato letto dal branch $BRANCH"
      ;;
    2) echo "Branch $BRANCH non trovato: primo avvio (si salva l'ultima partita, nessun invio)" ;;
    *) echo "Impossibile controllare il branch $BRANCH: giro annullato, stato invariato" >&2; return 1 ;;
  esac
}

save() {
  if [ ! -f "$FILE" ]; then
    echo "$FILE assente: niente da salvare"
    return 0
  fi
  git config user.name "github-actions[bot]"
  git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
  rm -rf "$WORKTREE"
  local status
  status="$(branch_status)"
  if [ "$status" = 0 ]; then
    git fetch --quiet --depth=1 origin "$BRANCH"
    git worktree add --quiet -B "$BRANCH" "$WORKTREE" FETCH_HEAD
  elif [ "$status" != 2 ]; then
    echo "Impossibile controllare il branch $BRANCH: stato non salvato" >&2
    return 1
  else
    git worktree add --quiet --detach "$WORKTREE"
    git -C "$WORKTREE" checkout --quiet --orphan "$BRANCH"
    git -C "$WORKTREE" rm -r --quiet --cached . >/dev/null 2>&1 || true
    git -C "$WORKTREE" clean -fdq
  fi
  cp "$FILE" "$WORKTREE/$FILE"
  git -C "$WORKTREE" add "$FILE"
  if git -C "$WORKTREE" diff --cached --quiet; then
    echo "$FILE invariato"
    return 0
  fi
  git -C "$WORKTREE" commit --quiet -m "Aggiorna state.json"
  for i in 1 2 3; do
    if git -C "$WORKTREE" push --quiet origin "$BRANCH"; then
      echo "Stato salvato sul branch $BRANCH"
      return 0
    fi
    sleep $((i * 5))
  done
  echo "Push dello stato non riuscito" >&2
  return 1
}

case "${1:-}" in
  load) load ;;
  save) save ;;
  *) echo "uso: $0 load|save" >&2; exit 2 ;;
esac
