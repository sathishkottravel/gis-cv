"""REST adapter over the service layer."""
from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, Query, Security, UploadFile
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from app import service
from app.auth import require_uploader

router = APIRouter(prefix="/api")

# Declared so Swagger shows an "Authorize" button; checked by require_uploader.
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False,
                              description="Dev API key (`API_KEY` in `.env`) for scripts and Swagger.")


class Error(BaseModel):
    detail: str
    code: str


class _Camel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class Sign(_Camel):
    id: int
    class_id: int
    label: str
    confidence: float = Field(description="Classifier confidence, 0..1")
    low_confidence: bool = Field(validation_alias="low_conf", description="True when confidence < 0.5")
    lat: float
    lng: float
    location_source: str = Field(validation_alias="loc_source", description="`exif` or `manual`")
    image_url: str
    uploaded_by: str
    created_at: datetime


class SignType(_Camel):
    class_id: int
    label: str


class Sample(_Camel):
    file: str
    class_id: int = Field(description="Expected GTSRB class")
    label: str
    url: str


@router.post(
    "/signs", status_code=201, response_model=Sign, tags=["signs"],
    summary="Upload a sign photo",
    description="Classifies the photo, takes the location from EXIF GPS or `lat`/`lng`, "
                "stores the image and records the sign.",
    responses={400: {"model": Error, "description": "Not a JPEG/PNG, or larger than 10 MB"},
               401: {"model": Error, "description": "No GitHub session and no valid X-API-Key"},
               422: {"model": Error, "description": "Location required, or invalid coordinates"},
               503: {"model": Error, "description": "Object storage unavailable"}},
)
async def upload_sign(
    file: UploadFile = File(..., description="JPEG or PNG traffic sign photo, max 10 MB"),
    lat: float | None = Form(None, description="Latitude; ignored if the photo has EXIF GPS"),
    lng: float | None = Form(None, description="Longitude; ignored if the photo has EXIF GPS"),
    _api_key: str | None = Security(api_key_header),
    uploader: str = Depends(require_uploader),
):
    return Sign.model_validate(service.create_sign(await file.read(), lat, lng, uploader))


@router.get(
    "/signs", response_model=list[Sign], tags=["signs"],
    summary="List signs",
    description="Newest first, at most 500. Give all four bounding box values or none.",
    responses={422: {"model": Error, "description": "Partial or invalid bounding box"}},
)
def get_signs(
    min_lng: float | None = Query(None, description="West edge"),
    min_lat: float | None = Query(None, description="South edge"),
    max_lng: float | None = Query(None, description="East edge"),
    max_lat: float | None = Query(None, description="North edge"),
    class_id: int | None = Query(None, ge=0, le=42, description="Only signs of this GTSRB class"),
):
    bbox = service.make_bbox(min_lng, min_lat, max_lng, max_lat)
    return [Sign.model_validate(s) for s in service.list_signs(bbox, class_id)]


@router.get("/sign-types", response_model=list[SignType], tags=["signs"],
            summary="List the 43 supported sign types")
def get_sign_types():
    return [SignType.model_validate(t) for t in service.list_sign_types()]


@router.get("/samples", response_model=list[Sample], tags=["samples"],
            summary="List the registered sample images",
            responses={503: {"model": Error, "description": "Object storage unavailable"}})
def get_samples():
    return [Sample.model_validate(s) for s in service.list_samples()]
