from datetime import datetime, timedelta

# Keeps track of last feed messages sent
FEED_STATE = {}


def can_emit(feed_type, message, cooldown_minutes=10):
    """
    Returns True if a new feed message should be emitted.
    Prevents duplicates and spam.
    """

    now = datetime.now()

    if feed_type not in FEED_STATE:
        FEED_STATE[feed_type] = {
            "last_message": message,
            "last_time": now
        }
        return True

    last_entry = FEED_STATE[feed_type]

    # Same message → do not repeat
    if last_entry["last_message"] == message:
        return False

    # Cooldown check
    if now - last_entry["last_time"] < timedelta(minutes=cooldown_minutes):
        return False

    # Update state
    FEED_STATE[feed_type] = {
        "last_message": message,
        "last_time": now
    }

    return True

# monitoring/feed_state.py

LAST_STATE = {
    "oi_shift": None,
    "support": None,
    "resistance": None,
    "volatility": None,
    "premium_speed": None
}


def has_changed(key, new_value):
    """
    Returns True if the value has changed since last check
    """
    old_value = LAST_STATE.get(key)

    if old_value != new_value:
        LAST_STATE[key] = new_value
        return True

    return False
