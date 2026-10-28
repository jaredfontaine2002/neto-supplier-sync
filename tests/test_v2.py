import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from src.order_sync import (load_registry, parse_supplier_email_v2,
                            sync_to_neto_order, build_outbound_tracking_payload)
ROOT = Path(__file__).parent.parent

def load():
    return json.loads((ROOT / "data/mock_neto_orders.json").read_text())

def run(store, name):
    reg = load_registry()
    p = parse_supplier_email_v2((ROOT / f"data/emails_v2/{name}").read_text(), reg)
    return sync_to_neto_order(store, p)

def test_velocity_matches_N5001_by_number():
    store = load()
    r, payload = run(store, "04_velocity_N5001.txt")
    assert r["outcome"] == "AUTO_UPDATED" and r["order_id"] == "N5001"
    assert r["distributor"] == "Velocity Imports"
    # Safe mode: payload must NOT dispatch or email the customer
    assert "OrderStatus" not in payload["Order"]
    assert "SendOrderEmail" not in payload["Order"]
    assert payload["Order"]["OrderLine"][0]["SKU"] == "BRK-PAD-ORG"

def test_two_distributors_accumulate_on_same_order():
    store = load()
    run(store, "04_velocity_N5001.txt")
    r, _ = run(store, "05_trailhead_N5001.txt")
    assert r["distributor"] == "Trailhead Distribution"
    o = store["orders"][0]
    assert len(o["inbound_shipments"]) == 2
    assert o["status"] == "On Hold - Awaiting Parts"  # never dispatched

def test_new_part_flagged_not_invented():
    store = load()
    r, _ = run(store, "06_cycleparts_N5002.txt")
    assert "ADD_LINE_REVIEW" in r["outcome"]
    assert r["new_parts_not_on_order"][0]["sku"] == "CHN-12SP-116"
    o = next(x for x in store["orders"] if x["order_id"] == "N5002")
    assert len(o["lines"]) == 1  # no fake line was created

def test_outbound_payload_is_the_official_shape():
    p = build_outbound_tracking_payload("N5001", "SKU-1", "Australia Post eParcel", "ABC123", "2026-10-27 10:00:00")
    assert p["Order"]["OrderStatus"] == "Dispatched"
    assert p["Order"]["OrderLine"][0]["TrackingDetails"]["TrackingNumber"] == "ABC123"

if __name__ == "__main__":
    test_velocity_matches_N5001_by_number()
    test_two_distributors_accumulate_on_same_order()
    test_new_part_flagged_not_invented()
    test_outbound_payload_is_the_official_shape()
    print("4/4 v2 tests passed")
