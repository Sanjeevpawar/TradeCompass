# core/permission_engine.py

def apply_user_permission(decision, user_response):
    """
    Validate and apply user confirmation (YES / NO).

    This function:
    - Handles ONLY user intent
    - Is idempotent (safe to retry)
    - Does NOT activate or enter a trade
    """

    # ---------------------------------
    # 1️⃣ DECISION EXISTENCE CHECK
    # ---------------------------------
    if not decision:
        return {
            "status": "ERROR",
            "reason": "No active trade decision found",
            "next_step": "GET_NEW_DECISION"
        }

    current_status = decision.get("status")

    # ---------------------------------
    # 2️⃣ IDEMPOTENCY CHECK
    # ---------------------------------
    # If decision already finalized, return as-is
    if current_status in (
        "AWAITING_ENTRY_PREMIUMS",
        "REJECTED"
    ):
        return decision

    # ---------------------------------
    # 3️⃣ STATE VALIDATION
    # ---------------------------------
    if current_status != "AWAITING_CONFIRMATION":
        return {
            "status": "INVALID_STATE",
            "reason": "Trade is not awaiting user confirmation",
            "current_status": current_status,
            "next_step": "CHECK_TRADE_STATUS"
        }

    # ---------------------------------
    # 4️⃣ PAYLOAD VALIDATION
    # ---------------------------------
    if user_response is None:
        decision["status"] = "AWAITING_CONFIRMATION"
        decision["reason"] = "Awaiting user confirmation"
        decision["next_step"] = "ASK_USER_CONFIRMATION"
        return decision

    if not isinstance(user_response, str):
        decision["status"] = "CONFIRMATION_ERROR"
        decision["reason"] = "Confirmation value must be YES or NO"
        decision["next_step"] = "ASK_USER_CONFIRMATION"
        return decision

    user_response = user_response.strip().upper()

    # ---------------------------------
    # 5️⃣ VALID VALUE CHECK
    # ---------------------------------
    if user_response not in ("YES", "NO"):
        decision["status"] = "CONFIRMATION_ERROR"
        decision["reason"] = "Invalid response. Allowed values: YES or NO"
        decision["next_step"] = "ASK_USER_CONFIRMATION"
        return decision

    # ---------------------------------
    # 6️⃣ APPLY USER INTENT
    # ---------------------------------
    if user_response == "YES":
        decision["status"] = "AWAITING_ENTRY_PREMIUMS"
        decision["next_step"] = "COLLECT_ENTRY_PREMIUMS"
        return decision

    if user_response == "NO":
        decision["status"] = "REJECTED"
        decision["reason"] = "User rejected the trade"
        decision["next_step"] = "STOP_PROCESSING"
        return decision
