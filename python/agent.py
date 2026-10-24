import re
import difflib
from typing import Optional

from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_ollama import ChatOllama

from tools import get_player, top_players, compare_players, best_captain
from rag import rag_chain

LLM_NAME = "llama3.1:8b"
DEBUG = True
NOT_FOUND = "I don't have that data."
STRICT_UNDER = True   # True: "under 6m" means below 6.0. False: up to and including 6.0

PREMIUM_MIN = {"GK": 5.0, "DEF": 5.5, "MID": 7.0, "FWD": 7.5}   # same as PRICE_CUTOFFS
BUDGET_MAX = {"GK": 4.0, "DEF": 4.5, "MID": 5.0, "FWD": 5.5}


def log(*args):
    if DEBUG:
        print("   [debug]", *args)


# ---------- 1. router ----------
router_prompt = ChatPromptTemplate.from_messages([
    ("system", """Classify the user's question about Fantasy Premier League into ONE label.

TOOL  = needs ranking, sorting, filtering by price/position, or comparing two players
        (e.g. "best 5 midfielders under 6m", "Saka or Palmer?", "cheapest forward")
RAG   = asks for facts about one named player or a descriptive lookup
        (e.g. "tell me about Haaland", "is Saka at home?", "who is injured?")
OTHER = greetings or anything unrelated to FPL data

Reply with the label only."""),
    ("human", "{question}"),
])
router = router_prompt | ChatOllama(model=LLM_NAME, temperature=0) | StrOutputParser()


def route(question: str) -> str:
    raw = router.invoke({"question": question}).strip().upper()
    for label in ("TOOL", "RAG", "OTHER"):
        if label in raw:
            return label
    return "RAG"


# ---------- 2. tools (validate everything the model sends) ----------
VALID_POSITIONS = {"GK", "DEF", "MID", "FWD"}
VALID_SORTS = {"predicted_points", "price", "avg_pts_last3", "ppg", "total_points"}
SORT_ALIASES = {"cheapest": "price", "priciest": "price", "expensive": "price",
                "cost": "price", "form": "avg_pts_last3", "points": "total_points",
                "best": "predicted_points", "predicted": "predicted_points"}


def to_float(x):
    """Strings, 'null' and 0 or negatives all mean 'not provided'."""
    try:
        v = float(x) if x not in (None, "", "null") else None
    except (TypeError, ValueError):
        return None
    return v if v and v > 0 else None


@tool
def top_players_tool(position: Optional[str] = None,
                     max_price: Optional[float] = None,
                     min_price: Optional[float] = None,
                     n: int = 5,
                     sort_by: str = "predicted_points",
                     ascending: bool = False):
    """Ranked list of players. position is GK, DEF, MID or FWD (optional).
    max_price and min_price are in millions (6.0 means 6.0m). Leave them out unless
    the user gives a number or says premium or budget.
    n is how many players to return.
    sort_by is one of: predicted_points (default, 'best'), price ('cheapest' or 'priciest'),
    avg_pts_last3 (recent form), ppg, total_points.
    ascending is true for 'cheapest' or 'lowest', false for 'best', 'most' or 'priciest'."""
    position = position.upper() if position else None
    if position not in (None, *VALID_POSITIONS):
        return []
    sort_by = SORT_ALIASES.get(str(sort_by).lower(), sort_by)
    if sort_by not in VALID_SORTS:
        sort_by = "predicted_points"
    try:
        n = max(1, min(int(n), 10))
    except (TypeError, ValueError):
        n = 5
    asc = str(ascending).lower() in ("true", "1", "yes")
    return top_players(position, to_float(max_price), n, sort_by, asc, to_float(min_price))


@tool
def get_player_tool(name: str):
    """Look up one player by name and return their price and predicted points."""
    return get_player(name)


@tool
def compare_players_tool(player1: str, player2: str):
    """Compare two players side by side by name."""
    return compare_players(player1, player2)


tools = [top_players_tool, get_player_tool, compare_players_tool]
tools_by_name = {t.name: t for t in tools}

llm = ChatOllama(model=LLM_NAME, temperature=0)
llm_with_tools = llm.bind_tools(tools)


# ---------- 3. Python decides every risky argument from the question text ----------
POS_WORDS = r"(goalkeeper|keeper|defender|midfielder|forward|striker|player)"
UP_WORDS = ("over", "above", "at least", "more than", ">")
STRICT_WORDS = ("under", "below", "less than", "<")

# words we correct typos towards
KEYWORDS = ["cheapest", "priciest", "premium", "budget", "midfielder", "defender",
            "forward", "striker", "goalkeeper", "keeper"]
# valid words we must NOT touch (plurals would otherwise be turned into singulars)
KNOWN = set(KEYWORDS) | {"midfielders", "defenders", "forwards", "strikers",
                         "goalkeepers", "keepers", "players", "player", "cheaper",
                         "best", "top", "under", "below", "over", "above"}


def normalise(q: str) -> str:
    """Lowercase and fix typos like 'cheapst' -> 'cheapest'."""
    words = []
    for w in q.lower().split():
        clean = w.strip("?!,;:").rstrip(".")
        if clean in KNOWN or not clean.isalpha():
            words.append(clean)
            continue
        close = difflib.get_close_matches(clean, KEYWORDS, n=1, cutoff=0.85)
        words.append(close[0] if close else clean)
    return " ".join(words)


def fix_top_args(args: dict, question: str) -> dict:
    args = dict(args)
    q = normalise(question)
    pos = str(args.get("position") or "").upper()

    # A. price limits: ignore the model, read the number from the question
    args.pop("max_price", None)
    args.pop("min_price", None)
    m = re.search(r"(under|below|less than|max|up to|over|above|at least|more than|<|>)"
                  r"\s*£?(\d+(?:\.\d+)?)", q)
    m2 = re.search(r"£?(\d+(?:\.\d+)?)\s*m\b", q)
    if m:
        word, value = m.group(1), float(m.group(2))
        if word in UP_WORDS:
            args["min_price"] = value
        elif word in STRICT_WORDS and STRICT_UNDER:
            args["max_price"] = round(value - 0.01, 2)
        else:
            args["max_price"] = value
    elif m2:
        args["max_price"] = float(m2.group(1))

    if "max_price" not in args and "min_price" not in args:
        if "premium" in q and pos in PREMIUM_MIN:
            args["min_price"] = PREMIUM_MIN[pos]
        if "budget" in q and pos in BUDGET_MAX:
            args["max_price"] = BUDGET_MAX[pos]

    # B. sort: superlatives decide, not the model
    if any(w in q for w in ("cheapest", "lowest price", "least expensive")):
        args["sort_by"], args["ascending"] = "price", True
    elif any(w in q for w in ("priciest", "most expensive", "highest price")):
        args["sort_by"], args["ascending"] = "price", False
    else:
        args["ascending"] = False

    # C. how many: a typed count wins, then singular means 1, else 5
    count = re.search(r"\b(?:top|best|cheapest|priciest)\s+(\d+)\b", q)
    singular = re.search(
        r"\b(?:best|cheapest|priciest|most expensive|which|who is the|who's the)\s+(?:the\s+)?"
        r"(?:premium\s+|budget\s+)?" + POS_WORDS + r"\b", q)
    if count:
        args["n"] = int(count.group(1))
    elif singular:
        args["n"] = 1
    else:
        args["n"] = 5
    return args


def run_tool_call(call: dict, question: str):
    tool_obj = tools_by_name.get(call["name"])
    if tool_obj is None:
        return {"error": f"unknown tool {call['name']}"}
    args = call["args"]
    if call["name"] == "top_players_tool":
        args = fix_top_args(args, question)
        log("fixed args:", args)
    try:
        return tool_obj.invoke(args)
    except Exception as e:
        return {"error": str(e)}


# ---------- 4. formatting: Python writes every tool answer, no LLM ----------
STAT_LABELS = {
    "predicted_points": "Predicted points",
    "avg_pts_last3": "Last-3 average",
    "ppg": "Points per game",
    "total_points": "Total points",
    "ownership_pct": "Ownership",
    "avg_fdr_next5": "Easier fixtures",
}


def to_text(data) -> str:
    """Plain numbered lines for a list of player dicts."""
    return "\n".join(
        f"{i}. " + ", ".join(f"{k}: {v}" for k, v in row.items())
        for i, row in enumerate(data, 1)
    )


def format_top(data) -> str:
    base = {"web_name", "team_name", "pos_label", "price", "predicted_points"}
    lines = []
    for i, p in enumerate(data, 1):
        extra = "".join(f", {k}: {v}" for k, v in p.items() if k not in base)
        lines.append(f"{i}. {p['web_name']} ({p['team_name']}, {p['pos_label']}) "
                     f"- £{p['price']}m, {p['predicted_points']} predicted points{extra}")
    return "\n".join(lines)


