"""
Extract n8n execution data into a CSV for anomaly-detection experiments.

Uses the n8n Public API (GET /api/v1/executions, header X-N8N-API-KEY,
cursor pagination, max 250 per page). Standard library only.

Usage:
    export N8N_API_KEY="your-key"          # Settings -> n8n API -> Create API key
    python extract_n8n_executions.py --base-url http://localhost:5678 \
        --workflow-id <ID> --out executions.csv

Output: one row per execution with run-level features, per-node durations,
and the ground-truth label written by the "Choose Scenario" node.
"""
import argparse
import csv
import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()

LABEL_NODE = "Choose Scenario"  # node that outputs {"scenario": ...}


def fetch_executions(base_url, api_key, workflow_id=None, status=None, max_pages=1000):
    """Yield executions (with full data) page by page."""
    cursor = None
    for _ in range(max_pages):
        params = {"includeData": "true", "limit": "250"}
        if workflow_id:
            params["workflowId"] = workflow_id
        if status:
            params["status"] = status
        if cursor:
            params["cursor"] = cursor
        url = f"{base_url.rstrip('/')}/api/v1/executions?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(url, headers={"X-N8N-API-KEY": api_key, "Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            page = json.load(resp)
        for ex in page.get("data", []):
            yield ex
        cursor = page.get("nextCursor")
        if not cursor:
            return


def parse_ts(value):
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def first_json(task):
    """First output item's json of a node run, if any."""
    try:
        return task["data"]["main"][0][0]["json"]
    except (KeyError, IndexError, TypeError):
        return None


def flatten(ex):
    started, stopped = parse_ts(ex.get("startedAt")), parse_ts(ex.get("stoppedAt"))
    result = (ex.get("data") or {}).get("resultData") or {}
    run_data = result.get("runData") or {}
    run_error = result.get("error") or {}

    row = {
        "execution_id": ex.get("id"),
        "workflow_id": ex.get("workflowId"),
        "mode": ex.get("mode"),
        "status": ex.get("status"),
        "finished": ex.get("finished"),
        "retry_of": ex.get("retryOf"),
        "started_at": ex.get("startedAt"),
        "stopped_at": ex.get("stoppedAt"),
        "duration_s": round((stopped - started).total_seconds(), 3) if started and stopped else None,
        "hour_of_day": started.hour if started else None,
        "weekday": started.weekday() if started else None,
        "last_node": result.get("lastNodeExecuted"),
        "nodes_executed": len(run_data),
        "has_error": bool(run_error),
        "error_message": run_error.get("message"),
        "error_node": (run_error.get("node") or {}).get("name") if isinstance(run_error.get("node"), dict) else None,
        "items_out_total": 0,
        "scenario": None,
        "is_anomaly": None,
    }

    for node_name, tasks in run_data.items():
        key = node_name.lower().replace(" ", "_")
        row[f"node_{key}_ms"] = sum((t.get("executionTime") or 0) for t in tasks)
        row[f"node_{key}_runs"] = len(tasks)
        for t in tasks:
            try:
                row["items_out_total"] += sum(len(branch or []) for branch in t["data"]["main"])
            except (KeyError, TypeError):
                pass
            if t.get("error") and not row["error_node"]:
                row["error_node"] = node_name

    label_tasks = run_data.get(LABEL_NODE) or []
    label = first_json(label_tasks[0]) if label_tasks else None
    if label:
        row["scenario"] = label.get("scenario")
        row["is_anomaly"] = int(label.get("scenario") != "normal")

    # Some n8n versions omit "status" in API results; derive it as a fallback.
    if not row["status"]:
        row["status"] = "error" if row["has_error"] else ("success" if row["finished"] else "unknown")
    return row


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base-url", default="http://localhost:5678")
    ap.add_argument("--api-key", default=os.environ.get("N8N_API_KEY"))
    ap.add_argument("--workflow-id")
    ap.add_argument("--status", choices=["canceled", "error", "running", "success", "waiting"])
    ap.add_argument("--out", default="executions.csv")
    ap.add_argument("--from-json", help="Read a saved API response (for offline testing) instead of calling n8n")
    args = ap.parse_args()

    if args.from_json:
        with open(args.from_json) as f:
            executions = json.load(f).get("data", [])
    else:
        if not args.api_key:
            sys.exit("Missing API key: set N8N_API_KEY or pass --api-key")
        executions = fetch_executions(args.base_url, args.api_key, args.workflow_id, args.status)

    rows = [flatten(ex) for ex in executions]
    if not rows:
        sys.exit("No executions found.")

    columns = list(dict.fromkeys(k for r in rows for k in r))  # union, first-seen order
    with open(args.out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=columns)
        w.writeheader()
        w.writerows(rows)

    labelled = sum(r["is_anomaly"] is not None for r in rows)
    anomalies = sum(r["is_anomaly"] == 1 for r in rows)
    print(f"Wrote {len(rows)} executions to {args.out} ({labelled} labelled, {anomalies} injected anomalies)")


if __name__ == "__main__":
    main()
