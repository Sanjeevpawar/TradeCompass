from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Instrument:
    symbol: str
    security_id: str
    exchange_segment: str
    instrument_type: str = "INDEX"


@dataclass(frozen=True)
class OptionSelection:
    strike: float
    option_type: str
    security_id: str | None
    expiry: str
    ltp: float
    bid: float | None
    ask: float | None
    volume: int | None
    oi: int | None
    iv: float | None
    delta: float | None
    gamma: float | None
    theta: float | None
    vega: float | None
    alternatives: list[dict[str, Any]] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


@dataclass(frozen=True)
class RiskSnapshot:
    approved: bool
    entry: float | None
    stop_loss: float | None
    target: float | None
    risk: float | None
    reward: float | None
    risk_reward: float | None
    underlying_invalidation: float | None
    stop_basis: str | None
    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    rejection_reasons: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


@dataclass(frozen=True)
class TradeCompassSignal:
    signal_id: str
    timestamp: str
    symbol: str
    decision: str
    direction: str | None
    setup: str
    strength: str
    spot: float | None
    suggested_option: dict[str, Any] | None
    risk: dict[str, Any]
    technical_evidence: dict[str, Any]
    chain_evidence: dict[str, Any]
    reasons: list[str]
    wait_reason: str | None
    config_version: str = "phase12-v1"
    engine_version: str = "phase12-v1"

    def as_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()
