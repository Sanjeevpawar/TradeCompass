# Phase 10.4 corrected validator

Fixes the raw acquisition validator to support Dhan Unix-epoch timestamps and interpret
timestamps in Asia/Kolkata (IST), which is the exchange-local date used by the manifest.

This patch only changes validation code/tests. Raw Dhan data is unchanged.
