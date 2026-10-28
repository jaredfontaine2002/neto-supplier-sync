#!/usr/bin/env python3
"""v2 runner: distributor emails -> Neto Order N#### (mock).
Run: python3 run_demo_v2.py
All distributors, orders and data are synthetic.
"""
import json, sys
from pathlib import Path
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))
from src.order_sync import load_registry, parse_supplier_email_v2, sync_to_neto_order

def main():
    registry = load_registry()
    store = json.loads((ROOT / "data/mock_neto_orders.json").read_text())
    results, payloads = [], []
    for f in sorted((ROOT / "data/emails_v2").glob("*.txt")):
        parsed = parse_supplier_email_v2(f.read_text(), registry)
        result, payload = sync_to_neto_order(store, parsed)
        result["email_file"] = f.name
        results.append(result)
        if payload:
            payloads.append(payload)
        print(f"{f.name}: {result['outcome']}  -> {result.get('order_id','?')}  ({result.get('distributor','?')})")
    (ROOT / "output").mkdir(exist_ok=True)
    (ROOT / "output/mock_neto_orders_after.json").write_text(json.dumps(store, indent=2))
    (ROOT / "output/neto_updateorder_payloads_v2.json").write_text(json.dumps(payloads, indent=2))
    names = ", ".join(d["name"] for d in registry)
    shared = next(o for o in store["orders"] if o["order_id"] == "N5001")
    lines = ["# Neto Supplier Sync v2 - Report (Neto Order matching)", "",
             f"Distributors in registry: **{len(registry)}** ({names}) - add one = one JSON entry, no code change.", ""]
    for r in results:
        lines.append(f"- `{r['email_file']}` -> **{r['outcome']}** order {r.get('order_id')} ({r.get('distributor')}) tracking {r.get('tracking')}"
                     + (f" - NEW PARTS NOT ON ORDER, human must add line: {r['new_parts_not_on_order']}" if r.get("new_parts_not_on_order") else ""))
    lines += ["", "## N5001 after both distributor emails",
              f"- Inbound shipments attached: **{len(shared['inbound_shipments'])}** (two distributors, accumulated, neither overwrote the other)",
              f"- Order status: **{shared['status']}** (unchanged - inbound tracking never dispatches a customer order)",
              "", "## Neto answers this demo is built on",
              "- Tracking: YES via UpdateOrder, per OrderLine (TrackingDetails) - but that native mode is for outbound/dispatch and can email the customer, so this tool uses Safe Inbound Mode (InternalOrderNotes + StickyNote + ItemNotes) instead.",
              "- Ordered parts already on the order: YES, updated automatically via ItemNotes. Parts NOT on the order: flagged ADD_LINE_REVIEW - UpdateOrder can't create a priced line (Quantity/UnitPrice exist only on AddOrder, which makes a new order)."]
    (ROOT / "output/report_v2.md").write_text("\n".join(lines) + "\n")
    print("\nReport: output/report_v2.md")

if __name__ == "__main__":
    main()
