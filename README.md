# 🛡️ Fraud Monitoring Dashboard

<div align="center">

  <img src="https://capsule-render.vercel.app/api?type=waving&color=0:0F172A,50:0F766E,100:06B6D4&height=220&section=header&text=Fraud%20Monitoring&fontSize=42&fontColor=FFFFFF&animation=fadeIn&fontAlignY=38&desc=Intelligent%20Risk%20Analysis%20%7C%20Human-in-the-Loop%20AI&descSize=15&descAlignY=60" width="100%" alt="Animated Fraud Monitoring Dashboard banner" />

  <h3>Detect Risk. Investigate Transactions. Preserve Trust.</h3>

  **Built by Rayyan Anwar**

  *AI/ML Engineer · Researcher · Technology Manager · Software Developer*

  <p>
    <img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python" />
    <img src="https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI" />
    <img src="https://img.shields.io/badge/SQLite-003B57?style=for-the-badge&logo=sqlite&logoColor=white" alt="SQLite" />
    <img src="https://img.shields.io/badge/Responsible_AI-6D28D9?style=for-the-badge" alt="Responsible AI" />
  </p>

  <p>
    <img src="https://img.shields.io/badge/Tests-22%20Passed-success?style=flat-square" alt="22 tests passed" />
    <img src="https://img.shields.io/badge/Data-Synthetic-blue?style=flat-square" alt="Synthetic data" />
    <img src="https://img.shields.io/badge/License-MIT-green?style=flat-square" alt="MIT License" />
    <img src="https://img.shields.io/badge/Review-Human--in--the--Loop-orange?style=flat-square" alt="Human review required" />
  </p>

  <p>
    <a href="#-overview">Overview</a> •
    <a href="#-features">Features</a> •
    <a href="#-performance--evaluation">Evaluation</a> •
    <a href="#-quick-start">Quick Start</a> •
    <a href="#-documentation">Documentation</a>
  </p>

</div>

---

## ⚡ Overview

**Fraud Monitoring Dashboard** is a risk-ranked transaction monitoring and investigation system designed to help analysts prioritize suspicious activity, review alerts, document decisions, and maintain an auditable record of every status change.

Built with Python, FastAPI, SQLite, and a lightweight browser dashboard, the project demonstrates practical engineering for a human-supervised risk monitoring workflow.

Instead of treating a model score as a final verdict, the system gives authorized reviewers the tools to investigate transactions and make documented decisions.

> [!IMPORTANT]
> **Synthetic data. Human review required.** Risk scores are relative signals, not proof of fraud. The system does not automatically block transactions or take enforcement actions. Read the [Model Card](docs/MODEL_CARD.md) before adapting this project.

## ✨ Features

<table>
  <tr>
    <td width="50%">
      <h3>🎯 Risk-Ranked Queue</h3>
      Prioritize transactions using risk scores and risk bands, with filtering, sorting, and pagination.
    </td>
    <td width="50%">
      <h3>🚨 High-Risk Alerts</h3>
      Surface high-risk transactions and summarize monitoring activity through dashboard statistics.
    </td>
  </tr>
  <tr>
    <td width="50%">
      <h3>👤 Human Review Workflow</h3>
      Enforce allowed status transitions, mandatory review notes, and conflict detection.
    </td>
    <td width="50%">
      <h3>🔐 Role-Based Access</h3>
      Support viewer, analyst, and admin roles through API-key-based authorization.
    </td>
  </tr>
  <tr>
    <td width="50%">
      <h3>🧾 Append-Only Audit Trail</h3>
      Protect audit history using SQLite triggers and export review data to CSV.
    </td>
    <td width="50%">
      <h3>📥 Validated Data Ingestion</h3>
      Import CSV transactions or load synthetic samples, with rejected rows and reasons reported.
    </td>
  </tr>
</table>

## 📊 Performance & Evaluation

Results from the committed synthetic-data evaluation are summarized below.

| Metric | Result |
|---|---:|
| Top-50 queue precision | 1.00 |
| Random queue precision baseline | 0.019 |
| High-risk band precision | 0.67 |
| High-risk band recall | 0.43 |
| High-risk alerts | Approximately 2.7/day |
| Randomized workflow operations checked | 3,000 |
| Ingestion benchmark | 20,000 rows in approximately 0.3 seconds |
| Executed tests reported | 22 passing |

