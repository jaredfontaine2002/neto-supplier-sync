"""Parse supplier dispatch / invoice emails into structured data.

Stdlib-only. Regex first (fast, auditable) — in production you'd add an
LLM fallback for messy formats, behind the same confidence score.
Every field found / missed affects `confidence`. Low confidence must
never auto-post to Neto.
"""
import re
from dataclasses import dataclass, field, asdict


@dataclass
class ParsedEmail:
    supplier: str | None = None
    po_ref: str | None = None
    invoice_number: str | None = None
    carrier: str | None = None
    tracking_number: str | None = None
    dispatch_date: str | None = None
    eta: str | None = None
    invoice_total: float | None = None
    shipped: list = field(default_factory=list)      # [{sku, qty}]
    backordered: list = field(default_factory=list)  # [{sku, qty, eta}]
    confidence: float = 0.0
    missing: list = field(default_factory=list)

    def to_dict(self):
        return asdict(self)


def _one(pattern, text, flags=re.IGNORECASE):
    m = re.search(pattern, text, flags)
    return m.group(1).strip() if m else None


def _items(section_text):
    out = []
    for sku, qty in re.findall(r"SKU:\s*([A-Z0-9\-]+)\s+Qty:\s*(\d+)", section_text, re.I):
        out.append({"sku": sku, "qty": int(qty)})
    return out


def parse_email(text: str) -> ParsedEmail:
    p = ParsedEmail()
    p.supplier = _one(r"Supplier:\s*(.+)", text)
    p.po_ref = _one(r"(?:Purchase Order|Your Ref):\s*([A-Z]{2}-PO-\d+)", text)
    p.invoice_number = _one(r"Invoice Number:\s*([A-Z0-9\-]+)", text)
    p.carrier = _one(r"Carrier:\s*(.+)", text)
    p.tracking_number = _one(r"Tracking Number:\s*([A-Z0-9]+)", text)
    p.dispatch_date = _one(r"Dispatch Date:\s*(\d{4}-\d{2}-\d{2})", text)
    p.eta = _one(r"^ETA:\s*(\d{4}-\d{2}-\d{2})", text, re.I | re.M)
    total = _one(r"Invoice Total:\s*\$?([\d,]+\.\d{2})", text)
    p.invoice_total = float(total.replace(",", "")) if total else None

    # Split shipped vs backorder sections
    parts = re.split(r"BACKORDER[^\n]*\n", text, flags=re.I)
    p.shipped = _items(parts[0])
    if len(parts) > 1:
        p.backordered = _items(parts[1])
        bo_eta = _one(r"Backorder ETA:\s*(\d{4}-\d{2}-\d{2})", parts[1])
        for item in p.backordered:
            item["eta"] = bo_eta

    # Confidence: PO + tracking are the keys that make automation safe
    score = 0.0
    for val, weight in [(p.po_ref, 0.4), (p.tracking_number, 0.25),
                        (p.invoice_number, 0.15), (p.supplier, 0.1),
                        (bool(p.shipped), 0.1)]:
        if val:
            score += weight
        else:
            pass
    p.confidence = round(score, 2)
    for name, val in [("po_ref", p.po_ref), ("tracking_number", p.tracking_number),
                      ("invoice_number", p.invoice_number), ("supplier", p.supplier)]:
        if not val:
            p.missing.append(name)
    return p
