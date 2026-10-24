from paths import PYTHON, DATA
import pandas as pd

# ---------- load and decode ----------
df = pd.read_csv(PYTHON / "outputs" / "gw_predictions.csv")

teams = pd.read_csv(DATA / "team_encoding.csv")
teams["team_name"] = teams["team_name"].str.strip()
team_map = dict(zip(teams["encoded"], teams["team_name"]))
df["team_name"] = df["team"].map(team_map)

df["full_name"] = df["first_name"].str.strip() + " " + df["last_name"].str.strip()

COLS = ["web_name", "team_name", "pos_label", "price", "predicted_points"]
COMPARE_COLS = COLS + ["avg_pts_last3", "ppg", "total_points",
                       "avg_fdr_next5", "ownership_pct", "opponent"]
SORTABLE = {"predicted_points", "price", "avg_pts_last3", "ppg", "total_points"}

# stat -> True if higher is better (for fixtures, lower difficulty is better)
COMPARE_STATS = {
    "predicted_points": True,
    "avg_pts_last3": True,
    "ppg": True,
    "total_points": True,
    "ownership_pct": True,
    "avg_fdr_next5": False,
}


# ---------- tool 1: look up a player ----------
def get_player(name, limit=5, cols=COLS):
    exact = df[df["web_name"].str.lower() == name.lower().strip()]
    if len(exact) == 1:
        return exact[cols].round(2).to_dict("records")

    haystack = (df["web_name"] + " " + df["full_name"]).str.lower()
    mask = pd.Series(True, index=df.index)
    for word in name.lower().split():
        mask &= haystack.str.contains(word, regex=False, na=False)

    res = df[mask]
    if res.empty:
        return []
    return res[cols].head(limit).round(2).to_dict("records")


# ---------- tool 2: ranked players ----------
def top_players(position=None, max_price=None, n=5,
                sort_by="predicted_points", ascending=False, min_price=None):
    if sort_by not in SORTABLE:
        sort_by = "predicted_points"

    mask = pd.Series(True, index=df.index)
    if position is not None:
        mask &= (df["pos_label"] == position)
    if max_price is not None:
        mask &= (df["price"] <= max_price)
    if min_price is not None:
        mask &= (df["price"] >= min_price)

    res = df[mask]
    if res.empty:
        return []
    res = res.sort_values(sort_by, ascending=ascending).head(n)
    cols = COLS if sort_by in COLS else COLS + [sort_by]
    return res[cols].round(2).to_dict("records")


# ---------- tool 3: compare two players (pandas decides who wins each stat) ----------
def compare_players(p1, p2):
    missing, ambiguous, players = [], {}, []

    for name in (p1, p2):
        found = get_player(name, limit=3, cols=COMPARE_COLS)
        if not found:
            missing.append(name)
        elif len(found) > 1:
            ambiguous[name] = [f"{p['web_name']} ({p['team_name']}, {p['pos_label']})" for p in found]
        else:
            players.append(found[0])

    if missing or ambiguous:
        return {"found": False, "missing": missing, "ambiguous": ambiguous}

    a, b = players
    better = {}
    for stat, higher_is_better in COMPARE_STATS.items():
        if a[stat] == b[stat]:
            better[stat] = "tie"
        elif (a[stat] > b[stat]) == higher_is_better:
            better[stat] = a["web_name"]
        else:
            better[stat] = b["web_name"]

    return {
        "found": True,
        "players": players,
        "better": better,
        "predicted_points_diff": round(a["predicted_points"] - b["predicted_points"], 2),
    }


# ---------- tool 4: captain pick from the user's squad ----------
def best_captain(squad_ids, n=3):
    res = df[df["player_id"].isin(squad_ids)]
    if res.empty:
        return []
    res = res.sort_values("predicted_points", ascending=False).head(n)
    return res[COLS].round(2).to_dict("records")


if __name__ == "__main__":
    print(top_players("MID", 6.0, 5))
    print(compare_players("Saka", "Palmer"))
    ids = df.loc[df["web_name"].isin(["Haaland", "Saka", "Raya"]), "player_id"].tolist()
    print(best_captain(ids))