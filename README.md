# Smart Waste Water Prediction Treatment

Production-ready digital twin + forecasting system for wastewater treatment monitoring.

## Step 1 -> Data Generator Code
- Module: `backend/app/services/data_generator.py`
- Generates **24 hourly points/day** for only:
  - BOD
  - COD
  - pH
  - DO
  - NH3-N (`NH3_N`)
  - TP
- Realistic pattern logic:
  - 6 AM-10 AM: high load
  - 12 PM-4 PM: medium load
  - night: low load
- Correlation logic:
  - `COD ~ 2 * BOD`
  - DO inversely linked to BOD
- Daily abnormal operating events:
  - 3-6 anomaly hours every 24 hours
  - organic overload, low DO, pH shock, or nutrient spike
  - related parameters move together realistically, for example BOD/COD rise while DO drops

## Step 2 -> Dataset Creation
- Script: `scripts/create_dataset.py`
- Storage: `backend/data/synthetic_stp_data.csv`
- Default range: last 183 days (~6 months), hourly data

Continuous append mode:
- Script: `scripts/run_continuous_generator.py`
- Appends new generated hourly rows into the existing CSV instead of replacing it
- Default cadence: one new hour per cycle (3600 seconds)

Run:
```bash
python scripts/create_dataset.py
```

## Step 3 -> Model Code (CNN-LSTM-Attention)
- Architecture: `backend/app/models/cnn_lstm_attention.py`
- Training + inference: `backend/app/services/model_pipeline.py`
- Input: past 24-72h (configured at 72h)
- Output: next 24h, hour-by-hour, multi-feature forecast

Train manually:
```bash
python scripts/train_model.py
```

## Step 4 -> Backend API
- Framework: FastAPI
- Entry point: `backend/app/main.py`
- Routes: `backend/app/api/routes.py`

Endpoints:
- `POST /api/auth/login`
- `GET /api/data/current?hours=24`
- `GET /api/predictions/next-day?history_hours=72`
- `GET /api/alerts?source=both`
- `POST /api/admin/regenerate?days=45&seed=42` (admin only)

Run backend:
```bash
uvicorn app.main:app --reload --app-dir backend
```

## Step 5 -> Frontend Dashboard
- UI: React + Vite, reusing the original dashboard styling and behavior
- Files:
  - `frontend/index.html`
  - `frontend/src/App.jsx`
  - `frontend/src/main.jsx`
  - `frontend/app.js`
  - `frontend/styles.css`
- Features:
  - Login screen (admin/operator)
  - Real-time snapshot cards
  - 24-hour forecast cards
  - Color status (green/orange/red)
  - Real vs predicted chart
  - Alerts panel
  - Explainability text

Open in browser:
- `http://127.0.0.1:8000/`

Run React frontend locally:
```bash
cd frontend
npm install
npm run dev
```

Build React frontend:
```bash
cd frontend
npm run build
```

## Step 6 -> Integration
System flow:
1. Startup seeds/generates dataset (if missing)
2. Real-time endpoint serves latest hourly rows
3. Prediction endpoint trains/loads model from the latest dataset and forecasts the next 24 hours
4. Alert engine evaluates real + predicted records
5. Frontend fetches APIs and displays a weather-style 24-hour forecast view

## Authentication Roles
Default users:
- Admin: `admin` / `admin123`
- Operator: `operator` / `operator123`

Role behavior:
- `operator`: view-only dashboard
- `admin`: full access including regenerate endpoint

## Folder Structure
```text
prooooooooojjectt/
├─ backend/
│  ├─ app/
│  │  ├─ api/
│  │  │  ├─ routes.py
│  │  │  └─ schemas.py
│  │  ├─ core/
│  │  │  ├─ auth.py
│  │  │  ├─ config.py
│  │  │  └─ security.py
│  │  ├─ models/
│  │  │  └─ cnn_lstm_attention.py
│  │  ├─ services/
│  │  │  ├─ alert_engine.py
│  │  │  ├─ data_generator.py
│  │  │  ├─ data_store.py
│  │  │  ├─ explainability.py
│  │  │  └─ model_pipeline.py
│  │  └─ main.py
│  ├─ data/
│  └─ requirements.txt
├─ frontend/
│  ├─ index.html
│  ├─ app.js
│  └─ styles.css
├─ scripts/
│  ├─ create_dataset.py
│  └─ train_model.py
├─ .gitignore
└─ README.md
```

## Setup Instructions
1. Create venv and activate
2. Install dependencies
3. Run backend

```bash
python -m venv .venv
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
uvicorn app.main:app --reload --app-dir backend
```

## Sample Outputs
### Sample alert payload
```json
{
  "severity": "critical",
  "message": "Critical: DO dropping dangerously at 5 AM",
  "time": "2026-04-30T05:00:00",
  "source": "predicted"
}
```

### Sample explainability text
```text
Prediction influenced by rising COD and falling DO trends.
```

## Notes
- MLSS is intentionally excluded.
- Data is pattern-driven and not purely random.
- Exactly one spike is generated per day.
