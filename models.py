from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    message: str

class ChatResponse(BaseModel):
    session_id: str
    reply: str
    current_step: str
    state: Dict[str, Any]
    quick_replies: List[str] = []
    booking: Optional[Dict[str, Any]] = None
    options: Optional[Dict[str, Any]] = None

class ResetRequest(BaseModel):
    session_id: Optional[str] = None

class LocationModel(BaseModel):
    location_id: Optional[str] = None
    city: str
    country: str
    airport_name: str
    airport_code: str
    description: Optional[str] = None

class HotelModel(BaseModel):
    hotel_id: Optional[str] = None
    location_id: str
    name: str
    address: str
    description: Optional[str] = None
    rating: float = 4.8
    image_url: Optional[str] = None

class RoomModel(BaseModel):
    room_id: Optional[str] = None
    hotel_id: Optional[str] = None
    name: str
    category: str
    description: Optional[str] = None
    price_per_night: float
    capacity_per_room: int = 2
    total_rooms: int = 5
    available_rooms: Optional[int] = None
    amenities: List[str] = []
    badge: Optional[str] = None
    image_url: Optional[str] = None

class RoomCountUpdateRequest(BaseModel):
    room_id: str
    new_count: int
    hotel_id: Optional[str] = None

class AvailabilityCheckRequest(BaseModel):
    hotel_id: Optional[str] = None
    room_id: str
    checkin_date: str
    checkout_date: str
    requested_count: int = 1

class BookingModel(BaseModel):
    booking_id: str
    session_id: str
    location_id: Optional[str] = None
    location_city: Optional[str] = None
    airport_code: Optional[str] = None
    hotel_id: str
    hotel_name: str
    guest_type: str  # "individual" or "company"
    guest_name: str
    company_name: Optional[str] = None
    total_members: int
    rooms_count: int
    room_id: str
    room_name: str
    checkin_date: str
    checkout_date: str
    total_nights: int
    price_per_night: float
    total_amount: float
    airport_pickup: bool = False
    airport_drop: bool = False
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None
    special_requests: Optional[str] = None
    status: str = "confirmed"
    created_at: Optional[str] = None
