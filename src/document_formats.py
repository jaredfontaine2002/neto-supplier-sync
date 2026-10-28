"""Stage-aware parsing of real-world distributor document formats.

The samples in data/sample_docs/ are SYNTHETIC recreations of two common
distributor document shapes (a shipped tax invoice and a sales order
confirmation), built to capture lessons that tidy invented emails miss:

1. The data is in the PDF ATTACHMENT, not the email body. Real bodies are
   often 3-4 lines. Any live version must extract PDF text first.
2. The shop's Neto order number IS on the supplier document, labelled
   'Order No:' — matching on it works.
3. There are STAGES. A sales order CONFIRMATION (received / processing)
   has no tracking yet. A shipped TAX INVOICE is a later stage. One
   parser, stage-aware outcomes.
4. Tracking can be MISSING even when shipped: a supplier can write
   'Shipping Connote -' and leave the connote blank on the invoice while
   saying 'shipped today'. Rule: record the shipment, flag
   TRACKING_MISSING, queue a chase-up — never invent a number.
5. DELIVER-TO CAN BE THE CUSTOMER: on some invoices the 'Customer:' box
   is the shop and the 'Deliver to:' box is the end customer — that
   looks like a drop-ship / direct-to-customer delivery, the one case
   where outbound tracking mode may apply.
   WARNING: plain PDF text extraction can reorder two-column layouts
   and pair labels with the wrong blocks. Customer / Deliver-to needs
   layout-aware (coordinate-based) extraction; header fields (order
   no., invoice no.) extract reliably as plain text.

The shop's locality marker below is how the demo decides whether a
Deliver-to block is the shop itself; in production this should come
from configuration, not a constant.
"""
import re

STAGE_CONFIRMATION = "ORDER_CONFIRMATION"
STAGE_INVOICE_SHIPPED = "INVOICE_SHIPPED"

SHOP_LOCALITY_MARKERS = ("Sampleton", "SAMPLETON")


def _one(pat, text, flags=re.I):
    m = re.search(pat, text, flags)
    return m.group(1).strip() if m else None


def classify_stage(text):
    if "SALES ORDER CONFIRMATION" in text.upper() or "being processed" in text:
        return STAGE_CONFIRMATION
    if "TAX INVOICE" in text.upper() or "Invoice" in text:
        return STAGE_INVOICE_SHIPPED
    return "UNKNOWN"


def parse_document(text, registry):
    from src.order_sync import identify_distributor, extract_neto_order_id
    stage = classify_stage(text)
    distributor = identify_distributor(text, registry)
    neto_id = extract_neto_order_id(text) or _one(r"Order No:?\s*(N\d{3,})", text)

    # Invoice / supplier order numbers, per common labels
    invoice = (_one(r"Invoice No:?\s*#?([A-Z]\d{5,})", text)
               or _one(r"Invoice #([A-Z]\d{5,})", text))
    supplier_order = (_one(r"Supplier (?:Sales )?Order No:?\s*([A-Z]{3}\d{5,})", text)
                      or _one(r"\b([A-Z]{3}\d{6,})\b", text))

    # Items — two common label shapes
    items = []
    for code, desc, qty in re.findall(
            r"CODE:\s*(\S+)\s+DESCRIPTION:\s*(.+?)\s+BARCODE:.*?QTY:\s*(\d+)", text, re.I | re.S):
        items.append({"sku": code, "description": desc.strip(), "qty": int(qty)})
    if not items:
        code = _one(r"Code:\s*(\S+)", text)
        desc = _one(r"Description:\s*(.+)", text)
        qty = _one(r"Qty:\s*(\d+)", text)
        if code:
            items.append({"sku": code, "description": desc, "qty": int(qty or 1)})

    total = (_one(r"TOTAL inc GST \$?([\d,]+\.\d{2})", text)
             or _one(r"TOTAL AMOUNT DUE:\s*([\d,]+\.\d{2})", text))
    connote = _one(r"Con#:\s*([A-Z0-9]{6,})", text)
    tracking_missing = (stage == STAGE_INVOICE_SHIPPED and not connote)
    # Deliver-to block: short window after the label (formats differ, and
    # long windows bleed into other blocks - see module docstring point 5).
    m = re.search(r"Deliver to:|DELIVER TO", text)
    window = text[m.start():m.start() + 120] if m else ""
    deliver_to_is_shop = any(marker in window for marker in SHOP_LOCALITY_MARKERS)
    deliver_to_customer = bool(m) and not deliver_to_is_shop

    return {
        "stage": stage,
        "distributor": distributor,
        "neto_order_id": neto_id,
        "invoice_number": invoice,
        "supplier_order_number": supplier_order,
        "items": items,
        "invoice_total": float(total.replace(",", "")) if total else None,
        "tracking_number": connote,
        "tracking_missing": tracking_missing,
        "deliver_to_is_shop": deliver_to_is_shop,
        "deliver_to_customer_address": deliver_to_customer,
    }


def outcome_for(parsed):
    """Stage-aware Neto update plan (Safe Inbound Mode throughout)."""
    if not parsed["neto_order_id"]:
        return "REVIEW_QUEUE", "No Neto N-number found in email or PDF."
    if parsed["stage"] == STAGE_CONFIRMATION:
        return "ORDER_RECORDED", ("Ordered parts + supplier order no. recorded on the Neto order "
                                  "as a sticky/internal note. No tracking attempted - none exists yet. "
                                  "A later dispatch document will add it.")
    if parsed["stage"] == STAGE_INVOICE_SHIPPED and parsed["tracking_missing"]:
        return "SHIPPED_RECORDED + TRACKING_MISSING", ("Invoice + parts recorded, order marked "
                                                       "'supplier shipped'. Connote was blank in BOTH the "
                                                       "supplier email and its invoice PDF, so a chase-up task "
                                                       "is queued - no tracking number was invented.")
    return "AUTO_UPDATED", "Invoice, parts and tracking recorded on the Neto order."
