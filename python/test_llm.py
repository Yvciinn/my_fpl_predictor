import shutil
import pandas as pd
from paths import PYTHON, DATA
from langchain_core.documents import Document
from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma

# ---------- load and decode ----------
df = pd.read_csv(PYTHON / "outputs" / "gw_predictions.csv")
teams = pd.read_csv(DATA / "team_encoding.csv")
teams["team_name"] = teams["team_name"].str.strip()
team_map = dict(zip(teams["encoded"], teams["team_name"]))

df["team_name"] = df["team"].map(team_map)
df["opponent"] = df["opponent"].str.strip()

# ---------- numbers into words ----------
PRICE_CUTOFFS = {          # (budget: price <= first, premium: price >= second)
    "GK":  (4.0, 5.0),
    "DEF": (4.5, 5.5),
    "MID": (5.0, 7.0),
    "FWD": (5.5, 7.5),
}

def price_tier(price: float, pos: str) -> str:
    budget_max, premium_min = PRICE_CUTOFFS[pos]
    if price >= premium_min:
        return "premium"
    if price <= budget_max:
        return "budget"
    return "mid-price"

def fixture_difficulty(fdr: float):
    if pd.isna(fdr):
        return None
    fdr = round(fdr, 2)          # avoids 2.9999 being labelled "easy"
    if fdr < 3.0:
        return "easy"
    if fdr < 3.3:
        return "average"
    return "difficult"

def n(count: int, word: str) -> str:
    return f"{count} {word}" if count == 1 else f"{count} {word}s"

df["price_tier"] = [price_tier(p, pos) for p, pos in zip(df["price"], df["pos_label"])]

# ---------- row -> text ----------
def row_to_text(r) -> str:
    parts = []

    parts.append(
        f"{r['web_name']} ({r['team_name']}) is a {r['price_tier']} {r['pos_label']} "
        f"priced at £{r['price']:.1f}m."
    )
    parts.append(
        f"Averaged {r['avg_pts_last3']:.1f} points over the last 3 games, "
        f"{r['ppg']:.1f} points per game, {int(r['total_points'])} total points this season."
    )

    venue = "at home" if r["was_home"] == 1 else "away"
    parts.append(
        f"Predicted {r['predicted_points']:.1f} points in gameweek {int(r['GW'])} "   # check GW vs GW+1
        f"against {r['opponent']} ({venue})."
    )

    diff = fixture_difficulty(r["avg_fdr_next5"])
    if diff:
        parts.append(f"Upcoming fixtures are {diff} (average difficulty {r['avg_fdr_next5']:.2f}).")

    pos = r["pos_label"]
    if pos == "GK":
        parts.append(f"{n(int(r['clean_sheets']), 'clean sheet')}, {n(int(r['saves']), 'save')}.")
    elif pos == "DEF":
        parts.append(f"{n(int(r['clean_sheets']), 'clean sheet')}, {n(int(r['goals']), 'goal')}, {n(int(r['assists']), 'assist')}.")
    else:
        parts.append(f"{n(int(r['goals']), 'goal')}, {n(int(r['assists']), 'assist')}.")

    parts.append(f"Owned by {r['ownership_pct']:.1f}% of managers.")

    if r["status"] != "a":
        chance = r["chance_next_gw"]
        chance_txt = f" ({int(chance)}% chance of playing)" if pd.notna(chance) else ""
        news = r["news"] if isinstance(r["news"], str) and r["news"].strip() else "flagged as a doubt"
        parts.append(f"Availability: {news}{chance_txt}.")

    return " ".join(parts)

# ---------- row -> Document ----------
def row_to_document(r) -> Document:
    metadata = {
        "player_id": int(r["player_id"]),
        "name": str(r["web_name"]),
        "team": str(r["team_name"]),
        "position": str(r["pos_label"]),
        "price": float(r["price"]),
        "price_tier": str(r["price_tier"]),
        "predicted_points": float(r["predicted_points"]),
        "gameweek": int(r["GW"]),
        "doc_type": "player_prediction",
    }
    return Document(page_content=row_to_text(r), metadata=metadata)

docs = [row_to_document(r) for _, r in df.iterrows()]
assert len(docs) == len(df)
print(docs[0].page_content)

# ---------- embeddings + Chroma ----------
if __name__ == "__main__":
    emb = OllamaEmbeddings(model="nomic-embed-text")
    shutil.rmtree(PYTHON / "chroma_db", ignore_errors=True)

    vectorstore = Chroma.from_documents(
        documents=docs,
        embedding=emb,
        collection_name="fpl_players",
        persist_directory=str(PYTHON / "chroma_db"),
        ids=[str(d.metadata["player_id"]) for d in docs],
    )
    print("stored:", vectorstore._collection.count())   # must be 331