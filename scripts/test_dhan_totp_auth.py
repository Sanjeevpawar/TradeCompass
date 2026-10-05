from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pyotp


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def load_env_file() -> None:
    env_path = PROJECT_ROOT / ".env"

    if not env_path.exists():
        raise RuntimeError(".env file not found.")

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()

        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()

        if key and value and key not in os.environ:
            os.environ[key] = value


def require_env(name: str) -> str:
    value = os.getenv(name)

    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")

    return value


def generate_access_token() -> dict:
    load_env_file()

    client_id = require_env("DHAN_CLIENT_ID")
    pin = require_env("DHAN_PIN")
    totp_secret = require_env("DHAN_TOTP_SECRET")

    if not pin.isdigit() or len(pin) != 6:
        raise RuntimeError("DHAN_PIN must contain exactly 6 digits.")

    totp = pyotp.TOTP(totp_secret).now()

    query = urlencode(
        {
            "dhanClientId": client_id,
            "pin": pin,
            "totp": totp,
        }
    )

    url = f"https://auth.dhan.co/app/generateAccessToken?{query}"

    request = Request(
        url,
        method="POST",
        headers={
            "Accept": "application/json",
        },
    )

    try:
        with urlopen(request, timeout=20) as response:
            raw = response.read().decode("utf-8")
            status_code = response.status
    except Exception as exc:
        raise RuntimeError(
            f"Dhan authentication request failed: {exc}"
        ) from exc

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"Dhan returned a non-JSON response. HTTP {status_code}"
        ) from exc

    if status_code != 200:
        error_message = payload.get("errorMessage") or payload.get("message")
        raise RuntimeError(
            f"Dhan authentication failed. HTTP {status_code}: "
            f"{error_message or 'unknown error'}"
        )

    access_token = payload.get("accessToken")

    if not access_token:
        raise RuntimeError(
            "Dhan authentication response did not contain accessToken."
        )

    return payload


if __name__ == "__main__":
    try:
        result = generate_access_token()

        print("DHAN_TOTP_AUTH=SUCCESS")
        print(f"CLIENT_ID_SET={bool(result.get('dhanClientId'))}")
        print(f"EXPIRY_TIME={result.get('expiryTime')}")
        print("ACCESS_TOKEN_RECEIVED=True")

    except Exception as exc:
        print(f"DHAN_TOTP_AUTH=FAILED")
        print(f"ERROR={exc}")
        raise SystemExit(1)