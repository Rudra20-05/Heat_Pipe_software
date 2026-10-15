import React, { useEffect, useRef, useState } from "react";
import { getConfiguration, calculate, psychro, sweep as sweepApi, download } from "./api/client.js";
import { Num, Sel, Txt } from "./components/Field.jsx";
import Results, { StatusBadge } from "./components/Results.jsx";
import ProjectManager from "./components/ProjectManager.jsx";
import CalibrationView from "./components/CalibrationView.jsx";
import { fmt } from "./utils/paths.js";

function StreamForm({ c, set, k, title, errors, derived }) {
  const mode = c[k].input_mode;
  return (
    <fieldset className="stream-fieldset">
      <legend>{title}</legend>
      <Num {...{ c, set, errors }} path={`${k}.flow`} label="Airflow" />
      <Sel
        {...{ c, set }}
        path={`${k}.flow_unit`}
        label="Flow unit"
        options={[
          ["cfm", "CFM (ft³/min)"],
          ["m3/s", "m³/s"],
          ["m3/h", "m³/h"],
          ["l/s", "L/s"],
        ]}
      />
      <Sel
        {...{ c, set }}
        path={`${k}.flow_basis`}
        label="Flow basis"
        options={[
          ["actual", "Actual (at inlet condition density)"],
          ["standard", "Standard (dry air 20 °C, 101.325 kPa)"],
        ]}
      />
      <Num {...{ c, set, errors }} path={`${k}.db`} label="Inlet dry-bulb" unit="°C" />
      <Sel
        {...{ c, set }}
        path={`${k}.input_mode`}
        label="Humidity input mode"
        options={[
          ["db_rh", "Dry-bulb + Relative Humidity"],
          ["db_wb", "Dry-bulb + Wet-bulb"],
        ]}
      />
      {mode === "db_rh" ? (
        <Num {...{ c, set, errors }} path={`${k}.rh`} label="Relative humidity" unit="%" />
      ) : (
        <Num {...{ c, set, errors }} path={`${k}.wb`} label="Wet-bulb" unit="°C" />
      )}
      <Num
        {...{ c, set, errors }}
        path={`${k}.fin_length_mm`}
        label="Fin length override"
        unit="mm"
        hint="Blank = uses equipment fin length"
      />
      <div className="derived" aria-live="polite">
        <span className="derived-title">Derived inlet state: </span>
        {derived ? (
          <>
            WB <b>{fmt(derived.wb)} °C</b> · RH <b>{fmt(derived.rh, 1)} %</b> · W{" "}
            <b>{fmt(derived.w * 1000, 3)} g/kg</b> · h <b>{fmt(derived.h)} kJ/kg</b> · DP{" "}
            <b>{fmt(derived.dp)} °C</b> · ρ <b>{fmt(derived.rho, 4)} kg/m³</b>
          </>
        ) : (
          <span className="text-muted">Calculated properties unavailable for current inputs.</span>
        )}
      </div>
    </fieldset>
  );
}

