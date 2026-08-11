import joblib
import pandas as pd
import numpy as np
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent))
from paths import DATA, MODELS, PYTHON

df_model  = pd.read_csv(DATA / 'df_model.csv')
lookup    = pd.read_csv(DATA / 'player_lookup.csv')
fixtures  = pd.read_csv(DATA / 'fixtures_2627.csv')
encoding  = pd.read_csv(DATA / 'team_encoding.csv')
live      = pd.read_csv(PYTHON / 'fpl_live_dataset.csv')
model     = joblib.load(MODELS / 'fpl_model.pkl')

gw1 = fixtures[fixtures['GW'] == 1]
live_players = live[(live['status'] == 'a') & ((live['chance_next_gw'] >= 75) | (live['chance_next_gw'].isna()))]
relegated = ['Burnley', 'West Ham', 'Wolves']
live_players = live_players[~live_players['team'].isin(relegated)]

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

gw1['home_team'] = gw1['home_team'].replace(name_map)
gw1['away_team'] = gw1['away_team'].replace(name_map)

fixture_map = {}
for _, row in gw1.iterrows():
    fixture_map[row['home_team']] = {'opponent': row['away_team'], 'was_home': 1}
    fixture_map[row['away_team']] = {'opponent': row['home_team'], 'was_home': 0}

live_players['opponent'] = live_players['team'].map(lambda t: fixture_map.get(t, {}).get('opponent'))
live_players['was_home'] = live_players['team'].map(lambda t: fixture_map.get(t, {}).get('was_home'))

live_players = live_players.dropna(subset=['opponent'])


live_players["name"]=live_players["first_name"]+" "+live_players["last_name"]
live_players = live_players.merge(lookup, on='name', how='left')
live_players = live_players.dropna(subset=['player_id'])
team_enc_map = encoding.set_index('team_name')['encoded'].to_dict()

team_enc_map['Coventry'] = 28
team_enc_map['Hull'] = 29

live_players['team_encoded']     = live_players['team'].map(team_enc_map)
live_players['opponent_encoded'] = live_players['opponent'].map(team_enc_map)
enc = {'GK': 2, 'GKP': 2, 'DEF': 0, 'MID': 3, 'FWD': 1}
live_players['position'] = live_players['position'].map(enc)
live_players['avg_pts_last3'] = live_players['ppg'].astype(float)
live_players['avg_min_last3'] = live_players['minutes'].astype(float) / 38
live_players['avg_starts_last3'] = (live_players['avg_min_last3'] >= 60).astype(int)


avg_vs_opp = df_model.groupby(['player_id', 'opponent_team_name'])['total_points'].mean().reset_index()
avg_vs_opp.columns = ['player_id', 'opponent_team_name', 'avg_points_vs_opponent']
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


features = ['position', 'value', 'GW', 'season', 'team_encoded', 'was_home',
            'player_id', 'opponent_encoded', 'avg_minutes_last3',
            'avg_starts_last3', 'avg_points_last3', 'avg_points_vs_opponent',
            'avg_goals_conceded_opponent', 'avg_clean_sheets_opponent',
            'avg_goals_conceded_away', 'avg_goals_conceded_home']

#===================================================================================================
live_players['value'] = (live_players['price'] * 10).astype(int)
live_players['team'] = live_players['team_encoded']
live_players['avg_minutes_last3'] = live_players['avg_min_last3']
live_players['avg_points_last3'] = live_players['avg_pts_last3']
live_players['GW'] = 1
live_players['season'] = 2027

features = ['position', 'value', 'GW', 'season', 'team', 'was_home',
            'player_id', 'opponent_team_name', 'avg_minutes_last3',
            'avg_starts_last3', 'avg_points_last3', 'avg_points_vs_opponent',
            'avg_goals_conceded_opponent', 'avg_clean_sheets_opponent',
            'avg_goals_conceded_away', 'avg_goals_conceded_home']

X = live_players[features].fillna(0)
live_players['predicted_points'] = model.predict(X)

#================================================================================================
live_players = live_players.sort_values('predicted_points', ascending=False)
pos_map_rev = {0: 'DEF', 1: 'FWD', 2: 'GK', 3: 'MID'}
live_players['pos_label'] = live_players['position'].map(pos_map_rev)

print("\n" + "="*60)
print("top 20")
print("="*60)
print(live_players[['web_name', 'opponent', 'pos_label', 'price', 'predicted_points']].head(20).to_string(index=False))

print("\n" + "="*60)
print("top 10/position")
print("="*60)
for pos in ['GK', 'DEF', 'MID', 'FWD']:
    print(f"\n--- {pos} ---")
    print(live_players[live_players['pos_label'] == pos][
        ['web_name', 'opponent', 'price', 'predicted_points']
    ].head(10).to_string(index=False))

live_players.to_csv(DATA / 'gw1_predictions.csv', index=False)
print("saved")
