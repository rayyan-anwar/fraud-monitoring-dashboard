# Evaluation

Author: Rayyan Anwar

`python scripts/evaluate.py` writes `results/RESULTS.md`. The scorer is trained on one synthetic dataset (seed 0) and the dashboard is evaluated on a different one (seed 123, 20,000 transactions, 1.88% fraud), with ground truth kept outside the database.

## Committed run
| Measure | Value |
|---|---:|
| Precision in top 50 / 200 / 1000 of the queue | 1.00 / 0.74 / 0.25 (random queue: 0.019) |
| High-band alerts | 242 over 90 days (about 2.7 per day) |
| High-band precision / recall | 0.67 / 0.43 |
| Workflow fuzz: 3000 random status changes, 3 reviewers | 617 accepted, 2383 rejected, 0 disagreements with an independent state model; audit rows 618 = 1 + accepted (exact) |
| Ingest + score 20,000 rows | about 0.3 s |
| Filtered ranked list query | median about 3 ms, p95 about 6 ms |

## Interpretation and caveats
- The ranking concentrates fraud strongly at the top of the queue (precision 1.00 at 50), but recall of the high band is 0.43 because many synthetic fraud cases look legitimate by construction.
- `reviewed_precision` shown in the UI is computed only over reviewed alerts, so it is biased toward the queue and is not the model's precision.
- Workflow correctness is verified against an independent model of the transition rules, which tests the implementation, not whether the rules suit a real fraud operation.
- Latency is from SQLite on a 1-core sandbox; a production deployment needs a server database, backups, and load testing.
