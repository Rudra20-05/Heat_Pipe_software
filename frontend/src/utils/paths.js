export const getIn = (o, p) => p.split(".").reduce((a, k) => (a == null ? a : a[k]), o);
export const setIn = (o, p, v) => {
  const ks = p.split("."); const c = structuredClone(o); let r = c;
  ks.slice(0, -1).forEach((k) => { r = r[k]; }); r[ks.at(-1)] = v; return c;
};
export const toNum = (s) => (s === "" || s == null ? null : Number(s));
export const fmt = (v, d = 2) => (v == null || Number.isNaN(v) ? "n/a" : Number(v).toFixed(d));
