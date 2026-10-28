import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from src.parser import parse_email
from src.sync import sync_one

ROOT = Path(__file__).parent.parent

def load():
    return json.loads((ROOT / "data/mock_neto.json").read_text())

def test_full_dispatch_auto_updates():
    store = load()
    p = parse_email((ROOT / "data/emails/01_partsco_full.txt").read_text())
    r, payloads = sync_one(store, p)
    assert r["outcome"] == "AUTO_UPDATED"
    assert r["new_po_status"] == "In Transit"
    po = store["purchase_orders"][0]
    assert po["tracking_number"] == "34XDK111222301000931501"
    assert po["supplier_invoice"] == "INV-PC-884120"
    # inbound != outbound: customer order must NOT be dispatched
    assert store["customer_orders"][0]["status"] == "On Hold - Awaiting Part"
    assert payloads[1]["order"]["OrderStatus"] != "Dispatched"

def test_partial_shipment_records_backorder():
    store = load()
    p = parse_email((ROOT / "data/emails/02_velocity_partial.txt").read_text())
    r, _ = sync_one(store, p)
    assert r["outcome"] == "AUTO_UPDATED"
    assert r["new_po_status"] == "Partially Shipped"
    assert r["backordered"][0]["sku"] == "RTR-160-ICE"

def test_missing_po_goes_to_review():
    store = load()
    before = json.dumps(store)
    p = parse_email((ROOT / "data/emails/03_missing_po.txt").read_text())
    r, payloads = sync_one(store, p)
    assert r["outcome"] == "REVIEW_QUEUE"
    assert payloads is None
    assert json.dumps(store) == before  # nothing mutated

if __name__ == "__main__":
    test_full_dispatch_auto_updates()
    test_partial_shipment_records_backorder()
    test_missing_po_goes_to_review()
    print("3/3 tests passed")
