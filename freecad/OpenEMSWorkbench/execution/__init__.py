"""Execution package."""

try:
	from validation import run_preflight, summarize_findings
except ImportError:
	from OpenEMSWorkbench.validation import run_preflight, summarize_findings


def preflight_gate(analysis):
	findings = run_preflight(analysis)
	summary = summarize_findings(findings)
	return summary["ok"], findings, summary
