import React from "react";
import { getIn, setIn, toNum } from "../utils/paths.js";

export function Num({ c, set, path, label, unit, step = "any", hint, errors = [], integer }) {
  const id = `f-${path}`;
  const v = getIn(c, path);
  const err = errors.find((e) => e.field === path);
  return (
    <div className="field">
      <label htmlFor={id}>{label}</label>
      <div className="inputwrap">
        <input id={id} type="number" step={integer ? 1 : step} value={v ?? ""} aria-invalid={!!err} aria-describedby={err ? `${id}-e` : undefined}
          onChange={(e) => set(setIn(c, path, toNum(e.target.value)))} />
        {unit && <span className="unit">{unit}</span>}
      </div>
      {hint && <small className="hint">{hint}</small>}
      {err && <small id={`${id}-e`} className="err" role="alert">{err.message}</small>}
    </div>
  );
}

export function Sel({ c, set, path, label, options }) {
  const id = `f-${path}`;
  return (
    <div className="field">
      <label htmlFor={id}>{label}</label>
      <select id={id} value={getIn(c, path) ?? ""} onChange={(e) => set(setIn(c, path, e.target.value))}>
        {options.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
      </select>
    </div>
  );
}

export function Txt({ c, set, path, label }) {
  const id = `f-${path}`;
  return (
    <div className="field">
      <label htmlFor={id}>{label}</label>
      <input id={id} type="text" value={getIn(c, path) ?? ""} onChange={(e) => set(setIn(c, path, e.target.value))} />
    </div>
  );
}
