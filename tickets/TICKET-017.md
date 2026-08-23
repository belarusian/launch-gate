# TICKET-017: wire check 2 (endpoint-contention) into the README classification matrix

## Evidence
`README.md` item 2 is a two-line high-level description ("via the launch-registry
(below), with a socket snapshot fallback. Never guesses occupancy."). The
implemented + tested behavior (Cycle 5 fixes + Cycle 6 edge pins) is far more
specific than that, so the documented behavior does not yet match the code.

## Impact
A reader of the README cannot tell: how the FIVE_* endpoints are parsed (and the
no-script / no-endpoint GO note), the registry fresh/stale/absent/foreign-project
matrix, that a non-empty registry is authoritative (socket fallback skipped), the
socket-snapshot fallback (`--ss-file` precedence over live `ss`, pid-lineage
attribution, the no-attributable-pid honesty note), or the never-guess
"no occupancy data" note.

## Suggestion
Expand README item 2 to the full classification matrix, matching the implemented
+ tested behavior exactly (no invented behavior): endpoint parse + no-data note;
registry scan (fresh foreign = NO-GO, fresh same-project = GO, stale = GO note,
malformed = skipped, non-empty dir = authoritative / socket skipped); socket
fallback (`--ss-file` precedence, lineage vs foreign pid, no-pid note, multi-line
foreign-wins, empty/None lineage); and the no-occupancy-data note.
