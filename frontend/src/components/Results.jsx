import React from "react";
import { fmt } from "../utils/paths.js";
import LineChart from "./LineChart.jsx";

export function StatusBadge({ status }) {
  const norm = (status || "").toLowerCase();
  let cls = "tag-preliminary";
  let text = status || "preliminary";

  if (norm.includes("unavailable") || norm.includes("insufficient") || norm === "none") {
    cls = "tag-unavailable";
    text = "unavailable";
  } else if (norm.includes("calibrated")) {
    cls = "tag-calibrated";
    text = "calibrated";
  } else if (norm.includes("calculated")) {
    cls = "tag-calculated";
    text = "calculated";
  } else if (norm.includes("entered")) {
    cls = "tag-entered";
    text = "entered";
  } else if (norm.includes("preliminary")) {
    cls = "tag-preliminary";
    text = "preliminary";
  }

  return <span className={`badge ${cls}`}>{text}</span>;
}

const Kpi = ({ label, value, unit, tag }) => (
  <div className={`kpi ${value == null ? "kpi-na" : ""}`}>
    <span className="kl">{label}</span>
    <span className="kv">
      {value == null ? "Unavailable" : value}
      {value != null && unit ? <small> {unit}</small> : null}
    </span>
    <StatusBadge status={value == null ? "unavailable" : tag || "preliminary"} />
  </div>
);

