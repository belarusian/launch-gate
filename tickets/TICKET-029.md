# TICKET-029: wire wall-sizing (check 3) into the README

## Evidence
The README's check 3 (item 3) entry is a one-liner:
`outer_wall >= 3 * max_observed inner-pass duration.`
The implemented + tested behavior (Cycle 8 + Cycle 9) is richer and should be
documented so the README matches the code:
- the two observation sources: the fourseer report's `Duration (s)` column (4th
  cell; `-` rows skipped) and the `cycles.out` consecutive start-marker gaps
  (`< 2` markers = none);
- the verdict: `outer_wall >= 3 * max_observed` is GO, else NO-GO (naming the
  required value);
- observations present but no outer wall (no `--script`, or a script without a
  perl-alarm wall) -> NO-GO ("cannot verify sizing");
- no observations -> GO with the conservative-default note.

## Impact
The one-liner is accurate but incomplete; a reader cannot tell which artifacts
are read, how the observation is derived, or when the check is NO-GO. Wiring it
makes the documented behavior match the implemented + tested behavior.

## Suggestion
Expand README item 3 to the full classification matrix (bullets), matching the
style of items 1/2/4. Do not invent behavior that is not implemented.
