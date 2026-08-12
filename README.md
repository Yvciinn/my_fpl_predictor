# ⚽ FPL Predictor — Phase 1

A machine learning pipeline that predicts Fantasy Premier League points for every player ahead of a gameweek, using historical performance data, fixture difficulty, and opponent strength.

Built to combine two things I'm into — football and machine learning — and to move past gut-feeling FPL picks toward data-driven ones.

> **Status:** Phase 1 — data pipeline + ML prediction engine (this repo).
> **Next:** Phase 2 will wrap this into a full MERN stack web app that generates the optimal lineup for the current gameweek automatically. Stay tuned.

![Prediction results](img/resultat.png)

---

## What it does

1. Scrapes historical Premier League fixture and gameweek data across 6 seasons.
2. Engineers features per player: rolling form, performance vs specific opponents, opponent defensive strength, fixture difficulty.
3. Trains and compares several regression models (Linear, Ridge, Lasso, Random Forest, XGBoost, LightGBM, and a Voting ensemble) to predict a player's Fantasy points for the next gameweek.
4. Pulls **live** current-season data from the official FPL API.
5. Generates ranked point predictions for every available player, overall and by position.

## Project structure

```
myfpl_predictor/
├── data/                          # all processed CSVs
│   ├── df_model.csv               # engineered training dataset
│   ├── fixtures_2627.csv          # current season fixture list
│   ├── player_lookup.csv          # name ↔ player_id mapping
│   ├── team_encoding.csv          # team name ↔ encoded id mapping
│   └── gw1_predictions.csv        # latest output predictions
├── models/
│   ├── fpl_model.pkl              # best single model (Linear Regression)
│   └── fpl_ensemble.pkl           # voting ensemble
├── img/
│   └── resultat.png
├── python/
│   ├── fixtures.ipynb             # scrapes current season fixtures
│   ├── features.ipynb             # builds the historical training dataset
│   ├── model.ipynb                # trains and compares ML models
│   ├── fpl_data_collector.py      # pulls live FPL API data
│   ├── predict.py                 # generates gameweek predictions
│   └── paths.py                   # portable path resolver (see below)
└── Fantasy-Premier-League-master/ # historical per-season data source
```

## Setup

```bash
git clone https://github.com/Yvciinn/my_fpl_predictor.git
cd my_fpl_predictor
pip install -r requirements.txt
```

Paths are resolved automatically via `python/paths.py` — no manual configuration needed regardless of where you clone the project.

## How to run

Run in this order:

1. **`python/fixtures.ipynb`** — pulls the current season's fixture list.
2. **`python/features.ipynb`** — builds the historical training dataset from `Fantasy-Premier-League-master/`.
3. **`python/model.ipynb`** — trains and evaluates models, saves the best ones to `models/`.
4. **`python/fpl_data_collector.py`** — pulls live player data for the upcoming gameweek.
   ```bash
   python fpl_data_collector.py
   ```
5. **`python/predict.py`** — generates and saves the gameweek's point predictions.
   ```bash
   python predict.py
   ```

Output: `data/gw1_predictions.csv`, plus a console printout of the top 20 players overall and the top 10 per position.

## Model results (validation season: 2025/26)

| Model | MAE | RMSE |
|---|---|---|
| **Random Forest** ✅ | **1.06** | **2.13** |
| LightGBM | 1.10 | 2.20 |
| XGBoost | 1.09 | 2.21 |
| Ensemble | 1.16 | 2.19 |
| Lasso | 1.21 | 2.18 |
| Linear Regression | 1.22 | 2.21 |
| Ridge | 1.22 | 2.21 |

Random Forest gave the best validation performance on this dataset (lowest MAE and RMSE) — the current production model (`fpl_model.pkl`) is the tuned Random Forest from `search_rf.best_estimator_`.

## Data sources

- [Official Fantasy Premier League API](https://fantasy.premierleague.com/api/) — live player, team, and fixture data.
- [Premier League Pulse Live API](https://footballapi.pulselive.com) — official fixture schedule.
- [vaastav/Fantasy-Premier-League](https://github.com/vaastav/Fantasy-Premier-League) — historical per-gameweek player data.

## Tech stack

Python, pandas, scikit-learn, XGBoost, LightGBM, joblib, requests.

## Roadmap

- [x] Phase 1 — data pipeline + ML prediction engine
- [ ] Phase 2 — full MERN stack web app: live gameweek lineup optimizer, auto-selecting the best XI + captain under budget and formation constraints
- [ ] Phase 3 — deployment + weekly automated predictions

## License

MIT

## Author

Built by Yassine Khemiri — [LinkedIn](https://www.linkedin.com/in/yassine-khemiri-602259333/) · [GitHub](https://github.com/Yvciinn)
