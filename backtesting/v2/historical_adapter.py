from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path

from backtesting.v2.models import HistoricalOptionBar


TRUE_VALUES = {"1", "true", "yes", "y"}


def _float(value: object) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _int(value: object) -> int:
    parsed = _float(value)
    return int(parsed) if parsed is not None else 0


def _bool(value: object) -> bool:
    return str(value or "").strip().lower() in TRUE_VALUES


def _first(row: dict[str, str], *names: str) -> str:
    for name in names:
        value = row.get(name)
        if value not in (None, ""):
            return str(value)
    return ""


def load_reconstructed_option_bars(
    path: str | Path,
    *,
    require_reconstruction_eligible: bool = True,
) -> tuple[list[HistoricalOptionBar], dict]:
    """Adapt Phase 9A fixed-contract CSV rows to the v2 backtester model.

    Rows are processed directly from the CSV instead of first materializing the
    entire file with list(reader). This keeps memory usage bounded for the
    full-year and larger historical datasets.

    Only fixed-contract rows marked reconstruction_eligible are passed by default.
    Derived expiry/Delta are preserved as research fields; this adapter does not
    upgrade them to broker-verified identity or broker-reported Greeks.
    """
    path = Path(path)
    rejected = Counter()
    bars: list[HistoricalOptionBar] = []
    identity = Counter()
    spread_available = 0
    delta_available = 0
    input_rows = 0

    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fields = set(reader.fieldnames or [])
        required = {
            "timestamp", "expiry", "strike", "option_type",
            "open", "high", "low", "close"
        }
        missing = sorted(required - fields)
        if missing:
            raise ValueError(
                f"Missing required reconstructed-option columns: {missing}"
            )

        for row in reader:
            input_rows += 1

            if require_reconstruction_eligible and not _bool(
                row.get("reconstruction_eligible")
            ):
                rejected["not_reconstruction_eligible"] += 1
                continue

            if str(row.get("contract_continuity") or "").upper() != "CONTINUOUS":
                rejected["not_continuous"] += 1
                continue

            expiry = _first(row, "expiry", "derived_expiry")
            strike = _float(row.get("strike"))
            option_type = str(row.get("option_type") or "").upper()
            timestamp = str(row.get("timestamp") or "")
            open_ = _float(row.get("open", row.get("option_open")))
            high = _float(row.get("high", row.get("option_high")))
            low = _float(row.get("low", row.get("option_low")))
            close = _float(row.get("close", row.get("option_close")))

            if (
                not timestamp
                or not expiry
                or strike is None
                or option_type not in {"CE", "PE"}
            ):
                rejected["invalid_identity"] += 1
                continue

            if (
                None in (open_, high, low, close)
                or min(open_, high, low, close) < 0
            ):
                rejected["invalid_ohlc"] += 1
                continue

            delta = _float(_first(row, "delta", "model_delta"))
            iv = _float(row.get("iv"))
            bid = _float(row.get("bid"))
            ask = _float(row.get("ask"))

            if delta is not None:
                delta_available += 1
            if bid is not None and ask is not None:
                spread_available += 1

            identity_status = str(
                row.get("contract_identity_status")
                or row.get("identity_status")
                or "DERIVED"
            ).upper()
            identity[identity_status] += 1

            bars.append(
                HistoricalOptionBar(
                    timestamp=timestamp,
                    expiry=expiry,
                    strike=strike,
                    option_type=option_type,
                    open=open_,
                    high=high,
                    low=low,
                    close=close,
                    volume=_int(_first(row, "volume", "option_volume")),
                    iv=iv,
                    delta=delta,
                    theta=_float(row.get("theta")),
                    gamma=_float(row.get("gamma")),
                    vega=_float(row.get("vega")),
                    bid=bid,
                    ask=ask,
                    spot=_float(_first(row, "spot", "option_spot")),
                )
            )

    bars.sort(
        key=lambda b: (b.timestamp, b.option_type, b.expiry, b.strike)
    )

    report = {
        "status": "PASS",
        "input": {"file": str(path), "rows": input_rows},
        "output": {"bars": len(bars), "rejected": dict(rejected)},
        "identity": dict(identity),
        "data_availability": {
            "delta_rows": delta_available,
            "spread_rows": spread_available,
            "spread_available_pct": (
                round(spread_available / len(bars) * 100, 2)
                if bars else 0.0
            ),
        },
        "research_policy": {
            "fixed_contract_only": True,
            "continuous_contract_only": True,
            "derived_identity_preserved": True,
            "missing_bid_ask_not_fabricated": True,
            "missing_delta_not_fabricated": True,
        },
    }

    return bars, report
