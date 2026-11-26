# AI Workflow Anomaly Detection

Python prototype for detecting anomalous executions in AI/LLM-based workflows, developed as part of my Bachelor's thesis
**"Automated Anomaly Detection and Failure Analysis in AI-Based Workflows"** (B.Eng. Mechatronics, THWS).

> **Status:** work in progress (thesis period Nov 2026 – Jan 2027)

## Goal

AI workflows (e.g. LLM agents orchestrated with n8n) can fail silently: runs take unusually long, nodes error out, or outputs change unexpectedly.
This project investigates whether such abnormal executions can be detected automatically, and compares two approaches:

- **Rule-based detection**: thresholds and checks on execution status, duration and node behaviour
- **Machine learning**: unsupervised anomaly detection with Isolation Forest (scikit-learn)

## Repository structure

```
├── src/
│   └── extract_n8n_executions.py      # Collects execution data via the n8n Public API
├── n8n/
│   └── anomaly_generator_workflow.json # n8n workflow that produces normal and anomalous runs
├── notebooks/
│   └── 01_exploration.ipynb           # Data exploration and first rule-based detectors
├── data/
│   └── executions.csv                 # Execution data from my own self-hosted n8n instance
├── results/                           # Plots and metrics
└── requirements.txt
```

## Setup

1. Run n8n locally (e.g. with Docker) and import `n8n/anomaly_generator_workflow.json`.
2. Create an API key in n8n (*Settings → n8n API*) and set it as an environment variable:
   ```bash
   export N8N_API_KEY="your-key"        # Windows PowerShell: $env:N8N_API_KEY="your-key"
   ```
3. Install dependencies and extract execution data:
   ```bash
   pip install -r requirements.txt
   python src/extract_n8n_executions.py --help
   ```
4. Open `notebooks/01_exploration.ipynb` to explore the data and run the detectors.

## Tech stack

Python · pandas · NumPy · scikit-learn · Matplotlib · Jupyter · n8n · Docker

## Data

All data in this repository was generated with my own n8n workflows. It contains no company or customer data.

## Author

Mohammed Shaaz · [LinkedIn](https://linkedin.com/in/mohammedshaaz)
