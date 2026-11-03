"""Upload authentication. Needs the docker compose `db` and `storage` services running."""
import base64
import json

import pytest
from fastapi.testclient import TestClient
from itsdangerous import TimestampSigner

from app import config, db
from app.main import app

STOP_PNG = (config.ROOT / "samples" / "14_stop.png").read_bytes()
UPLOAD = """mutation ($img: String!) {
  uploadSign(imageBase64: $img, lat: 59.329, lng: 18.069) { id uploadedBy }
}"""


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:  # no API key, no session
        yield c


@pytest.fixture(autouse=True)
def _clear_cookies(client):
    client.cookies.clear()
    yield
    client.cookies.clear()


def _count() -> int:
    return len(db.query_signs())


def _rest_upload(client, headers=None):
    return client.post("/api/signs", files={"file": ("sign.png", STOP_PNG, "image/png")},
                       data={"lat": "59.329", "lng": "18.069"}, headers=headers or {})


def _sign_in_as(client, login: str) -> None:
    """Set a session cookie the way Starlette's SessionMiddleware signs it."""
    data = base64.b64encode(json.dumps({"user": {"login": login, "avatar_url": None}}).encode())
    client.cookies.set("session", TimestampSigner(config.SESSION_SECRET).sign(data).decode())


def test_anonymous_rest_upload_is_401_and_stores_nothing(client):
    before = _count()
    resp = _rest_upload(client)
    assert resp.status_code == 401 and resp.json()["code"] == "AUTH_REQUIRED"
    assert _count() == before


def test_wrong_api_key_is_401(client):
    before = _count()
    assert _rest_upload(client, {"X-API-Key": "wrong-key"}).status_code == 401
    assert _count() == before


def test_anonymous_graphql_upload_is_auth_required(client):
    before = _count()
    body = client.post("/graphql", json={"query": UPLOAD,
                                         "variables": {"img": base64.b64encode(STOP_PNG).decode()}}).json()
    assert body["errors"][0]["extensions"]["code"] == "AUTH_REQUIRED"
    assert _count() == before


def test_reads_stay_public(client):
    assert client.get("/api/signs").status_code == 200
    assert client.get("/api/sign-types").status_code == 200
    assert client.post("/graphql", json={"query": "{ signTypes { classId } }"}).status_code == 200


def test_api_key_upload_records_api_key(client):
    resp = _rest_upload(client, {"X-API-Key": config.API_KEY})
    assert resp.status_code == 201
    sign = resp.json()
    db.delete_sign(sign["id"])
    assert sign["uploadedBy"] == "api-key"


def test_session_upload_records_github_login(client):
    _sign_in_as(client, "octocat")
    assert client.get("/auth/me").json() == {"user": {"login": "octocat", "avatar_url": None}}
    body = client.post("/graphql", json={"query": UPLOAD,
                                         "variables": {"img": base64.b64encode(STOP_PNG).decode()}}).json()
    sign = body["data"]["uploadSign"]
    db.delete_sign(sign["id"])
    assert sign["uploadedBy"] == "octocat"


def test_me_signed_out(client):
    resp = client.get("/auth/me")
    assert resp.status_code == 200 and resp.json() == {"user": None}


def test_logout_clears_session(client):
    _sign_in_as(client, "octocat")
    resp = client.get("/auth/logout", follow_redirects=False)
    assert resp.status_code in (302, 307) and resp.headers["location"] == "/"
    # The middleware expires the cookie (our hand-set cookie lives in a different jar slot,
    # so check the header rather than a follow-up /auth/me).
    set_cookie = resp.headers["set-cookie"]
    assert set_cookie.startswith("session=null;") and "expires=Thu, 01 Jan 1970" in set_cookie


def test_failed_callback_redirects_with_error(client):
    resp = client.get("/auth/callback?error=access_denied&state=x", follow_redirects=False)
    assert resp.status_code in (302, 307) and resp.headers["location"] == "/?auth_error=1"
    assert client.get("/auth/me").json() == {"user": None}


def test_login_redirects_to_github_or_reports_missing_config(client):
    resp = client.get("/auth/login", follow_redirects=False)
    assert resp.status_code in (302, 307)
    if config.GITHUB_CLIENT_ID:
        assert resp.headers["location"].startswith("https://github.com/login/oauth/authorize")
    else:
        assert resp.headers["location"] == "/?auth_error=1"
