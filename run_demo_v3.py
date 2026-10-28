#!/usr/bin/env python3
"""v3 runner: distributor-format documents (synthetic recreations of a
shipped invoice and an order confirmation) -> stage-aware Neto plan.
Run: python3 run_demo_v3.py
"""
import json, sys
from pathlib import Path
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))
from src.order_sync import load_registry
from src.document_formats import parse_document, outcome_for

def main():
    registry = load_registry()
    results = []
    for f in sorted((ROOT / "data/sample_docs").glob("*.txt")):
        parsed = parse_document(f.read_text(), registry)
        outcome, explanation = outcome_for(parsed)
        results.append({"file": f.name, **parsed, "outcome": outcome, "explanation": explanation})
        print(f"{f.name}: {outcome} -> {parsed['neto_order_id']} ({parsed['distributor']}, {parsed['stage']})")
    (ROOT / "output").mkdir(exist_ok=True)
    (ROOT / "output/sample_docs_result.json").write_text(json.dumps(results, indent=2))
    lines = ["# Neto Supplier Sync v3 - Distributor document formats (synthetic samples)", "",
             "Source: two synthetic documents recreating real-world distributor formats - a shipped", 
             "tax invoice and a sales order confirmation. No real business data is used.", ""]
    for r in results:
        lines += [f"## {r['file']}",
                  f"- Distributor: **{r['distributor']}** | Stage: **{r['stage']}** | Neto order: **{r['neto_order_id']}**",
                  f"- Invoice: {r['invoice_number']} | Supplier order no: {r['supplier_order_number']} | Total inc GST: ${r['invoice_total']}",
                  f"- Parts: " + "; ".join(f"{i['sku']} x{i['qty']} ({i['description']})" for i in r["items"]),
                  "- Tracking: " + (r["tracking_number"] or ("none yet - confirmation stage" if r["stage"] == "ORDER_CONFIRMATION" else "MISSING in source documents")),
                  f"- Deliver-to is the shop itself: **{r['deliver_to_is_shop']}**",
                  f"- Outcome: **{r['outcome']}** - {r['explanation']}", ""]
    lines += ["## What real-world document formats changed in the design",
              "1. **PDF parsing is mandatory** - real email bodies are often a few lines; everything that matters is in the attached PDF.",
              "2. **The N-number match works** - supplier PDFs carry the shop's Neto number as 'Order No:', so documents can be matched to orders reliably.",
              "3. **Stage-aware, not one-shot** - an order confirmation (record the order) comes before any dispatch/tracking document.",
              "4. **Missing tracking is a real case** - a supplier can ship with a blank connote in the email AND the invoice. Flag + chase, never invent.",
              "5. **Deliver-to can be the customer** - on some invoices the 'Customer:' box is the shop and the 'Deliver to:' box is the end customer (a direct-to-customer delivery). Plain PDF text extraction can reorder two-column layouts and flip this pair - layout-aware extraction is required for this field."]
    (ROOT / "output/report_v3.md").write_text("\n".join(lines) + "\n")
    print("\nReport: output/report_v3.md")

if __name__ == "__main__":
    main()