export default function Results({ r, sweep }) {
  const s = r.streams.supply;
  const e = r.streams.exhaust;
  const p = r.performance;
  const th = p.status;
  const pd = r.pressure_drop;

  const row = (lab, a, b, unit, d = 2) => (
    <tr key={lab}>
      <th>{lab}</th>
      <td>{a != null ? fmt(a, d) : <span className="text-muted">Unavailable</span>}</td>
      <td>{b != null ? fmt(b, d) : <span className="text-muted">Unavailable</span>}</td>
      <td>{unit}</td>
    </tr>
  );

  const g = (st, io, k, mul = 1) => (st && st[io] ? st[io][k] * mul : null);

  return (
    <section aria-labelledby="res-h" className="results-section">
      <div className="results-header">
        <h2 id="res-h">Calculation Results</h2>
        <div className="results-meta">
          <span>Overall status: <StatusBadge status={r.status} /></span>
          <span>Model: <code>v{r.model_version}</code></span>
          <span>Thermal calibration: <StatusBadge status={r.calibration?.status || "preliminary"} /></span>
        </div>
      </div>

      <p className="note info-box"><b>Heat Flow Direction:</b> {p.direction}</p>

      <div className="kpis">
        <Kpi label="Supply outlet DB" value={s.outlet ? fmt(s.outlet.db) : null} unit="°C" tag={th} />
        <Kpi label="Exhaust outlet DB" value={e.outlet ? fmt(e.outlet.db) : null} unit="°C" tag={th} />
        <Kpi label="Temp. effectiveness" value={p.effectiveness_pct != null ? fmt(p.effectiveness_pct, 1) : null} unit="%" tag={th} />
        <Kpi label="Heat recovery duty" value={p.q_kw != null ? fmt(p.q_kw, 2) : null} unit="kW" tag={th} />
        <Kpi label="Supply ΔP" value={pd.supply.value_pa != null ? fmt(pd.supply.value_pa, 1) : null} unit="Pa" tag={pd.supply.status} />
        <Kpi label="Exhaust ΔP" value={pd.exhaust.value_pa != null ? fmt(pd.exhaust.value_pa, 1) : null} unit="Pa" tag={pd.exhaust.status} />
      </div>

      <div className="tables">
        <table>
          <caption>Air Stream State Properties (Psychrometrics)</caption>
          <thead>
            <tr>
              <th>Property</th>
              <th>Supply</th>
              <th>Exhaust</th>
              <th>Unit</th>
            </tr>
          </thead>
          <tbody>
            {row("Inlet dry-bulb", s.inlet.db, e.inlet.db, "°C")}
            {row("Outlet dry-bulb", g(s, "outlet", "db"), g(e, "outlet", "db"), "°C")}
            {row("Inlet wet-bulb", s.inlet.wb, e.inlet.wb, "°C")}
            {row("Outlet wet-bulb", g(s, "outlet", "wb"), g(e, "outlet", "wb"), "°C")}
            {row("Inlet RH", s.inlet.rh, e.inlet.rh, "%", 1)}
            {row("Outlet RH", g(s, "outlet", "rh"), g(e, "outlet", "rh"), "%", 1)}
            {row("Inlet humidity ratio", s.inlet.w * 1000, e.inlet.w * 1000, "g/kg", 3)}
            {row("Outlet humidity ratio", g(s, "outlet", "w", 1000), g(e, "outlet", "w", 1000), "g/kg", 3)}
            {row("Inlet enthalpy", s.inlet.h, e.inlet.h, "kJ/kg")}
            {row("Outlet enthalpy", g(s, "outlet", "h"), g(e, "outlet", "h"), "kJ/kg")}
            {row("Dew point (inlet)", s.inlet.dp, e.inlet.dp, "°C")}
            {row("Density (inlet)", s.inlet.rho, e.inlet.rho, "kg/m³", 4)}
            {row("Dry-air mass flow", s.flow.m_dry_kgs, e.flow.m_dry_kgs, "kg/s", 4)}
            <tr>
              <th>Condensate</th>
              <td colSpan="2">
                {p.condensate?.rate_lph > 0
                  ? `${fmt(p.condensate.rate_lph, 2)} L/h`
                  : p.condensate?.status || "None"}
              </td>
              <td>L/h</td>
            </tr>
          </tbody>
        </table>

        <table>
          <caption>Core Performance & Geometry Summary</caption>
          <thead>
            <tr>
              <th>Parameter</th>
              <th>Supply</th>
              <th>Exhaust</th>
              <th>Unit</th>
            </tr>
          </thead>
          <tbody>
            {row("Face area", s.geometry.face_area_m2, e.geometry.face_area_m2, "m²", 4)}
            {row("Face velocity", s.flow.face_velocity_ms, e.flow.face_velocity_ms, "m/s")}
            {row("Pressure drop", pd.supply.value_pa, pd.exhaust.value_pa, "Pa", 1)}
            {row("Temperature change (ΔT)", p.delta_t_hot_k, p.delta_t_cold_k, "K")}
            {row("Air stream heat duty", p.q_hot_air_kw, p.q_cold_air_kw, "kW")}
            <tr>
              <th>Energy balance error</th>
              <td colSpan="2">{p.energy_balance_error_pct != null ? `${fmt(p.energy_balance_error_pct, 6)} %` : <span className="text-muted">Unavailable</span>}</td>
              <td>%</td>
            </tr>
            <tr>
              <th>Enthalpy effectiveness</th>
              <td colSpan="2">{p.enthalpy_effectiveness_pct != null ? `${fmt(p.enthalpy_effectiveness_pct, 1)} %` : <span className="text-muted">Unavailable</span>}</td>
              <td>%</td>
            </tr>
            <tr>
              <th>Rows / tubes per row / circuits</th>
              <td colSpan="3">{r.geometry.rows} rows · {r.geometry.tubes_per_row} tubes/row · {r.geometry.parallel_circuits} circuits</td>
            </tr>
            <tr>
              <th>Tubes per circuit</th>
              <td colSpan="3">
                {r.geometry.tubes_per_circuit ?? <span className="text-muted">Unavailable (non-integral split: 31 / 2)</span>}
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      {r.performance.effectiveness_definition && (
        <p className="note"><b>Effectiveness definition:</b> {r.performance.effectiveness_definition}</p>
      )}

      <h3>Stream Operating Profile</h3>
      <LineChart
        title="Supply Stream: Inlet → Outlet Dry-Bulb"
        xLabel="0 = Inlet, 1 = Outlet"
        yLabel="°C"
        points={[{ x: 0, y: s.inlet.db }, { x: 1, y: s.outlet?.db ?? null }]}
      />

      {sweep && (
        <div className="charts">
          <LineChart
            title="Heat Recovery vs Supply Airflow"
            xLabel="Airflow (CFM)"
            yLabel="Heat Duty (kW)"
            points={sweep.points.map((q) => ({ x: q.supply_flow, y: q.q_kw }))}
          />
          <LineChart
            title="Temperature Effectiveness vs Supply Airflow"
            xLabel="Airflow (CFM)"
            yLabel="Effectiveness (%)"
            points={sweep.points.map((q) => ({ x: q.supply_flow, y: q.effectiveness_pct }))}
          />
          <LineChart
            title="Supply ΔP vs Supply Airflow"
            xLabel="Airflow (CFM)"
            yLabel="Pressure Drop (Pa)"
            points={sweep.points.map((q) => ({ x: q.supply_flow, y: q.dp_supply_pa }))}
          />
        </div>
      )}

      <div className="audit-lists">
        <div className="audit-card">
          <h3>Active Warnings ({r.warnings.length})</h3>
          <ul>
            {r.warnings.map((w, i) => (
              <li key={i}>
                <b>{w.field}:</b> {w.message}
              </li>
            ))}
            {!r.warnings.length && <li>No warnings.</li>}
          </ul>
        </div>

        <div className="audit-card">
          <h3>Unavailable Outputs & Missing Data</h3>
          <ul>
            {r.unavailable.map((u, i) => (
              <li key={i}>
                <b>{u.output}:</b> {u.reason}
                {u.missing?.length ? (
                  <span className="missing-fields"> (Missing: {u.missing.join(", ")})</span>
                ) : null}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  );
}
