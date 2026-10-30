from pymongo import MongoClient
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from config import settings
import logging
import uuid
import re

logger = logging.getLogger(__name__)

from seed_indian_airports import INDIAN_LOCATIONS, INDIAN_HOTELS, INDIAN_ROOMS_TEMPLATE

DEFAULT_LOCATIONS = INDIAN_LOCATIONS
DEFAULT_HOTELS = INDIAN_HOTELS
DEFAULT_ROOMS_TEMPLATE = INDIAN_ROOMS_TEMPLATE

class DatabaseManager:
    def __init__(self):
        self.client: Optional[MongoClient] = None
        self.db = None
        self._connect()

    def _connect(self):
        try:
            self.client = MongoClient(
                settings.MONGODB_URI,
                serverSelectionTimeoutMS=3000,
                connectTimeoutMS=3000
            )
            self.db = self.client[settings.MONGODB_DB_NAME]
            self.client.admin.command('ping')
            logger.info("Successfully connected to MongoDB (%s)", settings.MONGODB_DB_NAME)
        except Exception as e:
            logger.warning("MongoDB connection attempt warning: %s", e)

    @property
    def is_connected(self) -> bool:
        try:
            if self.client:
                self.client.admin.command('ping')
                return True
        except Exception:
            pass
        return False

    @property
    def locations_collection(self):
        return self.db["locations"]

    @property
    def hotels_collection(self):
        return self.db["hotels"]

    @property
    def rooms_collection(self):
        return self.db["rooms"]

    @property
    def sessions_collection(self):
        return self.db["chat_sessions"]

    @property
    def bookings_collection(self):
        return self.db["bookings"]

    def seed_database(self, force: bool = False) -> Dict[str, int]:
        """Seed default locations, hotels, and rooms into separate MongoDB collections."""
        if not self.is_connected:
            self._connect()

        # 1. Seed Locations
        loc_col = self.locations_collection
        if loc_col.count_documents({}) == 0 or force:
            if force:
                loc_col.delete_many({})
            loc_docs = [dict(loc, created_at=datetime.utcnow(), updated_at=datetime.utcnow()) for loc in DEFAULT_LOCATIONS]
            loc_col.insert_many(loc_docs)

        # 2. Seed Hotels
        hotel_col = self.hotels_collection
        if hotel_col.count_documents({}) == 0 or force:
            if force:
                hotel_col.delete_many({})
            hotel_docs = [dict(h, created_at=datetime.utcnow(), updated_at=datetime.utcnow()) for h in DEFAULT_HOTELS]
            hotel_col.insert_many(hotel_docs)

        # 3. Seed Rooms across Hotels
        room_col = self.rooms_collection
        if room_col.count_documents({}) == 0 or force:
            if force:
                room_col.delete_many({})
            all_hotels = list(hotel_col.find({}, {"_id": 0}))
            room_docs = []
            for h in all_hotels:
                for r in DEFAULT_ROOMS_TEMPLATE:
                    doc = dict(r)
                    doc["hotel_id"] = h["hotel_id"]
                    doc["hotel_name"] = h["name"]
                    doc["location_id"] = h["location_id"]
                    doc["available_rooms"] = doc["total_rooms"]
                    doc["created_at"] = datetime.utcnow()
                    doc["updated_at"] = datetime.utcnow()
                    room_docs.append(doc)
            room_col.insert_many(room_docs)

        return {
            "locations": loc_col.count_documents({}),
            "hotels": hotel_col.count_documents({}),
            "rooms": room_col.count_documents({})
        }

    # Backward compatibility helper
    def seed_rooms(self, force: bool = False) -> int:
        res = self.seed_database(force=force)
        return res["rooms"]

    # ==============================================================
    # LOCATIONS MANAGEMENT
    # ==============================================================
    def get_all_locations(self) -> List[Dict[str, Any]]:
        if not self.is_connected:
            self._connect()
        return list(self.locations_collection.find({}, {"_id": 0}))

    def get_location_by_id_or_name(self, query: str) -> Optional[Dict[str, Any]]:
        if not self.is_connected:
            self._connect()
        q = query.strip()
        # Direct ID or airport code match
        loc = self.locations_collection.find_one({
            "$or": [
                {"location_id": q.upper()},
                {"airport_code": q.upper()}
            ]
        }, {"_id": 0})
        if loc:
            return loc

        # Case-insensitive city / name match
        loc = self.locations_collection.find_one({
            "$or": [
                {"city": {"$regex": q, "$options": "i"}},
                {"airport_name": {"$regex": q, "$options": "i"}},
                {"country": {"$regex": q, "$options": "i"}}
            ]
        }, {"_id": 0})
        return loc

    def get_location_by_id(self, location_id: str) -> Optional[Dict[str, Any]]:
        return self.get_location_by_id_or_name(location_id)

    def add_location(self, loc_data: Dict[str, Any]) -> str:
        if not self.is_connected:
            self._connect()
        loc_data.setdefault("location_id", f"LOC-{loc_data.get('airport_code', 'GEN').upper()}")
        loc_data["created_at"] = datetime.utcnow()
        loc_data["updated_at"] = datetime.utcnow()
        self.locations_collection.update_one(
            {"location_id": loc_data["location_id"]},
            {"$set": loc_data},
            upsert=True
        )
        return loc_data["location_id"]

    def delete_location(self, location_id: str) -> bool:
        if not self.is_connected:
            self._connect()
        res = self.locations_collection.delete_one({"location_id": location_id})
        # Cascade delete hotels and rooms
        self.hotels_collection.delete_many({"location_id": location_id})
        self.rooms_collection.delete_many({"location_id": location_id})
        return res.deleted_count > 0

    # ==============================================================
    # HOTELS MANAGEMENT
    # ==============================================================
    def get_all_hotels(self, location_id: Optional[str] = None) -> List[Dict[str, Any]]:
        if not self.is_connected:
            self._connect()
        filter_query = {"location_id": location_id} if location_id else {}
        return list(self.hotels_collection.find(filter_query, {"_id": 0}))

    def get_hotel_by_id_or_name(self, query: str, location_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        if not self.is_connected:
            self._connect()
        q = query.strip()
        filter_base = {"location_id": location_id} if location_id else {}

        # Check by hotel_id
        doc = self.hotels_collection.find_one({**filter_base, "hotel_id": q.upper()}, {"_id": 0})
        if doc:
            return doc

        # Check by name regex
        doc = self.hotels_collection.find_one({
            **filter_base,
            "name": {"$regex": q, "$options": "i"}
        }, {"_id": 0})
        return doc

    def get_hotel_by_id(self, hotel_id: str) -> Optional[Dict[str, Any]]:
        return self.get_hotel_by_id_or_name(hotel_id)

    def add_hotel(self, hotel_data: Dict[str, Any]) -> str:
        if not self.is_connected:
            self._connect()
        if not hotel_data.get("hotel_id"):
            loc_code = hotel_data.get("location_id", "LOC").replace("LOC-", "")
            hotel_data["hotel_id"] = f"HTL-{loc_code}-{uuid.uuid4().hex[:4].upper()}"
        hotel_data["created_at"] = datetime.utcnow()
        hotel_data["updated_at"] = datetime.utcnow()
        self.hotels_collection.update_one(
            {"hotel_id": hotel_data["hotel_id"]},
            {"$set": hotel_data},
            upsert=True
        )
        # Seed standard rooms for this new hotel if none exist
        if self.rooms_collection.count_documents({"hotel_id": hotel_data["hotel_id"]}) == 0:
            for r in DEFAULT_ROOMS_TEMPLATE:
                doc = dict(r)
                doc["hotel_id"] = hotel_data["hotel_id"]
                doc["hotel_name"] = hotel_data["name"]
                doc["location_id"] = hotel_data.get("location_id", "")
                doc["available_rooms"] = doc["total_rooms"]
                doc["created_at"] = datetime.utcnow()
                doc["updated_at"] = datetime.utcnow()
                self.rooms_collection.insert_one(doc)
        return hotel_data["hotel_id"]

    def delete_hotel(self, hotel_id: str) -> bool:
        if not self.is_connected:
            self._connect()
        res = self.hotels_collection.delete_one({"hotel_id": hotel_id})
        self.rooms_collection.delete_many({"hotel_id": hotel_id})
        return res.deleted_count > 0

    # ==============================================================
    # ROOMS & INVENTORY MANAGEMENT
    # ==============================================================
    def get_all_rooms(self, hotel_id: Optional[str] = None) -> List[Dict[str, Any]]:
        if not self.is_connected:
            self._connect()
        filter_query = {"hotel_id": hotel_id} if hotel_id else {}
        rooms = list(self.rooms_collection.find(filter_query, {"_id": 0}))
        # Fallback to general rooms if none found for hotel_id
        if not rooms and hotel_id:
            rooms = list(self.rooms_collection.find({}, {"_id": 0})[:5])
        return rooms

    def get_room_by_id_or_name(self, identifier: str, hotel_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        if not self.is_connected:
            self._connect()
        q = identifier.strip()
        filter_base = {"hotel_id": hotel_id} if hotel_id else {}

        # 1. By exact room_id
        room = self.rooms_collection.find_one({**filter_base, "room_id": q.upper()}, {"_id": 0})
        if room:
            return room

        # 2. By name regex
        room = self.rooms_collection.find_one({
            **filter_base,
            "name": {"$regex": q, "$options": "i"}
        }, {"_id": 0})
        if room:
            return room

        # 3. If hotel filter had no match, try global room search
        if hotel_id:
            return self.get_room_by_id_or_name(identifier, hotel_id=None)

        return None

    def add_or_update_room(self, room_data: Dict[str, Any]) -> str:
        """Add new room category or update total inventory count."""
        if not self.is_connected:
            self._connect()
        if not room_data.get("room_id"):
            room_data["room_id"] = f"RM-{uuid.uuid4().hex[:6].upper()}"
        
        room_data["total_rooms"] = int(room_data.get("total_rooms", 5))
        room_data["available_rooms"] = room_data["total_rooms"]
        room_data["updated_at"] = datetime.utcnow()

        filter_q = {"room_id": room_data["room_id"]}
        if room_data.get("hotel_id"):
            filter_q["hotel_id"] = room_data["hotel_id"]

        self.rooms_collection.update_one(filter_q, {"$set": room_data}, upsert=True)
        return room_data["room_id"]

    def update_room_count(self, room_id: str, new_count: int, hotel_id: Optional[str] = None) -> bool:
        """Control Panel action: Adjust total room count for a room."""
        if not self.is_connected:
            self._connect()
        filter_q = {"room_id": room_id}
        if hotel_id:
            filter_q["hotel_id"] = hotel_id
        res = self.rooms_collection.update_many(
            filter_q,
            {"$set": {"total_rooms": int(new_count), "available_rooms": int(new_count), "updated_at": datetime.utcnow()}}
        )
        return res.modified_count > 0


    def delete_room(self, room_id: str, hotel_id: Optional[str] = None) -> bool:
        if not self.is_connected:
            self._connect()
        filter_q = {"room_id": room_id}
        if hotel_id:
            filter_q["hotel_id"] = hotel_id
        res = self.rooms_collection.delete_many(filter_q)
        return res.deleted_count > 0

    # ==============================================================
    # DATE-SPECIFIC ROOM AVAILABILITY CHECKER
    # ==============================================================
    def check_room_availability_for_dates(
        self,
        hotel_id: Optional[str],
        room_id: str,
        checkin_date: str,
        checkout_date: str,
        requested_count: int = 1
    ) -> Tuple[bool, int, str]:
        """
        Check if room has available count for the date range [checkin_date, checkout_date).
        Returns: (is_available, remaining_count, message)
        """
        if not self.is_connected:
            self._connect()

        # Fetch room definition
        room = self.get_room_by_id_or_name(room_id, hotel_id=hotel_id)
        if not room:
            return False, 0, f"Room type '{room_id}' not found."

        total_physical_rooms = int(room.get("total_rooms", 5))

        # Find overlapping confirmed bookings
        # Condition: checkin < requested_checkout AND checkout > requested_checkin
        overlap_query: Dict[str, Any] = {
            "room_id": room["room_id"],
            "status": "confirmed",
            "checkin_date": {"$lt": checkout_date},
            "checkout_date": {"$gt": checkin_date}
        }
        if hotel_id:
            overlap_query["hotel_id"] = hotel_id

        overlapping_bookings = list(self.bookings_collection.find(overlap_query))
        total_booked_on_dates = sum(int(b.get("rooms_count", 1)) for b in overlapping_bookings)

        remaining_rooms = max(0, total_physical_rooms - total_booked_on_dates)

        if remaining_rooms <= 0:
            return (
                False,
                0,
                f"⚠️ The **{room['name']}** is fully booked from **{checkin_date}** to **{checkout_date}** (0 rooms available)."
            )

        if remaining_rooms < requested_count:
            return (
                False,
                remaining_rooms,
                f"⚠️ Only **{remaining_rooms}** {room['name']} room(s) available from **{checkin_date}** to **{checkout_date}**, but you requested **{requested_count}**."
            )

        return (
            True,
            remaining_rooms,
            f"✅ {remaining_rooms} room(s) available for {room['name']} on these dates."
        )

    # ==============================================================
    # BOOKINGS MANAGEMENT & SEARCH
    # ==============================================================
    def create_booking(self, booking_data: Dict[str, Any]) -> str:
        if not self.is_connected:
            self._connect()
        booking_data["created_at"] = datetime.utcnow().isoformat()
        doc_to_insert = dict(booking_data)
        result = self.bookings_collection.insert_one(doc_to_insert)
        return str(result.inserted_id)

    def get_all_bookings(self) -> List[Dict[str, Any]]:
        if not self.is_connected:
            self._connect()
        return list(self.bookings_collection.find({}, {"_id": 0}).sort("created_at", -1))

    def get_booking_by_id(self, booking_id: str) -> Optional[Dict[str, Any]]:
        if not self.is_connected:
            self._connect()
        return self.bookings_collection.find_one(
            {"booking_id": {"$regex": f"^{booking_id.strip()}$", "$options": "i"}},
            {"_id": 0}
        )

    def find_booking_by_query(self, query: str) -> Optional[Dict[str, Any]]:
        """Search booking by Reference Code, Guest Name, Company Name, or Email."""
        if not self.is_connected:
            self._connect()
        q = query.strip()
        if not q:
            return None

        # Look for BK-XXXXXX pattern
        bk_match = re.search(r'\b(BK-[A-Z0-9]{4,8})\b', q, flags=re.I)
        if bk_match:
            return self.get_booking_by_id(bk_match.group(1))

        # Check by email
        email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', q)
        if email_match:
            res = self.bookings_collection.find_one(
                {"contact_email": {"$regex": email_match.group(0), "$options": "i"}},
                {"_id": 0}
            )
            if res:
                return res

        # Check by guest_name or company_name
        res = self.bookings_collection.find_one({
            "$or": [
                {"guest_name": {"$regex": q, "$options": "i"}},
                {"company_name": {"$regex": q, "$options": "i"}},
                {"booking_id": {"$regex": q, "$options": "i"}}
            ]
        }, {"_id": 0})
        return res

    def delete_booking(self, booking_id: str) -> bool:
        """Delete a reservation from MongoDB by booking ID."""
        if not self.is_connected:
            self._connect()
        res = self.bookings_collection.delete_one({
            "booking_id": {"$regex": f"^{booking_id.strip()}$", "$options": "i"}
        })
        return res.deleted_count > 0

    # ==============================================================
    # SESSION MANAGEMENT
    # ==============================================================
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        if not self.is_connected:
            self._connect()
        return self.sessions_collection.find_one({"session_id": session_id}, {"_id": 0})

    def save_session(self, session_id: str, session_data: Dict[str, Any]):
        if not self.is_connected:
            self._connect()
        session_data["updated_at"] = datetime.utcnow().isoformat()
        self.sessions_collection.replace_one(
            {"session_id": session_id},
            session_data,
            upsert=True
        )

db_manager = DatabaseManager()
