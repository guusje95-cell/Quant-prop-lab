#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
PYTHONPATH=src python3 -m qpl.reporting.report       # v1 report (regenerated; original preserved as research_report_v1_original.html)
PYTHONPATH=src python3 -m qpl.reporting.report_v3    # audit_v1_report.html + v3_research_report.html
