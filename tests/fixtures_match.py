"""Partita analizzata finta, con i campi dello schema OpenDota (odota/core MatchResponse)."""

from __future__ import annotations

import copy
from typing import Any

PLAYER_ID = 295689331
HERO_KEYS = {
    "npc_dota_hero_antimage": "Anti-Mage",
    "npc_dota_hero_pudge": "Pudge",
    "npc_dota_hero_crystal_maiden": "Crystal Maiden",
    "npc_dota_hero_lion": "Lion",
}

_BASE: dict[str, Any] = {
    "match_id": 9015942600,
    "version": 22,
    "duration": 2590,
    "radiant_win": False,
    "radiant_gold_adv": [0, 800, 3000, 9000, 12300, 4000, -2000, -9000],
    "objectives": [
        {"type": "CHAT_MESSAGE_FIRSTBLOOD", "time": 95, "player_slot": 131, "key": 2},
        {"type": "building_kill", "time": 700, "key": "npc_dota_goodguys_tower1_mid"},
    ],
    "players": [
        {"player_slot": 0, "account_id": 1, "hero_id": 14, "hero_damage": 15000},
        {"player_slot": 1, "account_id": None, "hero_id": 5, "hero_damage": 6000},
        {"player_slot": 2, "account_id": 3, "hero_id": 26, "hero_damage": 8000},
        {
            "player_slot": 131,
            "account_id": PLAYER_ID,
            "hero_id": 1,
            "hero_damage": 31000,
            "killed_by": {
                "npc_dota_hero_pudge": 4,
                "npc_dota_hero_lion": 1,
                "npc_dota_creep_goodguys_melee": 2,
            },
            "killed": {
                "npc_dota_hero_crystal_maiden": 6,
                "npc_dota_hero_pudge": 3,
                "npc_dota_creep_goodguys_melee": 180,
            },
            "multi_kills": {"2": 3, "3": 1, "4": 1},
            "kill_streaks": {"3": 2, "4": 1, "5": 1, "6": 1},
            "life_state_dead": 142,
            "benchmarks": {
                "gold_per_min": {"raw": 742, "pct": 0.93},
                "xp_per_min": {"raw": 810, "pct": 0.88},
                "last_hits_per_min": {"raw": 9, "pct": 0.71},
                "hero_damage_per_min": {"raw": 718, "pct": 0.64},
            },
        },
        {"player_slot": 132, "account_id": 5, "hero_id": 2, "hero_damage": 12000},
        {"player_slot": 133, "account_id": 6, "hero_id": 8, "hero_damage": 9000},
    ],
}


def parsed_match(**overrides: Any) -> dict[str, Any]:
    m = copy.deepcopy(_BASE)
    m.update(overrides)
    return m


def hero_player(match: dict[str, Any]) -> dict[str, Any]:
    return next(p for p in match["players"] if p["account_id"] == PLAYER_ID)
