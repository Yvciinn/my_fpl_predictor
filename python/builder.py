import pandas as pd
import numpy as np
import pulp
from pulp import LpProblem, LpMaximize, LpVariable, lpSum, LpStatus, PULP_CBC_CMD
import json
from paths import PYTHON,BASE

gw=8


players = pd.read_csv(rf'{BASE}\python\outputs\gw_predictions.csv')
prob = LpProblem("FPL_Team_Selector", LpMaximize)
x = LpVariable.dicts("player", players.index, cat='Binary')

prob += lpSum([players.loc[i, 'predicted_points'] * x[i] for i in players.index])
#total = 15
prob += lpSum([x[i] for i in players.index]) == 15
#GK == 2 
prob += lpSum([x[i] for i in players.index if players.loc[i, 'pos_label'] == 'GK']) == 2
#DEF == 5 
prob += lpSum([x[i] for i in players.index if players.loc[i, 'pos_label'] == 'DEF']) == 5
#Mid == 5 
prob += lpSum([x[i] for i in players.index if players.loc[i, 'pos_label'] == 'MID']) == 5
#att == 3
prob += lpSum([x[i] for i in players.index if players.loc[i, 'pos_label'] == 'FWD']) == 3
#bdgt <=100
# budget <= 100
prob += lpSum([players.loc[i, 'price'] * x[i] for i in players.index]) <= 100
# max 3 players per club
for team in players['team'].unique():
    prob += lpSum([x[i] for i in players.index if players.loc[i, 'team'] == team]) <= 3
prob.solve(PULP_CBC_CMD(msg=0))

print(f"Status: {LpStatus[prob.status]}")


selected = players[[x[i].value() == 1 for i in players.index]].copy()
selected = selected.sort_values('pos_label')

print(f"\n total price: £{selected['price'].sum():.1f}m")
print(f"total predicted points: {selected['predicted_points'].sum():.2f}")

print("\n" + "="*60)
print("team selected")
print("="*60)
for pos in ['GK', 'DEF', 'MID', 'FWD']:
    print(f"\n--- {pos} ---")
    print(selected[selected['pos_label'] == pos][['web_name', 'opponent', 'price', 'predicted_points']].to_string(index=False))
print("===================================================")
selected['rank'] = selected.groupby('pos_label')['predicted_points'].rank(ascending=False)
formations = [
    {'DEF': 3, 'MID': 5, 'FWD': 2},
    {'DEF': 3, 'MID': 4, 'FWD': 3},
    {'DEF': 4, 'MID': 3, 'FWD': 3},
    {'DEF': 4, 'MID': 4, 'FWD': 2},
    {'DEF': 4, 'MID': 5, 'FWD': 1},
    {'DEF': 5, 'MID': 3, 'FWD': 2},
    {'DEF': 5, 'MID': 4, 'FWD': 1},
    {'DEF': 5, 'MID': 2, 'FWD': 3},
]

best_score=0
best_formation=None
best_lineup=None 

for formation in formations : 
    gk=selected[selected['pos_label']=='GK'].nlargest(1,'predicted_points')
    defs=selected[selected['pos_label']=='DEF'].nlargest(formation['DEF'],'predicted_points')
    mids=selected[selected['pos_label']=='MID'].nlargest(formation['MID'],'predicted_points')
    fwds=selected[selected['pos_label']=='FWD'].nlargest(formation['FWD'],'predicted_points')
    lineup=pd.concat([gk,defs,mids,fwds])
    score=lineup['predicted_points'].sum()

    if score>best_score :
        best_score = score
        best_formation=formation
        best_lineup=lineup

selected['is_starter']=selected.index.isin(best_lineup.index).astype(int)
sorted_lp=best_lineup.sort_values('predicted_points',ascending=False)
captain=sorted_lp.iloc[0]['web_name']
vice_captain=sorted_lp.iloc[1]["web_name"]
selected["is_captain"]=(selected["web_name"]==captain).astype(int)
selected["is_vice_captain"]=(selected["web_name"]==vice_captain).astype(int)
keep_cols = ['id','web_name', 'first_name', 'last_name', 'team', 
             'pos_label', 'price', 'opponent', 'was_home',
             'predicted_points', 'avg_pts_last3', 
             'is_starter', 'is_captain', 'is_vice_captain']

squad = {}
for pos in ['GK', 'DEF', 'MID', 'FWD']:
    squad[pos] = selected[selected['pos_label'] == pos][keep_cols].to_dict('records')

output = {
    "gameweek": gw,
    "generated_at": pd.Timestamp.now().isoformat(),
    "budget": {
        "total": 100.0,
        "spent": round(selected['price'].sum(), 1),
        "remaining": round(100.0 - selected['price'].sum(), 1)
    },
    "summary": {
        "total_predicted_points": round(best_lineup['predicted_points'].sum(), 2),
        "best_formation": f"{best_formation['DEF']}-{best_formation['MID']}-{best_formation['FWD']}"
    },
    "captain": captain,
    "vice_captain": vice_captain,
    "squad": squad
}
dump = PYTHON / 'outputs' / 'best_team.json'
with open(dump, 'w') as f:
    json.dump(output, f, indent=2)
    print("saved")                   