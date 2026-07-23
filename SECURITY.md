# Security and responsible disclosure

## Software vulnerabilities

Report suspected security issues privately to erwinrandy3@gmail.com. Please do
not open a public issue for an unpatched vulnerability. We aim to acknowledge
reports within a reasonable window and to coordinate a fix and disclosure.

## Dataset findings (responsible disclosure)

SynthAudit-Bench can surface structural flaws in named public datasets. Findings
that name a dataset follow a responsible-disclosure procedure:

1. Notify the dataset maintainers before public release, with a reasonable
   response window.
2. Frame findings as structural properties of the released file, never as
   judgments of the authors.
3. Offer the constructive remedy (the honest feature view and re-benchmark
   recipe) where applicable.
4. Keep a disclosure log with dates and responses.

## Benchmark integrity

The public gold set is memorizable. The held-out and re-seeded partitions exist
to detect overfitting and must be preserved. Contributors must not exfiltrate
held-out labels or attempt re-identification of individuals in datasets that
describe people (all such records are synthetic).
