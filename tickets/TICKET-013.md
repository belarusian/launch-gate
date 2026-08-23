# TICKET-013: parse_ss reads the wrong column — socket fallback returns [] for real `ss -tnp`

## Evidence
`launch_gate/endpoint_contention.py`, `parse_ss` sets `local = cols[3]`.
Real `ss -tnp` columns are:
`[Netid, State, Recv-Q, Send-Q, Local Address:Port, Peer Address:Port, Process]`
so `cols[3]` is the **Send-Q** (a number), not the local address. Verified
empirically: `parse_ss(<real ss -tnp text>)` returns `[]`.

## Impact
The socket-snapshot fallback (brief case (f)) never sees any established
line, so a foreign pid holding a target endpoint is never detected →
misclassified as GO (false negative). The fallback is dead against real
`ss` output (it only worked for a 4-column synthetic layout).

## Suggestion
Read the local address from `cols[4]` (Local Address:Port). Keep the
`ESTAB` state filter and the `users:(("name",pid=N,...))` pid extraction.
