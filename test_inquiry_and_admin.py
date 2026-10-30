import sys
import asyncio
sys.path.insert(0, r"c:\Users\SANJEEV\Documents\GitHub\hotel_booking")

from fastapi.testclient import TestClient
from main import app
from database import db_manager
from booking_agent import booking_agent, STEP_COMPLETED

def test_routes():
    client = TestClient(app)

    # 1. Test GET /
    r = client.get("/")
    assert r.status_code == 200
    assert "Northstar Air Service" in r.text
    print("✅ GET / returns 200 with Northstar Air Service UI")

    # 2. Test GET /admin
    r = client.get("/admin")
    assert r.status_code == 200
    assert "Northstar Air Service - Control Panel" in r.text
    assert "Hotel & Inventory Control Panel" in r.text
    assert "AIR SERVICE" in r.text
    print("✅ GET /admin returns 200 with matching Northstar Air Service UI layout")

    # 3. Test APIs
    r = client.get("/api/locations")
    assert r.status_code == 200
    assert r.json()["success"] is True
    print(f"✅ GET /api/locations returned {len(r.json()['locations'])} locations")

    r = client.get("/api/hotels")
    assert r.status_code == 200
    assert r.json()["success"] is True
    print(f"✅ GET /api/hotels returned {len(r.json()['hotels'])} hotels")

    r = client.get("/api/rooms")
    assert r.status_code == 200
    assert r.json()["success"] is True
    print(f"✅ GET /api/rooms returned {len(r.json()['rooms'])} rooms")

async def test_specific_inquiries():
    sid = "test-checkin-hotel-session"
    booking_agent.reset_session(sid)

    # Create dummy reservation
    b_id = "BK-AC9EF9"
    db_manager.bookings_collection.delete_one({"booking_id": b_id})
    db_manager.create_booking({
        "booking_id": b_id,
        "session_id": sid,
        "location_id": "LOC-MAA",
        "location_city": "Chennai",
        "airport_code": "MAA",
        "hotel_id": "HTL-MAA-AIRPORT",
        "hotel_name": "Grand Azure Airport Palace & Spa",
        "hotel_address": "GST Road, Meenambakkam, Chennai (1.5 km to MAA Airport)",
        "guest_type": "company",
        "guest_name": "Alex Morgan",
        "company_name": "Acme Corp",
        "rooms_count": 2,
        "room_name": "Luxury Family & Team Villa",
        "room_id": "FAM-VLA",
        "checkin_date": "2026-10-29",
        "checkout_date": "2026-10-30",
        "total_nights": 1,
        "price_per_night": 220.0,
        "total_amount": 440.0,
        "airport_pickup": True,
        "airport_drop": True,
        "status": "confirmed"
    })

    session = booking_agent.get_or_create_session(sid)
    session["booking_id"] = b_id
    session["current_step"] = STEP_COMPLETED
    session["guest_name"] = "Alex Morgan"
    db_manager.save_session(sid, session)

    # Test the user's exact phrase:
    res = await booking_agent.process_user_message(sid, "when my checkin is there and which hotel")
    print("\n--- User Query: 'when my checkin is there and which hotel' ---")
    print("REPLY:\n" + res["reply"])
    
    assert "Grand Azure Airport Palace & Spa" in res["reply"]
    assert "2026-10-29" in res["reply"]
    assert "2026-10-30" in res["reply"]
    assert "BK-AC9EF9" in res["reply"]
    assert "Your reservation (BK-AC9EF9) is confirmed. You can ask me" not in res["reply"]
    assert res.get("booking") is not None
    print("✅ Exact query correctly returned both hotel and check-in date with booking voucher!")

    # Test 'which hotel'
    res_hotel = await booking_agent.process_user_message(sid, "which hotel")
    assert "Grand Azure Airport Palace & Spa" in res_hotel["reply"]
    assert "GST Road" in res_hotel["reply"]
    print("✅ 'which hotel' returned property name and address")

    # Test 'when is my checkin'
    res_cin = await booking_agent.process_user_message(sid, "when is my checkin")
    assert "2026-10-29" in res_cin["reply"]
    assert "2:00 PM" in res_cin["reply"]
    print("✅ 'when is my checkin' returned check-in date and standard 2:00 PM time")

    # Test 'is pickup included'
    res_veh = await booking_agent.process_user_message(sid, "is pickup included")
    assert "Pick-up" in res_veh["reply"]
    assert "Confirmed" in res_veh["reply"]
    print("✅ 'is pickup included' returned pickup/drop chauffeur status")

    # Clean up
    db_manager.bookings_collection.delete_one({"booking_id": b_id})
    db_manager.sessions_collection.delete_one({"session_id": sid})
    print("\n🎉 ALL TESTS AND VALIDATIONS PASSED 100%!")

if __name__ == "__main__":
    test_routes()
    asyncio.run(test_specific_inquiries())
