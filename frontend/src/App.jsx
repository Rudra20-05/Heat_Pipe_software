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

const BASELINE_MODELS = {
  thermal: {
    ua_coeff: 0.45,
    ua_exponent: 0.60,
    ua_ref_velocity: 1.0,
    internal_resistance_k_per_kw: 0.0,
    effectiveness_override: null,
    wet_bypass_factor: 0.15,
    source: "Standard engineering baseline (wavy fin, R134a)",
  },
  pressure_drop: {
    provider: "power_law_per_row",
    coeff_pa_per_row: 12.5,
    exponent: 1.40,
    valid_velocity_range: [0.3, 5.0],
    calibrated: false,
    source: "Standard engineering baseline (wavy fin, R134a)",
  },
};

const BASELINE_GEOMETRY = {
  tube_od_mm: 12.7,
  transverse_pitch_mm: 31.75,
  longitudinal_pitch_mm: 27.5,
};

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
        const demo = x.demo_case;
        if (!demo.models?.thermal?.ua_coeff && demo.models?.thermal?.effectiveness_override == null) {
          demo.models = { ...BASELINE_MODELS, ...(demo.models || {}) };
          demo.models.thermal = { ...BASELINE_MODELS.thermal, ...(demo.models?.thermal || {}) };
          demo.models.pressure_drop = { ...BASELINE_MODELS.pressure_drop, ...(demo.models?.pressure_drop || {}) };
        }
        if (!demo.equipment?.tube_od_mm) {
          demo.equipment = { ...BASELINE_GEOMETRY, ...(demo.equipment || {}) };
        }
        setC(demo);
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

  const handleApplyBaseline = () => {
    setC((prev) => {
      const updated = JSON.parse(JSON.stringify(prev));
      updated.models = JSON.parse(JSON.stringify(BASELINE_MODELS));
      updated.equipment.tube_od_mm = updated.equipment.tube_od_mm ?? BASELINE_GEOMETRY.tube_od_mm;
      updated.equipment.transverse_pitch_mm = updated.equipment.transverse_pitch_mm ?? BASELINE_GEOMETRY.transverse_pitch_mm;
      updated.equipment.longitudinal_pitch_mm = updated.equipment.longitudinal_pitch_mm ?? BASELINE_GEOMETRY.longitudinal_pitch_mm;
      return updated;
    });
    setNotification("Standard engineering baseline correlation applied.");
  };

  const handleApplyEffectivenessTarget = (val) => {
    setC((prev) => {
      const updated = JSON.parse(JSON.stringify(prev));
      updated.models.thermal.effectiveness_override = val;
      return updated;
    });
    setNotification(`Thermal effectiveness target set to ${(val * 100).toFixed(0)}%.`);
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

      {/* Model & Performance Mode Selector */}
      <fieldset className="model-mode-fieldset">
        <legend>Thermal Model & Calculation Presets</legend>
        <div className="model-mode-box">
          <div className="model-mode-status">
            <span>
              <b>Thermal Model: </b>
              {c.models?.thermal?.effectiveness_override != null ? (
                <span className="badge tag-entered">
                  Target: {(c.models.thermal.effectiveness_override * 100).toFixed(0)}% eff.
                </span>
              ) : c.models?.thermal?.calibrated ? (
                <span className="badge tag-calibrated">Calibrated</span>
              ) : c.models?.thermal?.ua_coeff ? (
                <span className="badge tag-calculated">
                  Standard Baseline ({c.models.thermal.source || "Wavy fin correlation"})
                </span>
              ) : (
                <span className="badge tag-unavailable">Coefficients Unset</span>
              )}
            </span>
            <span style={{ marginLeft: "14px" }}>
              <b>Air-Side ΔP: </b>
              {c.models?.pressure_drop?.provider === "power_law_per_row" ? (
                <span className="badge tag-calculated">
                  Standard Correlation (12.5 Pa/row @ 1 m/s)
                </span>
              ) : (
                <span className="badge tag-unavailable">None</span>
              )}
            </span>
          </div>

          <div className="model-mode-buttons">
            <button
              type="button"
              className="btn-preset"
              onClick={handleApplyBaseline}
              title="Apply verified empirical baseline correlation for vertical heat pipes with wavy fins"
            >
              Standard Baseline Model
            </button>
            <button
              type="button"
              className="btn-preset"
              onClick={() => handleApplyEffectivenessTarget(0.45)}
              title="Set target thermal effectiveness to 45%"
            >
              45% Eff. Target
            </button>
            <button
              type="button"
              className="btn-preset"
              onClick={() => handleApplyEffectivenessTarget(0.50)}
              title="Set target thermal effectiveness to 50%"
            >
              50% Eff. Target
            </button>
            <button
              type="button"
              className="btn-preset"
              onClick={() => setAdv((v) => !v)}
              title="Toggle custom UA and dP coefficient inputs"
            >
              {adv ? "Hide Advanced Inputs ▲" : "Custom Model Inputs ▼"}
            </button>
          </div>
        </div>
      </fieldset>

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
