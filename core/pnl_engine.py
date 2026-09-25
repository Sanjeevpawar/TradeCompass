"""PnL calculations for paper/live monitoring."""

LOT_SIZE = 50  # NIFTY default; later supplied by instrument metadata.


def _lookup_ltp(leg, ltp_map):
    """Accept both legacy strike-only and safer instrument+strike keys."""
    strike = leg["strike"]
    instrument = leg["instrument"]
    return ltp_map.get(f"{instrument}_{strike}", ltp_map.get(strike))


def calculate_pnl(decision, ltp_map):
    total_pnl = 0.0
    leg_details = []

    for leg in decision.get("legs", []):
        entry = leg.get("entry_premium")
        if entry is None:
            continue
        ltp = _lookup_ltp(leg, ltp_map)
        if ltp is None:
            continue

        multiplier = LOT_SIZE * leg.get("quantity", 1)
        pnl = (entry - ltp) if leg["side"] == "SELL" else (ltp - entry)
        pnl *= multiplier
        total_pnl += pnl
        leg_details.append({
            "strike": leg["strike"],
            "instrument": leg["instrument"],
            "side": leg["side"],
            "entry": entry,
            "ltp": ltp,
            "pnl": pnl,
        })

    return {"total_pnl": total_pnl, "legs": leg_details}
