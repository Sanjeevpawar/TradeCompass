# main.py

from data.market_data import (
    get_daily_market_data,
    get_spot_market_data,
    get_option_chain_data,
    get_live_market_snapshot
)

from analysis.daily_chart import analyze_daily_chart
from analysis.spot_analysis import analyze_spot_context
from analysis.option_chain import analyze_option_chain

from strategy.strategy_selector import select_strategy
from strategy.strike_selector import select_strikes

from core.decision_builder import build_decision
from core.permission_engine import apply_user_permission

from monitoring.monitoring_engine import monitor_trade

from config import MODE
from ui.user_messages import build_user_trade_message


def main():
    # =============================
    # 1. FETCH DATA
    # =============================
    daily_data = get_daily_market_data()
    spot_data = get_spot_market_data()
    option_data = get_option_chain_data()

    # =============================
    # 2. ANALYZE MARKET
    # =============================
    daily_ctx = analyze_daily_chart(daily_data)
    spot_ctx = analyze_spot_context(spot_data)
    option_ctx = analyze_option_chain(option_data)

    # =============================
    # 3. HARD SAFETY GATE
    # =============================
    if daily_ctx["risk"] == "HIGH" or option_ctx["market_state"] == "dangerous":
        decision = {
            "action": "NO_TRADE",
            "status": "BLOCKED",
            "reason": "Market conditions unsafe for option selling",
            "next_step": "WAIT"
        }

        if MODE == "DEBUG":
            from pprint import pprint
            print("\n=== DECISION STATE (DEBUG) ===")
            pprint(decision)
        else:
            print(
                "ACTION     : NO TRADE\n"
                "REASON     : Market conditions are not safe today\n"
                "NEXT STEP  : Wait for next update"
            )
        return

    # =============================
    # 4. STRATEGY + STRIKES
    # =============================
    strategy_ctx = select_strategy(daily_ctx, spot_ctx, option_ctx)
    strike_ctx = select_strikes(strategy_ctx, option_ctx)

    # =============================
    # 5. BUILD DECISION OBJECT
    # =============================
    decision = build_decision(
        daily_ctx,
        spot_ctx,
        option_ctx,
        strategy_ctx,
        strike_ctx
    )

    # =============================
    # 6. USER PERMISSION FLOW
    # =============================
    # In dashboard / API, this will come from frontend
    user_response = None      # change to "YES" or "NO" to test

    decision = apply_user_permission(decision, user_response)

    # =============================
    # 7. LIVE MONITORING (ONLY IF CONFIRMED)
    # =============================
    if decision.get("status") == "CONFIRMED":
        market_snapshot = get_live_market_snapshot()
        monitor_result = monitor_trade(decision, market_snapshot)

        if MODE == "DEBUG":
            from pprint import pprint
            print("\n=== MONITORING UPDATE (DEBUG) ===")
            pprint(monitor_result)
        else:
            if monitor_result["action"] == "HOLD":
                print(
                    "ACTION     : HOLD\n"
                    "STATUS     : Trade within safe zone\n"
                    "NEXT STEP  : No action required"
                )

            elif monitor_result["action"] == "ALERT":
                print(
                    "ACTION     : ALERT\n"
                    f"REASON     : {monitor_result['reason']}\n"
                    "NEXT STEP  : Monitor closely"
                )

            elif monitor_result["action"] == "EXIT":
                print(
                    "ACTION     : EXIT\n"
                    f"REASON     : {monitor_result['reason']}\n"
                    "NEXT STEP  : Close all positions"
                )

        return

    # =============================
    # 8. OUTPUT (NOT CONFIRMED YET)
    # =============================
    if MODE == "DEBUG":
        from pprint import pprint
        print("\n=== DECISION STATE (DEBUG) ===")
        pprint(decision)

    else:
        if decision["status"] == "WAITING_USER_CONFIRMATION":
            user_message = build_user_trade_message(strategy_ctx, strike_ctx)
            print("\n" + user_message)

        elif decision["status"] == "REJECTED":
            print(
                "ACTION     : TRADE CANCELLED\n"
                "NEXT STEP  : Wait for next update"
            )


if __name__ == "__main__":
    main()
