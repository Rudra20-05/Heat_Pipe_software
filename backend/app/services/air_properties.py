"""Airflow conversion and transport properties. SI internally."""
import math
from . import psychrometrics as P

CFM_TO_M3S = 0.45359237 ** 0 * 4.71947443e-4  # 1 ft3/min = 4.71947443e-4 m3/s (exact: 0.3048^3/60)
CFM_TO_M3S = 0.3048 ** 3 / 60.0
UNITS = {"cfm": CFM_TO_M3S, "m3/s": 1.0, "m3/h": 1 / 3600.0, "l/s": 1e-3}
# "Standard" air basis used when flow_basis == "standard": dry air at 20 degC, 101325 Pa
STD_T, STD_P = 20.0, 101325.0
RHO_DRY_STD = STD_P / (P.R_DA * (STD_T + 273.15))  # ~1.2041 kg dry air / m3


def to_m3s(q, unit):
    if unit not in UNITS:
        raise ValueError(f"Unsupported airflow unit '{unit}'")
    return q * UNITS[unit]


def flow(q, unit, basis, st):
    """Return dict(q_actual m3/s, m_dry kg/s) for an inlet state `st`.

    basis 'actual'  : entered flow is volumetric flow at inlet conditions.
    basis 'standard': entered flow is at STD conditions (dry air 20 C, 101.325 kPa); the dry-air
                      mass flow is q * RHO_DRY_STD and actual volume = m_dry * v(inlet).
    """
    q_si = to_m3s(q, unit)
    if basis == "actual":
        m_dry = q_si * st["rho_dry"]
        q_act = q_si
    elif basis == "standard":
        m_dry = q_si * RHO_DRY_STD
        q_act = m_dry * st["v"]
    else:
        raise ValueError("flow_basis must be 'actual' or 'standard'")
    return {"q_actual_m3s": q_act, "m_dry_kgs": m_dry, "m_humid_kgs": m_dry * (1 + st["w"])}


def viscosity_air(t):
    """Dynamic viscosity of air [Pa s], Sutherland (adequate for -40..85 degC)."""
    T = t + 273.15
    return 1.458e-6 * T ** 1.5 / (T + 110.4)
