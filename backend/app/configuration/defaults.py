"""Demo case (from the supplied H&M software screenshot) and model defaults. Demo values are EDITABLE EXAMPLES,
not manufacturer-validated performance data. Missing construction details are deliberately left as None."""
import copy

MODEL_VERSION = "0.1.0-preliminary"

DEMO_CASE = {
    "project": {"customer": "", "project_name": "", "reference_number": "", "tag_number": "1",
                "date": "2026-10-12", "engineer": "", "design_case": "Screenshot demo", "notes": ""},
    "equipment": {
        "brand": "H&M", "model_code": None, "configuration": "VHP", "refrigerant": "R134a", "rows": 4,
        "tube_nominal": "1/2", "tube_od_mm": None, "tube_thk_mm": 0.34, "tube_type": "inner_groove",
        "transverse_pitch_mm": None, "longitudinal_pitch_mm": None,
        "fin_material": "aluminium", "fin_thk_mm": 0.14, "fin_pitch_mm": 2.1,
        "fin_type": "sine_wave_rippled_edges", "fin_coating": "nano", "frame": "galvanized_steel",
        "tubes_per_row": 31, "fin_length_mm": 1000, "fin_height_mm": 984.25,
        "circuits": 2, "circuit_orientation": "vertical", "installation": "vertical",
        "altitude_m": 0, "site_pressure_pa": None,
    },
    "scenario": "heating",
    "supply": {"flow": 3000, "flow_unit": "cfm", "flow_basis": "actual", "input_mode": "db_rh",
               "db": 30, "rh": 50, "wb": None, "fin_length_mm": None},
    "exhaust": {"flow": 2118.88, "flow_unit": "cfm", "flow_basis": "actual", "input_mode": "db_wb",
                "db": 25, "rh": None, "wb": 18.7, "fin_length_mm": None},
    "models": {
        "thermal": {"ua_coeff": None, "ua_exponent": None, "ua_ref_velocity": 1.0,
                    "internal_resistance_k_per_kw": 0.0, "effectiveness_override": None,
                    "wet_bypass_factor": None},
        "pressure_drop": {"provider": "none", "coeff_pa_per_row": None, "exponent": None,
                          "valid_velocity_range": None, "calibrated": False, "source": ""},
    },
    "tolerances": {"energy_balance_pct": 1.0, "min_delta_t_k": 0.5},
}

# Values printed by the old software for the demo case (for discrepancy reporting only).
OLD_SOFTWARE_REFERENCE = {
    "supply": {"w_gkg": 13.31, "h_kjkg": 66.2, "wb_c": 22.53},
    "exhaust": {"w_gkg": 10.91, "h_kjkg": 64.21, "rh_pct": 55.0},
    "face_area_m2": 0.984, "face_velocity_ms": {"supply": 1.44, "exhaust": 1.02},
}


def demo_case():
    return copy.deepcopy(DEMO_CASE)
