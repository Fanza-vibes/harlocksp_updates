"""Curiosità di una partita analizzata da OpenDota. Solo funzioni pure.

Ogni curiosità ha un punteggio: si pubblicano solo le più notevoli (al massimo MAX_FACTS).
Ordine indicativo: rampage > ultra kill > nemesi/rimonta > triple kill/vittima > serie di kill >
first blood/danni > percentili > tempo da morto.
Campi usati (verificati sullo schema di odota/core): killed_by, killed, multi_kills, kill_streaks,
objectives (CHAT_MESSAGE_FIRSTBLOOD), radiant_gold_adv, benchmarks, hero_damage, life_state_dead.
Se un campo manca, la curiosità relativa viene semplicemente saltata.
Privacy: si usano solo nomi di eroi, mai nickname o chat degli altri giocatori.
"""

from __future__ import annotations

from dataclasses import dataclass
from html import escape
from typing import Any

from .formatter import format_duration
from .stats import is_radiant

Match = dict[str, Any]
Player = dict[str, Any]

MAX_FACTS = 5
HERO_PREFIX = "npc_dota_hero_"

NEMESIS_MIN = 2
VICTIM_MIN = 3
STREAK_MIN = 5
COMEBACK_GOLD = 8_000
THROW_GOLD = 10_000
PCT_HIGH = 0.85
PCT_LOW = 0.10
TEAM_DAMAGE_SHARE = 0.35
DEAD_SECONDS = 300

MULTI_KILLS = {3: ("TRIPLE KILL", 70), 4: ("ULTRA KILL", 90), 5: ("RAMPAGE", 120)}
KILL_STREAKS = {
    5: "Mega Kill",
    6: "Unstoppable",
    7: "Wicked Sick",
    8: "Monster Kill",
    9: "Godlike",
    10: "Beyond Godlike",
}
BENCHMARKS = {
    "gold_per_min": "GPM",
    "xp_per_min": "XPM",
    "kills_per_min": "Kill al minuto",
    "last_hits_per_min": "Last hit al minuto",
    "hero_damage_per_min": "Danni agli eroi",
    "tower_damage": "Danni alle torri",
    "hero_healing_per_min": "Cure",
}
# per il percentile "ironico" basso si usano solo metriche dove un valore basso fa sorridere
BENCHMARKS_LOW = ("gold_per_min", "last_hits_per_min", "hero_damage_per_min")


@dataclass(frozen=True)
class Fact:
    score: float
    text: str


def is_parsed(match: Match) -> bool:
    """OpenDota valorizza `version` solo dopo aver analizzato il replay."""
    return match.get("version") is not None


def find_player(match: Match, account_id: int) -> Player | None:
    return next(
        (p for p in match.get("players") or [] if isinstance(p, dict) and p.get("account_id") == account_id),
        None,
    )


def facts(match: Match, player: Player, hero_name: str, hero_keys: dict[str, str]) -> list[Fact]:
    """Tutte le curiosità candidate, non ordinate."""
    found: list[Fact | None] = [
        _nemesis(player, hero_keys),
        _victim(player, hero_keys),
        _multi_kill(player),
        _kill_streak(player),
        _first_blood(match, player),
        _comeback_or_throw(match, player),
        _best_percentile(player, hero_name),
        _worst_percentile(player, hero_name),
        _team_damage_share(match, player),
        _time_dead(player, int(match.get("duration") or 0)),
    ]
    return [f for f in found if f is not None]


def pick(candidates: list[Fact], limit: int = MAX_FACTS) -> list[Fact]:
    return sorted(candidates, key=lambda f: -f.score)[:limit]


def format_trivia(hero_name: str, chosen: list[Fact]) -> str:
    lines = [f"🔍 <b>Curiosità della partita</b> – {escape(hero_name)}", ""]
    lines += [f.text for f in chosen]
    return "\n".join(lines)


# --- singole curiosità -------------------------------------------------------


def _top_hero(counts: Any, hero_keys: dict[str, str]) -> tuple[str, int] | None:
    """Eroe con il conteggio più alto in un dizionario {nome_interno: n} (creep esclusi)."""
    if not isinstance(counts, dict):
        return None
    heroes = [
        (k, v) for k, v in counts.items() if isinstance(k, str) and k.startswith(HERO_PREFIX) and _is_int(v)
    ]
    if not heroes:
        return None
    key, n = max(heroes, key=lambda kv: (kv[1], kv[0]))
    return hero_keys.get(key) or key.removeprefix(HERO_PREFIX).replace("_", " ").title(), n


def _nemesis(player: Player, hero_keys: dict[str, str]) -> Fact | None:
    top = _top_hero(player.get("killed_by"), hero_keys)
    if not top or top[1] < NEMESIS_MIN:
        return None
    name, n = top
    extra = " Vendetta alla prossima?" if n >= 4 else ""
    return Fact(50 + 8 * min(n, 6), f"💀 Nemesi: ucciso <b>{n} volte</b> da <b>{escape(name)}</b>.{extra}")


def _victim(player: Player, hero_keys: dict[str, str]) -> Fact | None:
    top = _top_hero(player.get("killed"), hero_keys)
    if not top or top[1] < VICTIM_MIN:
        return None
    name, n = top
    return Fact(40 + 5 * min(n, 8), f"🎯 Vittima preferita: <b>{escape(name)}</b>, ucciso {n} volte")


def _max_key(counts: Any) -> tuple[int, int] | None:
    """Chiave numerica più alta con conteggio > 0 in {"3": 1, "4": 2}."""
    if not isinstance(counts, dict):
        return None
    valid = [(int(k), v) for k, v in counts.items() if str(k).isdigit() and _is_int(v) and v > 0]
    return max(valid) if valid else None


