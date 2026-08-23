# TICKET-1: No committed fixture for the 2-LLM driver dialect (distinct FIVE_BASE_URL / FIVE_LARGE_URL)

## Evidence

The seed defines two driver dialects:

- **Single-LLM** (`seed/reference-run-cycles.sh`, lines 30-31): both `FIVE_BASE_URL` and `FIVE_LARGE_URL` point to the same endpoint `http://192.168.1.161:8080/v1`.
- **2-LLM** (the actual `run-cycles.sh` at repo root, lines 30-31): `FIVE_BASE_URL=http://192.168.1.157:8080/v1` and `FIVE_LARGE_URL=http://192.168.1.161:8081/v1` — two *distinct* endpoints.

The committed fixture `tests/fixtures/driver_five_endpoints.sh` (lines 6-7) carries the single-LLM dialect: