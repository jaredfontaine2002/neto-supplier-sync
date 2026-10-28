"""Match a parsed supplier email to Neto (mock) and build update payloads.

CRITICAL BUSINESS RULE — the thing that makes this demo credible:
Inbound supplier tracking (distributor -> shop) is NOT outbound customer
tracking (shop -> customer). This code updates the purchase order and
adds an internal note to the linked customer order. It NEVER marks the
customer order 'Dispatched' — that only happens when the shop ships it on.
"""
import copy

CARRIER_URLS = {
    "Australia Post": "https://auspost.com.au/mypost/track/details/{t}",
    "Toll": "https://www.mytoll.com/track?trackingNumber={t}",
    "Sendle": "https://track.sendle.com/tracking?ref={t}",
}
AUTO_POST_THRESHOLD = 0.80


def tracking_url(carrier, tracking):
    if not carrier or not tracking:
        return None
    for key, tmpl in CARRIER_URLS.items():
        if key.lower() in carrier.lower():
            return tmpl.format(t=tracking)
    return None


def build_neto_payloads(po, customer_order, parsed, new_status):
    """Payloads shaped like Neto (Maropost) API calls.

    Live mapping to confirm in the shop's Neto sandbox/account before go-live:
    GetOrder / UpdateOrder are documented Neto actions and orders carry
    OrderStatus + TrackingNumber. The purchase-order side and the exact
    field for a supplier invoice depend on how the shop uses Neto (PO module
    vs order notes), so the mock adapter isolates that in one place.
    """
    url = tracking_url(parsed.carrier, parsed.tracking_number)
    return [
        {
            "action": "UpdatePurchaseOrder (mock adapter)",
            "po_id": po["po_id"],
            "set": {
                "SupplierInvoice": parsed.invoice_number,
                "Carrier": parsed.carrier,
                "TrackingNumber": parsed.tracking_number,
                "TrackingURL": url,
                "DispatchDate": parsed.dispatch_date,
                "ETA": parsed.eta,
                "InvoiceTotal": parsed.invoice_total,
                "Status": new_status,
            },
        },
        {
            "action": "UpdateOrder",
            "order": {
                "OrderID": customer_order["order_id"],
                "OrderStatus": customer_order["status"],  # unchanged on purpose
                "InternalNote": (
                    f"Supplier part inbound on {po['po_id']}: "
                    f"{parsed.supplier} inv {parsed.invoice_number}, "
                    f"{parsed.carrier} {parsed.tracking_number}, ETA {parsed.eta}. "
                    f"Tracking: {url}"
                ),
            },
        },
    ]


def sync_one(store, parsed):
    """Returns (result_dict, payloads_or_None). Mutates a copy of store data via caller."""
    if parsed.confidence < AUTO_POST_THRESHOLD or not parsed.po_ref:
        return ({"outcome": "REVIEW_QUEUE",
                 "reason": f"confidence {parsed.confidence} / missing {parsed.missing}",
                 "po_ref": parsed.po_ref}, None)

    po = next((x for x in store["purchase_orders"] if x["po_id"] == parsed.po_ref), None)
    if not po:
        return ({"outcome": "REVIEW_QUEUE",
                 "reason": f"PO {parsed.po_ref} not found in Neto",
                 "po_ref": parsed.po_ref}, None)

    shipped_skus = {i["sku"] for i in parsed.shipped}
    for line in po["lines"]:
        match = next((i for i in parsed.shipped if i["sku"] == line["sku"]), None)
        if match:
            line["qty_shipped"] = match["qty"]

    new_status = "Partially Shipped" if parsed.backordered else "In Transit"
    po.update({
        "supplier_invoice": parsed.invoice_number,
        "carrier": parsed.carrier,
        "tracking_number": parsed.tracking_number,
        "tracking_url": tracking_url(parsed.carrier, parsed.tracking_number),
        "dispatch_date": parsed.dispatch_date,
        "eta": parsed.eta,
        "invoice_total": parsed.invoice_total,
        "status": new_status,
    })
    if parsed.backordered:
        po["notes"].append(f"Backordered: {parsed.backordered}")

    cust = next(x for x in store["customer_orders"]
                if x["order_id"] == po["linked_customer_order"])
    payloads = build_neto_payloads(po, cust, parsed, new_status)
    cust["internal_notes"].append(payloads[1]["order"]["InternalNote"])

    return ({"outcome": "AUTO_UPDATED", "po_ref": po["po_id"],
             "customer_order": cust["order_id"], "new_po_status": new_status,
             "tracking_number": parsed.tracking_number,
             "shipped_skus": sorted(shipped_skus),
             "backordered": parsed.backordered}, payloads)