export default function App() {
  const [c, setC] = useState(null);
  const [cfg, setCfg] = useState(null);
  const [res, setRes] = useState(null);
  const [sw, setSw] = useState(null);
  const [errors, setErrors] = useState([]);
  const [busy, setBusy] = useState(false);
  const [adv, setAdv] = useState(false);
  const [derived, setDerived] = useState({});
  const [notification, setNotification] = useState("");
  const t = useRef();

  useEffect(() => {
    getConfiguration()
      .then((x) => {
        setCfg(x);
        setC(x.demo_case);
      })
      .catch((e) => setErrors(e.errors || [{ field: "config", message: String(e) }]));
  }, []);

  useEffect(() => {
    // derived-property refresh (backend psychrometrics), debounced 250ms
    if (!c) return;
    clearTimeout(t.current);
    t.current = setTimeout(async () => {
      const out = {};
      for (const k of ["supply", "exhaust"]) {
        const s = c[k];
        try {
          const resPsych = await psychro({
            db: s.db,
            mode: s.input_mode,
            rh: s.input_mode === "db_rh" ? s.rh : null,
            wb: s.input_mode === "db_wb" ? s.wb : null,
            altitude_m: c.equipment.altitude_m ?? 0,
            site_pressure_pa: c.equipment.site_pressure_pa,
          });
          out[k] = resPsych.state;
        } catch {
          out[k] = null;
        }
      }
      setDerived(out);
    }, 250);
  }, [c?.supply, c?.exhaust, c?.equipment?.altitude_m, c?.equipment?.site_pressure_pa]);

  if (!c) {
    return (
      <main className="loading-main">
        <h1>Vertical Heat Pipe (VHP) Selection</h1>
        {errors.length ? (
          <div className="errbox" role="alert">
            <p><b>Backend unreachable:</b> {errors[0].message}. Ensure the API is running on port 8000.</p>
          </div>
        ) : (
          <p className="loading-text">Loading application configuration…</p>
        )}
      </main>
    );
  }

  const run = async () => {
    setBusy(true);
    setErrors([]);
    setRes(null);
    setSw(null);
    try {
      const calculation = await calculate(c);
      setRes(calculation);
      try {
        const sweepResult = await sweepApi(c);
        setSw(sweepResult);
      } catch {
        /* airflow sweep optional */
      }
    } catch (e) {
      // Never render fake results on failure
      setErrors(e.errors || [{ field: "request", message: String(e) }]);
    } finally {
      setBusy(false);
    }
  };

  const handleApplyFitted = (fitted) => {
    setC((prev) => {
      const updated = JSON.parse(JSON.stringify(prev));
      if (fitted.thermal) {
        updated.models.thermal = { ...updated.models.thermal, ...fitted.thermal };
      }
      if (fitted.pressure_drop) {
        updated.models.pressure_drop = { ...updated.models.pressure_drop, ...fitted.pressure_drop };
      }
      return updated;
    });
    setNotification("Fitted model coefficients applied to current session.");
  };

  const eqN = (path, label, unit, extra = {}) => (
    <Num {...{ c, set: setC, errors }} path={`equipment.${path}`} label={label} unit={unit} {...extra} />
  );

  return (
    <main>
      <header className="app-header">
        <div className="header-title-row">
          <h1>Vertical Heat Pipe (VHP) Selection</h1>
          <span className="app-version-badge">H&M Tech · v0.1.0-preliminary</span>
        </div>
        <div className="banner" role="region" aria-label="Disclaimer">
          <b>Commercial Engineering Estimate:</b> Outputs are tagged with traceability. Thermal and pressure-drop performance are preliminary/unavailable until verified coefficients or reference datasets are provided.
        </div>
      </header>

      {/* Project Persistence (Save / Open) */}
      <ProjectManager
        currentCase={c}
        onProjectLoaded={(loaded) => {
          setC(loaded);
          setRes(null);
          setSw(null);
        }}
        onNotify={setNotification}
      />

      {notification && (
        <div className="notification-bar" role="status" aria-live="polite">
          {notification}
          <button type="button" onClick={() => setNotification("")} className="btn-close" aria-label="Close notification">×</button>
        </div>
      )}

      {/* Project Metadata */}
      <fieldset>
        <legend>Project Details</legend>
        <Txt {...{ c, set: setC }} path="project.customer" label="Customer" />
        <Txt {...{ c, set: setC }} path="project.project_name" label="Project name" />
        <Txt {...{ c, set: setC }} path="project.reference_number" label="Reference no." />
        <Txt {...{ c, set: setC }} path="project.tag_number" label="Tag no." />
        <Txt {...{ c, set: setC }} path="project.engineer" label="Engineer" />
        <Txt {...{ c, set: setC }} path="project.design_case" label="Design case" />
      </fieldset>

      {/* Equipment Geometry */}
      <fieldset>
        <legend>Equipment Specification (VHP Air-to-Air, R134a)</legend>
        <Sel
          {...{ c, set: setC }}
          path="scenario"
          label="Design scenario"
          options={[
            ["cooling", "Cooling season (Summer heat recovery)"],
            ["heating", "Heating season (Winter heat recovery)"],
          ]}
        />
        {eqN("rows", "Rows in airflow direction", "", { integer: true })}
        {eqN("tubes_per_row", "Tubes per row", "", { integer: true })}
        {eqN("fin_length_mm", "Fin length", "mm")}
        {eqN("fin_height_mm", "Fin height", "mm")}
        {eqN("fin_pitch_mm", "Fin spacing", "mm")}
        {eqN("fin_thk_mm", "Aluminium fin thickness", "mm")}
        {eqN("tube_thk_mm", "Copper tube thickness", "mm")}
        {eqN("circuits", "Parallel circuits (vertical)", "", { integer: true })}
        {eqN("altitude_m", "Installation altitude", "m")}
        {eqN("site_pressure_pa", "Site barometric pressure override", "Pa")}

        <div className="adv-toggle">
          <label className="adv-label" htmlFor="chk-advanced-mode">
            <input
              id="chk-advanced-mode"
              type="checkbox"
              checked={adv}
              onChange={(e) => setAdv(e.target.checked)}
            />
            <b>Advanced mode (custom pitches, UA, and dP models)</b>
          </label>
        </div>

        {adv && (
          <div className="adv-fields">
            {eqN("tube_od_mm", "Tube outside diameter (not assumed from nominal)", "mm")}
            {eqN("transverse_pitch_mm", "Transverse tube pitch (S_T)", "mm")}
            {eqN("longitudinal_pitch_mm", "Longitudinal tube pitch (S_L)", "mm")}
            <Txt {...{ c, set: setC }} path="equipment.model_code" label="Model code (optional)" />
          </div>
        )}
      </fieldset>

      {/* Two Air Streams */}
      <div className="two">
        <StreamForm {...{ c, set: setC, errors }} k="supply" title="Supply Air Stream" derived={derived.supply} />
        <StreamForm {...{ c, set: setC, errors }} k="exhaust" title="Return / Exhaust Air Stream" derived={derived.exhaust} />
      </div>

      {/* Advanced Model Parameters */}
      {adv && (
        <fieldset className="models-fieldset">
          <legend>Advanced Model Coefficients (User-Entered / Calibrated)</legend>
          <Num
            {...{ c, set: setC, errors }}
            path="models.thermal.ua_coeff"
            label="UA coefficient"
            unit="kW/K per m² face per row @ v_ref"
          />
          <Num
            {...{ c, set: setC, errors }}
            path="models.thermal.ua_exponent"
            label="UA face velocity exponent"
          />
          <Num
            {...{ c, set: setC, errors }}
            path="models.thermal.internal_resistance_k_per_kw"
            label="Internal fluid resistance"
            unit="K/kW"
          />
          <Num
            {...{ c, set: setC, errors }}
            path="models.thermal.effectiveness_override"
            label="Effectiveness override (0.0 – 1.0)"
            hint="User-specified thermal effectiveness (replaces calculation)"
          />
          <Num
            {...{ c, set: setC, errors }}
            path="models.thermal.wet_bypass_factor"
            label="Wet-coil bypass factor (0.0 – 1.0)"
            hint="Required when surface condensation occurs"
          />
          <Sel
            {...{ c, set: setC }}
            path="models.pressure_drop.provider"
            label="Pressure-drop provider"
            options={[
              ["none", "None (reported as unavailable)"],
              ["power_law_per_row", "Power law per row (user-supplied / calibrated)"],
            ]}
          />
          <Num
            {...{ c, set: setC, errors }}
            path="models.pressure_drop.coeff_pa_per_row"
            label="ΔP coefficient"
            unit="Pa/row @ 1 m/s"
          />
          <Num
            {...{ c, set: setC, errors }}
            path="models.pressure_drop.exponent"
            label="ΔP face velocity exponent"
          />
        </fieldset>
      )}

      {/* Action Buttons */}
      <div className="actions" role="region" aria-label="Calculations and Exports">
        <button type="button" onClick={run} disabled={busy} className="btn-primary btn-large">
          {busy ? "Calculating…" : "Calculate Performance"}
        </button>
        <button
          type="button"
          disabled={!res || busy}
          onClick={() => download("pdf", c, "heat_pipe_report.pdf")}
          className="btn-secondary"
        >
          Download PDF Report
        </button>
        <button
          type="button"
          disabled={!res || busy}
          onClick={() => download("csv", c, "heat_pipe_results.csv")}
          className="btn-secondary"
        >
          Export CSV Data
        </button>
      </div>

      {/* Field-level and Calculation Errors */}
      {errors.length > 0 && (
        <div className="errbox" role="alert" aria-live="assertive">
          <b>Calculation halted with input error(s):</b>
          <ul>
            {errors.map((e, i) => (
              <li key={i}>
                <b>{e.field}:</b> {e.message}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Calculation Results */}
      {res && <Results r={res} sweep={sw} />}

      {/* Calibration & Reference Evaluation Section */}
      <CalibrationView
        currentModels={c.models}
        onApplyFittedModels={handleApplyFitted}
      />

      {/* Discrepancies and Catalogue Context */}
      {cfg && (
        <details className="discrepancies-box">
          <summary><b>Catalogue Discrepancies & Items for Manufacturer Clarification</b></summary>
          <ul>
            {cfg.discrepancies.map((d) => (
              <li key={d.id}>
                <b>{d.item}:</b> {d.note}
              </li>
            ))}
          </ul>
        </details>
      )}
    </main>
  );
}
