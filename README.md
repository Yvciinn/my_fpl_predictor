# FPL Predictor 🤖⚽

An AI-powered Fantasy Premier League team predictor built with a MERN stack and Python ML pipeline.

## What it does
- Predicts points for every FPL player each gameweek using Machine Learning
- Generates an optimal 15-player squad within budget constraints
- Provides a Squad Builder UI to build and evaluate your own team
- Includes an AI assistant chatbot for FPL advice

## Tech Stack
- **Frontend:** React, Axios
- **Backend:** Node.js, Express, MongoDB Atlas
- **ML Pipeline:** Python, scikit-learn, Random Forest, pandas
- **AI Assistant:** FastAPI, LLM agent

## ML Model
- Trained on 6 seasons of FPL data (156k rows)
- Features: form, fixtures, opponent difficulty, historical averages
- MAE: ~1.06 points per player per gameweek

## Project Structure
├── frontend/ # React app
├── backend/ # Express + MongoDB API
├── python/ # ML pipeline + FastAPI chatbot
└── data/ # Historical FPL data (not tracked)


## Setup
```bash
# Backend
cd backend && npm install && npm run dev

# Frontend  
cd frontend && npm install && npm start

# ML API
cd python && uvicorn api:app --port 8000
```

## Weekly Workflow
1. Run `fpl_data_collector.py` to fetch live player data
2. Run `predict.py` to generate predictions
3. Run `builder.py` to pick best 15
4. Run `npm run import` to push to MongoDB
