"""Moist-air psychrometrics (ASHRAE Fundamentals 2017, Ch.1, SI units).

Conventions: temperatures in degC, pressure in Pa, humidity ratio W in kg water / kg dry air,
enthalpy in kJ/kg dry air, specific volume in m3/kg dry air, RH in percent (0-100).
Saturation pressure: Hyland-Wexler. Moist-air states are accepted for -40..85 degC;
outside that range StateError is raised (no silent extrapolation).
"""
import math
from scipy.optimize import brentq

T_MIN, T_MAX = -40.0, 85.0
R_DA = 287.042  # J/(kg K)


class StateError(ValueError):
    """Physically impossible or out-of-range psychrometric state."""


def _check_t(t):
    if not (isinstance(t, (int, float)) and math.isfinite(t)) or not (T_MIN <= t <= T_MAX):
        raise StateError(f"Dry-bulb temperature {t} degC outside supported range {T_MIN}..{T_MAX}")


def p_ws(t):
    """Saturation vapour pressure [Pa] (over water for t>=0, over ice below)."""
    T = t + 273.15
    if t >= 0:
        c = (-5.8002206e3, 1.3914993, -4.8640239e-2, 4.1764768e-5, -1.4452093e-8, 6.5459673)
        return math.exp(c[0] / T + c[1] + c[2] * T + c[3] * T**2 + c[4] * T**3 + c[5] * math.log(T))
    c = (-5.6745359e3, 6.3925247, -9.677843e-3, 6.2215701e-7, 2.0747825e-9, -9.484024e-13, 4.1635019)
    return math.exp(c[0] / T + c[1] + c[2] * T + c[3] * T**2 + c[4] * T**3 + c[5] * T**4 + c[6] * math.log(T))


def p_atm_altitude(z):
    """Standard-atmosphere pressure [Pa] at altitude z [m]. Valid -500..11000 m."""
    if not (isinstance(z, (int, float)) and math.isfinite(z)) or not (-500 <= z <= 11000):
        raise StateError("Altitude must be within -500..11000 m for the standard-atmosphere formula; "
                         "enter a site pressure override instead.")
    return 101325.0 * (1 - 2.25577e-5 * z) ** 5.2559


def w_from_pv(pv, p):
    if pv < 0 or pv >= p:
        raise StateError("Vapour pressure must satisfy 0 <= Pv < P")
    return 0.621945 * pv / (p - pv)


def pv_from_w(w, p):
    return p * w / (0.621945 + w)


def w_sat(t, p):
    pws = p_ws(t)
    if pws >= p:
        raise StateError("Saturation pressure exceeds total pressure at this temperature")
    return w_from_pv(pws, p)


def w_from_db_rh(t, rh, p):
    _check_t(t)
    if not (0 <= rh <= 100):
        raise StateError("Relative humidity must be within 0..100 %")
    return w_from_pv(rh / 100.0 * p_ws(t), p)


def rh_from_db_w(t, w, p):
    return 100.0 * pv_from_w(w, p) / p_ws(t)


def _w_wb(t, twb, p):
    ws = w_sat(twb, p)
    if twb >= 0:
        return ((2501 - 2.326 * twb) * ws - 1.006 * (t - twb)) / (2501 + 1.86 * t - 4.186 * twb)
    return ((2830 - 0.24 * twb) * ws - 1.006 * (t - twb)) / (2830 + 1.86 * t - 2.1 * twb)


def w_from_db_wb(t, twb, p):
    """Humidity ratio from dry-bulb and thermodynamic wet-bulb (ASHRAE eq. 35/37)."""
    _check_t(t)
    if twb > t + 1e-9:
        raise StateError("Wet-bulb temperature cannot exceed dry-bulb temperature")
    w = _w_wb(t, twb, p)
    if w < 0:
        raise StateError("Wet-bulb too low for this dry-bulb: implies negative humidity ratio")
    return w


def wb_from_db_w(t, w, p):
    _check_t(t)
    if w < 0:
        raise StateError("Humidity ratio must be >= 0")
    if w > w_sat(t, p) * (1 + 1e-9):
        raise StateError("Humidity ratio exceeds saturation at this dry-bulb temperature")
    f = lambda twb: _w_wb(t, twb, p) - w
    if f(t) <= 0:
        return t
    lo = -60.0
    if f(lo) > 0:
        raise StateError("Cannot bracket wet-bulb temperature")
    return brentq(f, lo, t, xtol=1e-10)


def dew_point(w, p):
    if w <= 0:
        raise StateError("Dew point undefined for zero humidity ratio")
    pv = pv_from_w(w, p)
    return brentq(lambda t: p_ws(t) - pv, -80.0, 100.0, xtol=1e-10)


def enthalpy(t, w):
    return 1.006 * t + w * (2501.0 + 1.86 * t)


def spec_volume(t, w, p):
    """m3 per kg dry air."""
    return R_DA * (t + 273.15) * (1 + 1.607858 * w) / p


def density_humid(t, w, p):
    """kg of moist air per m3 of moist air."""
    return (1 + w) / spec_volume(t, w, p)


def density_dry_basis(t, w, p):
    """kg of DRY air per m3 of moist air (= 1/v)."""
    return 1.0 / spec_volume(t, w, p)


def cp_moist(w):
    """kJ/(kg dry air K), consistent with the enthalpy equation above."""
    return 1.006 + 1.86 * w


def state(t, p, rh=None, wb=None, w=None):
    """Full state dict from exactly one of rh / wb / w."""
    if sum(x is not None for x in (rh, wb, w)) != 1:
        raise StateError("Specify exactly one of RH, wet-bulb or humidity ratio")
    if rh is not None:
        w = w_from_db_rh(t, rh, p)
    elif wb is not None:
        w = w_from_db_wb(t, wb, p)
    else:
        _check_t(t)
        if w > w_sat(t, p) * (1 + 1e-9):
            raise StateError("Humidity ratio exceeds saturation")
    return {
        "db": t, "w": w, "p": p,
        "rh": rh_from_db_w(t, w, p),
        "wb": wb_from_db_w(t, w, p),
        "dp": dew_point(w, p) if w > 0 else None,
        "h": enthalpy(t, w),
        "v": spec_volume(t, w, p),
        "rho": density_humid(t, w, p),
        "rho_dry": density_dry_basis(t, w, p),
    }
