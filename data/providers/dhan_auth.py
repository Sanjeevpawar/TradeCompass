from __future__ import annotations

import json
import os
import time
from datetime import datetime
from pathlib import Path
from tempfile import NamedTemporaryFile
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

import pyotp


class DhanAuthenticationError(RuntimeError):
    """Raised when Dhan authentication fails."""


class DhanAuthManager:
    """
    Manages Dhan 24-hour access tokens using TOTP authentication.

    The access token is cached:
    1. In memory for the lifetime of the Python process.
    2. In a local git-ignored cache file so a TradeCompass restart
       does not unnecessarily generate another Dhan token.

    The TOTP secret and Dhan PIN are never written to the token cache.
    """

    AUTH_URL = "https://auth.dhan.co/app/generateAccessToken"

    REFRESH_BUFFER_SECONDS = 300

    CACHE_FILE = (
        Path(__file__).resolve().parents[2]
        / "data"
        / "live"
        / "dhan_token_cache.json"
    )

    def __init__(
        self,
        client_id: str | None = None,
        pin: str | None = None,
        totp_secret: str | None = None,
    ) -> None:
        self._load_env_file()

        self.client_id = client_id or os.getenv("DHAN_CLIENT_ID")
        self.pin = pin or os.getenv("DHAN_PIN")
        self.totp_secret = totp_secret or os.getenv("DHAN_TOTP_SECRET")

        if not self.client_id:
            raise DhanAuthenticationError(
                "Missing DHAN_CLIENT_ID."
            )

        if not self.pin:
            raise DhanAuthenticationError(
                "Missing DHAN_PIN."
            )

        if not self.pin.isdigit() or len(self.pin) != 6:
            raise DhanAuthenticationError(
                "DHAN_PIN must contain exactly 6 digits."
            )

        if not self.totp_secret:
            raise DhanAuthenticationError(
                "Missing DHAN_TOTP_SECRET."
            )

        self._access_token: str | None = None
        self._expiry_epoch: float | None = None

        self._load_cached_token()

    @staticmethod
    def _load_env_file() -> None:
        """Load .env values without overwriting existing environment variables."""

        project_root = Path(__file__).resolve().parents[2]
        env_path = project_root / ".env"

        if not env_path.exists():
            return

        for raw_line in env_path.read_text(
            encoding="utf-8"
        ).splitlines():

            line = raw_line.strip()

            if not line:
                continue

            if line.startswith("#"):
                continue

            if "=" not in line:
                continue

            key, value = line.split("=", 1)

            key = key.strip()
            value = value.strip()

            if key and value and key not in os.environ:
                os.environ[key] = value

    def _load_cached_token(self) -> None:
        """
        Load the previously generated token from the local cache.

        Invalid or expired cache files are ignored safely.
        """

        if not self.CACHE_FILE.exists():
            return

        try:
            payload = json.loads(
                self.CACHE_FILE.read_text(encoding="utf-8")
            )

            access_token = payload.get("access_token")
            expiry_epoch = payload.get("expiry_epoch")
            cached_client_id = payload.get("client_id")

            if not access_token:
                return

            if expiry_epoch is None:
                return

            if cached_client_id != self.client_id:
                return

            expiry_epoch = float(expiry_epoch)

            if time.time() >= (
                expiry_epoch - self.REFRESH_BUFFER_SECONDS
            ):
                return

            self._access_token = access_token
            self._expiry_epoch = expiry_epoch

        except (
            OSError,
            ValueError,
            TypeError,
            json.JSONDecodeError,
        ):
            # Corrupt cache should never prevent authentication.
            self._access_token = None
            self._expiry_epoch = None

    def _save_cached_token(
        self,
        access_token: str,
        expiry_epoch: float,
    ) -> None:
        """
        Atomically save the token cache.

        The cache contains only:
        - client ID
        - access token
        - expiry timestamp

        It does NOT contain:
        - Dhan PIN
        - TOTP secret
        - generated TOTP
        """

        self.CACHE_FILE.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        payload = {
            "client_id": self.client_id,
            "access_token": access_token,
            "expiry_epoch": expiry_epoch,
        }

        temp_path: Path | None = None

        try:
            with NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=self.CACHE_FILE.parent,
                prefix=".dhan_token_cache_",
                suffix=".tmp",
                delete=False,
            ) as temp_file:

                json.dump(
                    payload,
                    temp_file,
                    indent=2,
                )

                temp_file.write("\n")
                temp_path = Path(temp_file.name)

            os.replace(
                temp_path,
                self.CACHE_FILE,
            )

        except OSError as exc:
            if temp_path is not None:
                try:
                    temp_path.unlink(missing_ok=True)
                except OSError:
                    pass

            raise DhanAuthenticationError(
                f"Unable to save Dhan token cache: {exc}"
            ) from exc

    def _token_is_usable(self) -> bool:
        """Return True when the cached token is safely usable."""

        if not self._access_token:
            return False

        if self._expiry_epoch is None:
            return False

        return time.time() < (
            self._expiry_epoch - self.REFRESH_BUFFER_SECONDS
        )

    def _generate_totp(self) -> str:
        """Generate the current 6-digit TOTP."""

        try:
            return pyotp.TOTP(self.totp_secret).now()

        except Exception as exc:
            raise DhanAuthenticationError(
                "Unable to generate Dhan TOTP."
            ) from exc

    def _request_new_token(self) -> None:
        """Request a fresh 24-hour access token from Dhan."""

        totp = self._generate_totp()

        query = urlencode(
            {
                "dhanClientId": self.client_id,
                "pin": self.pin,
                "totp": totp,
            }
        )

        url = f"{self.AUTH_URL}?{query}"

        request = Request(
            url,
            method="POST",
            headers={
                "Accept": "application/json",
            },
        )

        try:
            with urlopen(
                request,
                timeout=20,
            ) as response:

                status_code = response.status
                raw_response = response.read().decode(
                    "utf-8"
                )

        except Exception as exc:
            raise DhanAuthenticationError(
                f"Dhan authentication request failed: {exc}"
            ) from exc

        try:
            payload = json.loads(raw_response)

        except json.JSONDecodeError as exc:
            raise DhanAuthenticationError(
                "Dhan returned a non-JSON authentication "
                f"response. HTTP {status_code}."
            ) from exc

        if status_code != 200:
            self._raise_dhan_error(
                status_code,
                payload,
            )

        access_token = payload.get("accessToken")

        if not access_token:
            self._raise_dhan_error(
                status_code,
                payload,
                fallback=(
                    "Dhan returned HTTP 200 but no "
                    "accessToken."
                ),
            )

        expiry_time = payload.get("expiryTime")

        if not expiry_time:
            self._raise_dhan_error(
                status_code,
                payload,
                fallback=(
                    "Dhan returned an accessToken "
                    "without expiryTime."
                ),
            )

        try:
            expiry_epoch = self._parse_expiry_time(
                expiry_time
            )

        except Exception as exc:
            raise DhanAuthenticationError(
                "Unable to parse Dhan expiryTime: "
                f"{expiry_time}"
            ) from exc

        self._access_token = access_token
        self._expiry_epoch = expiry_epoch

        self._save_cached_token(
            access_token,
            expiry_epoch,
        )

    @staticmethod
    def _raise_dhan_error(
        status_code: int,
        payload: dict,
        fallback: str = (
            "Unknown Dhan authentication error."
        ),
    ) -> None:
        """Raise a sanitized Dhan authentication error."""

        error_type = payload.get("errorType")
        error_code = payload.get("errorCode")
        error_message = (
            payload.get("errorMessage")
            or payload.get("message")
        )

        details = []

        if error_type:
            details.append(
                f"type={error_type}"
            )

        if error_code:
            details.append(
                f"code={error_code}"
            )

        if error_message:
            details.append(
                f"message={error_message}"
            )

        detail_text = (
            ", ".join(details)
            if details
            else fallback
        )

        raise DhanAuthenticationError(
            "Dhan authentication failed. "
            f"HTTP {status_code}: {detail_text}"
        )

    @staticmethod
    def _parse_expiry_time(
        expiry_time: str,
    ) -> float:
        """
        Parse Dhan expiryTime.

        Naive timestamps are interpreted as Asia/Kolkata.
        """

        value = str(expiry_time)

        if value.endswith("Z"):
            value = (
                value[:-1]
                + "+00:00"
            )

        parsed = datetime.fromisoformat(value)

        if parsed.tzinfo is None:
            parsed = parsed.replace(
                tzinfo=ZoneInfo(
                    "Asia/Kolkata"
                )
            )

        return parsed.timestamp()

    def get_access_token(self) -> str:
        """
        Return a valid access token.

        Order:
        1. Use in-memory token.
        2. Use valid persisted token.
        3. Generate a new token with TOTP.
        """

        if not self._token_is_usable():
            self._load_cached_token()

        if not self._token_is_usable():
            self._request_new_token()

        if not self._access_token:
            raise DhanAuthenticationError(
                "Access token was not available after "
                "authentication."
            )

        return self._access_token

    def refresh(self) -> str:
        """
        Force generation of a fresh access token.

        Use sparingly because Dhan limits token generation
        frequency.
        """

        self._access_token = None
        self._expiry_epoch = None

        return self.get_access_token()

    def token_expiry_epoch(self) -> float | None:
        """Return cached token expiry as Unix epoch seconds."""

        return self._expiry_epoch