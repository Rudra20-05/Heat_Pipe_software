"""Thermal-conductance (UA) provider for each coil section.

UA_section = ua_coeff * A_face * N_rows * (v_face / v_ref) ** ua_exponent        [kW/K]

ua_coeff [kW/K per m2 face per row at v_ref] and ua_exponent have NO built-in default: they must be entered
or produced by calibration (calibration/fit.py). Without them the thermal result is 'insufficient data'.
Fin efficiency, tube-wall and air-side resistances are lumped into these coefficients for now; a
resistance-network provider can replace `section_ua` without touching the API or frontend.
"""


def section_ua(cfg, area_m2, rows, v_face):
    c, n = cfg.get("ua_coeff"), cfg.get("ua_exponent")
    if c is None or n is None:
        return None, "Thermal coefficients (ua_coeff, ua_exponent) not supplied; no manufacturer data available."
    if c <= 0 or not area_m2 or not rows or not v_face:
        return None, "Invalid thermal coefficient or missing geometry."
    vref = cfg.get("ua_ref_velocity", 1.0)
    return c * area_m2 * rows * (v_face / vref) ** n, None
