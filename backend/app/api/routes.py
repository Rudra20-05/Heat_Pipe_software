import json, os, uuid, pathlib
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse, Response
from pydantic import ValidationError
from ..schemas.models import Case, PsychroRequest, SweepRequest
from ..services import psychrometrics as P
from ..services.performance import calculate, CaseError
from ..services import validation as V
from ..configuration.defaults import demo_case, MODEL_VERSION, OLD_SOFTWARE_REFERENCE
from ..configuration import catalogue
from ..calibration import reference as R
from ..reports import export

router = APIRouter()
DATA = pathlib.Path(os.environ.get("HP_DATA_DIR", pathlib.Path(__file__).resolve().parents[2] / "data" / "projects"))
MAX_UPLOAD = 2_000_000


def _run(case: Case):
    try:
        return calculate(case.to_core())
    except CaseError as e:
        raise HTTPException(status_code=422, detail={"errors": e.errors})


@router.get("/health")
def health():
    return {"status": "ok", "model_version": MODEL_VERSION}


@router.get("/configuration")
def configuration():
    return {"model_version": MODEL_VERSION, "catalogue": catalogue.CATALOGUE, "discrepancies": catalogue.DISCREPANCIES,
            "demo_case": demo_case(), "old_software_reference": OLD_SOFTWARE_REFERENCE,
            "supported": {"configuration": ["VHP"], "refrigerant": ["R134a"], "flow_units": list(V.UNITS)},
            "feature_status": catalogue.FEATURE_STATUS}


@router.post("/calculate")
def calc(case: Case):
    return _run(case)


@router.post("/validate-case")
def validate_case(case: Case):
    errs, warns = V.validate(case.to_core())
    return {"valid": not errs, "errors": errs, "warnings": warns}


@router.post("/psychrometrics")
def psychro(req: PsychroRequest):
    try:
        p = req.site_pressure_pa if req.site_pressure_pa is not None else P.p_atm_altitude(req.altitude_m or 0)
        s = P.state(req.db, p, rh=req.rh) if req.mode == "db_rh" else P.state(req.db, p, wb=req.wb)
    except (P.StateError, TypeError) as e:
        raise HTTPException(status_code=422, detail={"errors": [{"field": "state", "message": str(e)}]})
    return {"pressure_pa": p, "state": s}


@router.post("/sweep")
def sweep(req: SweepRequest):
    out = []
    for f in req.factors:
        if f <= 0:
            raise HTTPException(status_code=422, detail={"errors": [{"field": "factors", "message": "Factors must be positive"}]})
        c = req.case.to_core()
        c["supply"]["flow"] *= f; c["exhaust"]["flow"] *= f
        try:
            r = calculate(c)
        except CaseError as e:
            raise HTTPException(status_code=422, detail={"errors": e.errors})
        pf = r["performance"]
        out.append({"factor": f, "supply_flow": c["supply"]["flow"], "q_kw": pf.get("q_kw"), "effectiveness_pct": pf.get("effectiveness_pct"),
                    "dp_supply_pa": r["pressure_drop"]["supply"]["value_pa"], "dp_exhaust_pa": r["pressure_drop"]["exhaust"]["value_pa"]})
    return {"points": out}


async def _read(upload: UploadFile):
    raw = await upload.read(MAX_UPLOAD + 1)
    if len(raw) > MAX_UPLOAD:
        raise HTTPException(status_code=413, detail="File too large")
    return raw


@router.post("/calibration/validate-dataset")
async def validate_dataset(file: UploadFile = File(...)):
    try:
        rows, issues = R.parse_csv(await _read(file))
    except (ValueError, UnicodeDecodeError) as e:
        raise HTTPException(status_code=422, detail=str(e))
    return {"rows": len(rows), "issues": issues, "ok": not [i for i in issues if i.get("severity") != "info"]}


@router.post("/calibration/evaluate")
async def evaluate(file: UploadFile = File(...), models: str = Form("{}"), split: str = Form("")):
    try:
        rows, issues = R.parse_csv(await _read(file)); m = json.loads(models)
    except (ValueError, UnicodeDecodeError) as e:
        raise HTTPException(status_code=422, detail=str(e))
    return {"issues": issues, **R.evaluate(rows, m or None, split or None)}


@router.post("/calibration/fit")
async def fit(file: UploadFile = File(...)):
    try:
        rows, _ = R.parse_csv(await _read(file))
    except (ValueError, UnicodeDecodeError) as e:
        raise HTTPException(status_code=422, detail=str(e))
    return R.fit(rows)


@router.post("/report/pdf")
def report_pdf(case: Case):
    r = _run(case)
    return Response(export.to_pdf(case.to_core(), r), media_type="application/pdf",
                    headers={"Content-Disposition": "attachment; filename=heat_pipe_report.pdf"})


@router.post("/report/csv")
def report_csv(case: Case):
    r = _run(case)
    return Response(export.to_csv(case.to_core(), r), media_type="text/csv",
                    headers={"Content-Disposition": "attachment; filename=heat_pipe_results.csv"})


# ---- project persistence: JSON files on the server's disk (survive restarts if the disk persists) ----
@router.post("/projects")
def save_project(case: Case, project_id: str = ""):
    DATA.mkdir(parents=True, exist_ok=True)
    pid = project_id if project_id.isalnum() and len(project_id) <= 32 else uuid.uuid4().hex[:12]
    (DATA / f"{pid}.json").write_text(json.dumps(case.to_core()), encoding="utf-8")
    return {"project_id": pid}


@router.get("/projects")
def list_projects():
    return {"projects": sorted(p.stem for p in DATA.glob("*.json"))} if DATA.exists() else {"projects": []}


@router.get("/projects/{pid}")
def get_project(pid: str):
    f = DATA / f"{pid}.json"
    if not pid.isalnum() or not f.exists():
        raise HTTPException(status_code=404, detail="Project not found")
    return json.loads(f.read_text(encoding="utf-8"))
