import React, { useState } from "react";
import { uploadCsv, evaluateCalibration, fitCalibration } from "../api/client.js";
import ParityChart from "./ParityChart.jsx";
import { fmt } from "../utils/paths.js";

export default function CalibrationView({ currentModels, onApplyFittedModels }) {
  const [file, setFile] = useState(null);
  const [valResult, setValResult] = useState(null);
  const [evalResult, setEvalResult] = useState(null);
  const [fitResult, setFitResult] = useState(null);
  const [busy, setBusy] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");
  const [activeMetric, setActiveMetric] = useState("q_kw");

  const handleFileChange = async (e) => {
    const selected = e.target.files[0];
    if (!selected) return;
    setFile(selected);
    setValResult(null);
    setEvalResult(null);
    setFitResult(null);
    setErrorMsg("");
    try {
      setBusy(true);
      const res = await uploadCsv("/api/calibration/validate-dataset", selected);
      setValResult(res);
    } catch (err) {
      setErrorMsg(err.message || "Failed to validate CSV");
    } finally {
      setBusy(false);
    }
  };

  const handleEvaluate = async () => {
    if (!file) return;
    setBusy(true);
    setErrorMsg("");
    try {
      const res = await evaluateCalibration(file, currentModels || {});
      setEvalResult(res);
    } catch (err) {
      setErrorMsg(err.message || "Evaluation failed");
    } finally {
      setBusy(false);
    }
  };

  const handleFit = async () => {
    if (!file) return;
    setBusy(true);
    setErrorMsg("");
    try {
      const res = await fitCalibration(file);
      setFitResult(res);
      if (res.status === "ok" && res.fitted && onApplyFittedModels) {
        onApplyFittedModels(res.fitted);
      }
    } catch (err) {
      setErrorMsg(err.message || "Fit failed");
    } finally {
      setBusy(false);
    }
  };

  // Build scatter pairs for ParityChart based on activeMetric
  const metricPairs = [];
  if (evalResult && evalResult.cases) {
    for (const c of evalResult.cases) {
      const valObj = c.values?.[activeMetric];
      if (valObj && valObj.reference != null && valObj.predicted != null) {
        metricPairs.push({
          ref: valObj.reference,
          pred: valObj.predicted,
          label: c.case_id,
        });
      }
    }
  }

  const metricLabels = {
    q_kw: { title: "Heat Recovery Duty", unit: "kW" },
    supply_out_db: { title: "Supply Outlet Dry-Bulb", unit: "°C" },
    exhaust_out_db: { title: "Exhaust Outlet Dry-Bulb", unit: "°C" },
    effectiveness_pct: { title: "Temperature Effectiveness", unit: "%" },
    dp_supply_pa: { title: "Supply Pressure Drop", unit: "Pa" },
    dp_exhaust_pa: { title: "Exhaust Pressure Drop", unit: "Pa" },
  };

  return (
    <fieldset className="cal-section" aria-labelledby="cal-legend">
      <legend id="cal-legend">Model Calibration & Reference Data Evaluation</legend>
      <p className="note">
        Upload measured manufacturer reference data (CSV) to evaluate model predictions or run guarded fitting.
        Fitting requires ≥ 6 training and ≥ 2 validation rows for VHP. Reference template is available at <code>backend/sample_data/reference_template.csv</code>.
      </p>

      <div className="cal-upload-bar">
        <label htmlFor="ref-csv-input" className="file-label">
          Choose Reference CSV:
        </label>
        <input
          id="ref-csv-input"
          type="file"
          accept=".csv"
          onChange={handleFileChange}
          disabled={busy}
        />
        <button
          type="button"
          onClick={handleEvaluate}
          disabled={!file || busy}
          className="btn-primary"
        >
          {busy ? "Processing…" : "Evaluate Model"}
        </button>
        <button
          type="button"
          onClick={handleFit}
          disabled={!file || busy}
          className="btn-secondary"
        >
          Run Guarded Fit
        </button>
      </div>

      {errorMsg && (
        <div className="errbox" role="alert">
          <b>Calibration Error:</b> {errorMsg}
        </div>
      )}

      {valResult && (
        <div className="cal-val-summary" aria-live="polite">
          <p>
            <b>Dataset Status:</b> {valResult.rows} rows parsed.{" "}
            {valResult.ok ? (
              <span className="tag t-cal">Valid format</span>
            ) : (
              <span className="tag t-na">Issues found</span>
            )}
          </p>
          {valResult.issues && valResult.issues.length > 0 && (
            <details>
              <summary>{valResult.issues.length} Note(s) / Warning(s)</summary>
              <ul className="issues-list">
                {valResult.issues.map((iss, i) => (
                  <li key={i} className={iss.severity === "info" ? "note" : "err"}>
                    Row {iss.row} [{iss.field}]: {iss.message}
                  </li>
                ))}
              </ul>
            </details>
          )}
        </div>
      )}

      {fitResult && (
        <div className="fit-result-banner" role="status" aria-live="polite">
          <h4>Guarded Fit Status: {fitResult.status}</h4>
          {fitResult.status === "refused" ? (
            <p className="note">
              <b>Fit Refused:</b> {fitResult.reason}
            </p>
          ) : (
            <div>
              <p className="ok"><b>Fitting Succeeded:</b> Provenance: {fitResult.provenance?.fitted_at_utc}</p>
              <pre>{JSON.stringify(fitResult.fitted, null, 2)}</pre>
            </div>
          )}
        </div>
      )}

      {evalResult && (
        <div className="eval-results" aria-live="polite">
          <h3>Evaluation Results</h3>

          {evalResult.skipped && evalResult.skipped.length > 0 && (
            <div className="skipped-notice note">
              <b>Skipped cases ({evalResult.skipped.length}):</b>{" "}
              {evalResult.skipped.map((s) => `${s.case_id} (${s.reason})`).join(", ")}
            </div>
          )}

          {evalResult.metrics && Object.keys(evalResult.metrics).length > 0 ? (
            <>
              <div className="metrics-table-wrap">
                <table>
                  <caption>Prediction Error Metrics vs Reference Data</caption>
                  <thead>
                    <tr>
                      <th>Metric</th>
                      <th>N Points</th>
                      <th>MAE</th>
                      <th>RMSE</th>
                      <th>Bias</th>
                      <th>MAPE (%)</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(evalResult.metrics).map(([k, m]) => (
                      <tr key={k}>
                        <td><b>{metricLabels[k]?.title || k}</b></td>
                        <td>{m.n}</td>
                        <td>{fmt(m.mae, 3)} {metricLabels[k]?.unit}</td>
                        <td>{fmt(m.rmse, 3)} {metricLabels[k]?.unit}</td>
                        <td>{fmt(m.bias, 3)} {metricLabels[k]?.unit}</td>
                        <td>{m.mape_pct != null ? `${fmt(m.mape_pct, 2)} %` : "n/a"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div className="parity-container">
                <div className="metric-selector">
                  <label htmlFor="parity-metric-select">Select metric to plot:</label>
                  <select
                    id="parity-metric-select"
                    value={activeMetric}
                    onChange={(e) => setActiveMetric(e.target.value)}
                  >
                    {Object.keys(evalResult.metrics).map((k) => (
                      <option key={k} value={k}>
                        {metricLabels[k]?.title || k}
                      </option>
                    ))}
                  </select>
                </div>

                <ParityChart
                  title={`Predicted vs Reference: ${metricLabels[activeMetric]?.title || activeMetric}`}
                  unit={metricLabels[activeMetric]?.unit}
                  pairs={metricPairs}
                />
              </div>
            </>
          ) : (
            <p className="note">
              No quantitative pairs could be evaluated against the current model (predictions were unavailable or missing reference outputs).
            </p>
          )}
        </div>
      )}
    </fieldset>
  );
}
