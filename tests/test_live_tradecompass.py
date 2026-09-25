from data.market_models import OptionChainSnapshot, OptionQuote
from live.chain_signals import build_live_chain_context


def _chain():
    return OptionChainSnapshot(
        "NIFTY", 26000, "2026-09-24", [
            OptionQuote(25900, "CE", "1", 100, 99, 101, 1000, 5000, 6000, 18, .65, .02, -1, .1),
            OptionQuote(26000, "CE", "2", 120, 119, 121, 1200, 6000, 7000, 18, .55, .02, -1, .1),
            OptionQuote(26100, "CE", "3", 90, 89, 91, 1500, 4000, 5000, 18, .45, .02, -1, .1),
            OptionQuote(25900, "PE", "4", 90, 89, 91, 1500, 9000, 7000, 18, -.55, .02, -1, .1),
            OptionQuote(26000, "PE", "5", 120, 119, 121, 1200, 10000, 8000, 18, -.55, .02, -1, .1),
            OptionQuote(26100, "PE", "6", 140, 139, 141, 1000, 7000, 6000, 18, -.45, .02, -1, .1),
        ]
    )


def test_chain_context_is_deterministic_and_uses_common_strikes():
    ctx = build_live_chain_context(_chain())
    assert ctx["pcr"] is not None
    assert ctx["call_oi"] == 15000
    assert ctx["put_oi"] == 26000
    assert ctx["data_quality"] == "COMPLETE"
    assert ctx["signal"] in {"BUY_CALL", "BUY_PUT", "WAIT"}


def test_chain_context_never_calls_oi_writers():
    ctx = build_live_chain_context(_chain())
    text = " ".join(ctx["bullish_evidence"] + ctx["bearish_evidence"]).lower()
    assert "writer" not in text
