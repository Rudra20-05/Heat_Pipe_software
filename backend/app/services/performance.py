"""Combined calculation service: psychrometrics -> flows -> geometry -> thermal -> pressure drop -> checks."""
import datetime
import math
from . import psychrometrics as P, air_properties as A, geometry as G, thermal_model as T
from . import heat_pipe_model as H, pressure_drop as PD, condensate as C, validation as V
from ..configuration.defaults import MODEL_VERSION


class CaseError(Exception):
    def __init__(self, errors):
        super().__init__("Invalid case")
        self.errors = errors


def _site_pressure(eq):
    if eq.get("site_pressure_pa") is not None:
        return eq["site_pressure_pa"], "site pressure override"
    return P.p_atm_altitude(eq.get("altitude_m") or 0), "standard atmosphere (altitude)"


def inlet_state(s, p):
    if s.get("input_mode", "db_rh") == "db_rh":
        return P.state(s["db"], p, rh=s["rh"])
    return P.state(s["db"], p, wb=s["wb"])


def _merge(case):
    from ..configuration.defaults import DEMO_CASE
    import copy
    out = copy.deepcopy(case)
    out.setdefault("models", {})
    out["models"].setdefault("thermal", {})
    out["models"].setdefault("pressure_drop", {})
    out.setdefault("tolerances", copy.deepcopy(DEMO_CASE["tolerances"]))
    return out


def _outlet(db, w, p):
    return P.state(db, p, w=w)


