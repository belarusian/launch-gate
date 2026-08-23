# TICKET-001: Baseline fails `ruff check` (F401, E501 x6, B905)

## Title
The launch_gate package does not pass the ruff gate; 8 findings must be fixed.

## Evidence
`python3 -m ruff check launch_gate/` reports 8 findings (line-length 100,
select E,F,W,I,B,UP):

- `launch_gate/endpoint_contention.py:25` — F401 `os` imported but unused.
- `launch_gate/endpoint_contention.py:179` — E501 line 104 > 100
  (`lines.append(f"registry file {path.name} is malformed; skipped (not counted as occupancy).")`).
- `launch_gate/endpoint_contention.py:275` — E501 line 105 > 100
  (`lines.append(SocketLine(local_hostport=f"{hostport[0]}:{hostport[1]}", pid=pid, process=process))`).
- `launch_gate/endpoint_contention.py:393` — E501 line 103 > 100
  (`lines.append("no occupancy data (no registry, no socket snapshot); GO with no occupancy data.")`).
- `launch_gate/prerequisites.py:198` — E501 line 108 > 100
  (`f"NO-GO: main out of sync with origin/main (ahead={state.ahead} behind={state.behind})."`).
- `launch_gate/wall_sizing.py:107` — B905 `zip()` without an explicit `strict=` parameter
  (`for a, b in zip(stamps, stamps[1:]):`).
- `launch_gate/wall_sizing.py:182` — E501 line 103 > 100
  (`lines.append(f"observed inner-pass durations: {sorted(observations)}.")`).
- `launch_gate/wall_sizing.py:215` — E501 line 108 > 100
  (`lines.append("no observed inner-pass durations found (no fourseer Duration, no cycles.out timestamps).")`).

## Impact
The documented gate (`ruff check launch_gate/`) fails, so the package cannot be
considered clean. Any CI or pre-commit gate that runs ruff will reject the tree.

## Suggestion
- Remove the unused `import os` at `endpoint_contention.py:25`.
- Wrap or reword the six E501 lines to fit within 100 columns (implicit string
  concatenation / line continuation), preserving the exact rendered text.
- Add `strict=False` to the `zip()` at `wall_sizing.py:107` (the two sequences
  differ by one element by construction, so `strict=False` is the honest choice).
- Re-run `python3 -m ruff check launch_gate/` until it reports no findings.
