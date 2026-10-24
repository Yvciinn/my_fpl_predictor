import requests
import pandas as pd
import time
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).resolve().parent))
from paths import PYTHON

BASE_URL = "https://fantasy.premierleague.com/api"

live = pd.read_csv(PYTHON / "fpl_live_dataset.csv")

records = []
for i, pid in enumerate(live['id'].tolist()):
    print(f"[{i+1}/{len(live)}] player {pid}", end="\r")
    try:
        r = requests.get(f"{BASE_URL}/element-summary/{pid}/", timeout=10)
        history = r.json().get("history", [])
        if history:
            last3 = history[-3:]
            avg_pts = round(sum(h["total_points"] for h in last3) / len(last3), 2)
            avg_min = round(sum(h["minutes"] for h in last3) / len(last3), 2)
        else:
            avg_pts = avg_min = None
        records.append({"id": pid, "avg_pts_last3": avg_pts, "avg_min_last3": avg_min})
    except:
        records.append({"id": pid, "avg_pts_last3": None, "avg_min_last3": None})
    time.sleep(0.3)

history_df = pd.DataFrame(records)
live = live.drop(columns=['avg_pts_last3', 'avg_min_last3'])
live = live.merge(history_df, on='id', how='left')
live.to_csv(PYTHON / "fpl_live_dataset.csv", index=False)
print(f"\nDone! NaN: {live['avg_pts_last3'].isna().sum()}")
print(live[['web_name', 'avg_pts_last3', 'avg_min_last3']].head(10))