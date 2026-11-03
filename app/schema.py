"""GraphQL adapter (Strawberry) over the service layer, mounted at /graphql."""
import base64
import binascii
from datetime import datetime

import strawberry
from graphql import GraphQLError
from strawberry.fastapi import GraphQLRouter
from strawberry.types import Info

from app import service
from app.auth import require_uploader
from app.errors import DomainError, InvalidImage


@strawberry.type
class Sign:
    id: int
    class_id: int
    label: str
    confidence: float
    low_confidence: bool
    lat: float
    lng: float
    location_source: str
    image_url: str
    uploaded_by: str
    created_at: datetime

    @classmethod
    def from_row(cls, s: dict) -> "Sign":
        return cls(id=s["id"], class_id=s["class_id"], label=s["label"], confidence=s["confidence"],
                   low_confidence=s["low_conf"], lat=s["lat"], lng=s["lng"],
                   location_source=s["loc_source"], image_url=s["image_url"],
                   uploaded_by=s["uploaded_by"], created_at=s["created_at"])


@strawberry.type
class SignType:
    class_id: int
    label: str


@strawberry.input
class BBoxInput:
    min_lng: float
    min_lat: float
    max_lng: float
    max_lat: float


def _call(fn, *args):
    """Run a service call, turning domain errors into GraphQL errors with extensions.code."""
    try:
        return fn(*args)
    except DomainError as exc:
        raise GraphQLError(str(exc), extensions={"code": exc.code}) from exc


@strawberry.type
class Query:
    @strawberry.field(description="Signs newest first (max 500), optionally inside a bounding box and of one class.")
    def signs(self, bbox: BBoxInput | None = None, class_id: int | None = None) -> list[Sign]:
        def run():
            box = bbox and service.make_bbox(bbox.min_lng, bbox.min_lat, bbox.max_lng, bbox.max_lat)
            return service.list_signs(box, class_id)
        return [Sign.from_row(s) for s in _call(run)]

    @strawberry.field(description="The 43 supported GTSRB sign types.")
    def sign_types(self) -> list[SignType]:
        return [SignType(**t) for t in service.list_sign_types()]


@strawberry.type
class Mutation:
    @strawberry.mutation(description="Upload a JPEG/PNG (base64, max 10 MB decoded). "
                                     "lat/lng are used only when the photo has no EXIF GPS.")
    def upload_sign(self, info: Info, image_base64: str,
                    lat: float | None = None, lng: float | None = None) -> Sign:
        uploader = _call(require_uploader, info.context["request"])
        try:
            data = base64.b64decode(image_base64.split(",", 1)[-1], validate=True)
        except (binascii.Error, ValueError):
            raise GraphQLError("Image is not valid base64.", extensions={"code": InvalidImage.code})
        return Sign.from_row(_call(service.create_sign, data, lat, lng, uploader))


schema = strawberry.Schema(query=Query, mutation=Mutation)
graphql_router = GraphQLRouter(schema, path="/graphql")
