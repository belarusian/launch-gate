# TICKET-5: No committed gate-log dialect fixtures (Results/Lessons table variants)

## Evidence

The seed's SEED.md (lines 22-24) explicitly warns:

> Gate-log dialects drift between projects (`### Results` vs `| Area | Status |` tables, `**Lessons:**` vs `### Lessons`). Parsers must tolerate variants and stay honest about what they could not parse.

The seed's `gate-log-sample.md` shows one dialect: