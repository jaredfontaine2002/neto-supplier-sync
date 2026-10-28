"""v2: Distributor email -> Neto Order (N####), matched by order number.

Answers the two Neto questions with the official Maropost developer docs
(developers.maropost.com .../orders-invoices/updateorder + addorder):

1. TRACKING on an existing Neto Order?
   YES, natively — but at ORDER-LINE level, and designed for OUTBOUND:
       UpdateOrder { OrderID: "N5001", OrderStatus: "Dispatched",
                     SendOrderEmail: "tracking",
                     OrderLine: [{ SKU, TrackingDetails: {
                         ShippingMethod, TrackingNumber, DateShipped }}]}
   The doc's own example is 'Mark an order as dispatched and add
   shipping tracking details', and the ShippingMethod must match an
   existing shipping service in Neto.
   => For INBOUND distributor->shop tracking we must NOT use that mode:
   it would mark the customer's order Dispatched and can email the
   customer the supplier's tracking number. Safe mode (below) writes
   InternalOrderNotes + a StickyNote + per-line ItemNotes, leaves
   OrderStatus untouched, and sends no customer email.

2. ORDERED PARTS as lines on an existing Neto Order?
   PARTLY. UpdateOrder's OrderLine only carries a limited field set
   (SKU, ItemNotes, ItemDescription, ItemSerialNumber, QuantityShipped,
   TrackingDetails, warehouse refs) — no Quantity / UnitPrice. Those
   exist only on AddOrder, which creates a NEW order. Neto community
   admins confirm line items are 'very limited' via UpdateOrder.
   => If the part SKU is already a line on N####: we update that line's
   ItemNotes with the inbound detail (fully automatic).
      If it is NOT on the order: we do NOT invent a billable line via
   API. We record it in the sticky/internal note and flag
   ADD_LINE_REVIEW for a human (in the Neto UI, lines can be adjusted
   on an unapproved/on-hold order; whether UpdateOrder accepts a brand
   new SKU line on a given account is a sandbox test, not a promise).
"""
import json, re
from pathlib import Path

ROOT = Path(__file__).parent.parent


def load_registry():
    return json.loads((ROOT / "data/distributors.json").read_text())["distributors"]


def identify_distributor(text, registry):
    low = text.lower()
    for d in registry:
        if any(a in low for a in d["aliases"]) or any(s in low for s in d["sender_patterns"]):
            return d["name"]
    return None


def extract_neto_order_id(text, distributor_entry=None):
    # Labelled first (any distributor's ref labels), then any bare N#### token
    labels = ["Neto Order", "Your Ref", "Order Number", "Order Ref",
              "Purchase Order", "Customer Order", "Our Order"]
    for lab in labels:
        m = re.search(rf"{lab}:?\s*(N\d{{3,}})\b", text, re.I)
        if m:
            return m.group(1).upper()
    m = re.search(r"\b(N\d{3,})\b", text)
    return m.group(1).upper() if m else None


def _one(pat, text):
    m = re.search(pat, text, re.I)
    return m.group(1).strip() if m else None


def parse_supplier_email_v2(text, registry):
    dist_name = None
    entry = None
    low = text.lower()
    for d in registry:
        if any(a in low for a in d["aliases"]) or any(s in low for s in d["sender_patterns"]):
            dist_name, entry = d["name"], d
            break
    shipped = [{"sku": s, "qty": int(q)} for s, q in
               re.findall(r"SKU:\s*([A-Z0-9\-]+)\s+Qty:\s*(\d+)", text, re.I)]
    total = _one(r"Invoice Total:\s*\$?([\d,]+\.\d{2})", text)
    return {
        "distributor": dist_name,
        "neto_order_id": extract_neto_order_id(text, entry),
        "invoice_number": _one(r"Invoice Number:\s*([A-Z0-9\-]+)", text),
        "carrier": _one(r"Carrier:\s*(.+)", text),
        "tracking_number": _one(r"Tracking Number:\s*([A-Z0-9]+)", text),
        "dispatch_date": _one(r"Dispatch Date:\s*(\d{4}-\d{2}-\d{2})", text),
        "eta": _one(r"^ETA:\s*(\d{4}-\d{2}-\d{2})", text),
        "invoice_total": float(total.replace(",", "")) if total else None,
        "shipped": shipped,
    }


