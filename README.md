# VoltWatch Simulator

VoltWatch Simulator is an end-to-end battery telemetry simulation platform that emulates a 16-cell lithium-ion Battery Management System (BMS), streams telemetry over MQTT and REST, persists telemetry in SQLite, and visualizes data in a React dashboard.

## Architecture

Battery Telemetry Simulator (Python)
-> MQTT + REST
-> Flask Backend API
-> SQLite Database
-> React Dashboard

## Project Structure

```text
voltwatch-simulator/
  backend/
    __init__.py
    app.py
    config.py
    models.py
    routes.py
    database.py
    mqtt_client.py
    battery_simulator.py
  frontend/
    package.json
    public/
      index.html
    src/
      index.js
      App.js
      Dashboard.js
      TelemetryChart.js
      api.js
      styles.css
  scripts/
    run_simulator.py
  requirements.txt
  README.md
```

## Features

- Simulates a fleet of 10+ batteries (16-cell Li-ion each) every 5 seconds
- Publishes telemetry to MQTT topic `voltwatch/battery/telemetry`
- Sends telemetry to Flask API endpoint `/api/telemetry`
- Stores telemetry in SQLite database
- Provides API endpoints for latest, history, and battery status
- Displays real-time charts and latest records on React dashboard
- Implements health state rules: `GOOD`, `WARNING`, `CRITICAL`

## Telemetry Payload

```json
{
  "device_id": "battery_pack_01",
  "timestamp": "2026-04-07T12:00:00+00:00",
  "pack_voltage": 52.38,
  "pack_current": 12.6,
  "soc": 91.4,
  "temperature": 33.2,
  "cycle_count": 4,
  "cell_voltages": [3.45, 3.44, 3.46, 3.45, 3.43, 3.47, 3.45, 3.44, 3.46, 3.45, 3.43, 3.44, 3.46, 3.45, 3.47, 3.44],
  "alarms": []
}
```

## Alarm Rules

- `OVER_TEMPERATURE` when temperature > 45 C
- `PACK_OVER_VOLTAGE` when pack voltage > 58 V
- `PACK_UNDER_VOLTAGE` when pack voltage < 44 V
- `CELL_IMBALANCE` when max cell delta > 0.1 V

## Health Rules

- `CRITICAL` when pack voltage outside limits
- `WARNING` when temperature > 40 C or cell imbalance > 0.08 V
- `GOOD` otherwise

## Backend API Endpoints

- `POST /api/telemetry` -> ingest telemetry payload
- `GET /api/telemetry/latest` -> fetch latest telemetry
- `GET /api/telemetry/history?limit=50` -> fetch historical telemetry
- `GET /api/powerbi/telemetry?limit=1000` -> fetch flat, Power BI-ready telemetry rows
- `GET /api/powerbi/telemetry?device_id=battery_pack_01&start=2026-04-01T00:00:00+00:00&end=2026-05-01T00:00:00+00:00` -> time-range extraction for one battery
- `GET /api/battery/status` -> fetch health + latest telemetry
- `GET /api/reports/monthly?month=YYYY-MM` -> export monthly CSV summary for all batteries
- `GET /api/reports/monthly?month=YYYY-MM&device_id=battery_pack_01` -> export monthly CSV for one battery

## Monthly Report Export

The dashboard includes month pickers and export buttons for:

- All batteries (from Battery List page)
- Selected battery (from Battery Details page)

You can also export directly from API:

```bash
curl -L "http://localhost:5000/api/reports/monthly?month=2026-04" -o monthly_all.csv
curl -L "http://localhost:5000/api/reports/monthly?month=2026-04&device_id=battery_pack_01" -o monthly_pack_01.csv
```

## Power BI Connection

Use the Power BI Web connector against this endpoint:

- `http://localhost:5000/api/powerbi/telemetry?limit=1000`

Optional filter example:

- `http://localhost:5000/api/powerbi/telemetry?device_id=battery_pack_01&start=2026-04-01T00:00:00+00:00&end=2026-05-01T00:00:00+00:00`

Power BI Desktop steps:

1. Get Data -> Web
2. Paste the endpoint URL above
3. In Navigator, select `items` and click To Table
4. Expand columns to flatten all fields (`pack_voltage`, `soc`, `cell_01` ... `cell_16`, `health`)
5. Change `timestamp` type to Date/Time
6. Load and build visuals

Refresh note:

- Keep the VoltWatch backend running on `http://localhost:5000` while refreshing in Power BI Desktop.

## Run Instructions

### macOS

Install Python 3 and Node.js (including npm) if they are not already installed.
Run these commands from the project root.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m backend.app
```

The backend starts at `http://localhost:5000`. Keep this terminal open.

In a second Terminal window, from the project root, activate the environment and
start the simulator:

```bash
source .venv/bin/activate
python scripts/run_simulator.py --interval 5
```

By default, this runs 10 battery devices (`battery_pack_01` to `battery_pack_10`).
To simulate more batteries:

```bash
python scripts/run_simulator.py --interval 5 --battery-count 20
```

In a third Terminal window, install frontend dependencies and start the dashboard:

```bash
cd frontend
npm ci
npm start
```

Dashboard runs on `http://localhost:3000` and reads API from `http://localhost:5000`.
Keep the backend and frontend terminals open while using the app.

If port 5000 is already in use on your Mac, start the backend on port 5001:

```bash
API_PORT=5001 python -m backend.app
```

In the frontend terminal, set its API URL to match:

```bash
REACT_APP_API_BASE=http://localhost:5001 npm start
```

## Continuous Integration

GitHub Actions runs on pushes, pull requests, and manual dispatch. It compiles the
Python backend and simulator, runs the backend smoke test, installs frontend
dependencies with `npm ci`, and builds the React dashboard.

## Notes

- SQLite database file defaults to `voltwatch.db` in project root.
- MQTT broker defaults to `broker.hivemq.com:1883`.
- MQTT topic defaults to `voltwatch/battery/telemetry`.
- CORS is enabled for local frontend development.
