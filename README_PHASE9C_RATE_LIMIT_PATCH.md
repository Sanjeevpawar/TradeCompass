# Phase 9C Rate-Limit / Retry Patch

This patch hardens the Dhan historical strike-band collector against HTTP 429 rate limits.

## Changes

- Default inter-request pause is now 0.5 seconds.
- HTTP 429 responses are retried automatically (default: 5 retries).
- Exponential backoff is used when `Retry-After` is not provided.
- If `Retry-After` is provided, it is respected.
- Non-429 errors are not retried automatically.
- The report records logical requests, total HTTP attempts, retry events, and final errors.
- Failed required requests still make the collection status `FAIL`; partial data is never silently treated as complete.
- Existing strike/expiry provenance and no-forward-fill policies are unchanged.

## Optional CLI controls

```powershell
py -m scripts.collect_dhan_strike_band --from-date 2026-09-01 --to-date 2026-09-05 --pause-seconds 0.5 --max-retries 5 --retry-backoff-seconds 1
```

## Validation

The Phase 9C test file contains tests for configuration defaults and HTTP 429 retry behavior.