def build_safe_updateorder_payload(order, parsed):
    """SAFE INBOUND mode: notes only. No Dispatched, no customer email."""
    note = (f"[Inbound {parsed['distributor']}] Inv {parsed['invoice_number']} "
            f"(${parsed['invoice_total']}) | {parsed['carrier']} "
            f"{parsed['tracking_number']} | Dispatched {parsed['dispatch_date']} "
            f"| ETA {parsed['eta']} | Parts: "
            + ", ".join(f"{i['sku']} x{i['qty']}" for i in parsed["shipped"]))
    lines = []
    for item in parsed["shipped"]:
        if any(l["sku"] == item["sku"] for l in order["lines"]):
            lines.append({"SKU": item["sku"], "ItemNotes": note})
    return {
        "NETOAPI_ACTION": "UpdateOrder",
        "endpoint": "https://<yourstore>.neto.com.au/do/WS/NetoAPI",
        "Order": {
            "OrderID": order["order_id"],
            # OrderStatus deliberately NOT sent -> Neto leaves it unchanged
            # SendOrderEmail deliberately NOT sent -> customer gets nothing
            "InternalOrderNotes": note,
            "StickyNotes": {"StickyNote": [{
                "Title": f"Inbound: {parsed['distributor']} {parsed['invoice_number']}",
                "Description": note}]},
            "OrderLine": lines,
        },
    }


def build_outbound_tracking_payload(order_id, sku, shipping_method, tracking, date_shipped):
    """OUTBOUND / drop-ship mode — ONLY when the distributor ships straight
    to the customer. This is the doc's official example shape."""
    return {
        "NETOAPI_ACTION": "UpdateOrder",
        "endpoint": "https://<yourstore>.neto.com.au/do/WS/NetoAPI",
        "Order": {
            "OrderID": order_id,
            "OrderStatus": "Dispatched",
            "SendOrderEmail": "tracking",
            "OrderLine": [{"SKU": sku, "TrackingDetails": {
                "ShippingMethod": shipping_method,
                "TrackingNumber": tracking,
                "DateShipped": date_shipped}}],
        },
    }


def sync_to_neto_order(store, parsed):
    if not parsed["neto_order_id"] or not parsed["distributor"]:
        return {"outcome": "REVIEW_QUEUE",
                "reason": f"missing neto_order_id={parsed['neto_order_id']} distributor={parsed['distributor']}"}, None
    order = next((o for o in store["orders"] if o["order_id"] == parsed["neto_order_id"]), None)
    if not order:
        return {"outcome": "REVIEW_QUEUE",
                "reason": f"Neto order {parsed['neto_order_id']} not found"}, None

    payload = build_safe_updateorder_payload(order, parsed)
    existing = {l["sku"] for l in order["lines"]}
    matched = [i for i in parsed["shipped"] if i["sku"] in existing]
    new_parts = [i for i in parsed["shipped"] if i["sku"] not in existing]

    order["inbound_shipments"].append({
        "distributor": parsed["distributor"], "invoice": parsed["invoice_number"],
        "carrier": parsed["carrier"], "tracking": parsed["tracking_number"],
        "eta": parsed["eta"], "parts": parsed["shipped"]})
    order["internal_notes"].append(payload["Order"]["InternalOrderNotes"])
    for item in matched:
        line = next(l for l in order["lines"] if l["sku"] == item["sku"])
        line["item_notes"] = payload["Order"]["InternalOrderNotes"]
        line["inbound"] = {"distributor": parsed["distributor"],
                           "tracking": parsed["tracking_number"], "eta": parsed["eta"]}
    # status intentionally unchanged
    outcome = "AUTO_UPDATED + ADD_LINE_REVIEW" if new_parts else "AUTO_UPDATED"
    return {"outcome": outcome, "order_id": order["order_id"],
            "distributor": parsed["distributor"],
            "matched_parts": matched, "new_parts_not_on_order": new_parts,
            "tracking": parsed["tracking_number"],
            "order_status_after": order["status"]}, payload
