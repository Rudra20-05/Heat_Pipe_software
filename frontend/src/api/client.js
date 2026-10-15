async function request(url, opts) {
  const res = await fetch(url, opts);
  if (res.ok) return res;
  let body = null;
  try { body = await res.json(); } catch { /* ignore */ }
  const errors = body?.detail?.errors || [{ field: "request", message: typeof body?.detail === "string" ? body.detail : `HTTP ${res.status}` }];
  const e = new Error("Request failed"); e.errors = errors; throw e;
}

const post = (url, body) => request(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });

export const getConfiguration = async () => (await request("/api/configuration")).json();
export const calculate = async (c) => (await post("/api/calculate", c)).json();
export const psychro = async (b) => (await post("/api/psychrometrics", b)).json();
export const sweep = async (case_) => (await post("/api/sweep", { case: case_ })).json();

export const download = async (kind, c, name) => {
  const blob = await (await post(`/api/report/${kind}`, c)).blob();
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = name;
  a.click();
  URL.revokeObjectURL(a.href);
};

export const uploadCsv = async (path, file) => {
  const fd = new FormData();
  fd.append("file", file);
  return (await request(path, { method: "POST", body: fd })).json();
};

export const saveProject = async (c, projectId = "") => {
  const q = projectId ? `?project_id=${encodeURIComponent(projectId)}` : "";
  return (await post(`/api/projects${q}`, c)).json();
};

export const listProjects = async () => (await request("/api/projects")).json();

export const getProject = async (pid) => (await request(`/api/projects/${encodeURIComponent(pid)}`)).json();

export const evaluateCalibration = async (file, models = {}, split = "") => {
  const fd = new FormData();
  fd.append("file", file);
  fd.append("models", JSON.stringify(models));
  fd.append("split", split);
  return (await request("/api/calibration/evaluate", { method: "POST", body: fd })).json();
};

export const fitCalibration = async (file) => {
  const fd = new FormData();
  fd.append("file", file);
  return (await request("/api/calibration/fit", { method: "POST", body: fd })).json();
};
