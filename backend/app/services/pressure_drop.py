"""Air-side pressure drop via a pluggable correlation provider.

No published finned-tube correlation is built in: coefficients for wavy/sine-wave fins with rippled edges
could not be verified against a source in this build, and none are guessed. Available providers:

* ``none``              -> returns 'unavailable' (default).
* ``power_law_per_row`` -> dP = c0 * N_rows * (rho/1.2) * v_face**n, with c0 [Pa per row at 1 m/s, rho=1.2 kg/m3]
                           and n supplied by the user or fitted by calibration/fit.py. Labelled PRELIMINARY /
                           CALIBRATED depending on `source`. Valid only inside `valid_velocity_range`.
Future H&M-specific or literature providers register in PROVIDERS with the same signature.
"""

RHO_REF = 1.2


def _none(cfg, rows, v, rho, eq):
    return None, "No pressure-drop correlation configured (supply coefficients or run calibration)."


def _power_law(cfg, rows, v, rho, eq):
    c0, n = cfg.get("coeff_pa_per_row"), cfg.get("exponent")
    if c0 is None or n is None or c0 <= 0 or n <= 0:
        return None, "power_law_per_row requires positive coeff_pa_per_row and exponent."
    return c0 * rows * (rho / RHO_REF) * v ** n, None


PROVIDERS = {"none": _none, "power_law_per_row": _power_law}


def compute(cfg, rows, v_face, rho, eq):
    """Return dict(value_pa|None, status, provider, source, reason, extrapolated)."""
    name = (cfg or {}).get("provider", "none")
    fn = PROVIDERS.get(name)
    if fn is None:
        return {"value_pa": None, "status": "unavailable", "provider": name,
                "reason": f"Unknown pressure-drop provider '{name}'."}
    if not rows or v_face is None or v_face <= 0:
        return {"value_pa": None, "status": "unavailable", "provider": name, "reason": "Rows or face velocity missing."}
    dp, reason = fn(cfg or {}, rows, v_face, rho, eq)
    if dp is None:
        return {"value_pa": None, "status": "unavailable", "provider": name, "reason": reason}
    if not (dp > 0) or dp != dp or dp == float("inf"):
        return {"value_pa": None, "status": "unavailable", "provider": name, "reason": "Non-physical result suppressed."}
    rng = cfg.get("valid_velocity_range")
    extrap = bool(rng and not (rng[0] <= v_face <= rng[1]))
    src = cfg.get("source", "")
    return {"value_pa": dp, "status": "calibrated" if cfg.get("calibrated") else "preliminary", "provider": name,
            "source": src, "extrapolated": extrap, "reason": None}
