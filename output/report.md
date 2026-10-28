# Neto Supplier Sync — Demo Report

Emails processed: **3** | Auto-updated in Neto (mock): **2** | Sent to human review queue: **1**

## What happened, email by email
- `01_partsco_full.txt` → **AUTO_UPDATED** (confidence 1.0) — PO EX-PO-1042 now 'In Transit', tracking 34XDK111222301000931501, linked customer order N9001 got an internal note (NOT marked dispatched)
- `02_velocity_partial.txt` → **AUTO_UPDATED** (confidence 1.0) — PO EX-PO-1043 now 'Partially Shipped', tracking 881900123401, linked customer order N9002 got an internal note (NOT marked dispatched)
- `03_missing_po.txt` → **REVIEW_QUEUE** (confidence 0.6) — confidence 0.6 / missing ['po_ref']

## Time saved (illustrative, at the manual rate in the code)
- Manual: ~6 min/email × 3 = ~18 min of searching + typing
- With this: auto ones take 0 min; only the review-queue one needs a human (~2 min to resolve the missing PO ref)

## Guardrails that fired
- Email with no PO reference → review queue, nothing posted. Automation that guesses is worse than no automation.
- Partial shipment → PO set to 'Partially Shipped', backordered SKU + its ETA recorded separately, not hidden.
- Inbound supplier tracking never marks a customer order Dispatched.

## Files
- `output/mock_neto_after.json` — Neto (mock) after the sync: compare with `data/mock_neto.json`
- `output/neto_payloads.json` — the exact Neto-shaped update payloads the live version would send
