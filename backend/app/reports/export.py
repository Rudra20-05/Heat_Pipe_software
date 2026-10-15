"""PDF (reportlab) and CSV export of a calculation result."""
import io, csv
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer

DISCLAIMER = ("PRELIMINARY ENGINEERING ESTIMATE - not manufacturer-certified and not a performance guarantee. Equipment selection "
              "and final operating limits must be confirmed against H&M design criteria.")


def _f(v, d=2):
    return "n/a" if v is None else (f"{v:.{d}f}" if isinstance(v, float) else str(v))


def flat_rows(case, res):
    rows = [("section", "item", "supply", "exhaust", "unit")]
    for key, lab, unit, d in [("db", "Dry-bulb", "degC", 2), ("wb", "Wet-bulb", "degC", 2), ("rh", "RH", "%", 1), ("dp", "Dew point", "degC", 2),
                              ("h", "Enthalpy", "kJ/kg", 2), ("rho", "Density", "kg/m3", 4)]:
        for io_ in ("inlet", "outlet"):
            g = lambda k: (res["streams"][k][io_] or {}).get(key)
            rows.append((io_, lab, _f(g("supply"), d), _f(g("exhaust"), d), unit))
    for io_ in ("inlet", "outlet"):
        g = lambda k: (res["streams"][k][io_] or {}).get("w")
        rows.append((io_, "Humidity ratio", _f(None if g("supply") is None else g("supply") * 1000, 3),
                     _f(None if g("exhaust") is None else g("exhaust") * 1000, 3), "g/kg"))
    for k, lab, unit, d in [("face_velocity_ms", "Face velocity", "m/s", 3), ("m_dry_kgs", "Dry-air mass flow", "kg/s", 4), ("q_actual_m3s", "Volume flow", "m3/s", 4)]:
        rows.append(("flow", lab, _f(res["streams"]["supply"]["flow"][k], d), _f(res["streams"]["exhaust"]["flow"][k], d), unit))
    rows.append(("geometry", "Face area", _f(res["streams"]["supply"]["geometry"]["face_area_m2"], 4), _f(res["streams"]["exhaust"]["geometry"]["face_area_m2"], 4), "m2"))
    rows.append(("pressure", "Pressure drop", _f(res["pressure_drop"]["supply"]["value_pa"], 1), _f(res["pressure_drop"]["exhaust"]["value_pa"], 1), "Pa"))
    pf = res["performance"]
    for k, lab, unit in [("q_kw", "Heat recovery (cold-air gain)", "kW"), ("q_hot_air_kw", "Hot-air duty", "kW"), ("effectiveness_pct", "Temperature effectiveness", "%"),
                         ("energy_balance_error_pct", "Energy balance error", "%"), ("inlet_delta_t_k", "Inlet delta-T", "K")]:
        rows.append(("performance", lab, _f(pf.get(k), 3), "", unit))
    rows.append(("model", "Model version / status", res["model_version"], res["status"], ""))
    return rows


def to_csv(case, res):
    buf = io.StringIO(); csv.writer(buf).writerows(flat_rows(case, res)); return buf.getvalue().encode("utf-8")


def to_pdf(case, res):
    buf = io.BytesIO(); ss = getSampleStyleSheet(); S = []
    doc = SimpleDocTemplate(buf, pagesize=A4, title="Heat pipe calculation report")
    tbl = lambda data, w=None: Table(data, colWidths=w, style=TableStyle([("GRID", (0, 0), (-1, -1), .25, colors.grey), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f3a68")),
                                       ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("FONTSIZE", (0, 0), (-1, -1), 8)]))
    S += [Paragraph("Vertical Heat Pipe Heat Exchanger - Calculation Report", ss["Title"]), Paragraph(DISCLAIMER, ss["BodyText"]), Spacer(1, 8)]
    pr = case.get("project", {})
    S.append(tbl([["Project field", "Value"]] + [[k, str(v or "")] for k, v in pr.items()] + [["Calculated (UTC)", res["timestamp_utc"]], ["Model version", res["model_version"]], ["Result status", res["status"]]]))
    S += [Spacer(1, 8), Paragraph("Equipment configuration (inputs)", ss["Heading2"]), tbl([["Parameter", "Value"]] + [[k, str(v)] for k, v in case["equipment"].items()])]
    S += [Spacer(1, 8), Paragraph("Air-stream inputs", ss["Heading2"]), tbl([["Parameter", "Supply", "Exhaust"]] + [[k, str(case["supply"].get(k)), str(case["exhaust"].get(k))] for k in case["supply"]])]
    S += [Spacer(1, 8), Paragraph(f"Scenario: {case['scenario']}. Site pressure {res['site_pressure_pa']:.0f} Pa ({res['site_pressure_source']}). {res['performance']['direction']}", ss["BodyText"])]
    S += [Paragraph("Results", ss["Heading2"]), tbl([list(r) for r in flat_rows(case, res)])]
    S += [Paragraph("Model, calibration and limitations", ss["Heading2"]),
          Paragraph(f"Calibration status: {res['calibration']['status']}. {res['calibration']['note']} Thermal: series-conductance isothermal heat-pipe model with user-supplied UA coefficients; "
                    "psychrometrics: ASHRAE Fundamentals Ch.1 (Hyland-Wexler); pressure drop: configurable correlation provider (none built in); "
                    "condensate: apparatus-dew-point / bypass-factor method only when a bypass factor is entered.", ss["BodyText"])]
    S.append(tbl([["Warning field", "Message"]] + [[w["field"], w["message"]] for w in res["warnings"]] or [["-", "-"]]))
    S.append(Spacer(1, 6)); S.append(tbl([["Unavailable output", "Reason"]] + [[u["output"], u["reason"]] for u in res["unavailable"]]))
    doc.build(S); return buf.getvalue()