def _multi_kill(player: Player) -> Fact | None:
    top = _max_key(player.get("multi_kills"))
    if not top or top[0] < 3:
        return None
    size, n = top
    name, score = MULTI_KILLS[min(size, 5)]
    times = f" (x{n})" if n > 1 else ""
    return Fact(score + 5 * (n - 1), f"🔥 <b>{name}!</b>{times}")


def _kill_streak(player: Player) -> Fact | None:
    top = _max_key(player.get("kill_streaks"))
    if not top or top[0] < STREAK_MIN:
        return None
    size = top[0]
    return Fact(35 + 5 * size, f"⚡ Serie di {size} kill senza morire: <b>{KILL_STREAKS[min(size, 10)]}</b>")


def _first_blood(match: Match, player: Player) -> Fact | None:
    fb = next(
        (
            o
            for o in match.get("objectives") or []
            if isinstance(o, dict) and o.get("type") == "CHAT_MESSAGE_FIRSTBLOOD"
        ),
        None,
    )
    if fb is None:
        return None
    slot = player.get("player_slot")
    when = f" al minuto {format_duration(fb['time'])}" if _is_int(fb.get("time")) and fb["time"] >= 0 else ""
    if fb.get("player_slot") == slot:
        return Fact(55, f"🩸 Ha fatto il <b>First Blood</b>{when}")
    if _first_blood_victim_slot(match, fb) == slot:
        return Fact(45, f"🩸 Ha subito il First Blood{when}… partenza in salita")
    return None


def _first_blood_victim_slot(match: Match, fb: dict[str, Any]) -> int | None:
    if _is_int(fb.get("victim_player_slot")):
        return fb["victim_player_slot"]
    # formato grezzo: `key` è l'indice della vittima nella lista dei giocatori
    players = match.get("players") or []
    try:
        return players[int(fb.get("key"))].get("player_slot")  # type: ignore[arg-type]
    except (TypeError, ValueError, IndexError, AttributeError):
        return None


def _comeback_or_throw(match: Match, player: Player) -> Fact | None:
    adv = [x for x in match.get("radiant_gold_adv") or [] if isinstance(x, (int, float))]
    if not adv or not isinstance(match.get("radiant_win"), bool):
        return None
    radiant = is_radiant(int(player.get("player_slot") or 0))
    ours = [x if radiant else -x for x in adv]  # vantaggio d'oro dal punto di vista della sua squadra
    won = match["radiant_win"] == radiant
    if won and -min(ours) >= COMEBACK_GOLD:
        gap = -min(ours)
        return Fact(65 + gap / 1000, f"🎢 <b>Rimonta!</b> Era sotto di {_gold(gap)} d'oro e ha vinto")
    if not won and max(ours) >= THROW_GOLD:
        gap = max(ours)
        return Fact(65 + gap / 1000, f"🙈 <b>Throw…</b> Era sopra di {_gold(gap)} d'oro e ha perso")
    return None


def _benchmarks(player: Player) -> list[tuple[str, float]]:
    bench = player.get("benchmarks")
    if not isinstance(bench, dict):
        return []
    out = []
    for key in BENCHMARKS:
        pct = (bench.get(key) or {}).get("pct") if isinstance(bench.get(key), dict) else None
        if isinstance(pct, (int, float)) and 0 <= pct <= 1:
            out.append((key, float(pct)))
    return out


def _best_percentile(player: Player, hero_name: str) -> Fact | None:
    best = max(_benchmarks(player), key=lambda kv: kv[1], default=None)
    if not best or best[1] < PCT_HIGH:
        return None
    key, pct = best
    return Fact(
        30 + (pct - PCT_HIGH) * 200,
        f"📈 {BENCHMARKS[key]} migliore del <b>{pct:.0%}</b> dei giocatori di {escape(hero_name)}",
    )


def _worst_percentile(player: Player, hero_name: str) -> Fact | None:
    low = [kv for kv in _benchmarks(player) if kv[0] in BENCHMARKS_LOW]
    worst = min(low, key=lambda kv: kv[1], default=None)
    if not worst or worst[1] > PCT_LOW:
        return None
    key, pct = worst
    return Fact(
        30,
        f"📉 {BENCHMARKS[key]} più basso del {1 - pct:.0%} dei giocatori di {escape(hero_name)}… giornata no",
    )


def _team_damage_share(match: Match, player: Player) -> Fact | None:
    radiant = is_radiant(int(player.get("player_slot") or 0))
    team = [
        p
        for p in match.get("players") or []
        if isinstance(p, dict) and is_radiant(int(p.get("player_slot") or 0)) == radiant
    ]
    total = sum(p.get("hero_damage") or 0 for p in team)
    own = player.get("hero_damage") or 0
    if not total or not _is_int(own):
        return None
    share = own / total
    if share < TEAM_DAMAGE_SHARE:
        return None
    return Fact(
        30 + (share - TEAM_DAMAGE_SHARE) * 100, f"💥 Ha fatto il <b>{share:.0%}</b> dei danni della squadra"
    )


def _time_dead(player: Player, duration: int) -> Fact | None:
    dead = player.get("life_state_dead")
    if (
        not isinstance(dead, int)
        or isinstance(dead, bool)
        or dead < DEAD_SECONDS
        or (duration and dead > duration)
    ):
        return None
    return Fact(25 + (dead - DEAD_SECONDS) / 60, f"⚰️ Ha passato <b>{format_duration(dead)}</b> da morto")


def _gold(n: float) -> str:
    return f"{round(n):,}".replace(",", ".")


def _is_int(v: Any) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)
