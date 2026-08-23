# TICKET-030: No committed fixture for the 2-LLM driver dialect (distinct FIVE_BASE_URL / FIVE_LARGE_URL)

## Evidence

The seed defines two driver dialects:

- Single-LLM (seed/reference-run-cycles.sh, lines 30-31): both FIVE_BASE_URL and FIVE_LARGE_URL point to the same endpoint http://192.168.1.161:8080/v1.
- 2-LLM (the actual run-cycles.sh at repo root, lines 30-31): FIVE_BASE_URL=http://192.168.1.157:8080/v1 and FIVE_LARGE_URL=http://192.168.1.161:8081/v1 — two distinct endpoints.

The committed fixture tests/fixtures/driver_five_endpoints.sh (lines 6-7) carries the single-LLM dialect:

    export FIVE_BASE_URL="${FIVE_BASE_URL:-http://192.168.1.161:8080/v1}"
    export FIVE_LARGE_URL="${FIVE_LARGE_URL:-http://192.168.1.161:8080/v1}"

Both URLs are identical, so parse_endpoints dedups to one. No committed fixture exercises the 2-LLM case where parse_endpoints must return two distinct endpoints and the endpoint-contention check must scan the registry for both.

The inline test test_parse_endpoints_dedup_and_order_preserving (test_endpoint_contention.py, line ~79) constructs a 2-endpoint script as a string literal but does not commit it as a fixture file.

## Impact

A regression in parse_endpoints that drops the second distinct URL (e.g. a dedup bug that treats different URLs as duplicates) would not be caught by any committed-fixture-backed test. The 2-LLM dialect is the actual production driver dialect (the repo's own run-cycles.sh), making this the higher-risk case.

## Suggestion

1. Add tests/fixtures/driver_two_llm.sh carrying the 2-LLM dialect (two distinct FIVE_* URLs, matching the seed run-cycles.sh lines 30-31).
2. Add a test in test_endpoint_contention.py that reads this fixture and asserts parse_endpoints returns both URLs in order.
3. Add a test that feeds the 2-LLM fixture through check_endpoint_contention with a registry entry covering only the first endpoint, verifying the second endpoint falls through to the socket fallback.
