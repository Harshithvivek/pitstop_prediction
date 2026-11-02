# F1 Pit Stop Prediction

A FastAPI inference service and Streamlit pit-wall dashboard for the supplied XGBoost classifier.

## Files needed at startup

Keep these files in the project directory:

- `pitstop.pkl` — the trained XGBoost classifier.
- `train.csv` — the training data used to rebuild the target encoders and median imputer that were not packaged with the model.

The API reproduces the feature engineering and preprocessing in `PitStops_XGBoost_Clean.ipynb`. It reads `train.csv` once at startup, derives the preprocessing statistics, and validates that its generated features match the model.

Pickle files can execute code when loaded. Only use a model file from a trusted source. The supplied model requires XGBoost 3.1.2; keep that version pinned when deploying this artifact.

## Run locally (Windows PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Start the API in one terminal:

```powershell
python -m uvicorn app:app --reload
```

In another terminal, start the Streamlit dashboard:

```powershell
python -m streamlit run streamlit_app.py
```

Open the Streamlit URL shown in the terminal for the dashboard, or visit `http://localhost:8501`. The sidebar shows whether the FastAPI model is ready. Open `http://127.0.0.1:8000/docs` for the interactive API. The service loads its model during startup and exits with an explicit error if the model or training data is unavailable or incompatible.

Optional artifact paths can be set with `MODEL_PATH` and `TRAIN_DATA_PATH`. Relative paths are resolved from this project directory.
Set `API_BASE_URL` to change the dashboard's default FastAPI address. The address can also be edited in the dashboard sidebar.

## Endpoints

- `GET /` — service links.
- `GET /health` — readiness check; returns `503` until the model is loaded.
- `POST /predict` — validated telemetry and next-lap pit-stop probability.

The request includes only the telemetry needed for prediction. Driver, circuit, and year are not collected or used by the retrained model. The lap-time field accepts either `LapTime (s)` (the training-data column name) or `LapTime_s`.

Example request:

```json
{
  "Compound": "HARD",
  "PitStop": 0,
  "LapNumber": 50,
  "Stint": 2,
  "TyreLife": 39,
  "Position": 8,
  "LapTime (s)": 78.491,
  "LapTime_Delta": -7.564,
  "Cumulative_Degradation": 21.019,
  "RaceProgress": 0.714286,
  "Position_Change": 5
}
```

Successful predictions return `pit_probability`, `recommendation`, `urgency_score`, and `tyre_life_laps`.

The Streamlit dashboard collects all 11 required telemetry fields, sends them to the FastAPI `/predict` endpoint, and displays the pit-call recommendation, probability, tyre urgency, tyre life, and track position.

The trained model is rebuilt without the `Driver`, `Race`, or `Year` features. To retrain it after changing the training data, run:

```powershell
python train_model.py
```

This writes the replacement model to `pitstop.pkl`. Keep `train.csv` alongside it; the API uses that file to rebuild compound encodings and feature medians.
