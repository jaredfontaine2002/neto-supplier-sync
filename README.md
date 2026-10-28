# Neto Supplier Sync

A Python tool that closes the gap between supplier emails and a
[Neto (Maropost)](https://www.maropost.com/) store: it reads supplier
invoice and dispatch emails — including the text of their PDF
attachments — extracts the invoice number, ordered parts and tracking
details, matches them to the right Neto order using the shop's own
order number (the `N####` reference printed on the supplier's
documents), and writes the result back onto that order as internal
notes. Staff can then answer *"where's that part?"* from the order
itself instead of searching inboxes.

Built for a bike shop ordering parts from many distributors, but the
pattern applies to any Neto store that buys from suppliers by email.
All data in this repository is **synthetic** — distributors, orders,
documents and prices are fictional, and nothing here connects to a
real store, inbox or API account.

Built in **Python** (stdlib only, no dependencies to install).

## The safety design (the important part)

Supplier tracking is *inbound* (distributor → shop); customer tracking
is *outbound* (shop → customer). Confusing the two is the classic way
to tell a customer their order has shipped when only a part has
shipped to the workshop. This tool is built around not doing that:

- **Safe Inbound Mode.** Updates are written as internal order notes,
  a sticky note, and per-line item notes via Neto's `UpdateOrder`.
  The payload deliberately omits `OrderStatus` and `SendOrderEmail`:
  an inbound supplier shipment **never marks a customer order
  Dispatched** and never emails the customer.
- **Confidence score + review queue.** Every parsed email is scored.
  Below the threshold — or missing a PO/order reference — nothing is
  posted; the email waits for a human. Automation that guesses is
  worse than no automation.
- **Parts are never invented.** If a shipped part is already a line on
  the Neto order, its line is updated. If it is *not* on the order, it
  is recorded in the note and flagged `ADD_LINE_REVIEW` — the API
  cannot create a priced line on an existing order, so a human adds
  it. (Research notes: [`NETO_ANSWERS.md`](NETO_ANSWERS.md).)
- **Tracking is never invented.** Documents are stage-aware: an order
  confirmation is recorded with no tracking (none exists yet), and a
  shipped invoice with a blank connote is flagged `TRACKING_MISSING`
  and queued for a chase-up.
- **Partial shipments stay honest.** Backordered SKUs and their ETAs
  are recorded separately, not buried.

## Architecture

```
src/parser.py            v1: supplier email -> structured data + confidence score
src/sync.py              v1: match PO in (mock) Neto, build payloads, guardrails
src/order_sync.py        v2: match by Neto order number N####; Safe Inbound
                         UpdateOrder payload builder (+ a separate outbound
                         payload builder for genuine drop-ship cases)
src/document_formats.py  v3: stage-aware parsing of distributor document
                         formats (confirmation vs shipped invoice,
                         tracking-missing and deliver-to detection)
data/distributors.json   supplier registry - one JSON entry per distributor,
                         no code change to add one
data/emails/             v1 synthetic supplier emails (full / partial / no PO)
data/emails_v2/          v2 synthetic dispatch emails referencing N#### orders
data/sample_docs/        v3 synthetic recreations of real-world distributor
                         documents (shipped invoice, order confirmation)
data/mock_neto*.json     mock Neto store state (before)
output/                  generated after-state, payloads and reports
tests/                   9 tests across the three versions
```

## Run the demo

No credentials, no network, no real data:

```bash
python3 tests/test_demo.py    # 3/3
python3 tests/test_v2.py      # 4/4
python3 tests/test_v3.py      # 2/2

python3 run_demo.py           # v1: emails -> PO sync, writes output/report.md
python3 run_demo_v2.py        # v2: emails -> Neto order sync (Safe Inbound Mode)
python3 run_demo_v3.py        # v3: document formats -> stage-aware outcomes
```

Then compare `data/mock_neto*.json` (before) with the files the runners
write into `output/` (after-state, the exact Neto-shaped payloads, and
plain-English reports).

## Going live (what a real deployment needs)

1. Written permission to (a) read a specific supplier-email inbox /
   forwarding rule and (b) use a Neto API key. Nothing real is
   connected in this demo.
2. Confirm in the store's Neto account how supplier orders are
   modelled (PO module vs order notes) and confirm the exact API
   fields — Neto documents `GetOrder` / `UpdateOrder`, `OrderStatus`
   and tracking on orders; the PO-side mapping is account-specific and
   is isolated in `src/sync.py:build_neto_payloads()` for that reason.
3. PDF text extraction in front of the parsers (in the real world the
   data lives in the attachment, not the email body), plus
   coordinate-aware extraction for two-column Customer / Deliver-to
   blocks (see `src/document_formats.py`).
4. Pilot on one supplier first, with a human reviewing every update
   in week one; auto-post only above the confidence threshold after
   that.

## License

MIT — see [`LICENSE`](LICENSE).
