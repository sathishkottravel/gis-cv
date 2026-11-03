"""Who is uploading. Stub until GitHub login lands in task group 6.

Takes the request so REST (as a FastAPI dependency) and GraphQL (from the
Strawberry context) share the same check.
"""
from fastapi import Request


def get_uploader(request: Request) -> str:
    return "api-key"
