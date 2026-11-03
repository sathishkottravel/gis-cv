"""GitHub OAuth sign-in (/auth/*) and the upload check shared by REST and GraphQL."""
import secrets

import httpx
from authlib.integrations.starlette_client import OAuth, OAuthError
from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from app import config
from app.errors import AuthRequired

oauth = OAuth()
oauth.register(
    "github",
    client_id=config.GITHUB_CLIENT_ID,
    client_secret=config.GITHUB_CLIENT_SECRET,
    authorize_url="https://github.com/login/oauth/authorize",
    access_token_url="https://github.com/login/oauth/access_token",
    api_base_url="https://api.github.com/",
    client_kwargs={"scope": "read:user"},
)

router = APIRouter(prefix="/auth", tags=["auth"])

_FAILED = "/?auth_error=1"


@router.get("/login", summary="Redirect to GitHub sign-in")
async def login(request: Request):
    if not config.GITHUB_CLIENT_ID:
        return RedirectResponse(_FAILED)
    return await oauth.github.authorize_redirect(request, str(request.url_for("auth_callback")))


@router.get("/callback", name="auth_callback", include_in_schema=False)
async def callback(request: Request):
    try:
        token = await oauth.github.authorize_access_token(request)
        resp = await oauth.github.get("user", token=token)
        resp.raise_for_status()
        user = resp.json()
    except (OAuthError, httpx.HTTPError, KeyError, ValueError):
        request.session.pop("user", None)
        return RedirectResponse(_FAILED)
    request.session["user"] = {"login": user["login"], "avatar_url": user.get("avatar_url")}
    return RedirectResponse("/")


@router.get("/logout", summary="Sign out")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/")


@router.get("/me", summary="The signed-in user, or null")
async def me(request: Request):
    return {"user": request.session.get("user")}


def require_uploader(request: Request) -> str:
    """GitHub login from the session, "api-key" for a valid X-API-Key, else AuthRequired."""
    user = request.session.get("user")
    if user:
        return user["login"]
    key = request.headers.get("X-API-Key")
    if config.API_KEY and key and secrets.compare_digest(key.encode(), config.API_KEY.encode()):
        return "api-key"
    raise AuthRequired("Sign in with GitHub (or send a valid X-API-Key) to upload signs.")