**How to interpret these results**

- The top-50 result comes from a synthetic evaluation and is not evidence of equivalent real-world fraud detection performance.
- The high-risk precision and recall values reflect the selected synthetic dataset and risk threshold.
- The ingestion timing is an observed benchmark, not a performance guarantee for every machine or dataset.
- Review-queue precision is subject to selection bias and should not be interpreted as overall production fraud-detection accuracy.

For methodology and limitations, see [Evaluation Documentation](docs/EVALUATION.md) and [`results/RESULTS.md`](results/RESULTS.md).

## 🧠 How It Works

<div align="center">

  <img src="https://img.shields.io/badge/01-Data%20Ingestion-0F766E?style=for-the-badge" alt="Step 1: Data ingestion" />
  <br />
  <img src="https://img.shields.io/badge/02-Validation%20%26%20Scoring-155E75?style=for-the-badge" alt="Step 2: Validation and scoring" />
  <br />
  <img src="https://img.shields.io/badge/03-Risk%20Ranking-1D4ED8?style=for-the-badge" alt="Step 3: Risk ranking" />
  <br />
  <img src="https://img.shields.io/badge/04-Human%20Investigation-6D28D9?style=for-the-badge" alt="Step 4: Human investigation" />
  <br />
  <img src="https://img.shields.io/badge/05-Audited%20Decision-9A3412?style=for-the-badge" alt="Step 5: Audited decision" />

</div>

1. **Ingest:** Upload a CSV file or load sample transactions.
2. **Validate:** Check incoming data and report rejected records with reasons.
3. **Score:** Calculate relative risk signals and assign risk bands.
4. **Prioritize:** Browse transactions, filter results, and inspect alerts.
5. **Review:** Authorized users change statuses using permitted transitions and mandatory notes.
6. **Audit:** Preserve review events and export supported datasets for further analysis.

## 🏗️ Technology Stack

| Component | Technology |
|---|---|
| Language | Python |
| API framework | FastAPI |
| Database | SQLite |
| Frontend | Browser-based HTML, CSS, and JavaScript |
| Data ingestion | CSV validation and sample loading |
| Authorization | API-key-based viewer, analyst, and admin roles |
| Audit integrity | SQLite triggers |
| Testing | Python unittest / pytest-compatible test suite |
| API documentation | FastAPI OpenAPI and Swagger UI |
| Deployment options | Local execution; Docker and CI configuration require the verification noted below |

## 🔒 Security & Responsible AI

Security and accountability are central to this project's design.

- **Human-in-the-loop:** Scores assist investigation rather than making final fraud determinations.
- **Role separation:** Viewer, analyst, and admin permissions support controlled access.
- **Review integrity:** Status transitions follow defined rules, and review notes are mandatory.
- **Concurrency protection:** Conflicting updates can be detected rather than silently overwriting newer decisions.
- **Auditability:** Audit history is designed to be append-only through SQLite triggers.
- **Safer exports:** CSV output includes formula-injection protection.
- **Input validation:** Invalid ingestion records are rejected with explanatory reasons.
- **Responsible interpretation:** Synthetic benchmarks must not be treated as production validation.

### Important deployment considerations

This repository is a demonstration project, not a production-certified financial monitoring platform.

Before using it with real transaction data, implement and independently verify production authentication, secure secret management, transport security, appropriate PII controls, retention policies, monitoring, database backups, access controls, and operational incident procedures.

An empty `MONITOR_API_KEYS` configuration disables authentication and makes every visitor an admin. **Use this setting only for local demonstrations.**

## 🚀 Quick Start

### Prerequisites

- Python 3.10 or a compatible version supported by the project's dependencies.
- Git.
- A terminal or command prompt.

### 1. Clone the repository

Replace the placeholder with your actual GitHub repository URL.

```bash
git clone https://github.com/YOUR-USERNAME/fraud-monitoring-dashboard.git
cd fraud-monitoring-dashboard
```

### 2. Create a virtual environment

**Windows PowerShell**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**Linux / macOS**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
python -m pip install --upgrade pip
pip install -r requirements-dev.txt
```

### 4. Run the tests

```bash
python -m pytest -q
```

The committed test report records 22 passing tests. The HTTP API tests were not executed in the original authoring sandbox, so verify the current test output in your environment and CI.

### 5. Start the dashboard

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8016
```

