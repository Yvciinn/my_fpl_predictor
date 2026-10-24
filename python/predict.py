import joblib
import pandas as pd
import numpy as np
import sys
import json
import math
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent))
from paths import DATA, MODELS, PYTHON

df_model  = pd.read_csv(DATA / 'df_model.csv')
lookup    = pd.read_csv(DATA / 'player_lookup.csv')
fixtures  = pd.read_csv(DATA / 'fixtures_2627.csv')
encoding  = pd.read_csv(DATA / 'team_encoding.csv')
live      = pd.read_csv(PYTHON / 'fpl_live_dataset.csv')
model     = joblib.load(MODELS / 'fpl_model.pkl')

GW = 8  


gw_fixtures = fixtures[fixtures['GW'] == GW].copy()


live_players = live[
    (live['status'] == 'a') &
    ((live['chance_next_gw'] >= 75) | (live['chance_next_gw'].isna()))
].copy()

relegated = ['Burnley', 'West Ham', 'Wolves']
live_players = live_players[~live_players['team'].isin(relegated)]

transfer_keywords = ['has joined', 'transferred', 'on loan', 'left the club']
mask = live_players['news'].str.lower().str.contains('|'.join(transfer_keywords), na=False)
live_players = live_players[~mask]

# standardize team names 
name_map = {
    'Brighton & Hove Albion': 'Brighton',
    'Manchester City':        'Man City',
    'Manchester United':      'Man Utd',
    'Newcastle United':       'Newcastle',
    'Nottingham Forest':      "Nott'm Forest",
    'Tottenham Hotspur':      'Spurs',
    'Coventry City':          'Coventry',
    'Hull City':              'Hull',
    'Leeds United':           'Leeds',
    'Ipswich Town':           'Ipswich',
}
gw_fixtures['home_team'] = gw_fixtures['home_team'].replace(name_map)
gw_fixtures['away_team'] = gw_fixtures['away_team'].replace(name_map)

#map players to fixture
fixture_map = {}
for _, row in gw_fixtures.iterrows():
    fixture_map[row['home_team']] = {'opponent': row['away_team'], 'was_home': 1}
    fixture_map[row['away_team']] = {'opponent': row['home_team'], 'was_home': 0}

live_players['opponent'] = live_players['team'].map(lambda t: fixture_map.get(t, {}).get('opponent'))
live_players['was_home'] = live_players['team'].map(lambda t: fixture_map.get(t, {}).get('was_home'))
live_players = live_players.dropna(subset=['opponent'])

#match to historical ids
live_players['name'] = live_players['first_name'] + ' ' + live_players['last_name']
live_players = live_players.merge(lookup, on='name', how='left')
live_players = live_players.dropna(subset=['player_id'])

team_enc_map = encoding.set_index('team_name')['encoded'].to_dict()
team_enc_map['Coventry'] = 28
team_enc_map['Hull'] = 29

live_players['team_encoded']     = live_players['team'].map(team_enc_map)
live_players['opponent_encoded'] = live_players['opponent'].map(team_enc_map)

pos_enc = {'GK': 2, 'GKP': 2, 'DEF': 0, 'MID': 3, 'FWD': 1}
live_players['position'] = live_players['position'].map(pos_enc)

#form
live_players['avg_pts_last3']    = live_players['avg_pts_last3'].fillna(live_players['ppg'].astype(float))
live_players['avg_min_last3']    = live_players['avg_min_last3'].fillna(live_players['minutes'].astype(float) / 38)
live_players['avg_starts_last3'] = (live_players['avg_min_last3'] >= 60).astype(int)

#historical vs opp
avg_vs_opp = df_model.groupby(['player_id', 'opponent_team_name']).agg(
    avg_points_vs_opponent=('total_points', 'mean'),
    games_vs_opponent=('total_points', 'count')
).reset_index()
avg_vs_opp.loc[avg_vs_opp['games_vs_opponent'] < 3, 'avg_points_vs_opponent'] = None
avg_vs_opp = avg_vs_opp.drop(columns=['games_vs_opponent'])

live_players = live_players.merge(
    avg_vs_opp,
    left_on=['player_id', 'opponent_encoded'],
    right_on=['player_id', 'opponent_team_name'],
    how='left'
)

player_avg = df_model.groupby('player_id')['total_points'].mean()
live_players['player_avg_tmp'] = live_players['player_id'].map(player_avg)
live_players['avg_points_vs_opponent'] = live_players['avg_points_vs_opponent'].fillna(live_players['player_avg_tmp'])
live_players['avg_points_vs_opponent'] = live_players['avg_points_vs_opponent'].fillna(live_players['avg_points_vs_opponent'].median())
live_players = live_players.drop(columns=['player_avg_tmp'])

