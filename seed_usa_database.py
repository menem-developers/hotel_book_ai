import sys
import logging
from datetime import datetime

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("seed_usa")

from database import db_manager
from seed_usa_airports import USA_LOCATIONS, USA_HOTELS, USA_ROOMS_TEMPLATE

def seed_usa_data():
    logger.info("Connecting to MongoDB...")
    if not db_manager.is_connected:
        db_manager._connect()

    logger.info("Purging old locations, hotels, rooms, bookings, and chat sessions...")
    db_manager.locations_collection.delete_many({})
    db_manager.hotels_collection.delete_many({})
    db_manager.rooms_collection.delete_many({})
    db_manager.bookings_collection.delete_many({})
    db_manager.sessions_collection.delete_many({})

    logger.info("Inserting %d USA Airport Hubs...", len(USA_LOCATIONS))
    loc_docs = [dict(loc, created_at=datetime.utcnow(), updated_at=datetime.utcnow()) for loc in USA_LOCATIONS]
    db_manager.locations_collection.insert_many(loc_docs)

    logger.info("Inserting %d USA Luxury Hotels...", len(USA_HOTELS))
    hotel_docs = [dict(h, created_at=datetime.utcnow(), updated_at=datetime.utcnow()) for h in USA_HOTELS]
    db_manager.hotels_collection.insert_many(hotel_docs)

    logger.info("Seeding room categories across all USA hotels...")
    all_hotels = list(db_manager.hotels_collection.find({}, {"_id": 0}))
    room_docs = []
    for h in all_hotels:
        for r in USA_ROOMS_TEMPLATE:
            doc = dict(r)
            doc["hotel_id"] = h["hotel_id"]
            doc["hotel_name"] = h["name"]
            doc["location_id"] = h["location_id"]
            doc["available_rooms"] = doc["total_rooms"]
            doc["created_at"] = datetime.utcnow()
            doc["updated_at"] = datetime.utcnow()
            room_docs.append(doc)
    db_manager.rooms_collection.insert_many(room_docs)

    loc_count = db_manager.locations_collection.count_documents({})
    hotel_count = db_manager.hotels_collection.count_documents({})
    room_count = db_manager.rooms_collection.count_documents({})
    booking_count = db_manager.bookings_collection.count_documents({})

    logger.info("=" * 60)
    logger.info("USA DATA SEEDED SUCCESSFULLY!")
    logger.info(f"• USA Airport Locations: {loc_count}")
    logger.info(f"• USA Luxury Hotels:     {hotel_count}")
    logger.info(f"• USA Room Records:      {room_count}")
    logger.info(f"• Remaining Bookings:    {booking_count}")
    logger.info("=" * 60)

    return {
        "locations": loc_count,
        "hotels": hotel_count,
        "rooms": room_count,
        "bookings": booking_count
    }

if __name__ == "__main__":
    seed_usa_data()
