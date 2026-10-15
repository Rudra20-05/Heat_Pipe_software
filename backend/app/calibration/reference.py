"""Reference-data import, validation, error metrics and (guarded) coefficient fitting. CSV is parsed as data only."""
import csv, io, copy, math
import numpy as np
from ..configuration.defaults import demo_case
from ..services.performance import calculate, CaseError

MAX_BYTES, MAX_ROWS = 2_000_000, 5000
COLUMNS = ["case_id", "configuration", "refrigerant", "rows", "tubes_per_row", "fin_length_mm", "fin_height_mm",
           "fin_pitch_mm", "fin_thk_mm", "tube_od_mm", "tube_thk_mm", "transverse_pitch_mm", "longitudinal_pitch_mm", "circuits",
           "altitude_m", "supply_flow_cfm", "supply_db", "supply_rh", "supply_wb", "exhaust_flow_cfm", "exhaust_db",
           "exhaust_rh", "exhaust_wb", "ref_supply_out_db", "ref_exhaust_out_db", "ref_supply_out_rh", "ref_exhaust_out_rh",
           "ref_supply_out_w_gkg", "ref_q_kw", "ref_effectiveness_pct", "ref_dp_supply_pa", "ref_dp_exhaust_pa",
           "split", "source", "notes"]
REQUIRED = ["case_id", "configuration", "rows", "supply_flow_cfm", "supply_db", "exhaust_flow_cfm", "exhaust_db"]
INTS = {"rows", "tubes_per_row", "circuits"}
TEXT = {"case_id", "configuration", "refrigerant", "split", "source", "notes"}


def parse_csv(raw: bytes):
    if len(raw) > MAX_BYTES:
        raise ValueError(f"File exceeds {MAX_BYTES} bytes")
    rd = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
    rows, issues = [], []
    for i, r in enumerate(rd, start=2):
        if i - 1 > MAX_ROWS:
            raise ValueError("Too many rows")
        clean = {}
        for k, v in r.items():
            if k is None or k not in COLUMNS:
                issues.append({"row": i, "field": k, "message": "Unknown column ignored"}); continue
            v = (v or "").strip()
            if v == "": clean[k] = None
            elif k in TEXT: clean[k] = v[:500]
            else:
                try: clean[k] = int(v) if k in INTS else float(v)
                except ValueError: issues.append({"row": i, "field": k, "message": f"Not numeric: {v!r}"}); clean[k] = None
        for k in REQUIRED:
            if clean.get(k) is None: issues.append({"row": i, "field": k, "message": "Required value missing"})
        if not clean.get("supply_rh") and not clean.get("supply_wb"): issues.append({"row": i, "field": "supply_rh/wb", "message": "RH or WB required"})
        if not clean.get("exhaust_rh") and not clean.get("exhaust_wb"): issues.append({"row": i, "field": "exhaust_rh/wb", "message": "RH or WB required"})
        if clean.get("configuration") and clean["configuration"] != "VHP":
            issues.append({"row": i, "field": "configuration", "message": f"{clean['configuration']} row excluded from VHP evaluation", "severity": "info"})
        clean["_row"] = i
        rows.append(clean)
    return rows, issues


def row_to_case(r, models=None):
    c = demo_case()
    eq = c["equipment"]
    for k in ("rows", "tubes_per_row", "fin_length_mm", "fin_height_mm", "fin_pitch_mm", "fin_thk_mm", "tube_od_mm", "tube_thk_mm",
              "transverse_pitch_mm", "longitudinal_pitch_mm", "circuits", "altitude_m"):
        eq[k] = r.get(k) if r.get(k) is not None else (None if k not in ("altitude_m",) else 0)
    for side in ("supply", "exhaust"):
        s = c[side]; s["flow"] = r[f"{side}_flow_cfm"]; s["flow_unit"] = "cfm"; s["db"] = r[f"{side}_db"]
        if r.get(f"{side}_rh") is not None: s.update(input_mode="db_rh", rh=r[f"{side}_rh"], wb=None)
        else: s.update(input_mode="db_wb", wb=r[f"{side}_wb"], rh=None)
    if models:
        for k, v in models.items(): c["models"][k].update(v)
    return c


REFS = {"supply_out_db": ("ref_supply_out_db", lambda p: p["streams"]["supply"]["outlet"]["db"]),
        "exhaust_out_db": ("ref_exhaust_out_db", lambda p: p["streams"]["exhaust"]["outlet"]["db"]),
        "supply_out_rh": ("ref_supply_out_rh", lambda p: p["streams"]["supply"]["outlet"]["rh"]),
        "q_kw": ("ref_q_kw", lambda p: p["performance"]["q_kw"]),
        "effectiveness_pct": ("ref_effectiveness_pct", lambda p: p["performance"]["effectiveness_pct"]),
        "dp_supply_pa": ("ref_dp_supply_pa", lambda p: p["pressure_drop"]["supply"]["value_pa"]),
        "dp_exhaust_pa": ("ref_dp_exhaust_pa", lambda p: p["pressure_drop"]["exhaust"]["value_pa"])}


