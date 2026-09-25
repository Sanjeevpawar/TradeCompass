import csv
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RECON = ROOT / "data" / "dhan_history" / "reconstructed"

OPTION_FILE = RECON / "nifty_fixed_contracts_1y.csv"
UNDERLYING_FILE = RECON / "nifty_underlying_1y.csv"
REPORT_FILE = RECON / "reconstructed_dataset_validation_report.json"


REQUIRED_OPTION = {
    "timestamp",
    "option_type",
    "open",
    "high",
    "low",
    "close",
    "strike",
    "spot",
    "expiry",
    "contract_key",
    "contract_continuity",
    "contract_identity_status",
    "same_day_gap_count",
    "duplicate_timestamp_count",
    "reconstruction_eligible",
}


VALID_OPTION_TYPES = {"CE", "PE"}

REQUIRED_UNDERLYING = {
    "timestamp",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "oi",
    "source_file",
}


def parse_ts(value):
    return datetime.fromisoformat(value)


def validate_option_row(r, row_number):
    errors = []

    option_type = str(
        r.get("option_type", "")
    ).strip().upper()

    if option_type not in VALID_OPTION_TYPES:
        errors.append(
            f"row {row_number}: invalid option_type: "
            f"{option_type!r}"
        )

    try:
        strike = float(r["strike"])

        if strike <= 0:
            errors.append(
                f"row {row_number}: invalid strike: {strike}"
            )

    except (TypeError, ValueError, KeyError) as exc:
        errors.append(
            f"row {row_number}: invalid strike: {exc}"
        )

    try:
        spot = float(r["spot"])

        if spot <= 0:
            errors.append(
                f"row {row_number}: non-positive spot: {spot}"
            )

    except (TypeError, ValueError, KeyError) as exc:
        errors.append(
            f"row {row_number}: invalid spot: {exc}"
        )

    prices = {}

    for field in ("open", "high", "low", "close"):
        try:
            value = float(r[field])
            prices[field] = value

            if value <= 0:
                errors.append(
                    f"row {row_number}: non-positive "
                    f"{field}: {value}"
                )

        except (TypeError, ValueError, KeyError) as exc:
            errors.append(
                f"row {row_number}: invalid "
                f"{field}: {exc}"
            )

    if len(prices) == 4:
        open_price = prices["open"]
        high_price = prices["high"]
        low_price = prices["low"]
        close_price = prices["close"]

        if high_price < low_price:
            errors.append(
                f"row {row_number}: high < low"
            )

        if not (
            low_price
            <= open_price
            <= high_price
        ):
            errors.append(
                f"row {row_number}: "
                f"open outside low/high range"
            )

        if not (
            low_price
            <= close_price
            <= high_price
        ):
            errors.append(
                f"row {row_number}: "
                f"close outside low/high range"
            )

    expiry = str(
        r.get("expiry", "")
    ).strip()

    try:
        datetime.fromisoformat(expiry)
    except (TypeError, ValueError) as exc:
        errors.append(
            f"row {row_number}: invalid expiry: "
            f"{expiry!r} ({exc})"
        )

    return errors


def validate_underlying_row(r, row_number):
    errors = []

    # ---------------------------------------------------------
    # Timestamp
    # ---------------------------------------------------------
    timestamp = str(
        r.get("timestamp", "")
    ).strip()

    try:
        parse_ts(timestamp)
    except Exception as exc:
        errors.append(
            f"underlying row {row_number}: "
            f"invalid timestamp: {exc}"
        )

    # ---------------------------------------------------------
    # OHLC
    # ---------------------------------------------------------
    prices = {}

    for field in (
        "open",
        "high",
        "low",
        "close",
    ):
        try:
            value = float(r[field])
            prices[field] = value

            if value <= 0:
                errors.append(
                    f"underlying row {row_number}: "
                    f"non-positive {field}: {value}"
                )

        except (TypeError, ValueError, KeyError) as exc:
            errors.append(
                f"underlying row {row_number}: "
                f"invalid {field}: {exc}"
            )

    if len(prices) == 4:
        open_price = prices["open"]
        high_price = prices["high"]
        low_price = prices["low"]
        close_price = prices["close"]

        if high_price < low_price:
            errors.append(
                f"underlying row {row_number}: "
                f"high < low"
            )

        if not (
            low_price
            <= open_price
            <= high_price
        ):
            errors.append(
                f"underlying row {row_number}: "
                f"open outside low/high range"
            )

        if not (
            low_price
            <= close_price
            <= high_price
        ):
            errors.append(
                f"underlying row {row_number}: "
                f"close outside low/high range"
            )

    # ---------------------------------------------------------
    # Volume
    # ---------------------------------------------------------
    try:
        volume = float(r["volume"])

        if volume < 0:
            errors.append(
                f"underlying row {row_number}: "
                f"negative volume: {volume}"
            )

    except (TypeError, ValueError, KeyError) as exc:
        errors.append(
            f"underlying row {row_number}: "
            f"invalid volume: {exc}"
        )

    # ---------------------------------------------------------
    # Open Interest
    #
    # OI is nullable in the current reconstructed dataset.
    # Blank values are allowed.
    # If populated, it must be numeric and non-negative.
    # ---------------------------------------------------------
    oi = str(
        r.get("oi", "")
    ).strip()

    if oi:
        try:
            oi_value = float(oi)

            if oi_value < 0:
                errors.append(
                    f"underlying row {row_number}: "
                    f"negative oi: {oi_value}"
                )

        except ValueError as exc:
            errors.append(
                f"underlying row {row_number}: "
                f"invalid oi: {exc}"
            )

    # ---------------------------------------------------------
    # Source file
    # ---------------------------------------------------------
    source_file = str(
        r.get("source_file", "")
    ).strip()

    if not source_file:
        errors.append(
            f"underlying row {row_number}: "
            f"missing source_file"
        )

    return errors


