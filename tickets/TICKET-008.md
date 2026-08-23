# TICKET-008: No dedicated unit tests for check 4 (prerequisites) — git-state matrix, stranded note, tool fold-in unpinned

## Title
`launch_gate/prerequisites.py` (check 4) has no dedicated test file. The
runner-prompt/gate-log presence, the git-state GO/NO-GO matrix, the
stranded-branch note, and the fourseer/spoke_lint/loop_doctor fold-in are only
incidentally exercised (via a real git repo) in `tests/test_cli.py`, so the
injectable `GitState` and `tool_available` paths are unpinned.

## Evidence
- `ls tests/` shows no `tests/test_prerequisites.py`.
- `grep -rn "check_prerequisites\|GitState\|collect_git_state" tests/` -> no
  matches. `tests/test_cli.py` only drives the whole CLI against a real git
  repo (one GO path, one not-a-repo NO-GO path); it never injects a
  `GitState` or a `tool_available` callable.
- The Cycle 3 brief requires dedicated tests: (a) runner-prompt + gate-log
  present/non-empty vs missing/empty via `tmp_path`; (b) git-state GO/NO-GO
  matrix via an injected `GitState` (on-main+clean+synced vs wrong-branch vs
  dirty vs out-of-sync vs no-origin); (c) stranded-branch note present while
  the verdict stays GO; (d) tool fold-in via an injected `tool_available`
  callable (available vs not). No real git subprocess in the unit tests.

## Impact
The injectable seams (`git_state`, `tool_available`) that make check 4
testable in-process are untested. A regression in the git-state matrix (e.g.
the `ahead==0 and behind==0` sync rule, the no-origin note, or the stranded
branch being reported as a note rather than NO-GO) or in the honest
"importable / not available" tool reporting would ship undetected.

## Suggestion
Add `tests/test_prerequisites.py` (stdlib-only, no git subprocess):
- (a) build an `ai_dir` under `tmp_path` with non-empty `runner-prompt*` and
  `gate*` files -> GO sub-check; then missing and zero-byte variants -> NO-GO.
  Assert the exact evidence lines.
- (b) construct `GitState(...)` directly and assert the verdict for each cell:
  on-main+clean+synced (ahead=0,behind=0,has_origin_main=True) = GO;
  wrong branch = NO-GO; dirty tree = NO-GO; out-of-sync (ahead or behind != 0)
  = NO-GO; no origin/main = GO with a "sync check skipped (note)" line;
  not a repo = NO-GO.
- (c) `build_branches=("build3",)` -> a "stranded build branch" note line is
  present AND the overall verdict stays GO.
- (d) inject `tool_available=lambda t: True` -> "importable on this host
  (verdict folded in)" for each of fourseer/spoke_lint/loop_doctor; inject
  `lambda t: False` -> "not available on this host".
Keep `project_dir` a `tmp_path` placeholder (never collected) since
`git_state` is injected.

---
GitHub issue: https://github.com/belarusian/launch-gate/issues/9
Closes #9
