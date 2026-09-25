from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class DataQualityResult:
    status: str
    reason: str | None
    candle_timestamp: str | None
    chain_fetched_at: str | None

    def as_dict(self) -> dict:
        return {
            "status": self.status,
            "reason": self.reason,
            "candle_timestamp": self.candle_timestamp,
            "chain_fetched_at": self.chain_fetched_at,
        }


def _parse_timestamp(value: str | int | float | None) -> datetime | None:
    if value is None:
        return None

    try:
        return datetime.fromtimestamp(float(value), tz=timezone.utc)
    except (TypeError, ValueError, OverflowError):
        pass

    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


def validate_snapshot_metadata(
    candle_timestamp: str | int | float | None,
    chain_fetched_at: str | None,
) -> DataQualityResult:
    candle_time = _parse_timestamp(candle_timestamp)
    chain_time = _parse_timestamp(chain_fetched_at)

    if candle_time is None:
        return DataQualityResult(
            "INVALID",
            "Candle timestamp is missing or invalid",
            str(candle_timestamp) if candle_timestamp is not None else None,
            chain_fetched_at,
        )

    if chain_time is None:
        return DataQualityResult(
            "INCOMPLETE",
            "Option-chain fetch timestamp is missing or invalid",
            str(candle_timestamp),
            chain_fetched_at,
        )

    return DataQualityResult(
        "METADATA_AVAILABLE",
        None,
        candle_time.isoformat(),
        chain_time.isoformat(),
    )
