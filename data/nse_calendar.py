"""NSE trading-calendar data used by historical contract identity logic.

This module intentionally keeps the holiday set explicit and reviewable rather
than silently relying on a generic India holiday calendar.  NIFTY expiry is
shifted to the previous trading day when the nominal Tuesday is an NSE
trading holiday.

Source: NSE India trading-holiday calendars for the F&O segment, 2025 and
2026.  Extend this module when the research window is expanded into later
years, or pass an explicit holiday set to ``resolve_expiry``.
"""

from datetime import date


# NSE F&O trading holidays for calendar year 2025.
NSE_FO_HOLIDAYS_2025 = frozenset(
    {
        date(2025, 2, 26),
        date(2025, 3, 14),
        date(2025, 3, 31),
        date(2025, 4, 10),
        date(2025, 4, 14),
        date(2025, 4, 18),
        date(2025, 5, 1),
        date(2025, 8, 15),
        date(2025, 8, 27),
        date(2025, 10, 2),
        date(2025, 10, 21),
        date(2025, 10, 22),
        date(2025, 11, 5),
        date(2025, 12, 25),
    }
)


# NSE trading holidays for calendar year 2026.  These are the dates relevant
# to the current research window; keeping the complete published list here
# makes the calendar deterministic for future reconstruction runs.
NSE_FO_HOLIDAYS_2026 = frozenset(
    {
        date(2026, 1, 15),
        date(2026, 1, 26),
        date(2026, 2, 19),
        date(2026, 3, 3),
        date(2026, 3, 19),
        date(2026, 3, 26),
        date(2026, 3, 31),
        date(2026, 4, 1),
        date(2026, 4, 3),
        date(2026, 4, 14),
        date(2026, 5, 1),
        date(2026, 5, 28),
        date(2026, 6, 26),
        date(2026, 8, 26),
        date(2026, 9, 14),
        date(2026, 10, 2),
        date(2026, 10, 20),
        date(2026, 11, 10),
        date(2026, 11, 24),
        date(2026, 12, 25),
    }
)


NSE_FO_HOLIDAYS = frozenset(NSE_FO_HOLIDAYS_2025 | NSE_FO_HOLIDAYS_2026)
