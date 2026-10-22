"""Demo case (from the supplied H&M software screenshot) and model defaults. Demo values are EDITABLE EXAMPLES,
not manufacturer-validated performance data. Missing construction details are deliberately left as None."""
import copy

MODEL_VERSION = "0.1.0-preliminary"

# Standard baseline engineering parameters for vertical heat pipe with wavy fins and R134a
DEFAULT_ENGINEERING_MODELS = {
    "thermal": {
        "ua_coeff": 0.45,  # kW/K per m2 face per row @ 1 m/s (standard wavy-fin VHP)
        "ua_exponent": 0.60,  # Face velocity power-law exponent
        "ua_ref_velocity": 1.0,
        "internal_resistance_k_per_kw": 0.0,
        "effectiveness_override": None,
        "wet_bypass_factor": 0.15,
        "source": "Standard engineering baseline (wavy fin, R134a)",
    },
    "pressure_drop": {
        "provider": "power_law_per_row",
        "coeff_pa_per_row": 12.5,  # Pa/row @ 1 m/s face velocity
        "exponent": 1.40,  # Velocity exponent
        "valid_velocity_range": [0.3, 5.0],
        "calibrated": False,
        "source": "Standard engineering baseline (wavy fin, R134a)",
    },
}

DEFAULT_GEOMETRY = {
    "tube_od_mm": 12.7,  # 1/2 in standard tube outside diameter
    "transverse_pitch_mm": 31.75,  # 1.25 in standard transverse pitch
    "longitudinal_pitch_mm": 27.5,  # Standard longitudinal pitch
}

DEMO_CASE = {
    "project": {"customer": "", "project_name": "", "reference_number": "", "tag_number": "1",
                "date": "2026-10-12", "engineer": "", "design_case": "Screenshot demo", "notes": ""},
    "equipment": {
        "brand": "H&M", "model_code": None, "configuration": "VHP", "refrigerant": "R134a", "rows": 4,
        "tube_nominal": "1/2", "tube_od_mm": 12.7, "tube_thk_mm": 0.34, "tube_type": "inner_groove",
        "transverse_pitch_mm": 31.75, "longitudinal_pitch_mm": 27.5,
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
    "models": copy.deepcopy(DEFAULT_ENGINEERING_MODELS),
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


def empty_case():
    c = demo_case()
    c["models"]["thermal"] = {
        "ua_coeff": None, "ua_exponent": None, "ua_ref_velocity": 1.0,
        "internal_resistance_k_per_kw": 0.0, "effectiveness_override": None,
        "wet_bypass_factor": None
    }
    c["models"]["pressure_drop"] = {
        "provider": "none", "coeff_pa_per_row": None, "exponent": None,
        "valid_velocity_range": None, "calibrated": False, "source": ""
    }
    c["equipment"]["tube_od_mm"] = None
    c["equipment"]["transverse_pitch_mm"] = None
    c["equipment"]["longitudinal_pitch_mm"] = None
    return c
