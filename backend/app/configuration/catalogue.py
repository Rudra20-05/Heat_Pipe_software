"""Catalogue facts with source, and open discrepancies. Source: supplied H&M Heat Pipe Catalogue PDF (page numbers as printed)
and the supplied screenshot of the H&M selection software."""
CATALOGUE = {
    "source": "H&M Heat Pipe Catalogue (pp. 2-7) + selection-software screenshot",
    "standard": {"refrigerant": "R-134a", "airflow_cfm": [500, 50000], "rows_deep": [1, 8], "tube_geometry": "1/2 in",
                 "copper_tube_dia_label": "32 x 28 mm (1 1/4\" x 1 1/8\")", "tube_type": "Inner groove", "tube_thk_mm": 0.32,
                 "fin_material": "Aluminium", "fin_thk_mm": 0.12, "fin_type": "Sine wave with rippled edges", "fin_fpi": [8, 14],
                 "coating": "Pre-coated hydrophobic blue fins", "casing_mm": [1.2, 1.6], "pressure_test_bar": 34},
    "optional": {"tube_thk_mm": [0.34, 0.48], "fin_type": ["Louvered"], "fin_thk_mm": [0.14, 0.15],
                 "casing": ["GSS painted", "SS 304", "SS 316"], "coating": ["Nano coating", "Heresite coating"]},
    "page": {"principle": 2, "benefits": 3, "construction": 5, "materials": 6, "software_example_WRHP": 7},
}
DISCREPANCIES = [
    {"id": "D1", "item": "'Copper Tube Dia. 32 x 28 mm (1 1/4\" x 1 1/8\")' (catalogue p.6)",
     "note": "Label says diameter but 32 x 28 mm is not a 1/2 in tube OD; it looks like transverse x longitudinal pitch. "
             "Supporting evidence: 31 tubes -> 984.25 mm and 27 tubes -> 857.25 mm fin height both equal tubes x 31.75 mm. "
             "NOT adopted as an input; tube OD and pitches stay user-entered until H&M confirms."},
    {"id": "D2", "item": "Old software enthalpy values for the demo case",
     "note": "Supply 30 C/50% prints 66.2 kJ/kg (recomputed 64.21). Exhaust 25 C/WB 18.7 prints 64.21 kJ/kg (recomputed 52.91). "
             "Supply wet-bulb prints 22.53 C (recomputed 22.0 C). Humidity ratios and exhaust RH agree."},
    {"id": "D3", "item": "Catalogue p.7 example is WRHP (3 rows), not VHP", "note": "Shown only as a reference row; excluded from VHP validation."},
    {"id": "D4", "item": "Catalogue p.7 energy recovery 26.77 kW",
     "note": "From its own states and equal CFM on both sides, hot-side sensible duty is ~22.1 kW; cold side ~24.0 kW (same CFM at different densities). "
             "Old software appears to use 5000 CFM for both coils of a wrap-around pipe although the air at 9.3 C is denser."},
    {"id": "D5", "item": "Screenshot has 'Heating' selected but supply (30 C) is warmer than return (25 C)",
     "note": "Handled: heat direction follows inlet temperatures; a warning is issued."},
    {"id": "D6", "item": "Tubes per row 31 with 2 vertical circuits", "note": "31 is not divisible by 2; tubes per circuit not computed."},
    {"id": "D7", "item": "Fin spacing 2.1 mm vs model code '12F'", "note": "2.1 mm = 12.1 FPI, consistent with '12F' reading but unconfirmed."},
]
FEATURE_STATUS = {
    "psychrometrics": "implemented (ASHRAE), tested", "face_area_velocity": "implemented, tested against screenshot",
    "thermal_dry": "implemented model; requires user/calibrated UA coefficients (preliminary)",
    "wet_coil": "implemented ADP/bypass-factor; requires user bypass factor (preliminary)",
    "pressure_drop": "provider framework only; no built-in correlation (unavailable until configured/calibrated)",
    "charge": "unavailable", "weight": "core-only estimate when tube OD and pitches entered", "price": "unavailable",
    "calibration": "CSV import, metrics, guarded fit implemented", "api_layer": "written, NOT run in this build (FastAPI absent)",
    "frontend": "written, NOT built or run in this build (no npm network)",
}
