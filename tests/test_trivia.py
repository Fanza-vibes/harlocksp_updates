from src.trivia import MAX_FACTS, facts, find_player, format_trivia, is_parsed, pick
from tests.fixtures_match import HERO_KEYS, PLAYER_ID, hero_player, parsed_match


def texts(match, hero_keys=HERO_KEYS):
    return [f.text for f in facts(match, hero_player(match), "Anti-Mage", hero_keys)]


def one(match, needle):
    found = [t for t in texts(match) if needle in t]
    assert len(found) == 1, texts(match)
    return found[0]


def test_is_parsed_and_find_player():
    m = parsed_match()
    assert is_parsed(m)
    assert not is_parsed(parsed_match(version=None))
    assert find_player(m, PLAYER_ID)["hero_id"] == 1
    assert find_player(m, 42) is None


def test_nemesis_ignores_creeps():
    assert "ucciso <b>4 volte</b> da <b>Pudge</b>" in one(parsed_match(), "Nemesi")
    assert "Vendetta" in one(parsed_match(), "Nemesi")


def test_nemesis_needs_two_deaths():
    m = parsed_match()
    hero_player(m)["killed_by"] = {"npc_dota_hero_pudge": 1}
    assert not any("Nemesi" in t for t in texts(m))


def test_victim():
    assert "<b>Crystal Maiden</b>, ucciso 6 volte" in one(parsed_match(), "Vittima")


def test_unknown_hero_key_falls_back_to_readable_name():
    m = parsed_match()
    hero_player(m)["killed_by"] = {"npc_dota_hero_new_hero": 3}
    assert "New Hero" in " ".join(texts(m, hero_keys={}))


def test_multi_kill_and_rampage():
    assert "ULTRA KILL!" in one(parsed_match(), "KILL!")
    m = parsed_match()
    hero_player(m)["multi_kills"] = {"5": 2}
    assert "RAMPAGE!</b> (x2)" in " ".join(texts(m))


def test_kill_streak():
    assert "Serie di 6 kill" in one(parsed_match(), "Serie")
    assert "Unstoppable" in one(parsed_match(), "Serie")


def test_first_blood_made_and_suffered():
    assert "Ha fatto il <b>First Blood</b> al minuto 1:35" in one(parsed_match(), "First Blood")
    m = parsed_match(objectives=[{"type": "CHAT_MESSAGE_FIRSTBLOOD", "time": 60, "player_slot": 0, "key": 3}])
    assert "Ha subito il First Blood" in one(m, "First Blood")
    m = parsed_match(
        objectives=[{"type": "CHAT_MESSAGE_FIRSTBLOOD", "player_slot": 0, "victim_player_slot": 131}]
    )
    assert "Ha subito il First Blood…" in one(m, "First Blood")


def test_comeback_for_dire():
    # Radiant era avanti di 12.300 (= Dire sotto) e ha vinto Dire
    assert "Era sotto di 12.300 d'oro e ha vinto" in one(parsed_match(), "Rimonta")


def test_throw():
    m = parsed_match(radiant_win=True)  # stesso andamento, ma questa volta vince Radiant
    assert not any("Rimonta" in t for t in texts(m))
    m = parsed_match(radiant_win=True, radiant_gold_adv=[0, -3000, -11000, -2000, 5000])
    assert "Era sopra di 11.000 d'oro e ha perso" in one(m, "Throw")


def test_best_and_worst_percentile():
    assert "GPM migliore del <b>93%</b> dei giocatori di Anti-Mage" in one(parsed_match(), "📈")
    m = parsed_match()
    hero_player(m)["benchmarks"]["last_hits_per_min"]["pct"] = 0.04
    assert "Last hit al minuto più basso del 96%" in one(m, "📉")


def test_team_damage_share_only_counts_own_team():
    # Dire: 31000 / (31000 + 12000 + 9000) = 60%
    assert "<b>60%</b> dei danni della squadra" in one(parsed_match(), "💥")


def test_time_dead():
    m = parsed_match()
    assert not any("da morto" in t for t in texts(m))
    hero_player(m)["life_state_dead"] = 380
    assert "<b>6:20</b> da morto" in one(m, "da morto")
    hero_player(m)["life_state_dead"] = 99999  # più della durata: dato sospetto, ignorato
    assert not any("da morto" in t for t in texts(m))


def test_missing_fields_never_crash():
    bare = {"match_id": 1, "players": [{"player_slot": 0, "account_id": PLAYER_ID, "hero_id": 1}]}
    assert facts(bare, bare["players"][0], "Anti-Mage", {}) == []
    weird = {
        "match_id": 1,
        "radiant_gold_adv": "x",
        "objectives": [None, {"type": "CHAT_MESSAGE_FIRSTBLOOD", "key": "abc"}],
        "players": [
            {
                "player_slot": 0,
                "account_id": PLAYER_ID,
                "killed_by": [],
                "multi_kills": {"abc": 1, "3": "x"},
                "benchmarks": {"gold_per_min": {"pct": 7}},
                "life_state_dead": True,
            }
        ],
    }
    assert facts(weird, weird["players"][0], "X", {}) == []


def test_pick_limits_and_orders():
    chosen = pick(facts(parsed_match(), hero_player(parsed_match()), "Anti-Mage", HERO_KEYS))
    assert len(chosen) == MAX_FACTS
    assert [f.score for f in chosen] == sorted((f.score for f in chosen), reverse=True)
    assert "ULTRA KILL" in chosen[0].text  # la giocata più spettacolare in cima


def test_format_trivia_escapes_hero_name():
    text = format_trivia("<Anti&Mage>", pick(facts(parsed_match(), hero_player(parsed_match()), "x", {})))
    assert text.startswith("🔍 <b>Curiosità della partita</b> – &lt;Anti&amp;Mage&gt;")


def test_no_player_names_in_output():
    m = parsed_match()
    for p in m["players"]:
        p["personaname"] = "NickSegreto"
    assert "NickSegreto" not in " ".join(texts(m))
