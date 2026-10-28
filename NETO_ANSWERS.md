# Two Neto questions — answered from Maropost's official API docs

Sources (official):
- UpdateOrder: https://developers.maropost.com/documentation/engineers/api-documentation/orders-invoices/updateorder
- AddOrder: https://developers.maropost.com/documentation/engineers/api-documentation/orders-invoices/addorder

## 1. "Is there a way in Neto to add tracking to a Neto Order?"

**Yes — natively, per order line, via `UpdateOrder`.**

The docs' own first example is literally titled *"Mark an order as
dispatched and add shipping tracking details"*:

```json
{ "Order": {
    "OrderID": "N1000",
    "OrderStatus": "Dispatched",
    "SendOrderEmail": "tracking",
    "OrderLine": [{ "SKU": "ABC-123",
      "TrackingDetails": {
        "ShippingMethod": "Australia Post eParcel",
        "TrackingNumber": "C123345767765",
        "DateShipped": "2014-01-03 02:40:10" }}]
}}
```

Two catches that decide the whole design:
- Tracking lives on the **OrderLine** (by SKU), not just the order —
  different lines can carry different tracking.
- The `ShippingMethod` **must match an existing shipping service**
  already set up in Neto.
- ⚠️ This mode is built for **outbound** (you → customer). Using it for
  a distributor's inbound shipment, as-is, would set the order to
  *Dispatched* and can send the customer a tracking email with the
  *supplier's* tracking number. Wrong and embarrassing.

**The solution — Safe Inbound Mode (the v2 demo):** same `UpdateOrder`
call to the same OrderID, but it writes `InternalOrderNotes` + a
`StickyNote` ("Inbound: Velocity Imports INV-…, carrier tracking…,
ETA …") + `ItemNotes` on the matched lines. No `OrderStatus`, no
`SendOrderEmail`. Staff see everything on the order; the customer sees
nothing until the shop actually ships/completes the job. If a
distributor ever drop-ships straight to the customer, *then* the
official outbound mode is correct — the demo includes that payload
builder too, kept separate on purpose.

## 2. "…and add the ordered parts to that Neto Order?"

**If the part is already a line on the order: yes, automatically.**
`UpdateOrder` can set that line's `ItemNotes`, `QuantityShipped` and
`TrackingDetails` — so the ordered part gets stamped with supplier,
invoice, tracking and ETA.

**If the part is NOT already a line on the order: not via the API, on
the documented fields.** `UpdateOrder`'s OrderLine has **no Quantity
and no UnitPrice** — those fields exist only on `AddOrder`, and
`AddOrder` creates a *new* order. Maropost community admins say the
same thing in plain English: order line items are "very limited" via
UpdateOrder.

So the tool's rule:
- Part on order → auto-updated. ✅
- Part not on order → recorded in the note **and flagged
  `ADD_LINE_REVIEW`**. A human adds the billable line in the Neto UI
  (lines can be adjusted while an order is unapproved / on hold), or
  the account is sandbox-tested for whether it accepts a new SKU line
  via UpdateOrder — a test, not a promise.

## 3. Matching: "our number N5001"

Exactly how v2 works:
1. Distributor identified from the registry (the demo ships with
   fictional distributors — Velocity Imports, Trailhead Distribution,
   CycleParts Direct, Harbour Imports, Parts Co, Summit Supply Co —
   each new one is one JSON entry). The registry-pattern approach works
   because each distributor sends from consistent addresses with
   consistent reference labels.
2. The Neto number is extracted from whatever label that distributor
   uses ("Your Ref: N5001", "Neto Order: N5001", "Order Number:
   N5001"…), with a bare `N####` fallback.
3. Multiple distributors can feed the **same** order — in the demo,
   N5001 receives shipments from two different distributors and both
   are accumulated on the order, neither overwrites the other.

## What a live deployment still needs from real life

- 2–3 real dispatch emails per distributor — every distributor formats
  references differently, and their exact wording/domains should not
  be guessed.
- Confirmation of how the shop quotes the N-number to the distributor
  when ordering (is it in the PO email subject/body?). The match is
  only as reliable as that habit — if the number isn't sent, it isn't
  in the reply, and the email lands in the review queue by design.
