#!/usr/bin/env bash
# Stato del bot su un branch dedicato, separato dal codice.
#
#   state_branch.sh load   copia state.json dal branch dello stato nella cartella di lavoro
#                          (se il branch non esiste ancora, resta lo state.json di main: migrazione)
#   state_branch.sh save   se state.json è cambiato, lo committa sul branch dello stato e fa push
#
# Così su main arrivano solo modifiche al codice, mai i salvataggi automatici del bot.
# Il workflow usa `concurrency`, quindi un solo giro alla volta scrive sul branch.
set -euo pipefail

BRANCH="${STATE_BRANCH:-bot-state}"
FILE="state.json"
WORKTREE="${RUNNER_TEMP:-/tmp}/bot-state"

branch_exists() {
  git ls-remote --exit-code --heads origin "$BRANCH" >/dev/null 2>&1
}

load() {
  if branch_exists; then
    git fetch --quiet --depth=1 origin "$BRANCH"
    git show "FETCH_HEAD:$FILE" > "$FILE"
    echo "Stato letto dal branch $BRANCH"
  else
    echo "Branch $BRANCH non ancora creato: uso $FILE di main (primo avvio dopo la migrazione)"
  fi
}

save() {
  if [ ! -f "$FILE" ]; then
    echo "$FILE assente: niente da salvare"
    return 0
  fi
  git config user.name "github-actions[bot]"
  git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
  rm -rf "$WORKTREE"
  if branch_exists; then
    git fetch --quiet --depth=1 origin "$BRANCH"
    git worktree add --quiet -B "$BRANCH" "$WORKTREE" FETCH_HEAD
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
