# TICKET-035: README canonical registry block emits pid as a JSON number, contradicting the documented string contract

## Evidence

The README "Canonical launch-registry block" documents the JSON content as:

    {
      "project": "<name>",
      "pid": "<driver pid>",
      ...
    }

i.e. `pid` is a **string** in the file. The Cycle-11 probe checklist restates this:
"pid is a string in the file".

But the canonical bash block a driver copies wrote:

    {"project": "$(basename "$PROJ")", "pid": $$, ...}

`$$` is unquoted, so the block emits `"pid": 12345` — a bare JSON **number**,
contradicting the documented string contract.

The code tolerates both: `_parse_registry_file` does `pid=str(data.get("pid", ""))`,
so a numeric pid is coerced to a string. There is no code bug — the drift is purely
in the README's canonical block, which is the template every four driver copies.

## Impact

1. A driver that copies the canonical block verbatim writes a numeric pid, so the
   on-disk registry file does not match the documented JSON contract.
2. Any future consumer that assumes `pid` is a string (per the documented contract)
   would be surprised by the block's own output.
3. The README is internally inconsistent (Content block says string; bash block emits number).

## Suggestion

Quote the pid in the canonical bash block: `"pid": "$$"` so the block emits pid as a
string, matching the documented contract. No code change (the parser already coerces
both forms). Pin the pid-as-string contract with a golden test.
