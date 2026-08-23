# TICKET-011 — README: wire redirect-safety + prerequisites to match behavior

**Capability:** `README.md` — under "The four checks", expand entries (1)
redirect-safety and (4) prerequisites so the documented behavior matches the
implemented + tested behavior. Do not invent behavior that is not implemented.

## redirect-safety matrix to document
- `>> cycles.out` (append) = GO (preserves history).
- bare `>` / `1> cycles.out` (truncate) = NO-GO against a marker-bearing
  `cycles.out`; GO when no history (first launch) or the file has no markers.
- a line that does not redirect into `cycles.out` (no redirect, a different
  file, `2> cycles.out` stderr-only, `2>&1`) = GO — nothing to gate.
- only `cycles.out` is gated; the marker dialect is `========== CYCLE N ==========`.

## prerequisites matrix to document
- runner prompt + gate log present/non-empty (substring match, first in sorted
  order wins).
- on `main` + clean + in-sync with `origin/main` = GO, else NO-GO; no
  `origin/main` = GO with a note.
- a stranded `build*` branch is a Phase-0 NOTE, never NO-GO.
- fourseer/spoke-lint/loop-doctor verdicts folded in when importable, "not
  available" otherwise, in that fixed order.

## Acceptance
README concise; every documented behavior is implemented and tested.
