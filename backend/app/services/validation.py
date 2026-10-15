"""Input validation. Errors reject the case (HTTP 422); warnings accompany the result."""
import math

CAT = {  # catalogue (H&M, p.6) ranges / options - source: supplied catalogue PDF
    "rows": (1, 8), "cfm": (500, 50000), "fin_fpi": (8, 14),
    "tube_thk": (0.32, 0.34, 0.48), "fin_thk": (0.12, 0.14, 0.15),
}
UNITS = ("cfm", "m3/s", "m3/h", "l/s")


def _num(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def validate(case):
    errs, warns = [], []
    E = lambda f, m: errs.append({"field": f, "message": m})
    W = lambda f, m: warns.append({"field": f, "message": m})
    eq = case.get("equipment", {})
    if eq.get("configuration", "VHP") != "VHP":
        E("equipment.configuration", "Only Vertical Heat Pipe (VHP) is supported in this release; HHP and WRHP are not modelled.")
    if str(eq.get("refrigerant", "R134a")).upper().replace("-", "") != "R134A":
        E("equipment.refrigerant", "Only R134a is supported.")
    for f in ("rows", "tubes_per_row", "circuits"):
        v = eq.get(f)
        if v is not None and (not isinstance(v, int) or isinstance(v, bool) or v < 1):
            E(f"equipment.{f}", "Must be a positive integer.")
    r = eq.get("rows")
    if isinstance(r, int) and r > 0 and not CAT["rows"][0] <= r <= CAT["rows"][1]:
        W("equipment.rows", f"Catalogue range is {CAT['rows'][0]}-{CAT['rows'][1]} rows deep.")
    for f in ("tube_od_mm", "tube_thk_mm", "transverse_pitch_mm", "longitudinal_pitch_mm", "fin_thk_mm",
              "fin_pitch_mm", "fin_length_mm", "fin_height_mm"):
        v = eq.get(f)
        if v is not None and (not _num(v) or v <= 0):
            E(f"equipment.{f}", "Must be a positive number.")
    od, tk, pt, pl = (eq.get(k) for k in ("tube_od_mm", "tube_thk_mm", "transverse_pitch_mm", "longitudinal_pitch_mm"))
    if _num(od) and _num(tk) and 2 * tk >= od:
        E("equipment.tube_thk_mm", "Wall thickness must be less than half the tube outside diameter.")
    if _num(od) and _num(pt) and pt <= od:
        E("equipment.transverse_pitch_mm", "Transverse pitch must exceed tube outside diameter.")
    if _num(od) and _num(pl) and pl <= od:
        E("equipment.longitudinal_pitch_mm", "Longitudinal pitch must exceed tube outside diameter.")
    fp = eq.get("fin_pitch_mm")
    if _num(fp) and fp > 0 and not (25.4 / CAT["fin_fpi"][1] - 0.02 <= fp <= 25.4 / CAT["fin_fpi"][0] + 0.02):
        W("equipment.fin_pitch_mm", "Outside catalogue fin pitch range 8-14 FPI (1.81-3.18 mm).")
    ft = eq.get("fin_thk_mm")
    if _num(ft) and ft not in CAT["fin_thk"]:
        W("equipment.fin_thk_mm", f"Not a catalogue fin thickness {CAT['fin_thk']} mm.")
    if _num(tk) and tk not in CAT["tube_thk"]:
        W("equipment.tube_thk_mm", f"Not a catalogue tube thickness {CAT['tube_thk']} mm.")
    if not eq.get("tube_od_mm"):
        W("equipment.tube_od_mm", "Actual tube outside diameter not entered (nominal size is not assumed equal to OD); "
                                  "Reynolds number, mass and charge outputs are unavailable.")
    for key in ("supply", "exhaust"):
        s = case.get(key, {})
        f = f"{key}."
        if not _num(s.get("flow")) or s["flow"] <= 0:
            E(f + "flow", "Airflow must be a positive number.")
        elif s.get("flow_unit", "cfm") == "cfm" and not CAT["cfm"][0] <= s["flow"] <= CAT["cfm"][1]:
            W(f + "flow", "Outside catalogue airflow range 500-50,000 CFM.")
        if s.get("flow_unit", "cfm") not in UNITS:
            E(f + "flow_unit", f"Unit must be one of {UNITS}.")
        if s.get("flow_basis", "actual") not in ("actual", "standard"):
            E(f + "flow_basis", "Must be 'actual' or 'standard'.")
        if not _num(s.get("db")) or not -40 <= s["db"] <= 85:
            E(f + "db", "Dry-bulb must be within -40..85 degC.")
        mode = s.get("input_mode", "db_rh")
        if mode == "db_rh":
            if not _num(s.get("rh")) or not 0 <= s["rh"] <= 100:
                E(f + "rh", "Relative humidity must be within 0..100 %.")
        elif mode == "db_wb":
            if not _num(s.get("wb")):
                E(f + "wb", "Wet-bulb temperature required.")
            elif _num(s.get("db")) and s["wb"] > s["db"]:
                E(f + "wb", "Wet-bulb cannot exceed dry-bulb.")
        else:
            E(f + "input_mode", "Must be 'db_rh' or 'db_wb'.")
    if case.get("scenario") not in ("cooling", "heating"):
        E("scenario", "Must be 'cooling' or 'heating'.")
    sp = eq.get("site_pressure_pa")
    if sp is not None and (not _num(sp) or not 30000 <= sp <= 110000):
        E("equipment.site_pressure_pa", "Site pressure must be within 30000..110000 Pa.")
    if sp is None and not _num(eq.get("altitude_m", 0)):
        E("equipment.altitude_m", "Altitude must be numeric.")
    sup, exh = case.get("supply", {}), case.get("exhaust", {})
    if _num(sup.get("db")) and _num(exh.get("db")):
        sup_hot = sup["db"] > exh["db"]
        if case.get("scenario") == "cooling" and not sup_hot:
            W("scenario", "'Cooling' scenario expects the supply air to be the warmer stream, but it is not. "
                          "Heat flows according to the actual inlet temperatures.")
        if case.get("scenario") == "heating" and sup_hot:
            W("scenario", "'Heating' scenario expects the supply air to be the colder stream, but the supply inlet is warmer. "
                          "Heat flows from supply to exhaust according to the actual inlet temperatures.")
    return errs, warns