def metrics(pairs):
    if not pairs: return None
    e = np.array([a - b for a, b in pairs]); ref = np.array([b for _, b in pairs])
    return {"n": len(pairs), "mae": float(np.mean(np.abs(e))), "rmse": float(np.sqrt(np.mean(e ** 2))), "bias": float(np.mean(e)),
            "mape_pct": float(np.mean(np.abs(e / ref)) * 100) if np.all(ref != 0) else None}


def evaluate(rows, models=None, split=None):
    """Predict each VHP row; compare against reference values. Rows whose prediction is unavailable are reported, not dropped silently."""
    cases, pairs, skipped = [], {k: [] for k in REFS}, []
    for r in rows:
        if r.get("configuration") != "VHP": skipped.append({"case_id": r.get("case_id"), "reason": "not VHP"}); continue
        if split and r.get("split") != split: continue
        try: p = calculate(row_to_case(r, models))
        except (CaseError, KeyError, TypeError) as e:
            skipped.append({"case_id": r.get("case_id"), "reason": f"invalid: {getattr(e, 'errors', e)}"}); continue
        rec = {"case_id": r["case_id"], "values": {}}
        for name, (col, fn) in REFS.items():
            if r.get(col) is None: continue
            try: pred = fn(p)
            except (TypeError, KeyError): pred = None
            if pred is None: rec["values"][name] = {"reference": r[col], "predicted": None, "note": "prediction unavailable"}; continue
            rec["values"][name] = {"reference": r[col], "predicted": pred, "abs_error": pred - r[col],
                                   "pct_error": (pred - r[col]) / r[col] * 100 if r[col] else None}
            pairs[name].append((pred, r[col]))
        cases.append(rec)
    return {"cases": cases, "skipped": skipped, "metrics": {k: metrics(v) for k, v in pairs.items() if v}}


def fit(rows, min_train=6):
    """Fit pressure-drop power law and thermal UA coefficients on split=='train' VHP rows; evaluate on split=='validate'.
    Refuses unless enough VHP rows exist in BOTH sets. Returns coefficients with provenance, never silently."""
    from scipy.optimize import least_squares
    vhp = [r for r in rows if r.get("configuration") == "VHP"]
    tr = [r for r in vhp if r.get("split") == "train"]; va = [r for r in vhp if r.get("split") == "validate"]
    if len(tr) < min_train or len(va) < 2:
        return {"status": "refused", "reason": f"Need >= {min_train} VHP rows with split=train and >= 2 with split=validate "
                f"(found {len(tr)} / {len(va)}). Not fitting to avoid over-fitting."}
    out = {"status": "ok", "n_train": len(tr), "n_validate": len(va), "provenance": "fitted from uploaded reference CSV"}
    dp = [(r, r["ref_dp_supply_pa"]) for r in tr if r.get("ref_dp_supply_pa")]
    if len(dp) >= 4:
        from ..services import psychrometrics as P, air_properties as A, geometry as G
        X, Y = [], []
        for r, d in dp:
            c = row_to_case(r); p = calculate(c); v = p["streams"]["supply"]["flow"]["face_velocity_ms"]
            rho = p["streams"]["supply"]["inlet"]["rho"]
            X.append(math.log(v)); Y.append(math.log(d / (r["rows"] * rho / 1.2)))
        n, lnc = np.polyfit(X, Y, 1)
        out["pressure_drop"] = {"provider": "power_law_per_row", "coeff_pa_per_row": math.exp(lnc), "exponent": float(n),
                                "valid_velocity_range": [math.exp(min(X)), math.exp(max(X))], "calibrated": True, "source": "fit"}
    eff = [r for r in tr if r.get("ref_effectiveness_pct")]
    if len(eff) >= 4:
        def res(x):
            m = {"thermal": {"ua_coeff": abs(x[0]), "ua_exponent": x[1]}}
            return [calculate(row_to_case(r, m))["performance"]["effectiveness_pct"] - r["ref_effectiveness_pct"] for r in eff]
        s = least_squares(res, [0.5, 0.6], bounds=([1e-6, 0.0], [1e3, 1.5]))
        out["thermal"] = {"ua_coeff": float(s.x[0]), "ua_exponent": float(s.x[1]), "calibrated": True, "ua_ref_velocity": 1.0}
    models = {k: v for k, v in out.items() if k in ("thermal", "pressure_drop")}
    out["train_metrics"] = evaluate(rows, models, "train")["metrics"]
    out["validation_metrics"] = evaluate(rows, models, "validate")["metrics"]
    return out