#opponent defensive stats
avg_gc  = df_model.groupby('opponent_team_name')['avg_goals_conceded_opponent'].mean().reset_index().rename(columns={'opponent_team_name': 'opp_enc'})
avg_cs  = df_model.groupby('opponent_team_name')['avg_clean_sheets_opponent'].mean().reset_index().rename(columns={'opponent_team_name': 'opp_enc'})
avg_gca = df_model.groupby('opponent_team_name')['avg_goals_conceded_away'].mean().reset_index().rename(columns={'opponent_team_name': 'opp_enc'})
avg_gch = df_model.groupby('opponent_team_name')['avg_goals_conceded_home'].mean().reset_index().rename(columns={'opponent_team_name': 'opp_enc'})

live_players = live_players.merge(avg_gc,  left_on='opponent_encoded', right_on='opp_enc', how='left').drop(columns=['opp_enc'])
live_players = live_players.merge(avg_cs,  left_on='opponent_encoded', right_on='opp_enc', how='left').drop(columns=['opp_enc'])
live_players = live_players.merge(avg_gca, left_on='opponent_encoded', right_on='opp_enc', how='left').drop(columns=['opp_enc'])
live_players = live_players.merge(avg_gch, left_on='opponent_encoded', right_on='opp_enc', how='left').drop(columns=['opp_enc'])

for col in ['avg_goals_conceded_opponent', 'avg_clean_sheets_opponent',
            'avg_goals_conceded_away', 'avg_goals_conceded_home']:
    live_players[col] = live_players[col].fillna(live_players[col].median())

#build features nd predict
live_players['value']             = (live_players['price'] * 10).astype(int)
live_players['team']              = live_players['team_encoded']
live_players['avg_minutes_last3'] = live_players['avg_min_last3']
live_players['avg_points_last3']  = live_players['avg_pts_last3']
live_players['GW']                = GW
live_players['season']            = 2027

features = ['position', 'value', 'GW', 'season', 'team', 'was_home',
            'player_id', 'opponent_team_name', 'avg_minutes_last3',
            'avg_starts_last3', 'avg_points_last3', 'avg_points_vs_opponent',
            'avg_goals_conceded_opponent', 'avg_clean_sheets_opponent',
            'avg_goals_conceded_away', 'avg_goals_conceded_home']

X = live_players[features].fillna(0)
live_players['predicted_points'] = model.predict(X)

#print(results)
live_players = live_players.sort_values('predicted_points', ascending=False)
pos_map_rev = {0: 'DEF', 1: 'FWD', 2: 'GK', 3: 'MID'}
live_players['pos_label'] = live_players['position'].map(pos_map_rev)

print("\n" + "="*60)
print(f"TOP 20 — GW{GW}")
print("="*60)
print(live_players[['web_name', 'opponent', 'pos_label', 'price', 'predicted_points']].head(20).to_string(index=False))

for pos in ['GK', 'DEF', 'MID', 'FWD']:
    print(f"\n--- {pos} ---")
    print(live_players[live_players['pos_label'] == pos][
        ['web_name', 'opponent', 'price', 'predicted_points']
    ].head(10).to_string(index=False))

#save CSV 
live_players.to_csv(PYTHON / 'outputs' / 'gw_predictions.csv', index=False)
print(f"\ngw_predictions.csv saved")

#add original team name
enc_to_team = encoding.set_index('encoded')['team_name'].to_dict()
live_players['team_name'] = live_players['team'].map(enc_to_team)

#Helper to recursively replace NaN with None
def replace_nan(obj):
    if isinstance(obj, list):
        return [replace_nan(item) for item in obj]
    if isinstance(obj, dict):
        return {k: replace_nan(v) for k, v in obj.items()}
    if isinstance(obj, float) and math.isnan(obj):
        return None
    return obj

#save all players JSON
tojson = live_players[['id',
    'player_id', 'web_name', 'team_name', 'pos_label', 'price',
    'ownership_pct', 'total_points', 'status', 'chance_next_gw',
    'news', 'avg_pts_last3', 'avg_min_last3', 'opponent',
    'was_home', 'predicted_points'
]]

players_list = json.loads(tojson.to_json(orient='records'))
players_list = replace_nan(players_list)

output_players = {
    "gameweek": GW,
    "generated_at": pd.Timestamp.now().isoformat(),
    "players": players_list
}

dump = PYTHON / 'outputs' / 'players.json'
with open(dump, 'w') as f:
    json.dump(output_players, f, indent=2)
print(f"players.json saved — {len(tojson)} players")
print(live_players.columns)

