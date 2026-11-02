"""FastAPI application: REST API and static UI."""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app import classifier, config, rest
from app.errors import DomainError, InvalidCoordinates, InvalidImage, LocationRequired, StorageUnavailable

STATUS_BY_ERROR = {
    InvalidImage: 400,
    LocationRequired: 422,
    InvalidCoordinates: 422,
    StorageUnavailable: 503,
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    classifier.load()
    yield


app = FastAPI(title="Sign Spotter Map", lifespan=lifespan)


@app.exception_handler(DomainError)
async def domain_error_handler(request: Request, exc: DomainError):
    status = STATUS_BY_ERROR.get(type(exc), 400)
    return JSONResponse(status_code=status, content={"detail": str(exc), "code": exc.code})


app.include_router(rest.router)
app.mount("/", StaticFiles(directory=config.ROOT / "static", html=True), name="static")
