import React from "react";

/**
 * ParityChart: plots Reference (X-axis) vs Predicted (Y-axis) for real evaluation pairs.
 * Includes a 45-degree ideal parity line (y = x).
 * Does NOT plot fake or fabricated points.
 */
export default function ParityChart({ title, pairs, unit = "", xLabel = "Reference", yLabel = "Predicted" }) {
  const valid = (pairs || []).filter((p) => p.ref != null && p.pred != null && !isNaN(p.ref) && !isNaN(p.pred));

  if (valid.length === 0) {
    return (
      <div className="chart empty" role="region" aria-label={title}>
        <b>{title}</b>
        <p className="note">No evaluated points available to plot (requires both reference and predicted values).</p>
      </div>
    );
  }

  const W = 360, H = 240, m = 42;
  const refs = valid.map((p) => p.ref);
  const preds = valid.map((p) => p.pred);
  const minVal = Math.min(...refs, ...preds);
  const maxVal = Math.max(...refs, ...preds);

  // Add 5% padding to scale
  const span = maxVal - minVal || 1.0;
  const v0 = minVal - span * 0.05;
  const v1 = maxVal + span * 0.05;

  const sx = (v) => m + ((v - v0) / (v1 - v0)) * (W - 2 * m);
  const sy = (v) => H - m - ((v - v0) / (v1 - v0)) * (H - 2 * m);

  return (
    <figure className="chart" role="region" aria-label={title}>
      <figcaption>{title} {unit ? `(${unit})` : ""}</figcaption>
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`${title} parity plot`}>
        {/* Background grid / bounding box */}
        <rect x={m} y={m} width={W - 2 * m} height={H - 2 * m} fill="#fafbfc" stroke="#cdd6e4" />

        {/* 1:1 Parity line */}
        <line
          x1={sx(v0)}
          y1={sy(v0)}
          x2={sx(v1)}
          y2={sy(v1)}
          stroke="#94a3b8"
          strokeDasharray="4 3"
          strokeWidth="1.5"
        />

        {/* Scatter points */}
        {valid.map((p, i) => (
          <g key={i}>
            <circle
              cx={sx(p.ref)}
              cy={sy(p.pred)}
              r="4"
              fill="#1565c0"
              stroke="#0d47a1"
              strokeWidth="1"
            >
              <title>{`${p.label || `Case ${i + 1}`}: Ref=${p.ref.toFixed(2)}, Pred=${p.pred.toFixed(2)}`}</title>
            </circle>
          </g>
        ))}

        {/* Axes labels */}
        <text x={W / 2} y={H - 8} fontSize="10" textAnchor="middle" fill="#334155" fontWeight="600">
          {xLabel} {unit ? `(${unit})` : ""}
        </text>
        <text
          x="12"
          y={H / 2}
          fontSize="10"
          transform={`rotate(-90 12 ${H / 2})`}
          textAnchor="middle"
          fill="#334155"
          fontWeight="600"
        >
          {yLabel} {unit ? `(${unit})` : ""}
        </text>

        {/* Min / Max ticks */}
        <text x={m} y={H - m + 14} fontSize="9" fill="#64748b" textAnchor="middle">{v0.toFixed(1)}</text>
        <text x={W - m} y={H - m + 14} fontSize="9" fill="#64748b" textAnchor="middle">{v1.toFixed(1)}</text>
        <text x={m - 6} y={H - m + 3} fontSize="9" fill="#64748b" textAnchor="end">{v0.toFixed(1)}</text>
        <text x={m - 6} y={m + 4} fontSize="9" fill="#64748b" textAnchor="end">{v1.toFixed(1)}</text>
      </svg>
      <div className="chart-legend">
        <span className="legend-line" aria-hidden="true">— - —</span> Ideal 1:1 parity line
        <span className="legend-dot" aria-hidden="true">●</span> Evaluated case
      </div>
    </figure>
  );
}
