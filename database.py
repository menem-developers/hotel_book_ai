from pymongo import MongoClient
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from config import settings
import logging
import uuid
import re

try:
    import dns.resolver
    dns.resolver.default_resolver = dns.resolver.Resolver()
    dns.resolver.default_resolver.lifetime = 6.0
    dns.resolver.default_resolver.timeout = 5.0
except Exception:
    pass

logger = logging.getLogger(__name__)

from seed_usa_airports import USA_LOCATIONS, USA_HOTELS, USA_ROOMS_TEMPLATE

DEFAULT_LOCATIONS = USA_LOCATIONS
DEFAULT_HOTELS = USA_HOTELS
DEFAULT_ROOMS_TEMPLATE = USA_ROOMS_TEMPLATE

class DatabaseManager:
    def __init__(self):
        self.client: Optional[MongoClient] = None
        self.db = None
        self._last_connect_attempt = 0.0
        self._in_memory_sessions: Dict[str, Any] = {}
        self._in_memory_bookings: Dict[str, Any] = {}
        self._connect()

    def _connect(self):
        import time
        now = time.time()
        if now - self._last_connect_attempt < 30.0:
            return
        self._last_connect_attempt = now
        try:
            self.client = MongoClient(
                settings.MONGODB_URI,
                serverSelectionTimeoutMS=1000,
                connectTimeoutMS=1000
            )
            self.db = self.client[settings.MONGODB_DB_NAME]
            self.client.admin.command('ping')
            logger.info("Successfully connected to MongoDB (%s)", settings.MONGODB_DB_NAME)
        except Exception as e:
            logger.warning("MongoDB connection attempt warning: %s", e)
            self.client = None
            self.db = None

    @property
    def is_connected(self) -> bool:
        return bool(self.client is not None and self.db is not None)

    @property
    def locations_collection(self):
        return self.db["locations"] if self.db is not None else None

    @property
    def hotels_collection(self):
        return self.db["hotels"] if self.db is not None else None

    @property
    def rooms_collection(self):
        return self.db["rooms"] if self.db is not None else None

    @property
    def sessions_collection(self):
        return self.db["chat_sessions"] if self.db is not None else None

    @property
    def bookings_collection(self):
        return self.db["bookings"] if self.db is not None else None

    def seed_database(self, force: bool = False, clear_bookings: bool = False) -> Dict[str, int]:
        """Seed default USA locations, hotels, and rooms into separate MongoDB collections."""
        if not self.is_connected:
            self._connect()

        loc_col = self.locations_collection
        hotel_col = self.hotels_collection
        room_col = self.rooms_collection
        book_col = self.bookings_collection
        sess_col = self.sessions_collection

        # Check if database needs USA migration
        has_usa = loc_col.find_one({"country": "United States"}) is not None
        should_reseed = force or (not has_usa)

        if should_reseed or clear_bookings:
            logger.info("Purging old records and seeding fresh USA airports, hotels, and rooms...")
            loc_col.delete_many({})
            hotel_col.delete_many({})
            room_col.delete_many({})
            book_col.delete_many({})
            sess_col.delete_many({})

            loc_docs = [dict(loc, created_at=datetime.utcnow(), updated_at=datetime.utcnow()) for loc in DEFAULT_LOCATIONS]
            if loc_docs:
                loc_col.insert_many(loc_docs)

            hotel_docs = [dict(h, created_at=datetime.utcnow(), updated_at=datetime.utcnow()) for h in DEFAULT_HOTELS]
            if hotel_docs:
                hotel_col.insert_many(hotel_docs)

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
            if room_docs:
                room_col.insert_many(room_docs)
        else:
            if loc_col.count_documents({}) == 0:
                loc_docs = [dict(loc, created_at=datetime.utcnow(), updated_at=datetime.utcnow()) for loc in DEFAULT_LOCATIONS]
                loc_col.insert_many(loc_docs)
            if hotel_col.count_documents({}) == 0:
                hotel_docs = [dict(h, created_at=datetime.utcnow(), updated_at=datetime.utcnow()) for h in DEFAULT_HOTELS]
                hotel_col.insert_many(hotel_docs)
            if room_col.count_documents({}) == 0:
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
                if room_docs:
                    room_col.insert_many(room_docs)

        return {
            "locations": loc_col.count_documents({}),
            "hotels": hotel_col.count_documents({}),
            "rooms": room_col.count_documents({}),
            "bookings": book_col.count_documents({})
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
            return list(DEFAULT_LOCATIONS)
        try:
            return list(self.locations_collection.find({}, {"_id": 0}))
        except Exception:
            return list(DEFAULT_LOCATIONS)

    def get_location_by_id_or_name(self, query: str) -> Optional[Dict[str, Any]]:
        q = query.strip().upper()
        if not self.is_connected:
            for l in DEFAULT_LOCATIONS:
                if l.get("location_id") == q or l.get("airport_code") == q:
                    return l
                if query.lower() in l.get("city", "").lower() or query.lower() in l.get("airport_name", "").lower():
                    return l
            return None
        try:
            # Direct ID or airport code match
            loc = self.locations_collection.find_one({
                "$or": [
                    {"location_id": q},
                    {"airport_code": q}
                ]
            }, {"_id": 0})
            if loc:
                return loc

            # Case-insensitive city / name match
            loc = self.locations_collection.find_one({
                "$or": [
                    {"city": {"$regex": query.strip(), "$options": "i"}},
                    {"airport_name": {"$regex": query.strip(), "$options": "i"}},
                    {"country": {"$regex": query.strip(), "$options": "i"}}
                ]
            }, {"_id": 0})
            return loc
        except Exception:
            for l in DEFAULT_LOCATIONS:
                if l.get("location_id") == q or l.get("airport_code") == q:
                    return l
                if query.lower() in l.get("city", "").lower() or query.lower() in l.get("airport_name", "").lower():
                    return l
            return None

    def get_location_by_id(self, location_id: str) -> Optional[Dict[str, Any]]:
        return self.get_location_by_id_or_name(location_id)

    def add_location(self, loc_data: Dict[str, Any]) -> str:
        if not self.is_connected:
            return loc_data.get("location_id", "LOC-GEN")
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
            return True
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
            if location_id:
                return [h for h in DEFAULT_HOTELS if h.get("location_id") == location_id]
            return list(DEFAULT_HOTELS)
        try:
            filter_query = {"location_id": location_id} if location_id else {}
            hotels = list(self.hotels_collection.find(filter_query, {"_id": 0}))
            if not hotels:
                if location_id:
                    return [h for h in DEFAULT_HOTELS if h.get("location_id") == location_id]
                return list(DEFAULT_HOTELS)
            return hotels
        except Exception:
            if location_id:
                return [h for h in DEFAULT_HOTELS if h.get("location_id") == location_id]
            return list(DEFAULT_HOTELS)

    def get_hotel_by_id_or_name(self, query: str, location_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        q = query.strip().lower()
        if not self.is_connected:
            for h in DEFAULT_HOTELS:
                if location_id and h.get("location_id") != location_id:
                    continue
                if h.get("hotel_id", "").lower() == q or q in h.get("name", "").lower():
                    return h
                for al in h.get("aliases", []):
                    if al.lower() in q or q in al.lower():
                        return h
            return None
        try:
            filter_base = {"location_id": location_id} if location_id else {}

            # Check by hotel_id
            doc = self.hotels_collection.find_one({**filter_base, "hotel_id": query.strip().upper()}, {"_id": 0})
            if doc:
                return doc

            # Check by name regex
            doc = self.hotels_collection.find_one({
                **filter_base,
                "name": {"$regex": query.strip(), "$options": "i"}
            }, {"_id": 0})
            if doc:
                return doc

            for h in DEFAULT_HOTELS:
                if location_id and h.get("location_id") != location_id:
                    continue
                if h.get("hotel_id", "").lower() == q or q in h.get("name", "").lower():
                    return h
                for al in h.get("aliases", []):
                    if al.lower() in q or q in al.lower():
                        return h
            return None
        except Exception:
            for h in DEFAULT_HOTELS:
                if location_id and h.get("location_id") != location_id:
                    continue
                if h.get("hotel_id", "").lower() == q or q in h.get("name", "").lower():
                    return h
            return None

    def get_hotel_by_id(self, hotel_id: str) -> Optional[Dict[str, Any]]:
        return self.get_hotel_by_id_or_name(hotel_id)
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
            rooms = []
            for r in DEFAULT_ROOMS_TEMPLATE:
                doc = dict(r)
                doc["hotel_id"] = hotel_id
                doc["available_rooms"] = doc.get("total_rooms", 5)
                rooms.append(doc)
            return rooms
        try:
            filter_query = {"hotel_id": hotel_id} if hotel_id else {}
            rooms = list(self.rooms_collection.find(filter_query, {"_id": 0}))
            if not rooms:
                rooms = []
                for r in DEFAULT_ROOMS_TEMPLATE:
                    doc = dict(r)
                    doc["hotel_id"] = hotel_id
                    doc["available_rooms"] = doc.get("total_rooms", 5)
                    rooms.append(doc)
            return rooms
        except Exception:
            rooms = []
            for r in DEFAULT_ROOMS_TEMPLATE:
                doc = dict(r)
                doc["hotel_id"] = hotel_id
                doc["available_rooms"] = doc.get("total_rooms", 5)
                rooms.append(doc)
            return rooms

    def get_room_by_id_or_name(self, identifier: str, hotel_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        q = identifier.strip().lower()
        if not self.is_connected:
            for r in DEFAULT_ROOMS_TEMPLATE:
                if r.get("room_id", "").lower() == q or q in r.get("name", "").lower():
                    doc = dict(r)
                    doc["hotel_id"] = hotel_id
                    doc["available_rooms"] = doc.get("total_rooms", 5)
                    return doc
            return None
        try:
            filter_base = {"hotel_id": hotel_id} if hotel_id else {}

            # 1. By exact room_id
            room = self.rooms_collection.find_one({**filter_base, "room_id": identifier.strip().upper()}, {"_id": 0})
            if room:
                return room

            # 2. By name regex
            room = self.rooms_collection.find_one({
                **filter_base,
                "name": {"$regex": identifier.strip(), "$options": "i"}
            }, {"_id": 0})
            if room:
                return room

            # 3. If hotel filter had no match, try global room search
            if hotel_id:
                return self.get_room_by_id_or_name(identifier, hotel_id=None)

            return None
        except Exception:
            for r in DEFAULT_ROOMS_TEMPLATE:
                if r.get("room_id", "").lower() == q or q in r.get("name", "").lower():
                    doc = dict(r)
                    doc["hotel_id"] = hotel_id
                    doc["available_rooms"] = doc.get("total_rooms", 5)
                    return doc
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
            room = self.get_room_by_id_or_name(room_id, hotel_id=hotel_id)
            if not room:
                return False, 0, f"Room type '{room_id}' not found."
            return True, room.get("total_rooms", 5), "Room available"
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
            return self._in_memory_sessions.get(session_id)
        try:
            doc = self.sessions_collection.find_one({"session_id": session_id}, {"_id": 0})
            if doc:
                return doc
            return self._in_memory_sessions.get(session_id)
        except Exception:
            return self._in_memory_sessions.get(session_id)

    def save_session(self, session_id: str, session_data: Dict[str, Any]):
        self._in_memory_sessions[session_id] = session_data
        if not self.is_connected:
            return
        try:
            session_data["updated_at"] = datetime.utcnow().isoformat()
            self.sessions_collection.replace_one(
                {"session_id": session_id},
                session_data,
                upsert=True
            )
        except Exception:
            pass

db_manager = DatabaseManager()
