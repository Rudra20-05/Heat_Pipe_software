from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from .api.routes import router
import os
app = FastAPI(title="Vertical Heat Pipe Selection API", version="0.1.0")

cors_origins_env = os.environ.get("HP_CORS_ORIGINS")
allowed_origins = [o.strip() for o in cors_origins_env.split(",")] if cors_origins_env else ["*"]
app.add_middleware(CORSMiddleware, allow_origins=allowed_origins,
                   allow_methods=["*"], allow_headers=["*"])
app.include_router(router)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_, exc: RequestValidationError):
    errors = []
    for err in exc.errors():
        loc = [str(x) for x in err.get("loc", []) if x not in ("body",)]
        field = ".".join(loc) if loc else "body"
        errors.append({"field": field, "message": err.get("msg", "Validation error")})
    return JSONResponse(status_code=422, content={"detail": {"errors": errors}})


@app.exception_handler(Exception)
async def unhandled(_, exc):  # never leak stack traces or return fake data
    return JSONResponse(status_code=500, content={"detail": "Internal calculation error. No result was produced."})
