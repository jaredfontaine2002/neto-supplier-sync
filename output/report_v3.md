# Neto Supplier Sync v3 - Distributor document formats (synthetic samples)

Source: two synthetic documents recreating real-world distributor formats - a shipped
tax invoice and a sales order confirmation. No real business data is used.

## 07_harbour_invoice_N6101.txt
- Distributor: **Harbour Imports** | Stage: **INVOICE_SHIPPED** | Neto order: **N6101**
- Invoice: H731204 | Supplier order no: None | Total inc GST: $31.9
- Parts: GEN-DAMP-01 x1 (Single-speed drivetrain damping module)
- Tracking: MISSING in source documents
- Deliver-to is the shop itself: **False**
- Outcome: **SHIPPED_RECORDED + TRACKING_MISSING** - Invoice + parts recorded, order marked 'supplier shipped'. Connote was blank in BOTH the supplier email and its invoice PDF, so a chase-up task is queued - no tracking number was invented.

## 08_velocity_confirmation_N6102.txt
- Distributor: **Velocity Imports** | Stage: **ORDER_CONFIRMATION** | Neto order: **N6102**
- Invoice: None | Supplier order no: VEL2048150 | Total inc GST: $41.8
- Parts: VIO-ORING-28 x1 (O-RING 28X1.8 - CHAINRING MOUNT (GEN 4)); VIO-LOCKRING-4 x1 (LOCKRING - E-BIKE DRIVE UNIT); FRT-AIR x1 (AIR FREIGHT SERVICE)
- Tracking: none yet - confirmation stage
- Deliver-to is the shop itself: **True**
- Outcome: **ORDER_RECORDED** - Ordered parts + supplier order no. recorded on the Neto order as a sticky/internal note. No tracking attempted - none exists yet. A later dispatch document will add it.

## What real-world document formats changed in the design
1. **PDF parsing is mandatory** - real email bodies are often a few lines; everything that matters is in the attached PDF.
2. **The N-number match works** - supplier PDFs carry the shop's Neto number as 'Order No:', so documents can be matched to orders reliably.
3. **Stage-aware, not one-shot** - an order confirmation (record the order) comes before any dispatch/tracking document.
4. **Missing tracking is a real case** - a supplier can ship with a blank connote in the email AND the invoice. Flag + chase, never invent.
5. **Deliver-to can be the customer** - on some invoices the 'Customer:' box is the shop and the 'Deliver to:' box is the end customer (a direct-to-customer delivery). Plain PDF text extraction can reorder two-column layouts and flip this pair - layout-aware extraction is required for this field.
