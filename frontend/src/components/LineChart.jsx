import React from "react";
// Minimal SVG line chart for REAL calculated points only. points: [{x, y}] (null y values are skipped).
export default function LineChart({ title, points, xLabel, yLabel }) {
  const pts = points.filter((p) => p.y != null);
  if (pts.length < 2) return <div className="chart empty"><b>{title}</b><p>Not available: model/coefficients required.</p></div>;
  const W = 360, H = 200, m = 36;
  const xs = pts.map((p) => p.x), ys = pts.map((p) => p.y);
  const x0 = Math.min(...xs), x1 = Math.max(...xs), y0 = Math.min(...ys, 0), y1 = Math.max(...ys);
  const sx = (x) => m + ((x - x0) / (x1 - x0 || 1)) * (W - 2 * m), sy = (y) => H - m - ((y - y0) / (y1 - y0 || 1)) * (H - 2 * m);
  return (
    <figure className="chart"><figcaption>{title}</figcaption>
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={title}>
        <line x1={m} y1={H - m} x2={W - m} y2={H - m} stroke="#789" /><line x1={m} y1={m} x2={m} y2={H - m} stroke="#789" />
        <polyline fill="none" stroke="#1565c0" strokeWidth="2" points={pts.map((p) => `${sx(p.x)},${sy(p.y)}`).join(" ")} />
        {pts.map((p, i) => <circle key={i} cx={sx(p.x)} cy={sy(p.y)} r="3" fill="#1565c0" />)}
        <text x={W / 2} y={H - 6} fontSize="10" textAnchor="middle">{xLabel}</text>
        <text x="10" y={H / 2} fontSize="10" transform={`rotate(-90 10 ${H / 2})`} textAnchor="middle">{yLabel}</text>
        <text x={m} y={m - 6} fontSize="9">{y1.toFixed(1)}</text><text x={m - 4} y={H - m + 10} fontSize="9" textAnchor="end">{y0.toFixed(0)}</text>
      </svg></figure>
  );
}
