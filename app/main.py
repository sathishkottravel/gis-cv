"""FastAPI application: REST API and static UI."""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app import auth, classifier, config, rest
from app.schema import graphql_router
from app.errors import AuthRequired, DomainError, InvalidCoordinates, InvalidImage, LocationRequired, StorageUnavailable

STATUS_BY_ERROR = {
    AuthRequired: 401,
    InvalidImage: 400,
    LocationRequired: 422,
    InvalidCoordinates: 422,
    StorageUnavailable: 503,
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    classifier.load()
    yield


DESCRIPTION = """
Upload traffic sign photos, have them classified by a pretrained GTSRB model, and query them by map area.

* **Uploads** need a GitHub session (sign in at `/auth/login`) or the dev API key: click **Authorize** and enter `API_KEY` from `.env`.
* **Reads** (`GET`) are public.
* Errors return `{"detail", "code"}`. GraphQL (with GraphiQL) is at `/graphql`.
"""

TAGS = [
    {"name": "signs", "description": "Upload, list and filter located traffic signs."},
    {"name": "samples", "description": "GTSRB sample images registered in object storage."},
    {"name": "auth", "description": "GitHub sign-in for the browser UI (session cookie)."},
]

app = FastAPI(title="Sign Spotter Map", version="0.1.0", description=DESCRIPTION,
              openapi_tags=TAGS, lifespan=lifespan)


@app.exception_handler(DomainError)
async def domain_error_handler(request: Request, exc: DomainError):
    status = STATUS_BY_ERROR.get(type(exc), 400)
    return JSONResponse(status_code=status, content={"detail": str(exc), "code": exc.code})


app.add_middleware(SessionMiddleware, secret_key=config.SESSION_SECRET, same_site="lax", https_only=False)
app.include_router(auth.router)
app.include_router(rest.router)
app.include_router(graphql_router)
app.mount("/", StaticFiles(directory=config.ROOT / "static", html=True), name="static")
