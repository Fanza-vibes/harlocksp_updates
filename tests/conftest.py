from __future__ import annotations

from typing import Any

import pytest


def make_match(match_id: int, **overrides: Any) -> dict[str, Any]:
    match = {
        "match_id": match_id,
        "player_slot": 1,
        "radiant_win": True,
        "duration": 2301,
        "game_mode": 22,
        "lobby_type": 7,
        "hero_id": 1,
        "start_time": 1_700_000_000 + match_id,
        "kills": 12,
        "deaths": 3,
        "assists": 8,
        "gold_per_min": 650,
        "xp_per_min": 720,
        "last_hits": 312,
    }
    match.update(overrides)
    return match


@pytest.fixture
def match_factory():
    return make_match
