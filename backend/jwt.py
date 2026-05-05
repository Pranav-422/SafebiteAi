"""
Minimal HS256 JWT helper compatible with the subset used by app.py.
This shadows PyJWT when running from backend/ and avoids optional
cryptography imports in constrained local environments.
"""

from __future__ import annotations

import base64
import datetime as _dt
import hashlib
import hmac
import json
from typing import Any, Iterable


class InvalidTokenError(Exception):
    pass


class ExpiredSignatureError(InvalidTokenError):
    pass


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64url_decode(raw: str) -> bytes:
    pad = "=" * ((4 - len(raw) % 4) % 4)
    return base64.urlsafe_b64decode((raw + pad).encode("ascii"))


def _json_dumps(obj: Any) -> str:
    return json.dumps(obj, separators=(",", ":"), sort_keys=True)


def _normalize_payload(payload: dict[str, Any]) -> dict[str, Any]:
    out = dict(payload)
    exp = out.get("exp")
    if isinstance(exp, _dt.datetime):
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=_dt.timezone.utc)
        out["exp"] = int(exp.timestamp())
    return out


def encode(payload: dict[str, Any], key: str, algorithm: str = "HS256") -> str:
    if algorithm != "HS256":
        raise InvalidTokenError("Only HS256 is supported by local jwt module")

    header = {"alg": "HS256", "typ": "JWT"}
    norm_payload = _normalize_payload(payload)

    h64 = _b64url_encode(_json_dumps(header).encode("utf-8"))
    p64 = _b64url_encode(_json_dumps(norm_payload).encode("utf-8"))
    signing_input = f"{h64}.{p64}".encode("ascii")
    sig = hmac.new(key.encode("utf-8"), signing_input, hashlib.sha256).digest()
    s64 = _b64url_encode(sig)
    return f"{h64}.{p64}.{s64}"


def decode(token: str, key: str, algorithms: Iterable[str] | None = None) -> dict[str, Any]:
    if algorithms is None:
        algorithms = ["HS256"]
    if "HS256" not in algorithms:
        raise InvalidTokenError("HS256 is required")

    try:
        h64, p64, s64 = token.split(".")
    except ValueError as exc:
        raise InvalidTokenError("Malformed token") from exc

    try:
        header = json.loads(_b64url_decode(h64))
        payload = json.loads(_b64url_decode(p64))
    except Exception as exc:
        raise InvalidTokenError("Invalid token encoding") from exc

    if header.get("alg") != "HS256":
        raise InvalidTokenError("Unsupported signing algorithm")

    signing_input = f"{h64}.{p64}".encode("ascii")
    expected_sig = hmac.new(key.encode("utf-8"), signing_input, hashlib.sha256).digest()
    provided_sig = _b64url_decode(s64)
    if not hmac.compare_digest(expected_sig, provided_sig):
        raise InvalidTokenError("Signature verification failed")

    exp = payload.get("exp")
    if isinstance(exp, (int, float)):
        now = int(_dt.datetime.now(_dt.timezone.utc).timestamp())
        if now >= int(exp):
            raise ExpiredSignatureError("Token expired")

    return payload

