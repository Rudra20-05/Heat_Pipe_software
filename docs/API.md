# API (FastAPI, prefix /api) - Executed and Verified

All endpoints are executed and verified with automated test suites (`test_api.py`).

| Method | Path | Purpose | Status |
|---|---|---|---|
| GET | /api/health | status + model version | Verified (200) |
| GET | /api/configuration | catalogue facts, discrepancies, demo case, feature status | Verified (200) |
| POST | /api/calculate | full calculation (422 with field errors on invalid input; never substitutes data) | Verified (200, 422) |
| POST | /api/validate-case | validation only | Verified (200) |
| POST | /api/psychrometrics | derived state for one stream (UI refresh) | Verified (200, 422) |
| POST | /api/sweep | airflow sweep `{case, factors}` | Verified (200, 422) |
| POST | /api/calibration/validate-dataset | multipart CSV validation (<= 2 MB) | Verified (200, 413, 422) |
| POST | /api/calibration/evaluate | multipart CSV + `models` JSON + `split` -> per-case errors, MAE/RMSE/bias | Verified (200) |
| POST | /api/calibration/fit | guarded fit (needs >= 6 train and >= 2 validate VHP rows) | Verified (200, refuses <6/2) |
| POST | /api/report/pdf, /api/report/csv | downloadable PDF report and CSV data export | Verified (200, 422) |
| POST | /api/projects | save case as JSON file in `HP_DATA_DIR` | Verified (200) |
| GET | /api/projects | list all saved project IDs | Verified (200) |
| GET | /api/projects/{pid} | retrieve saved project JSON by ID | Verified (200, 404) |

Interactive documentation (Swagger UI): `http://127.0.0.1:8000/docs`