def format_compare(data) -> str:
    lines = []
    for p in data["players"]:
        lines.append(
            f"{p['web_name']} ({p['team_name']}, {p['pos_label']}): £{p['price']}m, "
            f"{p['predicted_points']} predicted points vs {p['opponent']}, "
            f"last-3 average {p['avg_pts_last3']}, {p['ppg']} points per game, "
            f"{p['total_points']} total points, owned by {p['ownership_pct']}%, "
            f"fixture difficulty {p['avg_fdr_next5']}"
        )
    lines.append("")
    for stat, winner in data["better"].items():
        lines.append(f"{STAT_LABELS[stat]}: {'tie' if winner == 'tie' else winner}")
    return "\n".join(lines)


def format_captain(data) -> str:
    top = data[0]
    lines = [f"Captain pick: {top['web_name']} ({top['team_name']}), "
             f"{top['predicted_points']} predicted points."]
    if len(data) > 1:
        rest = ", ".join(f"{p['web_name']} ({p['predicted_points']})" for p in data[1:])
        lines.append(f"Next best in your squad: {rest}.")
    return "\n".join(lines)


def failure_message(data):
    if not data:
        return NOT_FOUND
    if isinstance(data, dict):
        if "error" in data:
            return NOT_FOUND
        if data.get("found") is False:
            if data.get("ambiguous"):
                opts = "; ".join(f"{k}: {', '.join(v)}" for k, v in data["ambiguous"].items())
                return f"Which player do you mean? {opts}"
            if data.get("missing"):
                return "I couldn't find: " + ", ".join(data["missing"]) + "."
            return NOT_FOUND
    return None


# ---------- 5. dispatcher ----------
def answer(question: str, squad: Optional[list] = None) -> str:
    # captain questions need the user's squad
    if "captain" in question.lower():
        if not squad:
            return "Send your squad so I can pick a captain from your players."
        data = best_captain(squad)
        return format_captain(data) if data else NOT_FOUND

    label = route(question)
    log("route:", label)

    if label == "OTHER":
        return "I can help with FPL players: ask about a player, a comparison, or the best players by position and price."

    if label == "TOOL":
        msg = llm_with_tools.invoke(question)
        log("tool_calls:", msg.tool_calls)
        if not msg.tool_calls:
            return rag_chain.invoke(question)

        call = msg.tool_calls[0]
        data = run_tool_call(call, question)
        log("tool result:", data)

        fixed = failure_message(data)
        if fixed:
            return fixed

        if call["name"] == "top_players_tool":
            return format_top(data)
        if call["name"] == "compare_players_tool":
            return format_compare(data)
        return to_text(data)

    return rag_chain.invoke(question)


# ---------- 6. tests: the right answer comes from pandas ----------
# under 6m is strict, so max_price is 5.99 (set STRICT_UNDER = False and use 6.0 to change)
ranking_tests = [
    ("best 5 midfielders under 6m",           dict(position="MID", max_price=5.99, n=5)),
    ("who's the priciest striker?",           dict(position="FWD", sort_by="price", n=1)),
    ("which defender gives the most points?", dict(position="DEF", sort_by="total_points", n=1)),
    ("cheapest premium midfielder",           dict(position="MID", min_price=7.0, sort_by="price", ascending=True, n=1)),
    ("best forwards",                         dict(position="FWD", n=5)),
    ("cheapest goalkeeper",                   dict(position="GK", sort_by="price", ascending=True, n=1)),
    ("top 3 forwards",                        dict(position="FWD", n=3)),
    ("best defender under 5m",                dict(position="DEF", max_price=4.99, n=1)),
    ("cheapst defender",                      dict(position="DEF", sort_by="price", ascending=True, n=1)),
    ("best goalkeepers under 4.5m",           dict(position="GK", max_price=4.49, n=5)),
    ("top 3 MID under 7",                     dict(position="MID", max_price=6.99, n=3)),
]

if __name__ == "__main__":
    DEBUG = False          # set True to see every stage
    ok = 0
    for q, true_args in ranking_tests:
        expected = top_players(**true_args)
        got = answer(q).splitlines()
        passed = (len(got) == len(expected)
                  and all(e["web_name"] in line for e, line in zip(expected, got)))
        ok += passed
        print("OK " if passed else "BAD", q)
        if not passed:
            print("   expected:", [e["web_name"] for e in expected])
            print("   got:     ", got)
    print(f"\n{ok}/{len(ranking_tests)} ranking tests")

    print("\n--- other question types ---")
    for q in ["compare haaland and isak", "Martinez or Saka?", "tell me about Haaland",
              "injured players?", "hello"]:
        print("\n==", q)
        print("ANSWER:", answer(q))

    print("\n--- captain ---")
    print(answer("who should I captain?"))
    print(answer("who should I captain?", squad=[1, 2, 3]))   # replace with real player_ids