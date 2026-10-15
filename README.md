# Vertical Heat Pipe (VHP) Heat Exchanger Selection - preliminary v0.1.0

**Read first - status of this build**
* **Engine & Backend API:** Fully tested and verified. 53 unit and automated API tests pass (`cd backend && python -m unittest discover -s tests -v` or `pytest`).
* **Frontend Web Application:** Verified running on React 18 + Vite (`npm run dev`, `npm run build`), with full interactive browser verification: demo case loading, debounced psychrometric derivation, execution of calculation, status badge rendering, project persistence (save/open), calibration dataset evaluation & parity plotting, and responsive mobile layout.
* **Engineering Data Status:** Thermal and pressure-drop results for H&M equipment remain **unavailable until coefficients are entered or calibrated** - no H&M VHP performance data has been provided yet, and none was invented or guessed. See `docs/VALIDATION.md`, `docs/ASSUMPTIONS.md`.

## Prerequisites (Windows)
Python 3.11+ and Node.js 20+.

## Backend
```powershell
cd heat-pipe-selection
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
cd backend
python -m unittest discover -s tests -v      # runs all 53 tests (or: pytest)
uvicorn app.main:app --reload --port 8000
```
Interactive API documentation is accessible at `http://127.0.0.1:8000/docs`.

## Frontend (second terminal)
```powershell
cd heat-pipe-selection\frontend
npm install
npm run dev
```
Open `http://localhost:5173` (the Vite dev server proxies `/api` to port 8000).

## Using the Selection Tool
1. **Demo Case:** Transcribed from the H&M VHP screenshot; loads automatically on application start. Press **Calculate Performance**: psychrometrics, face area (~0.984 m²), and face velocities (1.44 / 1.02 m/s) are calculated. Thermal and ΔP show "Unavailable" with explicit lists of missing inputs.
2. **Project Storage:** Save projects to server disk (`HP_DATA_DIR`) by entering a project ID or using auto-generated IDs. Saved projects populate the dropdown and can be loaded back into the interface.
3. **Advanced Mode:** Check **Advanced mode** to specify custom tube OD, longitudinal/transverse pitches, UA coefficients, effectiveness overrides, wet-coil bypass factor, and ΔP power-law coefficients (all tagged as preliminary).
4. **Calibration & Parity Plot:** Upload reference CSV files (following `backend/sample_data/reference_template.csv`). Evaluate predictions against reference points with MAE/RMSE/bias error metrics and a real-data parity plot ($y = x$). Guarded fitting enforces $\ge 6$ training rows and $\ge 2$ validation rows for VHP.
5. **Reports:** Generate PDF reports (`/api/report/pdf`) or export CSV summaries (`/api/report/csv`).

## Persistence / Deployment
Projects are JSON files stored in `HP_DATA_DIR` (default `backend/data/projects`). `docker compose up --build` runs the API. The frontend can be built for production with `npm run build` and served from `frontend/dist`.

## Implementation Status
| Feature | Status | Notes |
|---|---|---|
| Psychrometrics, CFM/standard-flow conversion, altitude | Implemented & verified | ASHRAE Hyland-Wexler equations; round-trip validated |
| Face area, face velocity | Implemented & verified | 0.98425 m², 1.44 / 1.02 m/s matching reference screenshot |
| Dry thermal model | Implemented & verified | Requires user-entered or calibrated UA coefficients |
| Wet-coil / condensate | Implemented & verified | ADP / bypass-factor model; requires entered bypass factor |
| Pressure drop | Provider framework verified | No built-in correlation; requires verified coefficients |
| Refrigerant charge, price | Unavailable | Awaiting internal volumes, charge rules, price tables |
| Weight | Core estimate implemented | Requires tube OD and longitudinal pitch |
| Project persistence | Implemented & verified | Save, list, and load project endpoints tested |
| Calibration & evaluation | Implemented & verified | Guarded fit refuses insufficient data; evaluation metrics & parity plot |
| PDF / CSV exports | Implemented & verified | Generated and validated via automated tests |
| FastAPI layer | Implemented & verified | 24 automated API tests in `test_api.py` passing |
| React 18 + Vite frontend | Implemented & verified | Built with zero errors; verified in browser |

## Troubleshooting
* `ModuleNotFoundError: app` - run uvicorn from the `backend` folder.
* Frontend shows "Backend unreachable" - ensure uvicorn is running on port 8000 first.
* 422 responses return field-level error messages; check input values.
* PowerShell blocks `npm` or `activate` - run `Set-ExecutionPolicy -Scope Process RemoteSigned` or use `npm.cmd`.