def validate():
    errors = []

    rows = 0
    contracts = {}
    seen = set()

    duplicate_contract_timestamps = 0

    timestamp_min = None
    timestamp_max = None

    if not OPTION_FILE.exists():
        raise FileNotFoundError(OPTION_FILE)

    if not UNDERLYING_FILE.exists():
        raise FileNotFoundError(UNDERLYING_FILE)

    # =========================================================
    # OPTION DATA
    # =========================================================
    with OPTION_FILE.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as f:

        reader = csv.DictReader(f)

        missing = (
            REQUIRED_OPTION
            - set(reader.fieldnames or [])
        )

        if missing:
            errors.append(
                f"missing option columns: "
                f"{sorted(missing)}"
            )

        for r in reader:
            rows += 1

            try:
                ts = parse_ts(r["timestamp"])
                strike = float(r["strike"])
                expiry = r["expiry"]
                option_type = r["option_type"]

            except Exception as exc:
                errors.append(
                    f"row {rows}: parse error: {exc}"
                )
                continue

            errors.extend(
                validate_option_row(r, rows)
            )

            if (
                timestamp_min is None
                or ts < timestamp_min
            ):
                timestamp_min = ts

            if (
                timestamp_max is None
                or ts > timestamp_max
            ):
                timestamp_max = ts

            # -------------------------------------------------
            # Duplicate contract timestamp
            # -------------------------------------------------
            key = r["contract_key"]

            dedupe_key = (
                key,
                r["timestamp"],
            )

            if dedupe_key in seen:
                duplicate_contract_timestamps += 1

                errors.append(
                    f"duplicate contract timestamp: "
                    f"{dedupe_key}"
                )

            seen.add(dedupe_key)

            # -------------------------------------------------
            # Contract key
            # -------------------------------------------------
            expected_key = (
                f"{expiry}|"
                f"{strike:g}|"
                f"{option_type}"
            )

            if key != expected_key:
                errors.append(
                    f"contract_key mismatch at row "
                    f"{rows}: {key} != {expected_key}"
                )

            # -------------------------------------------------
            # Reconstruction eligibility
            # -------------------------------------------------
            eligible = (
                r["reconstruction_eligible"]
                .strip()
                .lower()
                == "true"
            )

            continuity = r[
                "contract_continuity"
            ]

            if eligible != (
                continuity == "CONTINUOUS"
            ):
                errors.append(
                    f"eligibility mismatch for {key}"
                )

            # -------------------------------------------------
            # Contract identity
            # -------------------------------------------------
            if (
                r["contract_identity_status"]
                != "DERIVED"
            ):
                errors.append(
                    f"non-DERIVED identity for {key}"
                )

            # -------------------------------------------------
            # Contract metadata
            # -------------------------------------------------
            meta = contracts.setdefault(
                key,
                {
                    "expiry": expiry,
                    "strike": strike,
                    "option_type": option_type,
                    "continuity": continuity,
                    "eligible": eligible,
                    "rows": 0,
                    "gap_count":
                        r["same_day_gap_count"],
                    "dup_count":
                        r["duplicate_timestamp_count"],
                },
            )

            meta["rows"] += 1

            for field, value in [
                ("expiry", expiry),
                ("strike", strike),
                ("option_type", option_type),
                ("continuity", continuity),
                ("eligible", eligible),
            ]:
                if meta[field] != value:
                    errors.append(
                        f"inconsistent {field} "
                        f"within {key}"
                    )

            # -------------------------------------------------
            # Per-contract duplicate count
            # -------------------------------------------------
            try:
                if (
                    int(
                        r["duplicate_timestamp_count"]
                    )
                    != 0
                ):
                    errors.append(
                        f"nonzero duplicate count "
                        f"in {key}"
                    )

            except Exception:
                errors.append(
                    f"invalid duplicate_timestamp_count "
                    f"in {key}"
                )

    # =========================================================
    # CONTRACT-LEVEL VALIDATION
    # =========================================================
    continuity_counts = defaultdict(int)
    eligible_count = 0

    for meta in contracts.values():

        continuity_counts[
            meta["continuity"]
        ] += 1

        eligible_count += int(
            meta["eligible"]
        )

        if (
            meta["continuity"] == "CONTINUOUS"
            and int(meta["gap_count"]) != 0
        ):
            errors.append(
                f"continuous contract has gaps: "
                f"{meta}"
            )

        if (
            meta["continuity"] == "SINGLETON"
            and meta["rows"] != 1
        ):
            errors.append(
                f"singleton contract has "
                f"{meta['rows']} rows"
            )

    # =========================================================
    # UNDERLYING DATA
    # =========================================================
    underlying_rows = 0
    underlying_seen = set()

    with UNDERLYING_FILE.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as f:

        reader = csv.DictReader(f)

        missing_underlying = (
            REQUIRED_UNDERLYING
            - set(reader.fieldnames or [])
        )

        if missing_underlying:
            errors.append(
                f"missing underlying columns: "
                f"{sorted(missing_underlying)}"
            )

        for r in reader:
            underlying_rows += 1

            errors.extend(
                validate_underlying_row(
                    r,
                    underlying_rows,
                )
            )

            ts = r.get("timestamp")

            if ts in underlying_seen:
                errors.append(
                    f"duplicate underlying timestamp: "
                    f"{ts}"
                )

            underlying_seen.add(ts)

    # =========================================================
    # REPORT
    # =========================================================
    report = {
        "phase":
            "10.6_reconstructed_dataset_validation",

        "status":
            "PASS"
            if not errors
            else "BLOCKED",

        "option_rows": rows,

        "underlying_rows":
            underlying_rows,

        "contracts":
            len(contracts),

        "continuity":
            dict(
                sorted(
                    continuity_counts.items()
                )
            ),

        "reconstruction_eligible_contracts":
            eligible_count,

        "identity_status":
            "DERIVED_ONLY",

        "duplicate_contract_timestamps":
            duplicate_contract_timestamps,

        "timestamp_range": [
            timestamp_min.isoformat()
            if timestamp_min
            else None,

            timestamp_max.isoformat()
            if timestamp_max
            else None,
        ],

        "errors":
            errors[:100],

        "error_count":
            len(errors),
    }

    REPORT_FILE.write_text(
        json.dumps(
            report,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(
        "Reconstructed dataset validation: "
        f"{report['status']}"
    )

    print(
        f"Option rows: {rows}"
    )

    print(
        f"Underlying rows: "
        f"{underlying_rows}"
    )

    print(
        f"Contracts: {len(contracts)}"
    )

    print(
        "Continuity: "
        f"{dict(sorted(continuity_counts.items()))}"
    )

    print(
        "Reconstruction eligible: "
        f"{eligible_count}"
    )

    print(
        "Duplicate contract timestamps: "
        f"{duplicate_contract_timestamps}"
    )

    print(
        f"Errors: {len(errors)}"
    )

    print(
        "Report: "
        f"{REPORT_FILE.relative_to(ROOT)}"
    )

    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(validate())