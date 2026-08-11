import requests
import pandas as pd
import time
import json
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).resolve().parent))
from paths import PYTHON

BASE_URL = "https://fantasy.premierleague.com/api"

def fetch_bootstrap():
    print("F=fetching bootstrap data...")
    r = requests.get(f"{BASE_URL}/bootstrap-static/", timeout=15)
    r.raise_for_status()
    return r.json()

def fetch_fixtures():
    print("fetching fixtures...")
    r = requests.get(f"{BASE_URL}/fixtures/", timeout=15)
    r.raise_for_status()
    return r.json()

def fetch_player_history(player_id):
    """Fetch per-gameweek history for a single player."""
    r = requests.get(f"{BASE_URL}/element-summary/{player_id}/", timeout=10)
    r.raise_for_status()
    data = r.json()
    history = data.get("history", [])
    upcoming = data.get("fixtures", [])
    return history, upcoming

def build_players_df(bootstrap):
    """Build the main players dataframe from bootstrap data."""
    players = pd.DataFrame(bootstrap["elements"])
    teams   = pd.DataFrame(bootstrap["teams"])
    positions = pd.DataFrame(bootstrap["element_types"])

    # Map team names
    team_map = teams.set_index("id")["name"].to_dict()
    pos_map  = positions.set_index("id")["singular_name_short"].to_dict()

    players["team_name"]     = players["team"].map(team_map)
    players["position"]      = players["element_type"].map(pos_map)
    players["price"]         = players["now_cost"] / 10  # convert to £

    # Select and rename useful columns
    cols = {
        "id":                      "id",
        "first_name":              "first_name",
        "second_name":             "last_name",
        "web_name":                "web_name",
        "team_name":               "team",
        "position":                "position",
        "price":                   "price",
        "selected_by_percent":     "ownership_pct",
        "form":                    "form",
        "points_per_game":         "ppg",
        "total_points":            "total_points",
        "minutes":                 "minutes",
        "goals_scored":            "goals",
        "assists":                 "assists",
        "clean_sheets":            "clean_sheets",
        "goals_conceded":          "goals_conceded",
        "yellow_cards":            "yellow_cards",
        "red_cards":               "red_cards",
        "saves":                   "saves",
        "bonus":                   "bonus",
        "bps":                     "bps",
        "influence":               "influence",
        "creativity":              "creativity",
        "threat":                  "threat",
        "ict_index":               "ict_index",
        "transfers_in_event":      "transfers_in_gw",
        "transfers_out_event":     "transfers_out_gw",
        "value_form":              "value_form",
        "value_season":            "value_season",
        "status":                  "status",        # a=available, d=doubtful, i=injured, s=suspended
        "chance_of_playing_next_round": "chance_next_gw",
        "news":                    "news",
    }

    keep = [c for c in cols if c in players.columns]
    players = players[keep].rename(columns={c: cols[c] for c in keep})

    # Cast numeric fields
    numeric = ["form", "ppg", "influence", "creativity", "threat", "ict_index",
               "value_form", "value_season", "ownership_pct"]
    for col in numeric:
        if col in players.columns:
            players[col] = pd.to_numeric(players[col], errors="coerce")

    return players

def build_fixture_difficulty(fixtures, current_gw, n_ahead=5):
    """
    Compute average fixture difficulty (FDR) for each team
    over the next n_ahead gameweeks.
    Returns a dict: team_id -> avg_fdr
    """
    upcoming = [f for f in fixtures if not f["finished"] and f.get("event")]
    home_fdr, away_fdr = {}, {}

    for f in upcoming:
        gw = f["event"]
        if gw > current_gw + n_ahead:
            continue
        h, a = f["team_h"], f["team_a"]
        home_fdr.setdefault(h, []).append(f["team_h_difficulty"])
        away_fdr.setdefault(a, []).append(f["team_a_difficulty"])

    avg_fdr = {}
    all_teams = set(home_fdr) | set(away_fdr)
    for t in all_teams:
        scores = home_fdr.get(t, []) + away_fdr.get(t, [])
        avg_fdr[t] = round(sum(scores) / len(scores), 2) if scores else None

    return avg_fdr

def enrich_with_history(players_df, sample_size=None, delay=0.5):
    """
    Fetch per-player gameweek history and add:
    - last 3 GW average points
    - last 3 GW average minutes
    Optionally limit to sample_size players (useful for testing).
    """
    player_ids = players_df["id"].tolist()
    if sample_size:
        player_ids = player_ids[:sample_size]

    records = []
    for i, pid in enumerate(player_ids):
        print(f"  [{i+1}/{len(player_ids)}] player {pid}", end="\r")
        try:
            history, _ = fetch_player_history(pid)
            if history:
                last3 = history[-3:]
                avg_pts = round(sum(h["total_points"] for h in last3) / len(last3), 2)
                avg_min = round(sum(h["minutes"]       for h in last3) / len(last3), 2)
            else:
                avg_pts = avg_min = None
            records.append({"id": pid, "avg_pts_last3": avg_pts, "avg_min_last3": avg_min})
        except Exception:
            records.append({"id": pid, "avg_pts_last3": None, "avg_min_last3": None})
        time.sleep(delay)

    print()
    history_df = pd.DataFrame(records)
    return players_df.merge(history_df, on="id", how="left")

def main(
    output_path=None,
    fetch_history=True,
    history_sample=None,   
    history_delay=0.5,
    n_fixture_gws=5,
):
    if output_path is None:
        output_path = PYTHON / "fpl_live_dataset.csv"
    
    bootstrap = fetch_bootstrap()
    current_gw = next(
        (gw["id"] for gw in bootstrap["events"] if gw["is_current"]),
        bootstrap["events"][-1]["id"]
    )
    print(f"Current gameweek: {current_gw}")

    players = build_players_df(bootstrap)
    print(f"Players loaded: {len(players)}")

    fixtures = fetch_fixtures()

    teams_df = pd.DataFrame(bootstrap["teams"])
    team_name_map = teams_df.set_index("name")["id"].to_dict()
    avg_fdr = build_fixture_difficulty(fixtures, current_gw, n_fixture_gws)


    players["team_id"] = players["team"].map(team_name_map)
    players["avg_fdr_next5"] = players["team_id"].map(avg_fdr)
    players.drop(columns=["team_id"], inplace=True)

    if fetch_history:
        print(f"Fetching player history (sample={history_sample or 'all'})...")
        players = enrich_with_history(players, history_sample, history_delay)

    out = Path(output_path)
    players.to_csv(out, index=False)
    print(f"\nDataset saved → {out}  ({len(players)} rows, {len(players.columns)} cols)")
    print(players[["web_name","team","position","price","total_points","avg_fdr_next5"]].head(10).to_string(index=False))

def get_available_players():
    """Fetch live availability and return list of unavailable player names."""
    bootstrap = fetch_bootstrap()
    players = build_players_df(bootstrap)
    
    # filter unavailable players
    unavailable = players[
        (players['status'] != 'a') | 
        (players['chance_next_gw'] < 50)
    ][['web_name', 'first_name', 'last_name', 'status', 'chance_next_gw', 'news']]
    
    print(f"Unavailable players: {len(unavailable)}")
    print(unavailable.to_string(index=False))
    
    return unavailable
if __name__ == "__main__":
    main(
        output_path="fpl_live_dataset.csv",
        fetch_history=True,
        history_sample=None,   # change to e.g. 50 for a quick test run
        history_delay=0.5,
        n_fixture_gws=5,
    )
