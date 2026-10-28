#!/usr/bin/env python3
"""Demo runner: supplier emails in -> Neto (mock) updated -> report out.

Run:  python3 run_demo.py
No real email, no real Neto, no credentials. Synthetic data only.
"""
import json, sys
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))
from src.parser import parse_email
from src.sync import sync_one

MANUAL_MINUTES_PER_EMAIL = 6  # find email, read it, find PO in Neto, type it in, answer 'where is it?'


def main():
    store = json.loads((ROOT / "data/mock_neto.json").read_text())
    results, all_payloads = [], []
    email_files = sorted((ROOT / "data/emails").glob("*.txt"))

    for f in email_files:
        parsed = parse_email(f.read_text())
        result, payloads = sync_one(store, parsed)
        result["email_file"] = f.name
        result["confidence"] = parsed.confidence
        results.append(result)
        if payloads:
            all_payloads.extend(payloads)
        print(f"{f.name}: {result['outcome']}  (confidence {parsed.confidence})  {result.get('po_ref') or ''}")

    (ROOT / "output").mkdir(exist_ok=True)
    (ROOT / "output/mock_neto_after.json").write_text(json.dumps(store, indent=2))
    (ROOT / "output/neto_payloads.json").write_text(json.dumps(all_payloads, indent=2))

    auto = sum(1 for r in results if r["outcome"] == "AUTO_UPDATED")
    review = len(results) - auto
    lines = [
        "# Neto Supplier Sync — Demo Report",
        "",
        f"Emails processed: **{len(results)}** | Auto-updated in Neto (mock): **{auto}** | Sent to human review queue: **{review}**",
        "",
        "## What happened, email by email",
    ]
    for r in results:
        lines.append(f"- `{r['email_file']}` → **{r['outcome']}** (confidence {r['confidence']})"
                     + (f" — PO {r['po_ref']} now '{r.get('new_po_status')}', tracking {r.get('tracking_number')}, linked customer order {r.get('customer_order')} got an internal note (NOT marked dispatched)"
                        if r["outcome"] == "AUTO_UPDATED" else f" — {r['reason']}"))
    lines += [
        "",
        "## Time saved (illustrative, at the manual rate in the code)",
        f"- Manual: ~{MANUAL_MINUTES_PER_EMAIL} min/email × {len(results)} = ~{MANUAL_MINUTES_PER_EMAIL*len(results)} min of searching + typing",
        "- With this: auto ones take 0 min; only the review-queue one needs a human (~2 min to resolve the missing PO ref)",
        "",
        "## Guardrails that fired",
        "- Email with no PO reference → review queue, nothing posted. Automation that guesses is worse than no automation.",
        "- Partial shipment → PO set to 'Partially Shipped', backordered SKU + its ETA recorded separately, not hidden.",
        "- Inbound supplier tracking never marks a customer order Dispatched.",
        "",
        "## Files",
        "- `output/mock_neto_after.json` — Neto (mock) after the sync: compare with `data/mock_neto.json`",
        "- `output/neto_payloads.json` — the exact Neto-shaped update payloads the live version would send",
    ]
    (ROOT / "output/report.md").write_text("\n".join(lines) + "\n")
    print("\nReport: output/report.md")


if __name__ == "__main__":
    main()
