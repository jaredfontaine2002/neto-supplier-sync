# Neto Supplier Sync v2 - Report (Neto Order matching)

Distributors in registry: **6** (Velocity Imports, Trailhead Distribution, CycleParts Direct, Harbour Imports, Parts Co, Summit Supply Co) - add one = one JSON entry, no code change.

- `04_velocity_N5001.txt` -> **AUTO_UPDATED** order N5001 (Velocity Imports) tracking 881900112233
- `05_trailhead_N5001.txt` -> **AUTO_UPDATED** order N5001 (Trailhead Distribution) tracking 37LMN555666701000931501
- `06_cycleparts_N5002.txt` -> **AUTO_UPDATED + ADD_LINE_REVIEW** order N5002 (CycleParts Direct) tracking 37LMN777888901000931501 - NEW PARTS NOT ON ORDER, human must add line: [{'sku': 'CHN-12SP-116', 'qty': 1}]

## N5001 after both distributor emails
- Inbound shipments attached: **2** (two distributors, accumulated, neither overwrote the other)
- Order status: **On Hold - Awaiting Parts** (unchanged - inbound tracking never dispatches a customer order)

## Neto answers this demo is built on
- Tracking: YES via UpdateOrder, per OrderLine (TrackingDetails) - but that native mode is for outbound/dispatch and can email the customer, so this tool uses Safe Inbound Mode (InternalOrderNotes + StickyNote + ItemNotes) instead.
- Ordered parts already on the order: YES, updated automatically via ItemNotes. Parts NOT on the order: flagged ADD_LINE_REVIEW - UpdateOrder can't create a priced line (Quantity/UnitPrice exist only on AddOrder, which makes a new order).