def calculate(case_in):
    case = _merge(case_in)
    errs, warns = V.validate(case)
    if errs:
        raise CaseError(errs)
    eq, tm, pdm, tol = case["equipment"], case["models"]["thermal"], case["models"]["pressure_drop"], case["tolerances"]
    unavailable, prov = [], {}
    res = {"model_version": MODEL_VERSION, "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
           "scenario": case["scenario"], "status": "ok", "warnings": warns, "unavailable": unavailable}
    try:
        p, p_src = _site_pressure(eq)
        st = {k: inlet_state(case[k], p) for k in ("supply", "exhaust")}
    except P.StateError as e:
        raise CaseError([{"field": "inlet", "message": str(e)}])
    res["site_pressure_pa"], res["site_pressure_source"] = p, p_src

    fl, geo, vel = {}, {}, {}
    for k in ("supply", "exhaust"):
        s = case[k]
        fl[k] = A.flow(s["flow"], s.get("flow_unit", "cfm"), s.get("flow_basis", "actual"), st[k])
        g = G.face(eq, s.get("fin_length_mm") or (case["supply"].get("fin_length_mm") if k == "exhaust" else None))
        geo[k] = g
        warns += [{"field": f"geometry.{k}", "message": m} for m in g["warnings"]]
        vel[k] = fl[k]["q_actual_m3s"] / g["face_area_m2"] if g["face_area_m2"] else None
        if vel[k] is None:
            unavailable.append({"output": f"{k}.face_velocity", "reason": "Face area unavailable", "missing": g["missing"]})
        elif not (0.3 <= vel[k] <= 6.0):
            warns.append({"field": f"{k}.face_velocity", "message": f"Face velocity {vel[k]:.2f} m/s is outside the 0.3-6 m/s "
                                                                    "range commonly used for coil selection; check inputs."})
        md = case[k].get("measured_density")
        if md and abs(md - st[k]["rho"]) / st[k]["rho"] > 0.02:
            warns.append({"field": f"{k}.measured_density", "message": "Measured density differs >2% from calculated."})
    circ = G.circuits(eq)
    warns += [{"field": "equipment.circuits", "message": m} for m in circ["warnings"]]

    # ---------- thermal ----------
    sup_hot = case["supply"]["db"] > case["exhaust"]["db"]
    hk, ck = ("supply", "exhaust") if sup_hot else ("exhaust", "supply")
    dT = abs(case["supply"]["db"] - case["exhaust"]["db"])
    c = {k: fl[k]["m_dry_kgs"] * P.cp_moist(st[k]["w"]) for k in st}
    out = {k: None for k in st}
    perf = {"hot_stream": hk, "cold_stream": ck, "inlet_delta_t_k": dT,
            "direction": f"Heat flows from the {hk} air (warmer) to the {ck} air (cooler) through the heat pipes."}
    cond = {"status": "none", "rate_lph": 0.0}
    q_hot = q_cold = None
    thermal_ok = False

    if dT < tol["min_delta_t_k"]:
        warns.append({"field": "inlet", "message": f"Inlet temperature difference {dT:.2f} K is below {tol['min_delta_t_k']} K: "
                                                   "no meaningful heat transfer; effectiveness not reported."})
        out = {k: dict(st[k]) for k in st}
        q_hot = q_cold = 0.0
        unavailable.append({"output": "effectiveness", "reason": "Negligible inlet temperature difference", "missing": []})
        thermal_ok = True
    else:
        eov = tm.get("effectiveness_override")
        ua = {}
        for k in st:
            ua[k], why = T.section_ua(tm, geo[k]["face_area_m2"], eq.get("rows"), vel[k]) if vel[k] and geo[k]["face_area_m2"] \
                else (None, "Face geometry unavailable")
        r_int = tm.get("internal_resistance_k_per_kw") or 0.0
        th, tc = case[hk]["db"], case[ck]["db"]
        sol, mode = None, None
        if eov is not None:
            if not (0 < eov <= 1):
                raise CaseError([{"field": "models.thermal.effectiveness_override", "message": "Must be in (0, 1]."}])
            sol, mode = H.solve_fixed_effectiveness(th, tc, c[hk], c[ck], eov), "user-specified effectiveness"
            prov["thermal"] = "entered (effectiveness override)"
        elif ua[hk] is not None and ua[ck] is not None:
            sol, mode = H.solve_dry(th, tc, c[hk], c[ck], ua[hk], ua[ck], r_int), "ua_model"
            prov["thermal"] = "calibrated" if tm.get("calibrated") else "preliminary (user-supplied coefficients)"
            perf["ua_kw_per_k"] = {k: ua[k] for k in st}
        else:
            unavailable.append({"output": "thermal performance", "reason":
                                "No thermal coefficients and no effectiveness override supplied; outlet states, capacity, "
                                "effectiveness and condensate cannot be predicted.",
                                "missing": ["models.thermal.ua_coeff", "models.thermal.ua_exponent"]})
        if sol:
            w_h = st[hk]["w"]
            t_out_hot_dry = th - sol["q_kw"] / c[hk]
            scr = C.screen(t_out_hot_dry, st[hk]["dp"], sol.get("t_evap")) if st[hk]["dp"] else "none"
            bf = tm.get("wet_bypass_factor")
            if scr == "definite" and bf is None or (scr == "definite" and mode != "ua_model"):
                cond = {"status": "wet_coil_required", "rate_lph": None}
                unavailable.append({"output": "thermal performance (condensing)", "reason":
                                    "Dry-coil model predicts the cooled stream at/below its dew point. Condensation requires a "
                                    "wet-coil model with UA coefficients AND models.thermal.wet_bypass_factor; no moisture "
                                    "removal is predicted without them.", "missing": ["models.thermal.wet_bypass_factor"]})
                sol = None
            elif scr in ("definite", "possible") and bf is not None and mode == "ua_model":
                if not (0 < bf < 1):
                    raise CaseError([{"field": "models.thermal.wet_bypass_factor", "message": "Must be in (0, 1)."}])
                try:
                    wsol = H.solve_wet(st[hk], st[ck], fl[hk]["m_dry_kgs"], fl[ck]["m_dry_kgs"], bf,
                                       ua[ck], r_int)
                except ValueError:
                    wsol = None
                    unavailable.append({"output": "wet-coil solution", "reason": "Wet-coil root finding failed.", "missing": []})
                if wsol:
                    sol = wsol
                    out[hk] = _outlet(wsol["t_off_hot"], wsol["w_off_hot"], p)
                    out[ck] = _outlet(wsol["t_off_cold"], st[ck]["w"], p)
                    cond = {"status": "modelled (ADP/bypass-factor, user BF)", "rate_lph": C.litres_per_hour(wsol["condensate_kgs"]),
                            "kg_per_s": wsol["condensate_kgs"]}
                    q_hot = fl[hk]["m_dry_kgs"] * (st[hk]["h"] - out[hk]["h"]) - wsol["condensate_kgs"] * H.CP_LIQ_WATER * wsol["t_evap"]
                    q_cold = fl[ck]["m_dry_kgs"] * (out[ck]["h"] - st[ck]["h"])
                    prov["condensate"] = "preliminary (bypass factor entered by user)"
                    warns.append({"field": "condensate", "message": "Condensate and latent split depend on the entered bypass "
                                  "factor, which is held constant; treat as preliminary."})
            elif scr == "possible":
                warns.append({"field": "condensate", "message": "Evaporator fluid temperature is below the cooled-stream dew point; "
                              "surface condensation may occur. The dry result may be inaccurate. Provide wet_bypass_factor."})
            if sol and out[hk] is None:
                try:
                    out[hk] = _outlet(th - sol["q_kw"] / c[hk], st[hk]["w"], p)
                    out[ck] = _outlet(tc + sol["q_kw"] / c[ck], st[ck]["w"], p)
                except P.StateError as e:
                    unavailable.append({"output": "outlet states", "reason": f"Outlet state non-physical ({e}); "
                                        "indicates condensation. Provide a wet-coil model.", "missing": []})
                    sol = None
                    out = {k: None for k in st}
            if sol:
                q_hot = q_hot if q_hot is not None else fl[hk]["m_dry_kgs"] * (st[hk]["h"] - out[hk]["h"])
                q_cold = q_cold if q_cold is not None else fl[ck]["m_dry_kgs"] * (out[ck]["h"] - st[ck]["h"])
                thermal_ok = True
                if sol.get("t_evap") is not None:
                    perf["working_fluid_temp_evaporator_c"] = sol["t_evap"]
                    perf["working_fluid_temp_condenser_c"] = sol["t_cond"]
                    if not (-30 <= sol["t_evap"] <= 90):
                        warns.append({"field": "working_fluid", "message": "Working-fluid temperature outside the -30..90 degC "
                                      "envelope assumed for R134a; confirm with H&M."})
                    if sol["t_evap"] < 0:
                        warns.append({"field": "working_fluid", "message": "Evaporator-side temperature below 0 degC: "
                                      "frost formation possible; not modelled."})

    streams = {}
    for k in st:
        streams[k] = {"role": "hot (cooled)" if k == hk else "cold (heated)", "inlet": st[k], "outlet": out[k],
                      "flow": {**fl[k], "unit_entered": case[k].get("flow_unit"), "basis": case[k].get("flow_basis", "actual"),
                               "face_velocity_ms": vel[k], "q_input": case[k]["flow"]},
                      "geometry": geo[k]}
    res["streams"] = streams
    perf["condensate"] = cond
    if thermal_ok:
        eb = None
        if q_cold not in (None, 0) and q_hot is not None:
            eb = (q_hot - q_cold) / abs(q_cold) * 100
            if abs(eb) > tol["energy_balance_pct"]:
                warns.append({"field": "energy_balance", "message": f"Energy balance error {eb:.3f}% exceeds tolerance."})
        cmin = min(c.values())
        perf.update({"q_cold_air_kw": q_cold, "q_hot_air_kw": q_hot, "q_kw": q_cold,
                     "energy_balance_error_pct": eb, "c_kw_per_k": c,
                     "delta_t_hot_k": (case[hk]["db"] - out[hk]["db"]) if out[hk] else None,
                     "delta_t_cold_k": (out[ck]["db"] - case[ck]["db"]) if out[ck] else None})
        if dT >= tol["min_delta_t_k"] and out[ck]:
            e = q_cold / (cmin * dT)
            perf["effectiveness_pct"] = e * 100
            perf["effectiveness_definition"] = "Q_cold_air / (C_min * (T_hot,in - T_cold,in)), C = m_dry*(1.006+1.86W)"
            perf["effectiveness_hot_side_pct"] = (case[hk]["db"] - out[hk]["db"]) / dT * 100
            perf["effectiveness_cold_side_pct"] = (out[ck]["db"] - case[ck]["db"]) / dT * 100
            dh = st[hk]["h"] - st[ck]["h"]
            if dh > 0:
                perf["enthalpy_effectiveness_pct"] = q_cold / (min(fl[hk]["m_dry_kgs"], fl[ck]["m_dry_kgs"]) * dh) * 100
            if e > 1 + 1e-9 and cond["status"].startswith("modelled"):
                warns.append({"field": "effectiveness", "message": "Sensible effectiveness exceeds 1 because latent heat is "
                              "included in the cooled-stream duty; interpret with the enthalpy effectiveness."})
        perf["status"] = prov.get("thermal", "unavailable")
    else:
        res["status"] = "partial"
    res["performance"] = perf

    pds = {}
    for k in st:
        pds[k] = PD.compute(pdm, eq.get("rows"), vel[k], st[k]["rho"], eq)
        if pds[k]["status"] == "unavailable":
            unavailable.append({"output": f"{k}.pressure_drop", "reason": pds[k]["reason"], "missing": ["models.pressure_drop"]})
        elif pds[k].get("extrapolated"):
            warns.append({"field": f"{k}.pressure_drop", "message": "Face velocity outside the correlation's valid range (extrapolated)."})
    res["pressure_drop"] = pds
    if any(v["status"] == "unavailable" for v in pds.values()) or not thermal_ok:
        res["status"] = "partial"

    mass = {}
    for k in st:
        m, miss = G.core_mass(eq, geo[k]["fin_length_mm"], geo[k]["fin_height_mm"])
        mass[k] = m
    core = sum(mass.values()) if all(v is not None for v in mass.values()) else None
    res["geometry"] = {"rows": eq.get("rows"), "tubes_per_row": eq.get("tubes_per_row"),
                       "tubes_per_coil_section": circ["tubes_per_coil_section"],
                       "total_tubes_both_sections_assumed_2x": 2 * circ["tubes_per_coil_section"] if circ["tubes_per_coil_section"] else None,
                       "parallel_circuits": eq.get("circuits"), "tubes_per_circuit": circ["tubes_per_circuit"]}
    if circ["tubes_per_circuit"] is None:
        unavailable.append({"output": "tubes_per_circuit", "reason": "Circuit split not integral or circuiting definition unconfirmed.", "missing": circ["missing"]})
    res["mass_charge_price"] = {"core_mass_kg": core, "core_mass_note": "Copper tubes + aluminium fins only; excludes casing, headers, bends, refrigerant.",
                                "refrigerant_charge_kg": None, "price": None}
    if core is None:
        unavailable.append({"output": "weight", "reason": "Tube OD, longitudinal pitch and casing data missing.",
                            "missing": ["tube_od_mm", "longitudinal_pitch_mm", "casing mass data"]})
    unavailable.append({"output": "refrigerant_charge", "reason": "Internal tube volume and charge rule not available.", "missing": ["tube internal volume", "charge rule"]})
    unavailable.append({"output": "price", "reason": "No price list or cost model configured.", "missing": ["price table"]})
    res["calibration"] = {"status": "uncalibrated" if not tm.get("calibrated") else "calibrated",
                          "note": "Results are PRELIMINARY unless coefficients carry manufacturer calibration provenance."}
    res["provenance"] = prov
    res["checks"] = {"mass_flow_dry_kgs": {k: fl[k]["m_dry_kgs"] for k in st}}
    return res
