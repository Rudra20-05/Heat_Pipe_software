# Validation status (actually run in this build)

Test command: `cd backend && python -m unittest discover -s tests -v` (53 tests, all passing; also verified with `pytest`).
Frontend verification: `npm run build` (production build clean) and interactive browser verification on `http://localhost:5173`.

## What was verified

### Calculation engine (29 tests in `test_core.py`)
* Saturation pressure, altitude pressure, density, CFM conversion against reference values.
* Round-trip RH <-> wet-bulb <-> W; limits (RH range, wet-bulb > dry-bulb, supersaturation, altitude range).
* Face area and velocity of the demo case: 0.98425 m², 1.4385 m/s (supply), 1.016 m/s (exhaust) vs screenshot 0.984 / 1.44 / 1.02.
* Dry model: energy balance closes to ~1e-13 %; direction reverses with inlet temperatures; no moisture change; zero flow of heat at equal temperatures; thermal unavailable (no fake numbers) without coefficients.
* Wet model with bypass factor: energy balance closes to ~1e-14 %, outlet RH <= 100 %, condensate > 0; without BF the result is 'wet_coil_required'.
* Mechanics tests use ARBITRARY test coefficients; they do not predict H&M performance.

### API layer and workflows (24 tests in `test_api.py`)
* Health (`/api/health`) and catalogue configuration (`/api/configuration`).
* Schema validation: empty bodies, unrecognized extra fields (forbidden), invalid scenarios, out-of-range RH, negative rows, unsupported configurations (WRHP/HHP) all return HTTP 422 with structured field-level error details.
* Successful demo calculation: geometry, airflows, face area/velocity, and psychrometrics match expected values; thermal and dP report `status="unavailable"` with explicit missing fields.
* No fake results on failure: invalid inputs return 422 without producing partial/fake performance blocks.
* CSV uploads: oversized files (> 2 MB) return HTTP 413; malformed content returns HTTP 422; template CSV parsed correctly with non-VHP row excluded from VHP evaluation.
* Guarded fit refusal: `/api/calibration/fit` refuses fitting when dataset contains fewer than 6 training or 2 validation VHP rows.
* Report downloads: `/api/report/pdf` returns valid binary `%PDF`, `/api/report/csv` returns valid comma-separated values.
* Psychrometrics endpoint: derived properties refresh accurately.
* Airflow sweep endpoint: scales flow factors accurately.
* Project persistence: save project, list projects, and fetch project endpoints tested.

### Frontend interactive verification (tested via browser agent)
* Demo case automatically loads on startup.
* Project save and load functionality tested end-to-end with server persistence.
* Debounced psychrometric derivation refreshes properly when inputs change.
* Calculation shows tagged results and clearly distinguishes "unavailable" outputs with missing reasons.
* Model status badges correctly display preliminary, calibrated, calculated, entered, and unavailable states.
* Reference CSV upload, validation report, guarded fit refusal dialog, and parity plotting verified.
* Responsive wrapping verified on narrow mobile viewports (down to 400px width).

## Old-software / catalogue discrepancies found (recomputed with ASHRAE equations at 101325 Pa)
| Item | Old software | Recomputed |
|---|---|---|
| Supply 30 C / 50 %: humidity ratio | 13.31 g/kg | 13.31 (agrees) |
| Supply enthalpy | 66.2 kJ/kg | 64.21 |
| Supply wet-bulb | 22.53 C | 22.0 |
| Exhaust 25 C / WB 18.7: RH | 55 % | 55.05 (agrees) |
| Exhaust humidity ratio | 10.91 g/kg | 10.9 (agrees) |
| Exhaust enthalpy | 64.21 kJ/kg | 52.91 (the old value equals the recomputed *supply* enthalpy) |
| Catalogue p.7 inlet (33.8 C/WB 25.8): RH, W, h | 53.19 %, 17.68, 79.33 | 53.22, 17.68, 79.35 (agrees) |
| Catalogue p.7 energy recovery | 26.77 kW | hot-side sensible ~22.1 kW, cold side ~24.0 kW at equal CFM (different densities) |

The p.7 example is a WRHP and is not a VHP validation point. Temperature effectiveness there (32.98 %) is reproduced from its own temperatures.

## NOT validated (waiting on manufacturer data)
No measured or certified performance data for H&M VHP units has been provided. As a result, thermal capacity ($Q$), temperature effectiveness ($\varepsilon$), and air-side pressure drop ($\Delta P$) predictions cannot be manufacturer-certified until measured test datasets (at least 6 training + 2 validation cases per configuration) are imported through the calibration pipeline.