Open the following addresses in your browser:

| Resource | URL |
|---|---|
| Dashboard / application | http://127.0.0.1:8016 |
| Interactive API documentation | http://127.0.0.1:8016/docs |
| OpenAPI schema | http://127.0.0.1:8016/openapi.json |

Load the synthetic sample transactions to explore the workflow.

## 🔌 API Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/api/transactions` | Retrieve the transaction queue |
| `GET` | `/api/alerts` | Retrieve risk alerts |
| `GET` | `/api/stats` | Retrieve dashboard statistics |
| `GET` | `/api/export/*.csv` | Export supported CSV data |
| `POST` | `/api/ingest` | Ingest transaction data |
| `POST` | `/api/ingest/sample` | Load synthetic sample data |
| `POST` | `/api/transactions/{id}/status` | Request a transaction status change |

Consult `/docs` for the actual request schemas, parameters, and responses exposed by the running application.

## 🧪 Testing & Verification

The project includes tests for core ingestion, scoring, filtering, status transitions, audit integrity, and CSV export behavior.

The committed development report also records a randomized workflow check in which 3,000 operations matched an independent reference model.

| Verification item | Reported status |
|---|---|
| Core test suite | 22 tests passed |
| HTTP authorization tests | Written; not executed in the original authoring sandbox |
| Browser JavaScript | Syntax-checked; not fully browser-tested |
| Docker build | Not verified |
| Ruff linting | Not run |

Run the tests in your own environment before deployment. CI results should be used to confirm the current repository state.

## 🗺️ Project Roadmap

The following are possible future improvements, not claims of existing functionality.

- [ ] PostgreSQL support for production-oriented persistence.
- [ ] Single sign-on and stronger identity management.
- [ ] Model calibration and drift monitoring.
- [ ] Fairness evaluation across relevant populations.
- [ ] Notification integrations for high-risk alerts.
- [ ] Expanded browser end-to-end testing.
- [ ] Production deployment hardening and observability.
- [ ] Documented data-retention and privacy controls.

## 📚 Documentation

| Document | Description |
|---|---|
| [Architecture](docs/ARCHITECTURE.md) | Components and system design |
| [Evaluation](docs/EVALUATION.md) | Metrics, methodology, and caveats |
| [Model Card](docs/MODEL_CARD.md) | Intended use, limitations, and responsible adaptation |
| [Deployment](docs/DEPLOYMENT.md) | Deployment guidance |
| [Results](results/RESULTS.md) | Committed synthetic evaluation results |

## 📁 Repository Structure

```text
fraud-monitoring-dashboard/
├── app/                  # Application and API implementation
├── docs/
│   ├── ARCHITECTURE.md
│   ├── EVALUATION.md
│   ├── MODEL_CARD.md
│   └── DEPLOYMENT.md
├── results/
│   └── RESULTS.md
├── tests/                # Automated tests
├── requirements-dev.txt
├── LICENSE
├── .gitignore
└── README.md
```

*The tree above is a high-level illustration. Confirm exact paths against the repository before publishing.*

## 👨‍💻 About the Author

<div align="center">

  <h3>Rayyan Anwar</h3>

  **AI/ML Engineer | Researcher | Technology Manager | Software Developer**

  Building practical software at the intersection of artificial intelligence, engineering, risk analysis, and responsible technology.

  <p>
    <a href="https://github.com/rayyan-anwar>
      <img src="https://img.shields.io/badge/GitHub-181717?style=for-the-badge&logo=github&logoColor=white" alt="GitHub profile" />
    </a>
  </p>

</div>

For questions, suggestions, or potential improvements, open an issue in the repository.

## 📄 License

This project is licensed under the **MIT License**.

Copyright © Rayyan Anwar. See [`LICENSE`](LICENSE) for details.

---

<div align="center">

  <img src="https://capsule-render.vercel.app/api?type=waving&color=0:06B6D4,50:0F766E,100:0F172A&height=110&section=footer" width="100%" alt="Decorative animated footer" />

  **Built for transparent, auditable, human-supervised risk investigation.**

  <sub>Scores inform decisions. People remain accountable.</sub>

</div>
