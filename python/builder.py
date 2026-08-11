import pandas as pd
import numpy as np
from pulp import *

BASE = r'C:\Users\yacin\Documents\myfpl_predictor'

players = pd.read_csv(rf'{BASE}\data\gw1_predictions.csv')
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