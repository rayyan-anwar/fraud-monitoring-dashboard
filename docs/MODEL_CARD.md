# System Card

Author: Rayyan Anwar

**System:** a review queue around a class-balanced logistic-regression scorer trained on synthetic transactions. The scorer is a ranking signal; the system's purpose is the human workflow and its audit trail.

**Intended use:** education and as a reference design for alert triage tools. **Prohibited:** automated blocking, account closure, or accusing customers; any decision about real people without proper validation, fairness review and legal and compliance approval.

**Human oversight:** alerts only queue items; every status change needs an authenticated reviewer and a written note; confirmed fraud is final and logged; there is no auto-action.

**Data and privacy:** demo data is synthetic. If adapted to real data you must address PII handling, retention, access logging, encryption at rest, and regulation (for example PCI DSS and data-protection law); none of that is provided here.

**Limitations and risks:** uncalibrated scores; simplified features; no drift monitoring or retraining; no fairness audit (disparate impact could arise from features such as account age or country); SQLite is single-node; no rate limiting, password or SSO integration; no claim of fraud certification or security guarantee.
