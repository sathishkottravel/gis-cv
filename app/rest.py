"""REST adapter over the service layer."""
from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, UploadFile
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from app import service
from app.auth import get_uploader

router = APIRouter(prefix="/api")


class Sign(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    id: int
    class_id: int
    label: str
    confidence: float
    low_confidence: bool = Field(validation_alias="low_conf")
    lat: float
    lng: float
    location_source: str = Field(validation_alias="loc_source")
    image_url: str
    uploaded_by: str
    created_at: datetime


@router.post("/signs", status_code=201, response_model=Sign, tags=["signs"])
async def upload_sign(
    file: UploadFile = File(..., description="JPEG or PNG traffic sign photo, max 10 MB"),
    lat: float | None = Form(None, description="Latitude; ignored if the photo has EXIF GPS"),
    lng: float | None = Form(None, description="Longitude; ignored if the photo has EXIF GPS"),
    uploader: str = Depends(get_uploader),
):
    return Sign.model_validate(service.create_sign(await file.read(), lat, lng, uploader))
