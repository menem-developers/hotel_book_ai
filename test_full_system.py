import asyncio
import sys
import json
from datetime import datetime, timedelta

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from database import db_manager
from booking_agent import booking_agent
import main

async def run_full_test():
    print("=" * 60)
    print("STARTING COMPREHENSIVE END-TO-END TEST")
    print("=" * 60)

    # 1. Database seed check
    counts = db_manager.seed_database(force=True)
    print(f"MongoDB Collections: {counts}")
    assert counts["locations"] >= 4, "Expected at least 4 locations"
    assert counts["hotels"] >= 4, "Expected at least 4 hotels"
    assert counts["rooms"] >= 20, "Expected at least 20 rooms across hotels"
    print("PASS: MongoDB Seeded Successfully")

    # 2. Conversational Booking Flow
    session_id = f"test-sess-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    print(f"\n--- Starting Chat Session: {session_id} ---")

    # Turn 1: User arrives from airport, provides destination
    res = await booking_agent.process_user_message(session_id, "I am arriving at Dubai airport DXB")
    print("\n[User]: I am arriving at Dubai airport DXB")
    print(f"[AI Step: {res['current_step']}]:\n{res['reply'][:180]}...")
    assert "Grand Azure Airport Resort & Spa" in res["reply"], "Expected hotel list in Dubai"

    # Turn 2: User selects hotel
    res = await booking_agent.process_user_message(session_id, "Grand Azure Airport Resort")
    print("\n[User]: Grand Azure Airport Resort")
    print(f"[AI Step: {res['current_step']}]:\n{res['reply']}")
    assert "individual" in res["reply"].lower() or "company" in res["reply"].lower()

    # Turn 3: User says booking for company
    res = await booking_agent.process_user_message(session_id, "I am booking for my company")
    print("\n[User]: I am booking for my company")
    print(f"[AI Step: {res['current_step']}]:\n{res['reply']}")
    assert "company" in res["reply"].lower() or "organization" in res["reply"].lower()

    # Turn 4: User gives company name
    res = await booking_agent.process_user_message(session_id, "it's Menem Tech Corp")
    print("\n[User]: it's Menem Tech Corp")
    print(f"[AI Step: {res['current_step']}]:\n{res['reply']}")
    assert "Menem Tech Corp" in res["reply"]
    assert "guests" in res["reply"].lower() or "members" in res["reply"].lower()

    # Turn 5: User gives member count
    res = await booking_agent.process_user_message(session_id, "4 members")
    print("\n[User]: 4 members")
    print(f"[AI Step: {res['current_step']}]:\n{res['reply']}")
    assert "rooms" in res["reply"].lower()

    # Turn 6: User gives rooms count
    res = await booking_agent.process_user_message(session_id, "we need 2 rooms")
    print("\n[User]: we need 2 rooms")
    print(f"[AI Step: {res['current_step']}]:\n{res['reply'][:180]}...")
    assert "Deluxe Single" in res["reply"] or "Executive Double" in res["reply"]

    # Turn 7: User picks room category
    res = await booking_agent.process_user_message(session_id, "Executive Double")
    print("\n[User]: Executive Double")
    print(f"[AI Step: {res['current_step']}]:\n{res['reply']}")
    assert "date" in res["reply"].lower() or "checking in" in res["reply"].lower()

    # Turn 8: User provides checkin date
    res = await booking_agent.process_user_message(session_id, "coming thursday")
    print("\n[User]: coming thursday")
    print(f"[AI Step: {res['current_step']}]:\n{res['reply']}")
    assert "check-out" in res["reply"].lower() or "nights" in res["reply"].lower()
    checkin_saved = res["state"]["checkin_date"]
    print(f"Saved Checkin Date: {checkin_saved}")

    # Turn 9: User provides stay duration (checkout date)
    res = await booking_agent.process_user_message(session_id, "2 nights")
    print("\n[User]: 2 nights")
    print(f"[AI Step: {res['current_step']}]:\n{res['reply']}")
    assert "transportation" in res["reply"].lower() or "vehicle" in res["reply"].lower()
    checkout_saved = res["state"]["checkout_date"]
    print(f"Saved Checkout Date: {checkout_saved} (Total Nights: {res['state']['total_nights']})")

    # Turn 10: Airport vehicle selection -> User requests "both"
    res = await booking_agent.process_user_message(session_id, "both pick and drop")
    print("\n[User]: both pick and drop")
    print(f"[AI Step: {res['current_step']}]:\n{res['reply']}")
    assert res["state"]["airport_pickup"] is True, "Expected airport_pickup to be True"
    assert res["state"]["airport_drop"] is True, "Expected airport_drop to be True"
    print("PASS: airport_pickup = True, airport_drop = True")

    # Turn 11: Contact info
    res = await booking_agent.process_user_message(session_id, "menem.executive@example.com")
    print("\n[User]: menem.executive@example.com")
    print(f"[AI Step: {res['current_step']}]:\n{res['reply']}")
    assert "Booking Summary" in res["reply"]
    assert "Menem Tech Corp" in res["reply"]
    assert "Executive Double Room" in res["reply"]
    assert "Airport Pick-up" in res["reply"] and "Yes" in res["reply"]
    assert "Airport Drop-off" in res["reply"] and "Yes" in res["reply"]
    print("PASS: Summary includes destination, hotel, and airport transfer")

    # Turn 12: Confirmation
    res = await booking_agent.process_user_message(session_id, "yes confirm booking")
    print("\n[User]: yes confirm booking")
    print(f"[AI Step: {res['current_step']}]:\n{res['reply']}")
    assert res["booking"] is not None, "Expected booking object returned"
    booking_id = res["booking"]["booking_id"]
    print(f"PASS: Booking created with ID: {booking_id}")

    # 3. Test Booking Inquiry by AI: "what is my booking details?"
    print("\n--- Testing Booking Inquiry by AI ---")
    inquiry_res = await booking_agent.process_user_message(session_id, "what is my booking details?")
    print(f"[User]: what is my booking details?")
    print(f"[AI Reply]:\n{inquiry_res['reply']}")
    assert booking_id in inquiry_res["reply"], f"Expected {booking_id} in inquiry response"
    assert "Menem Tech Corp" in inquiry_res["reply"]
    assert "Executive Double Room" in inquiry_res["reply"]
    print("PASS: AI correctly answered booking details from MongoDB")

    # 4. Test Inquiring with explicit reference code
    inquiry_ref = await booking_agent.process_user_message(session_id, f"Can you check status of {booking_id}?")
    print(f"\n[User]: Can you check status of {booking_id}?")
    print(f"[AI Reply]:\n{inquiry_ref['reply']}")
    assert booking_id in inquiry_ref["reply"]
    print("PASS: AI answered query by exact booking reference")

    # 5. Test Date-Specific Room Availability Conflict & Rejection
    print("\n--- Testing Date Availability & Zero Inventory Check ---")
    hotel_id = res["booking"]["hotel_id"]
    room_id = res["booking"]["room_id"]

    # Temporarily set total_rooms to 0 to test 0 inventory rejection
    try:
        db_manager.rooms_collection.update_one(
            {"hotel_id": hotel_id, "room_id": room_id},
            {"$set": {"total_rooms": 0}}
        )
        is_avail, rem_count, msg = db_manager.check_room_availability_for_dates(
            hotel_id, room_id, checkin_saved, checkout_saved, requested_count=1
        )
        print(f"Availability with 0 total_rooms: is_avail={is_avail}, remaining={rem_count}, msg={msg}")
        assert is_avail is False, "Expected unavailable when total_rooms is 0"
        assert rem_count == 0

        # Test conversational rejection when user tries to book sold out room on those dates
        sess2 = f"test-sess-conflict-{datetime.utcnow().strftime('%H%M%S')}"
        t1 = await booking_agent.process_user_message(sess2, "Dubai")
        t2 = await booking_agent.process_user_message(sess2, "Grand Azure Airport Resort")
        t3 = await booking_agent.process_user_message(sess2, "individual")
        t4 = await booking_agent.process_user_message(sess2, "Alice")
        t5 = await booking_agent.process_user_message(sess2, "2 guests")
        t6 = await booking_agent.process_user_message(sess2, "1 room")
        t7 = await booking_agent.process_user_message(sess2, "Executive Double")
        t8 = await booking_agent.process_user_message(sess2, checkin_saved)
        res_conflict = await booking_agent.process_user_message(sess2, "2 nights")
        print(f"Sess2 Steps: t1={t1['current_step']}, t2={t2['current_step']}, t3={t3['current_step']}, t4={t4['current_step']}, t5={t5['current_step']}, t6={t6['current_step']}, t7={t7['current_step']}, t8={t8['current_step']}, conflict={res_conflict['current_step']}")
        print(f"\n[Conflict Response]:\n{res_conflict['reply'][:250]}...")
        assert "fully booked" in res_conflict["reply"].lower() or "0 rooms available" in res_conflict["reply"].lower()
        print("PASS: Conversational agent successfully detected 0 room availability on dates and alerted user!")
    finally:
        # Restore room count back to 20
        db_manager.rooms_collection.update_one(
            {"hotel_id": hotel_id, "room_id": room_id},
            {"$set": {"total_rooms": 20, "available_rooms": 20}}
        )

    # 6. Test Control Panel Endpoints
    print("\n--- Testing Control Panel Endpoints ---")
    stats = await main.get_admin_stats()
    print("Stats API:", stats["stats"])
    assert stats["stats"]["bookings_count"] >= 1
    assert stats["stats"]["airport_pickups"] >= 1
    assert stats["stats"]["airport_drops"] >= 1
    print("PASS: Stats API returned accurate counts")

    # Add a custom test location via Control Panel API
    new_loc = main.LocationModel(
        location_id="LOC-TEST",
        city="Tokyo",
        airport_name="Haneda International Airport",
        airport_code="HND",
        country="Japan"
    )
    add_loc_res = await main.add_location(new_loc)
    print("Add Location API:", add_loc_res)
    assert add_loc_res["success"] is True

    # Add a custom test hotel
    new_hotel = main.HotelModel(
        hotel_id="HTL-HND-TEST",
        location_id="LOC-TEST",
        name="Grand Azure Tokyo Bay Suites",
        address="1-1 Haneda Airport Expressway",
        rating=4.9,
        description="Luxury suites overlooking Tokyo Bay."
    )
    add_hotel_res = await main.add_hotel(new_hotel)
    print("Add Hotel API:", add_hotel_res)
    assert add_hotel_res["success"] is True

    # Adjust room count via Control Panel API
    count_req = main.RoomCountUpdateRequest(
        room_id="DLX-SGL",
        new_count=25,
        hotel_id="HTL-HND-TEST"
    )
    count_res = await main.update_room_count(count_req)
    print("Update Room Count API:", count_res)
    assert count_res["success"] is True

    # Verify Availability Check API
    avail_req = main.AvailabilityCheckRequest(
        hotel_id="HTL-HND-TEST",
        room_id="DLX-SGL",
        checkin_date="2026-12-01",
        checkout_date="2026-12-05",
        requested_count=2
    )
    avail_res = await main.check_availability_endpoint(avail_req)
    print("Check Availability API:", avail_res)
    assert avail_res["success"] is True
    assert avail_res["is_available"] is True
    assert avail_res["remaining_rooms"] >= 25

    # Test Delete Booking API
    del_res = await main.delete_booking_endpoint(booking_id)
    print("Delete Booking API:", del_res)
    assert del_res["success"] is True
    # Verify booking is gone
    check_deleted = db_manager.get_booking_by_id(booking_id)
    assert check_deleted is None, "Expected booking to be deleted from MongoDB"
    print(f"PASS: Booking {booking_id} successfully deleted from MongoDB via Delete button API")

    # Cleanup test records
    await main.delete_location("LOC-TEST")
    print("Cleaned up test location and cascade entities")

    print("\n" + "=" * 60)
    print("ALL TESTS PASSED WITH 100% SUCCESS!")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(run_full_test())
