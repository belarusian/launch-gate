# TICKET-012: parse_endpoints captures trailing shell `}"` from the `${FIVE_*:-...}` dialect

## Evidence
`launch_gate/endpoint_contention.py`, `parse_endpoints` uses
`_URL_RE = re.compile(r"https?://\S+")` and only strips `.,;` via
`url.rstrip(".,;")`. Against the seed driver dialect
(`reference-run-cycles.sh`):

    export FIVE_BASE_URL="${FIVE_BASE_URL:-http://192.168.1.161:8080/v1}"

the regex captures `http://192.168.1.161:8080/v1}"` (the `\S+` runs past the
URL into the closing `}"`). Verified empirically:
`parse_endpoints(...)` returns `['http://192.168.1.161:8080/v1}"']`.

## Impact
The registry stores the *clean* URL (`http://192.168.1.161:8080/v1`). The
checked driver's parsed endpoint carries the trailing `}"`, so the registry
overlap test (`e in target_set`) NEVER matches a real fresh foreign entry →
a genuine endpoint contention is misclassified as GO (false negative). This
breaks case (b) of the brief.

## Suggestion
Strip trailing shell/quote characters from each captured URL: extend the
`rstrip` set to include `}"'` (and keep `.,;`). Keep dedup + order.
