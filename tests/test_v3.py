import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from src.order_sync import load_registry
from src.document_formats import parse_document, outcome_for, STAGE_CONFIRMATION, STAGE_INVOICE_SHIPPED
ROOT = Path(__file__).parent.parent

def parse(name):
    return parse_document((ROOT / f"data/sample_docs/{name}").read_text(), load_registry())

def test_invoice_document_shipped_tracking_missing():
    p = parse("07_harbour_invoice_N6101.txt")
    assert p["distributor"] == "Harbour Imports"
    assert p["neto_order_id"] == "N6101"          # found in the PDF text, not the body
    assert p["invoice_number"] == "H731204"
    assert p["stage"] == STAGE_INVOICE_SHIPPED
    assert p["items"][0]["sku"] == "GEN-DAMP-01"
    assert p["invoice_total"] == 31.90
    assert p["tracking_missing"] is True          # Con# blank in email AND pdf
    # In this sample the Deliver-to block is the end customer, not the shop
    assert p["deliver_to_customer_address"] is True
    assert p["deliver_to_is_shop"] is False
    outcome, _ = outcome_for(p)
    assert "TRACKING_MISSING" in outcome

def test_confirmation_document_recorded_no_tracking():
    p = parse("08_velocity_confirmation_N6102.txt")
    assert p["distributor"] == "Velocity Imports"
    assert p["neto_order_id"] == "N6102"
    assert p["supplier_order_number"] == "VEL2048150"
    assert p["stage"] == STAGE_CONFIRMATION
    assert len(p["items"]) == 3                   # 2 parts + freight line
    assert {i["sku"] for i in p["items"]} == {"VIO-ORING-28", "VIO-LOCKRING-4", "FRT-AIR"}
    assert p["invoice_total"] == 41.80
    assert p["tracking_missing"] is False         # confirmation: no tracking expected yet
    assert p["deliver_to_is_shop"] is True        # Deliver-to is the shop's own address
    outcome, _ = outcome_for(p)
    assert outcome == "ORDER_RECORDED"

if __name__ == "__main__":
    test_invoice_document_shipped_tracking_missing()
    test_confirmation_document_recorded_no_tracking()
    print("2/2 v3 (document-format) tests passed")
